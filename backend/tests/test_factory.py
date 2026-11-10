from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import create_database_engine, create_session_factory
from app.factory import create_app


@dataclass(frozen=True)
class FixedClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant

    def today(self) -> date:
        return self.instant.date()


def test_default_settings_are_local_only() -> None:
    settings = Settings.model_construct()

    assert settings.api_host == "127.0.0.1"
    assert settings.allowed_origins == ["http://localhost:5173"]
    assert settings.database_url == "sqlite:///./aria.db"


def test_app_instances_use_isolated_database_configuration(tmp_path) -> None:
    clock = FixedClock(datetime(2026, 11, 9, 17, 0, tzinfo=UTC))
    first_settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'first.db').as_posix()}",
        _env_file=None,
    )
    first_engine = create_database_engine(first_settings.database_url)
    first_sessions = create_session_factory(first_engine)
    first = create_app(
        first_settings,
        engine=first_engine,
        session_factory=first_sessions,
        clock=clock,
    )

    second_settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'second.db').as_posix()}",
        _env_file=None,
    )
    second_engine = create_database_engine(second_settings.database_url)
    second_sessions = create_session_factory(second_engine)
    second = create_app(
        second_settings,
        engine=second_engine,
        session_factory=second_sessions,
        clock=clock,
    )

    assert first.state.settings is first_settings
    assert first.state.engine is first_engine
    assert first.state.session_factory is first_sessions
    assert first.state.clock is clock

    with TestClient(first) as first_client:
        response = first_client.post("/api/tasks", json={"title": "Fictional first task"})
        assert response.status_code == 201

    with TestClient(second) as second_client:
        response = second_client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

