from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class EventKind(StrEnum):
    EVENT = "event"
    APPOINTMENT = "appointment"
    COMMITMENT = "commitment"


class EventSource(StrEnum):
    LOCAL = "local"
    CALENDAR = "calendar"
    EMAIL = "email"
    IMPORT = "import"


@dataclass(frozen=True)
class Event:
    id: int
    title: str
    description: str
    kind: EventKind
    all_day: bool
    start_at: datetime | None
    end_at: datetime | None
    start_date: date | None
    end_date: date | None
    time_zone: str
    is_fixed: bool
    blocks_time: bool
    recurrence_rule: str | None
    recurrence_time_zone: str | None
    location: str
    calendar_name: str
    source_type: EventSource
    source_reference: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewEvent:
    title: str
    description: str
    kind: EventKind
    all_day: bool
    start_at: datetime | None
    end_at: datetime | None
    start_date: date | None
    end_date: date | None
    time_zone: str
    is_fixed: bool
    blocks_time: bool
    recurrence_rule: str | None
    recurrence_time_zone: str | None
    location: str
    calendar_name: str
    source_type: EventSource
    source_reference: str | None


def validate_event(event: Event | NewEvent) -> None:
    if not isinstance(event.title, str) or not event.title.strip():
        raise ValueError("title must not be blank")
    if not isinstance(event.calendar_name, str) or not event.calendar_name.strip():
        raise ValueError("calendar_name must not be blank")
    if not isinstance(event.kind, EventKind):
        raise ValueError("kind is required")
    if not isinstance(event.source_type, EventSource):
        raise ValueError("source_type is required")
    if not isinstance(event.all_day, bool):
        raise ValueError("all_day is required")
    if not isinstance(event.is_fixed, bool):
        raise ValueError("is_fixed is required")
    if not isinstance(event.blocks_time, bool):
        raise ValueError("blocks_time is required")
    if not event.time_zone:
        raise ValueError("time_zone is required")
    for value, field in (
        (event.time_zone, "time_zone"),
        (event.recurrence_time_zone, "recurrence_time_zone"),
    ):
        if value is None:
            continue
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"{field} must be a valid IANA time zone") from error
    if event.recurrence_time_zone and not event.recurrence_rule:
        raise ValueError("recurrence_time_zone requires recurrence_rule")
    if event.all_day:
        if event.start_date is None or event.end_date is None:
            raise ValueError("all-day events require start_date and end_date")
        if event.start_at is not None or event.end_at is not None:
            raise ValueError("all-day events cannot include timed bounds")
        if event.end_date <= event.start_date:
            raise ValueError("end_date must be after start_date")
        return
    if event.start_at is None or event.end_at is None:
        raise ValueError("timed events require start_at and end_at")
    if event.start_date is not None or event.end_date is not None:
        raise ValueError("timed events cannot include all-day dates")
    if event.start_at.tzinfo is None or event.start_at.utcoffset() is None:
        raise ValueError("start_at must be timezone-aware")
    if event.end_at.tzinfo is None or event.end_at.utcoffset() is None:
        raise ValueError("end_at must be timezone-aware")
    if event.end_at <= event.start_at:
        raise ValueError("end_at must be after start_at")
