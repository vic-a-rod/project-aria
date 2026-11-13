from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.domain.availability import (
    AvailabilityConflict,
    AvailabilityInterval,
    ConflictKind,
)


class ScheduleStrategy(StrEnum):
    PRIORITY_FIRST = "priority_first"
    DEADLINE_FIRST = "deadline_first"


class ScheduleSource(StrEnum):
    LOCAL = "local"
    EXTERNAL = "external"


class ScheduleChangeKind(StrEnum):
    ADDED = "added"
    MOVED = "moved"
    UNCHANGED = "unchanged"
    UNSCHEDULED = "unscheduled"


class ScheduleRiskCode(StrEnum):
    OVERDUE = "overdue"
    DEADLINE = "deadline_risk"
    CAPACITY = "insufficient_capacity"
    LOCKED_CONFLICT = "locked_conflict"


class ScheduleRiskSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ScheduleItem:
    reference: str
    title: str
    duration_minutes: int
    priority_score: float
    due_at: datetime | None
    is_fixed: bool = False
    source: ScheduleSource = ScheduleSource.LOCAL
    current_start_at: datetime | None = None
    current_end_at: datetime | None = None

    @property
    def is_locked(self) -> bool:
        return self.is_fixed or self.source == ScheduleSource.EXTERNAL


@dataclass(frozen=True)
class SchedulePlacement:
    reference: str
    title: str
    start_at: datetime
    end_at: datetime
    is_locked: bool


@dataclass(frozen=True)
class ScheduleChange:
    reference: str
    kind: ScheduleChangeKind
    before_start_at: datetime | None
    before_end_at: datetime | None
    after_start_at: datetime | None
    after_end_at: datetime | None


@dataclass(frozen=True)
class ScheduleRisk:
    code: ScheduleRiskCode
    severity: ScheduleRiskSeverity
    reference: str | None
    detail: str


@dataclass(frozen=True)
class ScheduleProposal:
    strategy: ScheduleStrategy
    placements: tuple[SchedulePlacement, ...]
    changes: tuple[ScheduleChange, ...]
    risks: tuple[ScheduleRisk, ...]
    unscheduled_references: tuple[str, ...]
    scheduled_minutes: int


def simulate_schedules(
    *,
    items: tuple[ScheduleItem, ...] | list[ScheduleItem],
    hard_free_intervals: tuple[AvailabilityInterval, ...]
    | list[AvailabilityInterval],
    hard_conflicts: tuple[AvailabilityConflict, ...]
    | list[AvailabilityConflict] = (),
    now: datetime,
    strategies: tuple[ScheduleStrategy, ...] = (
        ScheduleStrategy.PRIORITY_FIRST,
        ScheduleStrategy.DEADLINE_FIRST,
    ),
) -> tuple[ScheduleProposal, ...]:
    """Return alternative immutable schedules without changing input records."""
    _validate_aware(now, "now")
    normalized_items = tuple(items)
    if len({item.reference for item in normalized_items}) != len(normalized_items):
        raise ValueError("schedule item references must be unique")
    for item in normalized_items:
        _validate_item(item)
    free = _normalize_free_intervals(hard_free_intervals)
    proposals = [
        _simulate(
            strategy=strategy,
            items=normalized_items,
            free_intervals=free,
            hard_conflicts=tuple(hard_conflicts),
            now=now.astimezone(UTC),
        )
        for strategy in dict.fromkeys(strategies)
    ]
    return tuple(proposals)


