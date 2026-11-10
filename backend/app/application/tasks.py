from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

from app.application.clock import Clock
from app.domain.priority import PriorityResult, calculate_priority
from app.domain.tasks import NewTask, Task

TaskFieldValue = str | int | bool | date | datetime | tuple[str, ...] | None


class TaskSort(StrEnum):
    PRIORITY = "priority"
    DUE_DATE = "due_date"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class TaskRepository(Protocol):
    def list(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        project: str | None = None,
        tag: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]: ...

    def create(self, task: NewTask, *, timestamp: datetime) -> Task: ...

    def update(
        self,
        task_id: int,
        changes: dict[str, TaskFieldValue],
        *,
        timestamp: datetime,
    ) -> Task | None: ...

    def delete(self, task_id: int) -> bool: ...


@dataclass(frozen=True)
class TaskView:
    task: Task
    priority: PriorityResult


class TaskNotFoundError(LookupError):
    pass


class TaskService:
    def __init__(self, repository: TaskRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def list(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        project: str | None = None,
        tag: str | None = None,
        completed: bool | None = None,
        sort: TaskSort = TaskSort.PRIORITY,
        direction: SortDirection = SortDirection.DESC,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TaskView]:
        tasks = self._repository.list(
            search=search,
            category=category,
            project=project,
            tag=tag,
            completed=completed,
        )
        views = [self._view(task) for task in tasks]
        sorted_views = sorted(
            views,
            key=lambda item: self._sort_key(item, sort),
            reverse=direction == SortDirection.DESC,
        )
        return sorted_views[offset : offset + limit]

    def create(self, task: NewTask) -> TaskView:
        created = self._repository.create(task, timestamp=self._clock.now())
        return self._view(created)

    def update(self, task_id: int, changes: dict[str, TaskFieldValue]) -> TaskView:
        timestamp = self._clock.now()
        if changes.get("recurrence") is None and "recurrence" in changes:
            changes = dict(changes)
            changes.setdefault("recurrence_time_zone", None)
        if "is_completed" in changes:
            changes = dict(changes)
            changes["completed_at"] = timestamp if changes["is_completed"] else None
        updated = self._repository.update(
            task_id,
            changes,
            timestamp=timestamp,
        )
        if updated is None:
            raise TaskNotFoundError(task_id)
        return self._view(updated)

    def delete(self, task_id: int) -> None:
        if not self._repository.delete(task_id):
            raise TaskNotFoundError(task_id)

    def _view(self, task: Task) -> TaskView:
        priority = calculate_priority(
            importance=task.importance,
            due_date=task.due_date,
            estimated_minutes=task.estimated_minutes,
            is_completed=task.is_completed,
            today=self._clock.today(),
        )
        return TaskView(task=task, priority=priority)

    @staticmethod
    def _sort_key(view: TaskView, sort: TaskSort) -> tuple:
        task = view.task
        if sort == TaskSort.PRIORITY:
            value = view.priority.score
        elif sort == TaskSort.DUE_DATE:
            value = task.due_date.toordinal() if task.due_date else -1
        elif sort == TaskSort.CREATED_AT:
            value = task.created_at.timestamp()
        elif sort == TaskSort.UPDATED_AT:
            value = task.updated_at.timestamp()
        else:
            value = task.title.casefold()
        return (value, task.id)

