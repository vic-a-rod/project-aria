from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.availability import AvailabilityInterval
from app.domain.scheduling import (
    ScheduleItem,
    ScheduleProposal,
    ScheduleRiskCode,
    ScheduleStrategy,
    simulate_schedules,
)


class SustainableMode(StrEnum):
    NORMAL = "normal"
    LIGHTER = "lighter"
    FOCUS = "focus"


class WorkloadWarningCode(StrEnum):
    OVERLOAD = "overload"
    DEADLINE_AT_RISK = "deadline_at_risk"


class DeferralReason(StrEnum):
    FOCUS_SCOPE = "focus_scope"
    CAPACITY = "capacity"


@dataclass(frozen=True)
class WorkloadPolicy:
    normal_daily_capacity_minutes: int = 360
    lighter_daily_capacity_minutes: int = 180
    reserve_unscheduled_minutes: int = 60


@dataclass(frozen=True)
class WorkloadModeState:
    mode: SustainableMode
    expires_at: datetime
    focus_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkloadDeferral:
    reference: str
    reason: DeferralReason
    detail: str


@dataclass(frozen=True)
class WorkloadWarning:
    code: WorkloadWarningCode
    reference: str | None
    detail: str


@dataclass(frozen=True)
class DailyWorkload:
    day: date
    capacity_minutes: int
    scheduled_minutes: int
    unscheduled_minutes: int


@dataclass(frozen=True)
class SustainableWorkloadPlan:
    effective_mode: SustainableMode
    schedule: ScheduleProposal
    daily_workload: tuple[DailyWorkload, ...]
    deferrals: tuple[WorkloadDeferral, ...]
    warnings: tuple[WorkloadWarning, ...]


def plan_sustainable_workload(
    *,
    items: tuple[ScheduleItem, ...] | list[ScheduleItem],
    hard_free_intervals: tuple[AvailabilityInterval, ...]
    | list[AvailabilityInterval],
    protected_intervals: tuple[AvailabilityInterval, ...]
    | list[AvailabilityInterval] = (),
    now: datetime,
    time_zone: str,
    mode_state: WorkloadModeState | None = None,
    policy: WorkloadPolicy | None = None,
) -> SustainableWorkloadPlan:
    """Create a bounded plan that treats rest and unscheduled time as valid."""
    _validate_aware(now, "now")
    try:
        zone = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("time_zone must be a valid IANA time zone") from error
    configured = policy or WorkloadPolicy()
    _validate_policy(configured)
    effective_mode = _effective_mode(mode_state, now)
    base_free = tuple(hard_free_intervals)
    free = _subtract_intervals(base_free, protected_intervals)
    daily_limit = (
        configured.lighter_daily_capacity_minutes
        if effective_mode == SustainableMode.LIGHTER
        else configured.normal_daily_capacity_minutes
    )
    capacity_intervals, daily_capacity, daily_available = _capacity_intervals(
        free,
        zone=zone,
        daily_limit=daily_limit,
        reserve=configured.reserve_unscheduled_minutes,
    )

    normalized_items = tuple(items)
    horizon_end = max(
        (interval.end_at.astimezone(UTC) for interval in base_free),
        default=now.astimezone(UTC),
    )
    selected, deferrals = _select_items(
        normalized_items,
        mode=effective_mode,
        mode_state=mode_state,
        horizon_end=horizon_end,
    )
    schedule = simulate_schedules(
        items=selected,
        hard_free_intervals=capacity_intervals,
        now=now,
        strategies=(ScheduleStrategy.DEADLINE_FIRST,),
    )[0]

    deferrals.extend(
        WorkloadDeferral(
            reference=reference,
            reason=DeferralReason.CAPACITY,
            detail="The item remains unscheduled within the sustainable capacity limit.",
        )
        for reference in schedule.unscheduled_references
    )
    warnings = _warnings(
        selected,
        schedule,
        capacity_minutes=sum(daily_capacity.values()),
        horizon_end=horizon_end,
    )
    daily_workload = _daily_workload(
        schedule,
        daily_capacity=daily_capacity,
        daily_available=daily_available,
        zone=zone,
    )
    return SustainableWorkloadPlan(
        effective_mode=effective_mode,
        schedule=schedule,
        daily_workload=tuple(daily_workload),
        deferrals=tuple(sorted(deferrals, key=lambda item: (item.reference, item.reason.value))),
        warnings=tuple(warnings),
    )


