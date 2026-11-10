from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    description: str
    category: str
    tags: tuple[str, ...]
    start_date: date | None
    due_date: date | None
    estimated_minutes: int
    importance: int
    is_completed: bool
    is_fixed: bool
    recurrence: str | None
    notes: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewTask:
    title: str
    description: str
    category: str
    tags: tuple[str, ...]
    start_date: date | None
    due_date: date | None
    estimated_minutes: int
    importance: int
    is_completed: bool
    is_fixed: bool
    recurrence: str | None
    notes: str

