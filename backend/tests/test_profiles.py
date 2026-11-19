from datetime import UTC, datetime

from app.application.profiles import ProfileService
from app.domain.events import EventKind, EventSource, NewEvent
from app.domain.profiles import NewProfile
from app.domain.tasks import NewTask
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.event_repository import SqlAlchemyEventRepository
from app.infrastructure.migrations_runner import upgrade_database
from app.infrastructure.profile_repository import SqlAlchemyProfileRepository
from app.infrastructure.task_repository import SqlAlchemyTaskRepository

NOW = datetime(2026, 11, 18, 19, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def fictional_task(title: str) -> NewTask:
    return NewTask(
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
        is_fixed=False,
        recurrence=None,
        recurrence_time_zone=None,
        notes="",
    )


def fictional_event(title: str) -> NewEvent:
    return NewEvent(
        title=title,
        description="",
        kind=EventKind.EVENT,
        all_day=False,
        start_at=datetime(2026, 11, 20, 17, 0, tzinfo=UTC),
        end_at=datetime(2026, 11, 20, 18, 0, tzinfo=UTC),
        start_date=None,
        end_date=None,
        time_zone="UTC",
        is_fixed=True,
        blocks_time=True,
        recurrence_rule=None,
        recurrence_time_zone=None,
        location="",
        calendar_name="Aria",
        source_type=EventSource.LOCAL,
        source_reference=None,
    )


def test_profiles_create_and_scope_task_and_event_repositories(tmp_path) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'profiles.db').as_posix()}"
    )
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            profiles = ProfileService(SqlAlchemyProfileRepository(session), FixedClock())
            first = profiles.create(NewProfile(display_name="Fictional Tester One"))
            second = profiles.create(NewProfile(display_name="Fictional Tester Two"))
            assert [profile.display_name for profile in profiles.list()] == [
                "Local User",
                "Fictional Tester One",
                "Fictional Tester Two",
            ]

            first_tasks = SqlAlchemyTaskRepository(session, first.id)
            second_tasks = SqlAlchemyTaskRepository(session, second.id)
            first_task = first_tasks.create(
                fictional_task("First tester task"), timestamp=NOW
            )
            second_tasks.create(fictional_task("Second tester task"), timestamp=NOW)
            assert [task.title for task in first_tasks.list()] == ["First tester task"]
            assert [task.title for task in second_tasks.list()] == ["Second tester task"]
            assert (
                second_tasks.update(
                    first_task.id, {"title": "Wrong profile"}, timestamp=NOW
                )
                is None
            )
            assert second_tasks.delete(first_task.id) is False

            first_events = SqlAlchemyEventRepository(session, first.id)
            second_events = SqlAlchemyEventRepository(session, second.id)
            first_event = first_events.create(
                fictional_event("First tester event"), timestamp=NOW
            )
            second_events.create(fictional_event("Second tester event"), timestamp=NOW)
            assert [event.title for event in first_events.list()] == ["First tester event"]
            assert [event.title for event in second_events.list()] == ["Second tester event"]
            assert (
                second_events.update(
                    first_event.id, {"title": "Wrong profile"}, timestamp=NOW
                )
                is None
            )
            assert second_events.delete(first_event.id) is False
    finally:
        engine.dispose()
