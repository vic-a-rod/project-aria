from datetime import UTC, datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models import Task
from app.priority import calculate_priority
from app.schemas import PriorityExplanation, TaskCreate, TaskRead, TaskUpdate


def _serialize(task: Task) -> TaskRead:
    priority = calculate_priority(
        importance=task.importance,
        due_date=task.due_date,
        estimated_minutes=task.estimated_minutes,
        is_completed=task.is_completed,
    )
    return TaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        category=task.category,
        tags=[tag for tag in task.tags.split(",") if tag],
        start_date=task.start_date,
        due_date=task.due_date,
        estimated_minutes=task.estimated_minutes,
        importance=task.importance,
        is_completed=task.is_completed,
        is_fixed=task.is_fixed,
        recurrence=task.recurrence,
        notes=task.notes,
        created_at=task.created_at,
        updated_at=task.updated_at,
        priority=PriorityExplanation(score=priority.score, reasons=priority.reasons),
    )


def list_tasks(
    session: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    completed: bool | None = None,
) -> list[TaskRead]:
    statement: Select[tuple[Task]] = select(Task)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
                Task.tags.ilike(pattern),
            )
        )
    if category:
        statement = statement.where(Task.category == category)
    if completed is not None:
        statement = statement.where(Task.is_completed == completed)
    tasks = session.scalars(statement).all()
    return sorted(
        (_serialize(task) for task in tasks),
        key=lambda item: item.priority.score,
        reverse=True,
    )


def get_task(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)


def create_task(session: Session, payload: TaskCreate) -> TaskRead:
    data = payload.model_dump()
    data["tags"] = ",".join(data["tags"])
    task = Task(**data)
    session.add(task)
    session.commit()
    session.refresh(task)
    return _serialize(task)


def update_task(session: Session, task: Task, payload: TaskUpdate) -> TaskRead:
    changes = payload.model_dump(exclude_unset=True)
    if "tags" in changes:
        changes["tags"] = ",".join(changes["tags"] or [])
    for field, value in changes.items():
        setattr(task, field, value)
    task.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(task)
    return _serialize(task)


def delete_task(session: Session, task: Task) -> None:
    session.delete(task)
    session.commit()

