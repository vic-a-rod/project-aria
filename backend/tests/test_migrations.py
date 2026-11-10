from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import StatementError

from app.domain.tasks import NewTask
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.migrations_runner import (
    CURRENT_REVISION,
    INITIAL_REVISION,
    upgrade_database,
)
from app.infrastructure.models import CategoryRow, TagRow, TaskRow
from app.infrastructure.task_repository import SqlAlchemyTaskRepository


def database_url(path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_upgrade_from_empty_creates_current_task_schema(tmp_path) -> None:
    engine = create_database_engine(database_url(tmp_path / "migration.db"))

    upgrade_database(engine)

    inspector = inspect(engine)
    assert {
        "alembic_version",
        "categories",
        "events",
        "projects",
        "tags",
        "task_tags",
        "tasks",
    } <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("events")} == {
        "id",
        "title",
        "description",
        "kind",
        "all_day",
        "start_at",
        "end_at",
        "start_date",
        "end_date",
        "time_zone",
        "is_fixed",
        "blocks_time",
        "recurrence_rule",
        "recurrence_time_zone",
        "location",
        "calendar_name",
        "source_type",
        "source_reference",
        "created_at",
        "updated_at",
    }
    assert {column["name"] for column in inspector.get_columns("tasks")} == {
        "id",
        "title",
        "description",
        "category_id",
        "project_id",
        "start_date",
        "due_date",
        "estimated_minutes",
        "importance",
        "is_completed",
        "completed_at",
        "is_fixed",
        "recurrence_rule",
        "recurrence_time_zone",
        "notes",
        "created_at",
        "updated_at",
    }
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == CURRENT_REVISION
    engine.dispose()


def test_upgrade_adopts_only_the_known_pre_alembic_schema(tmp_path) -> None:
    engine = create_database_engine(database_url(tmp_path / "legacy.db"))
    upgrade_database(engine, INITIAL_REVISION)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO tasks ("
                "id, title, description, category, tags, start_date, due_date, "
                "estimated_minutes, importance, is_completed, is_fixed, recurrence, "
                "notes, created_at, updated_at"
                ") VALUES ("
                "1, 'Fictional migrated task', 'Preserve this row', 'Education', "
                "'school,forms,School', NULL, '2026-11-10', 45, 4, 1, 0, "
                "'FREQ=WEEKLY', '', '2026-11-01 17:00:00', '2026-11-09 17:00:00')"
            )
        )
        connection.execute(text("DROP TABLE alembic_version"))

    upgrade_database(engine)

    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == CURRENT_REVISION
    sessions = create_session_factory(engine)
    with sessions() as session:
        task = session.get(TaskRow, 1)
        assert task is not None
        assert task.title == "Fictional migrated task"
        assert task.category.name == "Education"
        assert [tag.name for tag in task.tags] == ["forms", "school"]
        assert task.recurrence_rule == "FREQ=WEEKLY"
        assert task.completed_at == datetime(2026, 11, 9, 17, 0, tzinfo=UTC)
        assert session.scalars(select(CategoryRow)).all()[0].normalized_name == "education"
        assert {tag.normalized_name for tag in session.scalars(select(TagRow)).all()} == {
            "forms",
            "school",
        }
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
                project=None,
                tags=("fictional",),
                start_date=None,
                due_date=date(2026, 11, 10),
                estimated_minutes=30,
                importance=3,
                is_completed=False,
                is_fixed=False,
                recurrence=None,
                recurrence_time_zone=None,
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
            project=None,
            tags=(),
            start_date=None,
            due_date=None,
            estimated_minutes=30,
            importance=3,
            is_completed=False,
            is_fixed=False,
            recurrence=None,
            recurrence_time_zone=None,
            notes="",
        )
        with pytest.raises(StatementError, match="timezone-aware"):
            repository.create(task, timestamp=datetime(2026, 11, 9, 17, 0))
    engine.dispose()