def _simulate(
    *,
    strategy: ScheduleStrategy,
    items: tuple[ScheduleItem, ...],
    free_intervals: tuple[AvailabilityInterval, ...],
    hard_conflicts: tuple[AvailabilityConflict, ...],
    now: datetime,
) -> ScheduleProposal:
    placements: list[SchedulePlacement] = []
    risks = _locked_conflict_risks(items, hard_conflicts)
    for item in items:
        if not item.is_locked:
            continue
        if item.current_start_at is None or item.current_end_at is None:
            risks.append(
                ScheduleRisk(
                    ScheduleRiskCode.CAPACITY,
                    ScheduleRiskSeverity.CRITICAL,
                    item.reference,
                    "A locked commitment has no persisted placement and cannot be moved.",
                )
            )
            continue
        placements.append(_placement(item, item.current_start_at, item.current_end_at))

    flexible_items = sorted(
        (item for item in items if not item.is_locked),
        key=lambda item: _item_sort_key(item, strategy),
    )
    available = list(free_intervals)
    unscheduled: list[str] = []
    for item in flexible_items:
        if item.due_at is not None and item.due_at.astimezone(UTC) <= now:
            risks.append(
                ScheduleRisk(
                    ScheduleRiskCode.OVERDUE,
                    ScheduleRiskSeverity.CRITICAL,
                    item.reference,
                    "The responsibility is already overdue.",
                )
            )
        slot = _allocate(
            available,
            duration=timedelta(minutes=item.duration_minutes),
            latest_end=item.due_at.astimezone(UTC) if item.due_at else None,
        )
        if slot is None:
            unscheduled.append(item.reference)
            due_within_window = (
                item.due_at is not None
                and bool(free_intervals)
                and item.due_at.astimezone(UTC) <= free_intervals[-1].end_at
            )
            risks.append(
                ScheduleRisk(
                    (
                        ScheduleRiskCode.DEADLINE
                        if due_within_window
                        else ScheduleRiskCode.CAPACITY
                    ),
                    (
                        ScheduleRiskSeverity.CRITICAL
                        if due_within_window
                        else ScheduleRiskSeverity.WARNING
                    ),
                    item.reference,
                    (
                        "No available interval can finish this responsibility before its deadline."
                        if due_within_window
                        else "No available interval is long enough for this responsibility."
                    ),
                )
            )
            continue
        start, end = slot
        placements.append(_placement(item, start, end))

    placements.sort(key=lambda item: (item.start_at, item.end_at, item.reference))
    changes = tuple(_changes(items, placements, set(unscheduled)))
    risks.sort(
        key=lambda item: (
            0 if item.severity == ScheduleRiskSeverity.CRITICAL else 1,
            item.code.value,
            item.reference or "",
        )
    )
    return ScheduleProposal(
        strategy=strategy,
        placements=tuple(placements),
        changes=changes,
        risks=tuple(risks),
        unscheduled_references=tuple(unscheduled),
        scheduled_minutes=sum(
            item.duration_minutes for item in flexible_items if item.reference not in unscheduled
        ),
    )


def _validate_item(item: ScheduleItem) -> None:
    if not item.reference.strip():
        raise ValueError("schedule item reference must not be blank")
    if item.duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")
    if not 0 <= item.priority_score <= 100:
        raise ValueError("priority_score must be between 0 and 100")
    if item.due_at is not None:
        _validate_aware(item.due_at, "due_at")
    if (item.current_start_at is None) != (item.current_end_at is None):
        raise ValueError("current placement requires both start and end")
    if item.current_start_at is not None and item.current_end_at is not None:
        _validate_aware(item.current_start_at, "current_start_at")
        _validate_aware(item.current_end_at, "current_end_at")
        if item.current_end_at <= item.current_start_at:
            raise ValueError("current_end_at must be after current_start_at")


def _validate_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _normalize_free_intervals(
    intervals: tuple[AvailabilityInterval, ...] | list[AvailabilityInterval],
) -> tuple[AvailabilityInterval, ...]:
    ordered = sorted(intervals, key=lambda item: (item.start_at, item.end_at))
    normalized: list[AvailabilityInterval] = []
    for interval in ordered:
        _validate_aware(interval.start_at, "free interval start_at")
        _validate_aware(interval.end_at, "free interval end_at")
        if interval.end_at <= interval.start_at:
            raise ValueError("free interval end_at must be after start_at")
        converted = AvailabilityInterval(
            interval.start_at.astimezone(UTC), interval.end_at.astimezone(UTC)
        )
        if normalized and converted.start_at < normalized[-1].end_at:
            raise ValueError("hard_free_intervals must not overlap")
        normalized.append(converted)
    return tuple(normalized)


