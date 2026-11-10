from datetime import UTC, datetime

from sqlalchemy import func, select

from app.domain.tasks import NewTask
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.migrations_runner import upgrade_database
from app.infrastructure.models import CategoryRow, ProjectRow, TagRow
from app.infrastructure.task_repository import SqlAlchemyTaskRepository


def new_task(
    title: str,
    *,
    category: str,
    project: str | None,
    tags: tuple[str, ...],
) -> NewTask:
    return NewTask(
        title=title,
        description="Fictional repository fixture",
        category=category,
        project=project,
        tags=tags,
        start_date=None,
        due_date=None,
        estimated_minutes=30,
        importance=3,
        is_completed=False,
        is_fixed=False,
        recurrence="FREQ=WEEKLY",
        recurrence_time_zone="UTC",
        notes="",
    )


def test_repository_normalizes_entities_and_filters_by_relationship(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'repository.db').as_posix()}")
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    timestamp = datetime(2026, 11, 9, 17, 0, tzinfo=UTC)

    with sessions() as session:
        repository = SqlAlchemyTaskRepository(session)
        repository.create(
            new_task(
                "Fictional architecture review",
                category="Education",
                project="Project Aria",
                tags=("School", "school", "Review"),
            ),
            timestamp=timestamp,
        )
        repository.create(
            new_task(
                "Fictional implementation",
                category=" education ",
                project="project aria",
                tags=("school", "Code"),
            ),
            timestamp=timestamp,
        )

        assert session.scalar(select(func.count(CategoryRow.id))) == 1
        assert session.scalar(select(func.count(ProjectRow.id))) == 1
        assert session.scalar(select(func.count(TagRow.id))) == 3
        assert len(repository.list(category="EDUCATION")) == 2
        assert len(repository.list(project="PROJECT ARIA")) == 2
        assert [task.title for task in repository.list(tag="review")] == [
            "Fictional architecture review"
        ]
        assert [task.title for task in repository.list(search="code")] == [
            "Fictional implementation"
        ]

    engine.dispose()

