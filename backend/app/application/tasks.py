from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from app.application.clock import Clock
from app.domain.priority import PriorityResult, calculate_priority
from app.domain.tasks import NewTask, Task

TaskFieldValue = str | int | bool | date | tuple[str, ...] | None


class TaskRepository(Protocol):
    def list(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
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
        completed: bool | None = None,
    ) -> list[TaskView]:
        tasks = self._repository.list(
            search=search,
            category=category,
            completed=completed,
        )
        return sorted(
            (self._view(task) for task in tasks),
            key=lambda item: item.priority.score,
            reverse=True,
        )

    def create(self, task: NewTask) -> TaskView:
        created = self._repository.create(task, timestamp=self._clock.now())
        return self._view(created)

    def update(self, task_id: int, changes: dict[str, TaskFieldValue]) -> TaskView:
        updated = self._repository.update(
            task_id,
            changes,
            timestamp=self._clock.now(),
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