def _effective_mode(
    state: WorkloadModeState | None, now: datetime
) -> SustainableMode:
    if state is None:
        return SustainableMode.NORMAL
    _validate_aware(state.expires_at, "mode expires_at")
    if state.expires_at <= now:
        return SustainableMode.NORMAL
    if state.mode == SustainableMode.FOCUS and not state.focus_references:
        raise ValueError("focus mode requires focus_references")
    return state.mode


def _validate_policy(policy: WorkloadPolicy) -> None:
    if policy.normal_daily_capacity_minutes <= 0:
        raise ValueError("normal daily capacity must be positive")
    if not 0 < policy.lighter_daily_capacity_minutes <= policy.normal_daily_capacity_minutes:
        raise ValueError("lighter daily capacity must be positive and no greater than normal")
    if policy.reserve_unscheduled_minutes < 0:
        raise ValueError("reserve_unscheduled_minutes must not be negative")


def _select_items(
    items: tuple[ScheduleItem, ...],
    *,
    mode: SustainableMode,
    mode_state: WorkloadModeState | None,
    horizon_end: datetime,
) -> tuple[tuple[ScheduleItem, ...], list[WorkloadDeferral]]:
    if mode != SustainableMode.FOCUS or mode_state is None:
        return items, []
    focus = set(mode_state.focus_references)
    selected: list[ScheduleItem] = []
    deferrals: list[WorkloadDeferral] = []
    for item in items:
        deadline_protected = item.due_at is not None and item.due_at.astimezone(UTC) <= horizon_end
        if item.is_locked or item.reference in focus or deadline_protected:
            selected.append(item)
            continue
        deferrals.append(
            WorkloadDeferral(
                reference=item.reference,
                reason=DeferralReason.FOCUS_SCOPE,
                detail="Deferred outside the temporary focus scope without risking a deadline.",
            )
        )
    return tuple(selected), deferrals


def _capacity_intervals(
    intervals: tuple[AvailabilityInterval, ...],
    *,
    zone: ZoneInfo,
    daily_limit: int,
    reserve: int,
) -> tuple[
    tuple[AvailabilityInterval, ...],
    dict[date, int],
    dict[date, int],
]:
    split = _split_by_local_day(intervals, zone)
    totals: dict[date, int] = {}
    for interval in split:
        day = interval.start_at.astimezone(zone).date()
        totals[day] = totals.get(day, 0) + _minutes(interval)
    capacities = {
        day: max(0, min(daily_limit, total - reserve)) for day, total in totals.items()
    }
    remaining = dict(capacities)
    bounded: list[AvailabilityInterval] = []
    for interval in split:
        day = interval.start_at.astimezone(zone).date()
        allowed = min(remaining[day], _minutes(interval))
        if allowed > 0:
            bounded.append(
                AvailabilityInterval(
                    interval.start_at,
                    interval.start_at + timedelta(minutes=allowed),
                )
            )
            remaining[day] -= allowed
    return tuple(bounded), capacities, totals


def _split_by_local_day(
    intervals: tuple[AvailabilityInterval, ...], zone: ZoneInfo
) -> list[AvailabilityInterval]:
    split: list[AvailabilityInterval] = []
    for interval in intervals:
        cursor = interval.start_at.astimezone(UTC)
        end = interval.end_at.astimezone(UTC)
        while cursor < end:
            local = cursor.astimezone(zone)
            next_day = datetime.combine(
                local.date() + timedelta(days=1), datetime.min.time(), tzinfo=zone
            ).astimezone(UTC)
            boundary = min(end, next_day)
            split.append(AvailabilityInterval(cursor, boundary))
            cursor = boundary
    return split


