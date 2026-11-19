from collections.abc import Generator
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.application.actions import ActionService
from app.application.applications import ApplicationService
from app.application.clock import Clock
from app.application.events import EventService
from app.application.preferences import PreferenceService
from app.application.profiles import ProfileService
from app.application.synchronization import SynchronizationService
from app.application.tasks import TaskService
from app.infrastructure.action_repository import SqlAlchemyActionRepository
from app.infrastructure.application_repository import SqlAlchemyApplicationRepository
from app.infrastructure.database import SessionFactory
from app.infrastructure.event_repository import SqlAlchemyEventRepository
from app.infrastructure.models import ProfileRow
from app.infrastructure.preference_repository import SqlAlchemyPreferenceRepository
from app.infrastructure.profile_repository import SqlAlchemyProfileRepository
from app.infrastructure.synchronization_repository import (
    SqlAlchemySynchronizationRepository,
)
from app.infrastructure.task_repository import SqlAlchemyTaskRepository


def create_task_service_dependency(
    session_factory: SessionFactory,
    clock: Clock,
    profile_id: Annotated[str, Header(alias="X-Aria-Profile-ID")] = "local-default",
) -> Generator[TaskService, None, None]:
    with session_factory() as session:
        if session.get(ProfileRow, profile_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="profile not found"
            )
        yield TaskService(SqlAlchemyTaskRepository(session, profile_id), clock)


def create_action_service_dependency(
    session_factory: SessionFactory,
    clock: Clock,
) -> Generator[ActionService, None, None]:
    with session_factory() as session:
        yield ActionService(SqlAlchemyActionRepository(session), clock)


def create_event_service_dependency(
    session_factory: SessionFactory,
    clock: Clock,
    profile_id: Annotated[str, Header(alias="X-Aria-Profile-ID")] = "local-default",
) -> Generator[EventService, None, None]:
    with session_factory() as session:
        if session.get(ProfileRow, profile_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="profile not found"
            )
        yield EventService(SqlAlchemyEventRepository(session, profile_id), clock)


def create_profile_service_dependency(
    session_factory: SessionFactory,
    clock: Clock,
) -> Generator[ProfileService, None, None]:
    with session_factory() as session:
        yield ProfileService(SqlAlchemyProfileRepository(session), clock)


def create_application_service_dependency(
    session_factory: SessionFactory,
    clock: Clock,
) -> Generator[ApplicationService, None, None]:
    with session_factory() as session:
        yield ApplicationService(SqlAlchemyApplicationRepository(session), clock)


def create_preference_service_dependency(
    session_factory: SessionFactory,
    clock: Clock,
) -> Generator[PreferenceService, None, None]:
    with session_factory() as session:
        yield PreferenceService(SqlAlchemyPreferenceRepository(session), clock)


def create_synchronization_service_dependency(
    session_factory: SessionFactory,
    clock: Clock,
) -> Generator[SynchronizationService, None, None]:
    with session_factory() as session:
        yield SynchronizationService(SqlAlchemySynchronizationRepository(session), clock)

