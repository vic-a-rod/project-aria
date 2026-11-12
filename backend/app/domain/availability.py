from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class AvailabilityBlockKind(StrEnum):
    FIXED = "fixed"
    FLEXIBLE = "flexible"
    PROTECTED = "protected"
    REST = "rest"


class ConflictKind(StrEnum):
    HARD = "hard"
    RESOLVABLE = "resolvable"


@dataclass(frozen=True)
class AvailabilityBlock:
    reference: str
    title: str
    start_at: datetime
    end_at: datetime
    kind: AvailabilityBlockKind
    recurrence_rule: str | None = None
    recurrence_time_zone: str | None = None


@dataclass(frozen=True)
class AvailabilityInterval:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True)
class AvailabilityOccurrence:
    reference: str
    title: str
    start_at: datetime
    end_at: datetime
    kind: AvailabilityBlockKind


@dataclass(frozen=True)
class AvailabilityConflict:
    kind: ConflictKind
    first_reference: str
    second_reference: str
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True)
class AvailabilityResult:
    free_intervals: tuple[AvailabilityInterval, ...]
    hard_free_intervals: tuple[AvailabilityInterval, ...]
    occurrences: tuple[AvailabilityOccurrence, ...]
    conflicts: tuple[AvailabilityConflict, ...]


@dataclass(frozen=True)
class _Recurrence:
    frequency: str
    interval: int
    weekdays: tuple[int, ...]
    count: int | None
    until: datetime | None


_WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def calculate_availability(
    *,
    window_start: datetime,
    window_end: datetime,
    blocks: tuple[AvailabilityBlock, ...] | list[AvailabilityBlock],
) -> AvailabilityResult:
    """Expand blocks, detect conflicts, and return deterministic UTC free time."""
    _validate_window(window_start, window_end)
    start_utc = window_start.astimezone(UTC)
    end_utc = window_end.astimezone(UTC)
    occurrences: list[AvailabilityOccurrence] = []
    for block in blocks:
        _validate_block(block)
        occurrences.extend(_expand_block(block, start_utc, end_utc))
    occurrences.sort(
        key=lambda item: (item.start_at, item.end_at, item.reference, item.kind.value)
    )

    all_busy = _merge_intervals(
        AvailabilityInterval(item.start_at, item.end_at) for item in occurrences
    )
    hard_busy = _merge_intervals(
        AvailabilityInterval(item.start_at, item.end_at)
        for item in occurrences
        if item.kind != AvailabilityBlockKind.FLEXIBLE
    )
    return AvailabilityResult(
        free_intervals=tuple(_subtract(start_utc, end_utc, all_busy)),
        hard_free_intervals=tuple(_subtract(start_utc, end_utc, hard_busy)),
        occurrences=tuple(occurrences),
        conflicts=tuple(_detect_conflicts(occurrences)),
    )


def recurring_wall_clock_blocks(
    *,
    reference: str,
    title: str,
    kind: AvailabilityBlockKind,
    days_of_week: tuple[int, ...],
    start_time: time,
    end_time: time,
    time_zone: str,
    anchor_date: date,
) -> tuple[AvailabilityBlock, ...]:
    """Adapt protected time, quiet hours, or rest rules into recurring blocks."""
    if not days_of_week or any(day not in range(7) for day in days_of_week):
        raise ValueError("days_of_week must contain integers from 0 through 6")
    try:
        zone = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("time_zone must be a valid IANA time zone") from error
    anchor_start = datetime.combine(anchor_date, start_time, tzinfo=zone)
    end_date = anchor_date + timedelta(days=1 if end_time <= start_time else 0)
    anchor_end = datetime.combine(end_date, end_time, tzinfo=zone)
    byday = ",".join(
        code for code, weekday in _WEEKDAYS.items() if weekday in set(days_of_week)
    )
    return (
        AvailabilityBlock(
            reference=reference,
            title=title,
            start_at=anchor_start,
            end_at=anchor_end,
            kind=kind,
            recurrence_rule=f"FREQ=WEEKLY;BYDAY={byday}",
            recurrence_time_zone=time_zone,
        ),
    )