def _subtract_intervals(
    free_intervals: tuple[AvailabilityInterval, ...] | list[AvailabilityInterval],
    protected_intervals: tuple[AvailabilityInterval, ...] | list[AvailabilityInterval],
) -> tuple[AvailabilityInterval, ...]:
    free = sorted(free_intervals, key=lambda item: (item.start_at, item.end_at))
    protected = sorted(protected_intervals, key=lambda item: (item.start_at, item.end_at))
    for interval in (*free, *protected):
        _validate_aware(interval.start_at, "interval start_at")
        _validate_aware(interval.end_at, "interval end_at")
        if interval.end_at <= interval.start_at:
            raise ValueError("interval end_at must be after start_at")
    result: list[AvailabilityInterval] = []
    for interval in free:
        fragments = [
            AvailabilityInterval(
                interval.start_at.astimezone(UTC), interval.end_at.astimezone(UTC)
            )
        ]
        for blocked in protected:
            blocked_start = blocked.start_at.astimezone(UTC)
            blocked_end = blocked.end_at.astimezone(UTC)
            next_fragments: list[AvailabilityInterval] = []
            for fragment in fragments:
                if blocked_end <= fragment.start_at or blocked_start >= fragment.end_at:
                    next_fragments.append(fragment)
                    continue
                if blocked_start > fragment.start_at:
                    next_fragments.append(AvailabilityInterval(fragment.start_at, blocked_start))
                if blocked_end < fragment.end_at:
                    next_fragments.append(AvailabilityInterval(blocked_end, fragment.end_at))
            fragments = next_fragments
        result.extend(fragments)
    return tuple(result)


def _warnings(
    items: tuple[ScheduleItem, ...],
    schedule: ScheduleProposal,
    *,
    capacity_minutes: int,
    horizon_end: datetime,
) -> list[WorkloadWarning]:
    due_effort = sum(
        item.duration_minutes
        for item in items
        if not item.is_locked
        and item.due_at is not None
        and item.due_at.astimezone(UTC) <= horizon_end
    )
    warnings: list[WorkloadWarning] = []
    if due_effort > capacity_minutes:
        warnings.append(
            WorkloadWarning(
                WorkloadWarningCode.OVERLOAD,
                None,
                (
                    f"Deadline-bound work requires {due_effort} minutes but sustainable "
                    f"capacity is {capacity_minutes} minutes."
                ),
            )
        )
    warnings.extend(
        WorkloadWarning(
            WorkloadWarningCode.DEADLINE_AT_RISK,
            risk.reference,
            risk.detail,
        )
        for risk in schedule.risks
        if risk.code in {ScheduleRiskCode.OVERDUE, ScheduleRiskCode.DEADLINE}
    )
    existing_deadline_warnings = {
        warning.reference
        for warning in warnings
        if warning.code == WorkloadWarningCode.DEADLINE_AT_RISK
    }
    by_reference = {item.reference: item for item in items}
    for reference in schedule.unscheduled_references:
        item = by_reference[reference]
        if (
            reference not in existing_deadline_warnings
            and item.due_at is not None
            and item.due_at.astimezone(UTC) <= horizon_end
        ):
            warnings.append(
                WorkloadWarning(
                    WorkloadWarningCode.DEADLINE_AT_RISK,
                    reference,
                    "Sustainable capacity cannot place this item before its deadline.",
                )
            )
    return sorted(warnings, key=lambda item: (item.code.value, item.reference or ""))


def _daily_workload(
    schedule: ScheduleProposal,
    *,
    daily_capacity: dict[date, int],
    daily_available: dict[date, int],
    zone: ZoneInfo,
) -> list[DailyWorkload]:
    scheduled: dict[date, int] = {day: 0 for day in daily_capacity}
    for placement in schedule.placements:
        if placement.is_locked:
            continue
        day = placement.start_at.astimezone(zone).date()
        scheduled[day] = scheduled.get(day, 0) + int(
            (placement.end_at - placement.start_at).total_seconds() // 60
        )
    return [
        DailyWorkload(
            day,
            capacity,
            scheduled.get(day, 0),
            daily_available[day] - scheduled.get(day, 0),
        )
        for day, capacity in sorted(daily_capacity.items())
    ]


def _minutes(interval: AvailabilityInterval) -> int:
    return int((interval.end_at - interval.start_at).total_seconds() // 60)


def _validate_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
