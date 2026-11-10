from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ApplicationStatus(StrEnum):
    SAVED = "saved"
    PREPARING = "preparing"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class InterviewStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ApplicationContact:
    id: int
    name: str
    role: str
    email: str
    phone: str
    notes: str


@dataclass(frozen=True)
class ApplicationInterview:
    id: int
    title: str
    start_at: datetime
    end_at: datetime
    time_zone: str
    location: str
    status: InterviewStatus
    notes: str


@dataclass(frozen=True)
class ApplicationFollowUp:
    id: int
    title: str
    due_date: date
    estimated_minutes: int
    importance: int
    completed_at: datetime | None
    notes: str


@dataclass(frozen=True)
class NewApplicationContact:
    name: str
    role: str
    email: str
    phone: str
    notes: str


@dataclass(frozen=True)
class NewApplicationInterview:
    title: str
    start_at: datetime
    end_at: datetime
    time_zone: str
    location: str
    status: InterviewStatus
    notes: str


@dataclass(frozen=True)
class NewApplicationFollowUp:
    title: str
    due_date: date
    estimated_minutes: int
    importance: int
    completed_at: datetime | None
    notes: str


@dataclass(frozen=True)
class Application:
    id: int
    company: str
    role: str
    status: ApplicationStatus
    posting_url: str | None
    posting_source: str
    applied_at: datetime | None
    deadline_at: datetime | None
    time_zone: str
    notes: str
    contacts: tuple[ApplicationContact, ...]
    interviews: tuple[ApplicationInterview, ...]
    follow_ups: tuple[ApplicationFollowUp, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewApplication:
    company: str
    role: str
    status: ApplicationStatus
    posting_url: str | None
    posting_source: str
    applied_at: datetime | None
    deadline_at: datetime | None
    time_zone: str
    notes: str
    contacts: tuple[NewApplicationContact, ...]
    interviews: tuple[NewApplicationInterview, ...]
    follow_ups: tuple[NewApplicationFollowUp, ...]


def _validate_zone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as error:
        raise ValueError("time_zone must be a valid IANA time zone") from error


def _validate_aware(value: datetime | None, field: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field} must be timezone-aware")


def validate_application(application: Application | NewApplication) -> None:
    if not isinstance(application.company, str) or not application.company.strip():
        raise ValueError("company must not be blank")
    if not isinstance(application.role, str) or not application.role.strip():
        raise ValueError("role must not be blank")
    if not isinstance(application.status, ApplicationStatus):
        raise ValueError("status is required")
    if not application.time_zone:
        raise ValueError("time_zone is required")
    _validate_zone(application.time_zone)
    _validate_aware(application.applied_at, "applied_at")
    _validate_aware(application.deadline_at, "deadline_at")
    for contact in application.contacts:
        if not contact.name.strip():
            raise ValueError("contact name must not be blank")
    for interview in application.interviews:
        if not interview.title.strip():
            raise ValueError("interview title must not be blank")
        _validate_zone(interview.time_zone)
        _validate_aware(interview.start_at, "interview start_at")
        _validate_aware(interview.end_at, "interview end_at")
        if interview.end_at <= interview.start_at:
            raise ValueError("interview end_at must be after start_at")
    for follow_up in application.follow_ups:
        if not follow_up.title.strip():
            raise ValueError("follow-up title must not be blank")
        if not 5 <= follow_up.estimated_minutes <= 1440:
            raise ValueError("follow-up estimated_minutes must be between 5 and 1440")
        if not 1 <= follow_up.importance <= 5:
            raise ValueError("follow-up importance must be between 1 and 5")
        _validate_aware(follow_up.completed_at, "follow-up completed_at")