def _validate_window(start: datetime, end: datetime) -> None:
    _validate_aware(start, "window_start")
    _validate_aware(end, "window_end")
    if end <= start:
        raise ValueError("window_end must be after window_start")


def _validate_block(block: AvailabilityBlock) -> None:
    if not block.reference.strip():
        raise ValueError("block reference must not be blank")
    _validate_aware(block.start_at, "block start_at")
    _validate_aware(block.end_at, "block end_at")
    if block.end_at <= block.start_at:
        raise ValueError("block end_at must be after start_at")
    if block.recurrence_time_zone and not block.recurrence_rule:
        raise ValueError("recurrence_time_zone requires recurrence_rule")
    if block.recurrence_rule:
        _parse_recurrence(
            block.recurrence_rule,
            block.recurrence_time_zone or _zone_key(block.start_at),
        )


def _validate_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _zone_key(value: datetime) -> str:
    key = getattr(value.tzinfo, "key", None)
    if not key:
        raise ValueError("recurring blocks require an explicit IANA time zone")
    return key


def _expand_block(
    block: AvailabilityBlock, window_start: datetime, window_end: datetime
) -> list[AvailabilityOccurrence]:
    if not block.recurrence_rule:
        occurrence = _occurrence(block, block.start_at, block.end_at)
        return [occurrence] if _overlaps(occurrence, window_start, window_end) else []

    zone_name = block.recurrence_time_zone or _zone_key(block.start_at)
    rule = _parse_recurrence(block.recurrence_rule, zone_name)
    zone = ZoneInfo(zone_name)
    anchor_start = block.start_at.astimezone(zone)
    anchor_end = block.end_at.astimezone(zone)
    overnight_days = (anchor_end.date() - anchor_start.date()).days
    end_clock = anchor_end.timetz().replace(tzinfo=None)
    start_clock = anchor_start.timetz().replace(tzinfo=None)
    occurrences: list[AvailabilityOccurrence] = []
    generated = 0
    candidate_date = anchor_start.date()
    final_date = window_end.astimezone(zone).date() + timedelta(days=1)
    while candidate_date <= final_date:
        if _recurs_on(candidate_date, anchor_start.date(), rule):
            occurrence_start = datetime.combine(candidate_date, start_clock, tzinfo=zone)
            occurrence_end = datetime.combine(
                candidate_date + timedelta(days=overnight_days), end_clock, tzinfo=zone
            )
            if occurrence_end <= occurrence_start:
                occurrence_end += timedelta(days=1)
            generated += 1
            if rule.count is not None and generated > rule.count:
                break
            if rule.until is not None and occurrence_start.astimezone(UTC) > rule.until:
                break
            occurrence = _occurrence(block, occurrence_start, occurrence_end)
            if _overlaps(occurrence, window_start, window_end):
                occurrences.append(occurrence)
        candidate_date += timedelta(days=1)
    return occurrences


def _parse_recurrence(value: str, zone_name: str) -> _Recurrence:
    try:
        zone = ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("recurrence_time_zone must be a valid IANA time zone") from error
    fields: dict[str, str] = {}
    for part in value.split(";"):
        if "=" not in part:
            raise ValueError("recurrence_rule must use KEY=VALUE parts")
        key, field_value = part.split("=", 1)
        fields[key.upper()] = field_value.upper()
    frequency = fields.get("FREQ")
    if frequency not in {"DAILY", "WEEKLY"}:
        raise ValueError("recurrence_rule supports FREQ=DAILY or FREQ=WEEKLY")
    try:
        interval = int(fields.get("INTERVAL", "1"))
        count = int(fields["COUNT"]) if "COUNT" in fields else None
    except ValueError as error:
        raise ValueError("recurrence INTERVAL and COUNT must be integers") from error
    if interval < 1 or (count is not None and count < 1):
        raise ValueError("recurrence INTERVAL and COUNT must be positive")
    try:
        weekdays = tuple(_WEEKDAYS[item] for item in fields.get("BYDAY", "").split(",") if item)
    except KeyError as error:
        raise ValueError("recurrence BYDAY contains an invalid weekday") from error
    until = _parse_until(fields.get("UNTIL"), zone)
    return _Recurrence(frequency, interval, weekdays, count, until)


