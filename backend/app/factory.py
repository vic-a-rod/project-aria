from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from app.api.routes import create_api_router
from app.application.clock import Clock
from app.config import Settings
from app.infrastructure import models  # noqa: F401
from app.infrastructure.clock import SystemClock
from app.infrastructure.database import (
    Base,
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.dependencies import create_task_service_dependency


def create_app(
    settings: Settings,
    *,
    engine: Engine | None = None,
    session_factory: SessionFactory | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Construct an Aria API instance from explicit application dependencies."""
    database_engine = engine or create_database_engine(settings.database_url)
    sessions = session_factory or create_session_factory(database_engine)
    application_clock = clock or SystemClock(ZoneInfo(settings.time_zone))

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(bind=database_engine)
        try:
            yield
        finally:
            database_engine.dispose()

    app = FastAPI(title="Project Aria API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = database_engine
    app.state.session_factory = sessions
    app.state.clock = application_clock

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    task_service_dependency = partial(
        create_task_service_dependency,
        sessions,
        application_clock,
    )
    app.include_router(create_api_router(task_service_dependency))
    return app

