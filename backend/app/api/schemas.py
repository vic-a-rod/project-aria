from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.application.tasks import TaskFieldValue, TaskView
from app.domain.tasks import NewTask


def validate_iana_time_zone(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as error:
        raise ValueError("must be a valid IANA time zone") from error
    return value


class TaskFields(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    category: str = Field(default="Personal", min_length=1, max_length=80)
    project: str | None = Field(default=None, min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list)
    start_date: date | None = None
    due_date: date | None = None
    estimated_minutes: int = Field(default=30, ge=5, le=1440)
    importance: int = Field(default=3, ge=1, le=5)
    is_completed: bool = False
    is_fixed: bool = False
    recurrence: str | None = Field(default=None, max_length=500)
    recurrence_time_zone: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str = ""

    @field_validator("title", "category")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))

    @field_validator("recurrence_time_zone")
    @classmethod
    def validate_recurrence_zone(cls, value: str | None) -> str | None:
        return validate_iana_time_zone(value)

    @model_validator(mode="after")
    def validate_recurrence_time_zone(self) -> "TaskFields":
        if self.recurrence_time_zone and not self.recurrence:
            raise ValueError("recurrence_time_zone requires recurrence")
        return self


class TaskCreate(TaskFields):
    def to_domain(self) -> NewTask:
        return NewTask(**self.model_dump(exclude={"tags"}), tags=tuple(self.tags))


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=80)
    project: str | None = Field(default=None, min_length=1, max_length=200)
    tags: list[str] | None = None
    start_date: date | None = None
    due_date: date | None = None
    estimated_minutes: int | None = Field(default=None, ge=5, le=1440)
    importance: int | None = Field(default=None, ge=1, le=5)
    is_completed: bool | None = None
    is_fixed: bool | None = None
    recurrence: str | None = Field(default=None, max_length=500)
    recurrence_time_zone: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = None

    @field_validator("recurrence_time_zone")
    @classmethod
    def validate_recurrence_zone(cls, value: str | None) -> str | None:
        return validate_iana_time_zone(value)

    def to_changes(self) -> dict[str, TaskFieldValue]:
        changes = self.model_dump(exclude_unset=True)
        if "tags" in changes:
            changes["tags"] = tuple(changes["tags"] or ())
        return changes


class PriorityExplanation(BaseModel):
    score: float
    reasons: list[str]


class TaskRead(TaskFields):
    id: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    priority: PriorityExplanation

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_view(cls, view: TaskView) -> "TaskRead":
        task = view.task
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            category=task.category,
            project=task.project,
            tags=list(task.tags),
            start_date=task.start_date,
            due_date=task.due_date,
            estimated_minutes=task.estimated_minutes,
            importance=task.importance,
            is_completed=task.is_completed,
            completed_at=task.completed_at,
            is_fixed=task.is_fixed,
            recurrence=task.recurrence,
            recurrence_time_zone=task.recurrence_time_zone,
            notes=task.notes,
            created_at=task.created_at,
            updated_at=task.updated_at,
            priority=PriorityExplanation(
                score=view.priority.score,
                reasons=view.priority.reasons,
            ),
        )