def _parse_until(value: str | None, zone: ZoneInfo) -> datetime | None:
    if value is None:
        return None
    for pattern, target_zone in (
        ("%Y%m%dT%H%M%SZ", UTC),
        ("%Y%m%dT%H%M%S", zone),
        ("%Y%m%d", zone),
    ):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=target_zone).astimezone(UTC)
        except ValueError:
            continue
    raise ValueError("recurrence UNTIL must use an iCalendar date or date-time")


def _recurs_on(candidate: date, anchor: date, rule: _Recurrence) -> bool:
    if candidate < anchor:
        return False
    days = (candidate - anchor).days
    if rule.frequency == "DAILY":
        return days % rule.interval == 0 and (
            not rule.weekdays or candidate.weekday() in rule.weekdays
        )
    weekdays = rule.weekdays or (anchor.weekday(),)
    return candidate.weekday() in weekdays and (days // 7) % rule.interval == 0


def _occurrence(
    block: AvailabilityBlock, start: datetime, end: datetime
) -> AvailabilityOccurrence:
    return AvailabilityOccurrence(
        reference=block.reference,
        title=block.title,
        start_at=start.astimezone(UTC),
        end_at=end.astimezone(UTC),
        kind=block.kind,
    )


def _overlaps(
    occurrence: AvailabilityOccurrence, window_start: datetime, window_end: datetime
) -> bool:
    return occurrence.start_at < window_end and occurrence.end_at > window_start


def _merge_intervals(
    intervals: Iterable[AvailabilityInterval],
) -> list[AvailabilityInterval]:
    ordered = sorted(intervals, key=lambda item: (item.start_at, item.end_at))
    merged: list[AvailabilityInterval] = []
    for interval in ordered:
        if not merged or interval.start_at > merged[-1].end_at:
            merged.append(interval)
        elif interval.end_at > merged[-1].end_at:
            merged[-1] = AvailabilityInterval(merged[-1].start_at, interval.end_at)
    return merged


def _subtract(
    window_start: datetime,
    window_end: datetime,
    busy: list[AvailabilityInterval],
) -> list[AvailabilityInterval]:
    cursor = window_start
    free: list[AvailabilityInterval] = []
    for interval in busy:
        start = max(window_start, interval.start_at)
        end = min(window_end, interval.end_at)
        if end <= window_start or start >= window_end:
            continue
        if start > cursor:
            free.append(AvailabilityInterval(cursor, start))
        cursor = max(cursor, end)
    if cursor < window_end:
        free.append(AvailabilityInterval(cursor, window_end))
    return free


def _detect_conflicts(
    occurrences: list[AvailabilityOccurrence],
) -> list[AvailabilityConflict]:
    conflicts: list[AvailabilityConflict] = []
    for index, first in enumerate(occurrences):
        for second in occurrences[index + 1 :]:
            if second.start_at >= first.end_at:
                break
            overlap_start = max(first.start_at, second.start_at)
            overlap_end = min(first.end_at, second.end_at)
            if overlap_start >= overlap_end or first.reference == second.reference:
                continue
            kind = (
                ConflictKind.RESOLVABLE
                if AvailabilityBlockKind.FLEXIBLE in {first.kind, second.kind}
                else ConflictKind.HARD
            )
            conflicts.append(
                AvailabilityConflict(
                    kind=kind,
                    first_reference=min(first.reference, second.reference),
                    second_reference=max(first.reference, second.reference),
                    start_at=overlap_start,
                    end_at=overlap_end,
                )
            )
    conflicts.sort(
        key=lambda item: (
            item.start_at,
            item.end_at,
            item.first_reference,
            item.second_reference,
        )
    )
    return conflicts
