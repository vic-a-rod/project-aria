from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select
from sqlalchemy.exc import StatementError

from app.domain.tasks import NewTask
from app.infrastructure.database import Base, create_database_engine, create_session_factory
from app.infrastructure.migrations_runner import INITIAL_REVISION, upgrade_database
from app.infrastructure.models import TaskRow
from app.infrastructure.task_repository import SqlAlchemyTaskRepository


def database_url(path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_upgrade_from_empty_creates_current_task_schema(tmp_path) -> None:
    engine = create_database_engine(database_url(tmp_path / "migration.db"))

    upgrade_database(engine)

    inspector = inspect(engine)
    assert {"alembic_version", "tasks"} <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("tasks")} == {
        "id",
        "title",
        "description",
        "category",
        "tags",
        "start_date",
        "due_date",
        "estimated_minutes",
        "importance",
        "is_completed",
        "is_fixed",
        "recurrence",
        "notes",
        "created_at",
        "updated_at",
    }
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == INITIAL_REVISION
    engine.dispose()


def test_upgrade_adopts_only_the_known_pre_alembic_schema(tmp_path) -> None:
    engine = create_database_engine(database_url(tmp_path / "legacy.db"))
    Base.metadata.create_all(engine)

    upgrade_database(engine)

    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == INITIAL_REVISION
    engine.dispose()


def test_sqlite_round_trips_datetimes_as_aware_utc(tmp_path) -> None:
    engine = create_database_engine(database_url(tmp_path / "utc.db"))
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    local_offset = datetime(2026, 11, 9, 10, 0, tzinfo=timezone(-timedelta(hours=7)))

    with sessions() as session:
        repository = SqlAlchemyTaskRepository(session)
        created = repository.create(
            NewTask(
                title="Fictional UTC migration task",
                description="",
                category="Education",
                tags=("fictional",),
                start_date=None,
                due_date=date(2026, 11, 10),
                estimated_minutes=30,
                importance=3,
                is_completed=False,
                is_fixed=False,
                recurrence=None,
                notes="",
            ),
            timestamp=local_offset,
        )
        loaded = session.scalar(select(TaskRow).where(TaskRow.id == created.id))

        assert created.created_at == datetime(2026, 11, 9, 17, 0, tzinfo=UTC)
        assert loaded is not None
        assert loaded.created_at == datetime(2026, 11, 9, 17, 0, tzinfo=UTC)
        assert loaded.created_at.utcoffset() == timedelta(0)
    engine.dispose()


def test_utc_type_rejects_naive_datetimes(tmp_path) -> None:
    engine = create_database_engine(database_url(tmp_path / "naive.db"))
    upgrade_database(engine)
    sessions = create_session_factory(engine)

    with sessions() as session:
        repository = SqlAlchemyTaskRepository(session)
        task = NewTask(
            title="Fictional invalid timestamp task",
            description="",
            category="Personal",
            tags=(),
            start_date=None,
            due_date=None,
            estimated_minutes=30,
            importance=3,
            is_completed=False,
            is_fixed=False,
            recurrence=None,
            notes="",
        )
        with pytest.raises(StatementError, match="timezone-aware"):
            repository.create(task, timestamp=datetime(2026, 11, 9, 17, 0))
    engine.dispose()

