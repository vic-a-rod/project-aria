from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class PreferenceKind(StrEnum):
    GENERAL = "general"
    PROTECTED_TIME = "protected_time"
    QUIET_HOURS = "quiet_hours"
    WORKLOAD_MODE = "workload_mode"


class PreferenceStatus(StrEnum):
    ACTIVE = "active"
    SUGGESTED = "suggested"
    DISMISSED = "dismissed"


class WorkloadMode(StrEnum):
    FOCUS = "focus"
    LIGHTER = "lighter"


@dataclass(frozen=True)
class Preference:
    id: int
    kind: PreferenceKind
    title: str
    key: str | None
    value: str | None
    days_of_week: tuple[int, ...]
    start_time: time | None
    end_time: time | None
    time_zone: str
    workload_mode: WorkloadMode | None
    effective_from: datetime | None
    expires_at: datetime | None
    status: PreferenceStatus
    suggestion_reason: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewPreference:
    kind: PreferenceKind
    title: str
    key: str | None
    value: str | None
    days_of_week: tuple[int, ...]
    start_time: time | None
    end_time: time | None
    time_zone: str
    workload_mode: WorkloadMode | None
    effective_from: datetime | None
    expires_at: datetime | None
    status: PreferenceStatus
    suggestion_reason: str | None
    approved_at: datetime | None = None


def _validate_aware(value: datetime | None, field: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field} must be timezone-aware")


def validate_preference(preference: Preference | NewPreference) -> None:
    if not isinstance(preference.title, str) or not preference.title.strip():
        raise ValueError("title must not be blank")
    if not isinstance(preference.kind, PreferenceKind):
        raise ValueError("kind is required")
    if not isinstance(preference.status, PreferenceStatus):
        raise ValueError("status is required")
    try:
        ZoneInfo(preference.time_zone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("time_zone must be a valid IANA time zone") from error

    if len(set(preference.days_of_week)) != len(preference.days_of_week) or any(
        day < 0 or day > 6 for day in preference.days_of_week
    ):
        raise ValueError("days_of_week must contain unique integers from 0 through 6")
    _validate_aware(preference.effective_from, "effective_from")
    _validate_aware(preference.expires_at, "expires_at")
    _validate_aware(preference.approved_at, "approved_at")
    if (
        preference.effective_from is not None
        and preference.expires_at is not None
        and preference.expires_at <= preference.effective_from
    ):
        raise ValueError("expires_at must be after effective_from")

    if preference.status == PreferenceStatus.SUGGESTED:
        if preference.approved_at is not None:
            raise ValueError("suggested preferences cannot already be approved")
        if not preference.suggestion_reason or not preference.suggestion_reason.strip():
            raise ValueError("suggested preferences require a suggestion_reason")

    if preference.kind == PreferenceKind.GENERAL:
        if not preference.key or not preference.key.strip():
            raise ValueError("general preferences require a key")
        if preference.value is None:
            raise ValueError("general preferences require a value")
        if (
            preference.days_of_week
            or preference.start_time is not None
            or preference.end_time is not None
            or preference.workload_mode is not None
        ):
            raise ValueError("general preferences cannot include schedule or workload fields")
    elif preference.kind in {
        PreferenceKind.PROTECTED_TIME,
        PreferenceKind.QUIET_HOURS,
    }:
        if not preference.days_of_week:
            raise ValueError("scheduled preferences require days_of_week")
        if preference.start_time is None or preference.end_time is None:
            raise ValueError("scheduled preferences require start_time and end_time")
        if preference.start_time == preference.end_time:
            raise ValueError("start_time and end_time must differ")
        if preference.workload_mode is not None:
            raise ValueError("scheduled preferences cannot set workload_mode")
    elif preference.kind == PreferenceKind.WORKLOAD_MODE:
        if preference.workload_mode is None:
            raise ValueError("workload mode preferences require workload_mode")
        if preference.expires_at is None:
            raise ValueError("workload mode preferences require expires_at")
        if (
            preference.days_of_week
            or preference.start_time is not None
            or preference.end_time is not None
        ):
            raise ValueError("workload mode preferences cannot include schedule fields")


def is_preference_effective(preference: Preference, at: datetime) -> bool:
    _validate_aware(at, "at")
    return (
        preference.status == PreferenceStatus.ACTIVE
        and (preference.effective_from is None or preference.effective_from <= at)
        and (preference.expires_at is None or preference.expires_at > at)
    )
