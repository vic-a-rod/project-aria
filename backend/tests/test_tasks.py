from dataclasses import replace
from datetime import UTC, date, datetime

from app.application.tasks import SortDirection, TaskService, TaskSort
from app.domain.tasks import Task


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 9, 17, 0, tzinfo=UTC)

    def today(self) -> date:
        return date(2026, 11, 9)


class FakeRepository:
    def __init__(self, tasks: list[Task]) -> None:
        self.tasks = tasks
        self.last_changes = {}

    def list(self, **_) -> list[Task]:
        return self.tasks

    def update(self, task_id, changes, *, timestamp):
        self.last_changes = changes
        for index, task in enumerate(self.tasks):
            if task.id == task_id:
                updated = replace(task, **changes, updated_at=timestamp)
                self.tasks[index] = updated
                return updated
        return None

    def delete(self, task_id):
        return False


def task(task_id: int, title: str) -> Task:
    timestamp = datetime(2026, 11, 1, 17, 0, tzinfo=UTC)
    return Task(
        id=task_id,
        title=title,
        description="",
        category="Personal",
        project=None,
        tags=(),
        start_date=None,
        due_date=None,
        estimated_minutes=30,
        importance=3,
        is_completed=False,
        completed_at=None,
        is_fixed=False,
        recurrence=None,
        recurrence_time_zone=None,
        notes="",
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_service_records_completion_time_and_clears_it_when_reopened() -> None:
    repository = FakeRepository([task(1, "Fictional task")])
    service = TaskService(repository, FixedClock())

    completed = service.update(1, {"is_completed": True})
    assert completed.task.completed_at == datetime(2026, 11, 9, 17, 0, tzinfo=UTC)

    reopened = service.update(1, {"is_completed": False})
    assert reopened.task.completed_at is None


def test_service_applies_explicit_stable_sort_and_pagination() -> None:
    repository = FakeRepository([task(2, "Beta"), task(1, "Alpha"), task(3, "Gamma")])
    service = TaskService(repository, FixedClock())

    page = service.list(
        sort=TaskSort.TITLE,
        direction=SortDirection.ASC,
        offset=1,
        limit=1,
    )

    assert [view.task.title for view in page] == ["Beta"]

