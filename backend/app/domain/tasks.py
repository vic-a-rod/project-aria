from dataclasses import dataclass
from datetime import date, datetime

DEFAULT_CATEGORY_NAME = "Personal"


@dataclass(frozen=True)
class Project:
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Tag:
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    description: str
    category: str
    project: str | None
    tags: tuple[str, ...]
    start_date: date | None
    due_date: date | None
    estimated_minutes: int
    importance: int
    is_completed: bool
    completed_at: datetime | None
    is_fixed: bool
    recurrence: str | None
    recurrence_time_zone: str | None
    notes: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewTask:
    title: str
    description: str
    category: str
    project: str | None
    tags: tuple[str, ...]
    start_date: date | None
    due_date: date | None
    estimated_minutes: int
    importance: int
    is_completed: bool
    is_fixed: bool
    recurrence: str | None
    recurrence_time_zone: str | None
    notes: str

