from dataclasses import asdict
from datetime import datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.application.tasks import TaskFieldValue
from app.domain.tasks import NewTask, Task
from app.infrastructure.models import TaskRow


class SqlAlchemyTaskRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        statement: Select[tuple[TaskRow]] = select(TaskRow)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    TaskRow.title.ilike(pattern),
                    TaskRow.description.ilike(pattern),
                    TaskRow.tags.ilike(pattern),
                )
            )
        if category:
            statement = statement.where(TaskRow.category == category)
        if completed is not None:
            statement = statement.where(TaskRow.is_completed == completed)
        return [self._to_domain(row) for row in self._session.scalars(statement).all()]

    def create(self, task: NewTask, *, timestamp: datetime) -> Task:
        values = asdict(task)
        values["tags"] = ",".join(task.tags)
        row = TaskRow(
            **values,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def update(
        self,
        task_id: int,
        changes: dict[str, TaskFieldValue],
        *,
        timestamp: datetime,
    ) -> Task | None:
        row = self._session.get(TaskRow, task_id)
        if row is None:
            return None
        normalized = dict(changes)
        if "tags" in normalized:
            normalized["tags"] = ",".join(normalized["tags"] or ())
        for field, value in normalized.items():
            setattr(row, field, value)
        row.updated_at = timestamp
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def delete(self, task_id: int) -> bool:
        row = self._session.get(TaskRow, task_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True

    @staticmethod
    def _to_domain(row: TaskRow) -> Task:
        return Task(
            id=row.id,
            title=row.title,
            description=row.description,
            category=row.category,
            tags=tuple(tag for tag in row.tags.split(",") if tag),
            start_date=row.start_date,
            due_date=row.due_date,
            estimated_minutes=row.estimated_minutes,
            importance=row.importance,
            is_completed=row.is_completed,
            is_fixed=row.is_fixed,
            recurrence=row.recurrence,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

