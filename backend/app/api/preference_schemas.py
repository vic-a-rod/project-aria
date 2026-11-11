from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.application.preferences import PreferenceFieldValue
from app.domain.preferences import (
    NewPreference,
    Preference,
    PreferenceKind,
    PreferenceStatus,
    WorkloadMode,
)


class PreferenceCreate(BaseModel):
    kind: PreferenceKind
    title: str = Field(min_length=1, max_length=200)
    key: str | None = Field(default=None, max_length=100)
    value: str | None = None
    days_of_week: list[int] = Field(default_factory=list)
    start_time: time | None = None
    end_time: time | None = None
    time_zone: str = Field(default="UTC", min_length=1, max_length=100)
    workload_mode: WorkloadMode | None = None
    effective_from: datetime | None = None
    expires_at: datetime | None = None
    suggested: bool = False
    suggestion_reason: str | None = None

    def to_domain(self) -> NewPreference:
        values = self.model_dump(exclude={"suggested"})
        values["days_of_week"] = tuple(values["days_of_week"])
        values["status"] = (
            PreferenceStatus.SUGGESTED if self.suggested else PreferenceStatus.ACTIVE
        )
        return NewPreference(**values)


class PreferenceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    key: str | None = Field(default=None, max_length=100)
    value: str | None = None
    days_of_week: list[int] | None = None
    start_time: time | None = None
    end_time: time | None = None
    time_zone: str | None = Field(default=None, min_length=1, max_length=100)
    workload_mode: WorkloadMode | None = None
    effective_from: datetime | None = None
    expires_at: datetime | None = None
    suggestion_reason: str | None = None

    def to_changes(self) -> dict[str, PreferenceFieldValue]:
        values = self.model_dump(exclude_unset=True)
        if "days_of_week" in values and values["days_of_week"] is not None:
            values["days_of_week"] = tuple(values["days_of_week"])
        return values


class PreferenceRead(BaseModel):
    id: int
    kind: PreferenceKind
    title: str
    key: str | None
    value: str | None
    days_of_week: list[int]
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

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, preference: Preference) -> "PreferenceRead":
        return cls.model_validate(preference)
