from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.application.tasks import TaskFieldValue
from app.domain.tasks import DEFAULT_CATEGORY_NAME, NewTask, Task
from app.infrastructure.models import CategoryRow, ProjectRow, TagRow, TaskRow


def normalize_name(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


class SqlAlchemyTaskRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        project: str | None = None,
        tag: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        statement: Select[tuple[TaskRow]] = (
            select(TaskRow)
            .join(TaskRow.category)
            .outerjoin(TaskRow.project)
            .outerjoin(TaskRow.tags)
            .options(
                selectinload(TaskRow.category),
                selectinload(TaskRow.project),
                selectinload(TaskRow.tags),
            )
            .distinct()
        )
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    TaskRow.title.ilike(pattern),
                    TaskRow.description.ilike(pattern),
                    CategoryRow.name.ilike(pattern),
                    ProjectRow.name.ilike(pattern),
                    TagRow.name.ilike(pattern),
                )
            )
        if category:
            statement = statement.where(CategoryRow.normalized_name == normalize_name(category))
        if project:
            statement = statement.where(ProjectRow.normalized_name == normalize_name(project))
        if tag:
            statement = statement.where(TagRow.normalized_name == normalize_name(tag))
        if completed is not None:
            statement = statement.where(TaskRow.is_completed == completed)
        return [self._to_domain(row) for row in self._session.scalars(statement).all()]

    def create(self, task: NewTask, *, timestamp: datetime) -> Task:
        values = asdict(task)
        category_name = values.pop("category") or DEFAULT_CATEGORY_NAME
        project_name = values.pop("project")
        tag_names = values.pop("tags")
        recurrence = values.pop("recurrence")
        row = TaskRow(
            **values,
            category=self._category(str(category_name), timestamp),
            project=self._project(str(project_name), timestamp) if project_name else None,
            tags=self._tags(tag_names, timestamp),
            recurrence_rule=recurrence,
            completed_at=timestamp if task.is_completed else None,
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
        if "category" in normalized:
            category_name = normalized.pop("category") or DEFAULT_CATEGORY_NAME
            row.category = self._category(str(category_name), timestamp)
        if "project" in normalized:
            project_name = normalized.pop("project")
            row.project = self._project(str(project_name), timestamp) if project_name else None
        if "tags" in normalized:
            tag_names = normalized.pop("tags") or ()
            row.tags = self._tags(tag_names, timestamp)
        if "recurrence" in normalized:
            normalized["recurrence_rule"] = normalized.pop("recurrence")
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

    def _category(self, name: str, timestamp: datetime) -> CategoryRow:
        normalized = normalize_name(name or DEFAULT_CATEGORY_NAME)
        existing = self._session.scalar(
            select(CategoryRow).where(CategoryRow.normalized_name == normalized)
        )
        if existing:
            return existing
        category = CategoryRow(
            name=name.strip() or DEFAULT_CATEGORY_NAME,
            normalized_name=normalized,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(category)
        return category

    def _project(self, name: str, timestamp: datetime) -> ProjectRow:
        normalized = normalize_name(name)
        existing = self._session.scalar(
            select(ProjectRow).where(ProjectRow.normalized_name == normalized)
        )
        if existing:
            return existing
        project = ProjectRow(
            name=name.strip(),
            normalized_name=normalized,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(project)
        return project

    def _tag(self, name: str, timestamp: datetime) -> TagRow:
        normalized = normalize_name(name)
        existing = self._session.scalar(select(TagRow).where(TagRow.normalized_name == normalized))
        if existing:
            return existing
        tag = TagRow(
            name=name.strip(),
            normalized_name=normalized,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(tag)
        return tag

    def _tags(self, names: tuple[str, ...], timestamp: datetime) -> list[TagRow]:
        resolved: list[TagRow] = []
        seen: set[str] = set()
        for value in names:
            name = str(value).strip()
            normalized = normalize_name(name)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            resolved.append(self._tag(name, timestamp))
        return resolved

    @staticmethod
    def _to_domain(row: TaskRow) -> Task:
        return Task(
            id=row.id,
            title=row.title,
            description=row.description,
            category=row.category.name,
            project=row.project.name if row.project else None,
            tags=tuple(tag.name for tag in row.tags),
            start_date=row.start_date,
            due_date=row.due_date,
            estimated_minutes=row.estimated_minutes,
            importance=row.importance,
            is_completed=row.is_completed,
            completed_at=row.completed_at,
            is_fixed=row.is_fixed,
            recurrence=row.recurrence_rule,
            recurrence_time_zone=row.recurrence_time_zone,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

