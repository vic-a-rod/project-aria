from collections.abc import Generator

from app.application.clock import Clock
from app.application.tasks import TaskService
from app.infrastructure.database import SessionFactory
from app.infrastructure.task_repository import SqlAlchemyTaskRepository


def create_task_service_dependency(
    session_factory: SessionFactory,
    clock: Clock,
) -> Generator[TaskService, None, None]:
    with session_factory() as session:
        yield TaskService(SqlAlchemyTaskRepository(session), clock)