def _item_sort_key(item: ScheduleItem, strategy: ScheduleStrategy) -> tuple:
    due = item.due_at.astimezone(UTC).timestamp() if item.due_at else float("inf")
    if strategy == ScheduleStrategy.DEADLINE_FIRST:
        return (due, -item.priority_score, item.duration_minutes, item.reference)
    return (-item.priority_score, due, item.duration_minutes, item.reference)


def _allocate(
    intervals: list[AvailabilityInterval],
    *,
    duration: timedelta,
    latest_end: datetime | None,
) -> tuple[datetime, datetime] | None:
    for index, interval in enumerate(intervals):
        candidate_end = interval.start_at + duration
        if candidate_end > interval.end_at:
            continue
        if latest_end is not None and candidate_end > latest_end:
            continue
        start = interval.start_at
        if candidate_end == interval.end_at:
            intervals.pop(index)
        else:
            intervals[index] = AvailabilityInterval(candidate_end, interval.end_at)
        return start, candidate_end
    return None


def _placement(
    item: ScheduleItem, start: datetime, end: datetime
) -> SchedulePlacement:
    return SchedulePlacement(
        reference=item.reference,
        title=item.title,
        start_at=start.astimezone(UTC),
        end_at=end.astimezone(UTC),
        is_locked=item.is_locked,
    )


def _changes(
    items: tuple[ScheduleItem, ...],
    placements: list[SchedulePlacement],
    unscheduled: set[str],
) -> list[ScheduleChange]:
    by_reference = {item.reference: item for item in placements}
    changes: list[ScheduleChange] = []
    for item in sorted(items, key=lambda value: value.reference):
        placement = by_reference.get(item.reference)
        before_start = (
            item.current_start_at.astimezone(UTC) if item.current_start_at else None
        )
        before_end = item.current_end_at.astimezone(UTC) if item.current_end_at else None
        if item.reference in unscheduled or placement is None:
            kind = ScheduleChangeKind.UNSCHEDULED
            after_start = after_end = None
        else:
            after_start, after_end = placement.start_at, placement.end_at
            if before_start is None:
                kind = ScheduleChangeKind.ADDED
            elif (before_start, before_end) == (after_start, after_end):
                kind = ScheduleChangeKind.UNCHANGED
            else:
                kind = ScheduleChangeKind.MOVED
        changes.append(
            ScheduleChange(
                reference=item.reference,
                kind=kind,
                before_start_at=before_start,
                before_end_at=before_end,
                after_start_at=after_start,
                after_end_at=after_end,
            )
        )
    return changes


def _locked_conflict_risks(
    items: tuple[ScheduleItem, ...],
    conflicts: tuple[AvailabilityConflict, ...],
) -> list[ScheduleRisk]:
    locked = {item.reference for item in items if item.is_locked}
    risks: list[ScheduleRisk] = []
    for conflict in conflicts:
        locked_references = locked & {
            conflict.first_reference,
            conflict.second_reference,
        }
        if conflict.kind != ConflictKind.HARD or not locked_references:
            continue
        reference = min(locked_references)
        other_reference = (
            conflict.first_reference
            if reference == conflict.second_reference
            else conflict.second_reference
        )
        risks.append(
            ScheduleRisk(
                ScheduleRiskCode.LOCKED_CONFLICT,
                ScheduleRiskSeverity.CRITICAL,
                reference,
                f"Locked commitment {reference} overlaps {other_reference}.",
            )
        )
    return risks
