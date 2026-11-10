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


def test_timed_event_lifecycle_preserves_time_zone_and_provenance(client: TestClient) -> None:
    created = client.post(
        "/api/events",
        json={
            "title": "Fictional advising appointment",
            "kind": "appointment",
            "start_at": "2026-11-10T09:00:00-07:00",
            "end_at": "2026-11-10T09:45:00-07:00",
            "time_zone": "America/Phoenix",
            "is_fixed": True,
            "location": "Fictional campus office",
            "calendar_name": "Education",
            "source_type": "calendar",
            "source_reference": "fictional-event-41",
        },
    )
    assert created.status_code == 201
    event = created.json()
    assert event["start_at"] == "2026-11-10T16:00:00Z"
    assert event["time_zone"] == "America/Phoenix"
    assert event["source_type"] == "calendar"
    assert event["created_at"] == "2026-11-09T17:00:00Z"

    listed = client.get(
        "/api/events",
        params={"kind": "appointment", "fixed": True, "source": "calendar"},
    )
    assert [item["id"] for item in listed.json()] == [event["id"]]

    updated = client.patch(
        f"/api/events/{event['id']}",
        json={"is_fixed": False, "blocks_time": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_fixed"] is False
    assert updated.json()["blocks_time"] is False

    assert client.delete(f"/api/events/{event['id']}").status_code == 204
    assert client.get("/api/events").json() == []


def test_all_day_recurring_commitment_and_invalid_event_shapes(client: TestClient) -> None:
    created = client.post(
        "/api/events",
        json={
            "title": "Fictional family day",
            "kind": "commitment",
            "all_day": True,
            "start_date": "2026-11-14",
            "end_date": "2026-11-15",
            "time_zone": "America/Phoenix",
            "recurrence_rule": "FREQ=WEEKLY;BYDAY=SA",
            "recurrence_time_zone": "America/Phoenix",
        },
    )
    assert created.status_code == 201
    assert created.json()["start_date"] == "2026-11-14"
    assert created.json()["start_at"] is None

    invalid_range = client.post(
        "/api/events",
        json={
            "title": "Fictional invalid event",
            "start_at": "2026-11-10T10:00:00Z",
            "end_at": "2026-11-10T09:00:00Z",
        },
    )
    assert invalid_range.status_code == 422
    assert invalid_range.json()["detail"] == "end_at must be after start_at"

    invalid_zone = client.patch(
        f"/api/events/{created.json()['id']}",
        json={"time_zone": "Not/AZone"},
    )
    assert invalid_zone.status_code == 422
    assert "valid IANA time zone" in invalid_zone.json()["detail"]

    required_null = client.patch(
        f"/api/events/{created.json()['id']}",
        json={"time_zone": None},
    )
    assert required_null.status_code == 422
    assert required_null.json()["detail"] == "time_zone is required"


def test_application_tracking_and_unified_workload(client: TestClient) -> None:
    created = client.post(
        "/api/applications",
        json={
            "company": "Fictional Robotics Cooperative",
            "role": "Software Intern",
            "status": "interviewing",
            "posting_url": "https://example.invalid/jobs/software-intern",
            "posting_source": "Fictional university board",
            "applied_at": "2026-11-01T16:00:00Z",
            "deadline_at": "2026-11-20T23:59:00-07:00",
            "time_zone": "America/Phoenix",
            "notes": "Entirely fictional application fixture.",
            "contacts": [
                {
                    "name": "Morgan Example",
                    "role": "Fictional recruiter",
                    "email": "morgan@example.invalid",
                }
            ],
            "interviews": [
                {
                    "title": "Fictional technical interview",
                    "start_at": "2026-11-15T10:00:00-07:00",
                    "end_at": "2026-11-15T11:00:00-07:00",
                    "time_zone": "America/Phoenix",
                    "location": "Fictional video room",
                }
            ],
            "follow_ups": [
                {
                    "title": "Send fictional thank-you note",
                    "due_date": "2026-11-16",
                    "estimated_minutes": 15,
                    "importance": 4,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    application = created.json()
    assert application["company"] == "Fictional Robotics Cooperative"
    assert application["contacts"][0]["email"] == "morgan@example.invalid"
    assert application["interviews"][0]["start_at"] == "2026-11-15T17:00:00Z"
    assert application["created_at"] == "2026-11-09T17:00:00Z"

    workload = client.get(f"/api/applications/{application['id']}/workload")
    assert workload.status_code == 200
    assert {item["kind"] for item in workload.json()} == {
        "application_deadline",
        "interview",
        "follow_up",
    }
    interview = next(item for item in workload.json() if item["kind"] == "interview")
    assert interview["estimated_minutes"] == 60
    assert interview["is_fixed"] is True

    updated = client.patch(
        f"/api/applications/{application['id']}", json={"status": "offer"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "offer"
    assert client.get("/api/applications", params={"status": "offer"}).json()[0][
        "id"
    ] == application["id"]

    assert client.delete(f"/api/applications/{application['id']}").status_code == 204
    assert client.get("/api/applications").json() == []


def test_application_rejects_invalid_interview_and_required_null(client: TestClient) -> None:
    invalid = client.post(
        "/api/applications",
        json={
            "company": "Fictional Studio",
            "role": "Design Intern",
            "interviews": [
                {
                    "title": "Invalid fictional interview",
                    "start_at": "2026-11-15T11:00:00Z",
                    "end_at": "2026-11-15T10:00:00Z",
                    "time_zone": "UTC",
                }
            ],
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"] == "interview end_at must be after start_at"

    created = client.post(
        "/api/applications",
        json={"company": "Fictional Studio", "role": "Design Intern"},
    )
    required_null = client.patch(
        f"/api/applications/{created.json()['id']}", json={"company": None}
    )
    assert required_null.status_code == 422
    assert required_null.json()["detail"] == "company must not be blank"

