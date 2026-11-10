from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.factory import create_app


@dataclass(frozen=True)
class FixedClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant

    def today(self) -> date:
        return self.instant.date()


@pytest.fixture
def client(tmp_path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'aria.db').as_posix()}",
        cors_origins="http://localhost:5173",
        time_zone="UTC",
        _env_file=None,
    )
    app = create_app(
        settings,
        clock=FixedClock(datetime(2026, 11, 9, 17, 0, tzinfo=UTC)),
    )
    with TestClient(app) as test_client:
        yield test_client


def test_task_lifecycle_uses_injected_clock(client: TestClient) -> None:
    created = client.post(
        "/api/tasks",
        json={
            "title": "Submit fictional scholarship form",
            "category": "Education",
            "project": "Fictional coursework",
            "tags": ["school", "forms"],
            "due_date": "2026-11-09",
            "recurrence": "FREQ=WEEKLY;BYDAY=MO",
            "recurrence_time_zone": "America/Phoenix",
            "importance": 4,
            "estimated_minutes": 25,
        },
    )
    assert created.status_code == 201
    task = created.json()
    assert task["created_at"] == "2026-11-09T17:00:00Z"
    assert task["priority"]["score"] == 85
    assert task["project"] == "Fictional coursework"
    assert task["recurrence"] == "FREQ=WEEKLY;BYDAY=MO"
    assert task["completed_at"] is None

    listed = client.get("/api/tasks", params={"category": "Education"})
    assert listed.status_code == 200
    assert any(item["id"] == task["id"] for item in listed.json())

    completed = client.patch(f"/api/tasks/{task['id']}", json={"is_completed": True})
    assert completed.status_code == 200
    assert completed.json()["priority"]["score"] == 0
    assert completed.json()["completed_at"] == "2026-11-09T17:00:00Z"

    reopened = client.patch(f"/api/tasks/{task['id']}", json={"is_completed": False})
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None

    deleted = client.delete(f"/api/tasks/{task['id']}")
    assert deleted.status_code == 204


def test_health_and_local_cors_defaults(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}

    allowed = client.options(
        "/api/tasks",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"

    denied = client.options(
        "/api/tasks",
        headers={
            "Origin": "https://example.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in denied.headers


def test_task_search_filters_sort_and_pagination(client: TestClient) -> None:
    fictional_tasks = [
        {
            "title": "Alpha design review",
            "description": "Prepare diagrams",
            "category": "Software",
            "project": "Project Aria",
            "tags": ["architecture", "review"],
        },
        {
            "title": "Beta application form",
            "description": "Submit a fictional application",
            "category": "Career",
            "project": "Internship search",
            "tags": ["forms"],
        },
        {
            "title": "Gamma reading",
            "description": "Read fictional course material",
            "category": "Education",
            "tags": ["school"],
            "is_completed": True,
        },
    ]
    for payload in fictional_tasks:
        assert client.post("/api/tasks", json=payload).status_code == 201

    search_results = client.get("/api/tasks", params={"search": "review"}).json()
    assert [task["title"] for task in search_results] == ["Alpha design review"]
    assert [
        task["title"]
        for task in client.get("/api/tasks", params={"project": "project aria"}).json()
    ] == ["Alpha design review"]
    assert [task["title"] for task in client.get("/api/tasks", params={"tag": "forms"}).json()] == [
        "Beta application form"
    ]
    assert [
        task["title"]
        for task in client.get("/api/tasks", params={"completed": True}).json()
    ] == ["Gamma reading"]

    page = client.get(
        "/api/tasks",
        params={"sort": "title", "direction": "asc", "offset": 1, "limit": 1},
    )
    assert page.status_code == 200
    assert [task["title"] for task in page.json()] == ["Beta application form"]

