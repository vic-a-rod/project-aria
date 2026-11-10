from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskFields(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    category: str = Field(default="Personal", min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list)
    start_date: date | None = None
    due_date: date | None = None
    estimated_minutes: int = Field(default=30, ge=5, le=1440)
    importance: int = Field(default=3, ge=1, le=5)
    is_completed: bool = False
    is_fixed: bool = False
    recurrence: str | None = Field(default=None, max_length=120)
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


class TaskCreate(TaskFields):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=80)
    tags: list[str] | None = None
    start_date: date | None = None
    due_date: date | None = None
    estimated_minutes: int | None = Field(default=None, ge=5, le=1440)
    importance: int | None = Field(default=None, ge=1, le=5)
    is_completed: bool | None = None
    is_fixed: bool | None = None
    recurrence: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class PriorityExplanation(BaseModel):
    score: float
    reasons: list[str]


class TaskRead(TaskFields):
    id: int
    created_at: datetime
    updated_at: datetime
    priority: PriorityExplanation

    model_config = ConfigDict(from_attributes=True)

