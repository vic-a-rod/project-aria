from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.events import EventFieldValue
from app.domain.events import Event, EventKind, EventSource, NewEvent


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    kind: EventKind = EventKind.EVENT
    all_day: bool = False
    start_at: datetime | None = None
    end_at: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    time_zone: str = Field(default="UTC", min_length=1, max_length=100)
    is_fixed: bool = True
    blocks_time: bool = True
    recurrence_rule: str | None = Field(default=None, max_length=500)
    recurrence_time_zone: str | None = Field(default=None, min_length=1, max_length=100)
    location: str = Field(default="", max_length=300)
    calendar_name: str = Field(default="Aria", min_length=1, max_length=200)
    source_type: EventSource = EventSource.LOCAL
    source_reference: str | None = Field(default=None, max_length=500)

    @field_validator("title", "calendar_name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    def to_domain(self) -> NewEvent:
        return NewEvent(**self.model_dump())


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    kind: EventKind | None = None
    all_day: bool | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    time_zone: str | None = Field(default=None, min_length=1, max_length=100)
    is_fixed: bool | None = None
    blocks_time: bool | None = None
    recurrence_rule: str | None = Field(default=None, max_length=500)
    recurrence_time_zone: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=300)
    calendar_name: str | None = Field(default=None, min_length=1, max_length=200)
    source_type: EventSource | None = None
    source_reference: str | None = Field(default=None, max_length=500)

    def to_changes(self) -> dict[str, EventFieldValue]:
        return self.model_dump(exclude_unset=True)


class EventRead(EventCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, event: Event) -> "EventRead":
        return cls.model_validate(event)
