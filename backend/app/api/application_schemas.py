from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.application.applications import ApplicationFieldValue
from app.domain.applications import (
    Application,
    ApplicationStatus,
    InterviewStatus,
    NewApplication,
    NewApplicationContact,
    NewApplicationFollowUp,
    NewApplicationInterview,
)


class ContactInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=80)
    notes: str = ""


class InterviewInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    time_zone: str = Field(min_length=1, max_length=100)
    location: str = Field(default="", max_length=300)
    status: InterviewStatus = InterviewStatus.SCHEDULED
    notes: str = ""


class FollowUpInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date
    estimated_minutes: int = Field(default=15, ge=5, le=1440)
    importance: int = Field(default=3, ge=1, le=5)
    completed_at: datetime | None = None
    notes: str = ""


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    status: ApplicationStatus = ApplicationStatus.SAVED
    posting_url: str | None = Field(default=None, max_length=1000)
    posting_source: str = Field(default="", max_length=200)
    applied_at: datetime | None = None
    deadline_at: datetime | None = None
    time_zone: str = Field(default="UTC", min_length=1, max_length=100)
    notes: str = ""
    contacts: list[ContactInput] = Field(default_factory=list)
    interviews: list[InterviewInput] = Field(default_factory=list)
    follow_ups: list[FollowUpInput] = Field(default_factory=list)

    def to_domain(self) -> NewApplication:
        return NewApplication(
            **self.model_dump(exclude={"contacts", "interviews", "follow_ups"}),
            contacts=tuple(NewApplicationContact(**item.model_dump()) for item in self.contacts),
            interviews=tuple(
                NewApplicationInterview(**item.model_dump()) for item in self.interviews
            ),
            follow_ups=tuple(
                NewApplicationFollowUp(**item.model_dump()) for item in self.follow_ups
            ),
        )


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    status: ApplicationStatus | None = None
    posting_url: str | None = Field(default=None, max_length=1000)
    posting_source: str | None = Field(default=None, max_length=200)
    applied_at: datetime | None = None
    deadline_at: datetime | None = None
    time_zone: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = None

    def to_changes(self) -> dict[str, ApplicationFieldValue]:
        return self.model_dump(exclude_unset=True)


class ContactRead(ContactInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class InterviewRead(InterviewInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class FollowUpRead(FollowUpInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ApplicationRead(ApplicationCreate):
    id: int
    contacts: list[ContactRead]
    interviews: list[InterviewRead]
    follow_ups: list[FollowUpRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, application: Application) -> "ApplicationRead":
        return cls.model_validate(application)


class WorkloadItemRead(BaseModel):
    kind: str
    reference_id: int
    title: str
    start_at: datetime | None
    end_at: datetime | None
    due_date: date | None
    estimated_minutes: int
    is_fixed: bool
    model_config = ConfigDict(from_attributes=True)
