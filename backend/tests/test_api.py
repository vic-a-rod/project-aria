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


def test_preferences_protected_time_and_temporary_workload_modes(client: TestClient) -> None:
    protected = client.post(
        "/api/preferences",
        json={
            "kind": "protected_time",
            "title": "Fictional family evenings",
            "days_of_week": [0, 1, 2, 3, 4],
            "start_time": "18:00:00",
            "end_time": "21:00:00",
            "time_zone": "America/Phoenix",
        },
    )
    assert protected.status_code == 201, protected.text
    assert protected.json()["status"] == "active"
    assert protected.json()["days_of_week"] == [0, 1, 2, 3, 4]

    quiet = client.post(
        "/api/preferences",
        json={
            "kind": "quiet_hours",
            "title": "Fictional overnight quiet hours",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "start_time": "22:00:00",
            "end_time": "07:00:00",
            "time_zone": "America/Phoenix",
        },
    )
    assert quiet.status_code == 201, quiet.text

    mode = client.post(
        "/api/preferences",
        json={
            "kind": "workload_mode",
            "title": "Fictional exam focus period",
            "workload_mode": "focus",
            "effective_from": "2026-11-09T00:00:00Z",
            "expires_at": "2026-11-12T00:00:00Z",
        },
    )
    assert mode.status_code == 201, mode.text

    effective = client.get("/api/preferences", params={"effective": True})
    assert effective.status_code == 200
    assert {item["id"] for item in effective.json()} == {
        protected.json()["id"],
        quiet.json()["id"],
        mode.json()["id"],
    }

    expired = client.post(
        "/api/preferences",
        json={
            "kind": "workload_mode",
            "title": "Expired fictional lighter period",
            "workload_mode": "lighter",
            "effective_from": "2026-11-01T00:00:00Z",
            "expires_at": "2026-11-02T00:00:00Z",
        },
    )
    assert expired.status_code == 201
    assert expired.json()["id"] not in {
        item["id"] for item in client.get("/api/preferences", params={"effective": True}).json()
    }


def test_suggested_preferences_require_explicit_approval(client: TestClient) -> None:
    suggested = client.post(
        "/api/preferences",
        json={
            "kind": "general",
            "title": "Fictional planning preference",
            "key": "planning.buffer_minutes",
            "value": "15",
            "suggested": True,
            "suggestion_reason": "Fictional repeated scheduling pattern.",
        },
    )
    assert suggested.status_code == 201, suggested.text
    preference = suggested.json()
    assert preference["status"] == "suggested"
    assert preference["approved_at"] is None
    assert preference["id"] not in {
        item["id"] for item in client.get("/api/preferences", params={"effective": True}).json()
    }

    approved = client.post(f"/api/preferences/{preference['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "active"
    assert approved.json()["approved_at"] == "2026-11-09T17:00:00Z"
    assert preference["id"] in {
        item["id"] for item in client.get("/api/preferences", params={"effective": True}).json()
    }
    assert client.post(f"/api/preferences/{preference['id']}/approve").status_code == 409

    missing_reason = client.post(
        "/api/preferences",
        json={
            "kind": "general",
            "title": "Invalid fictional suggestion",
            "key": "planning.invalid",
            "value": "true",
            "suggested": True,
        },
    )
    assert missing_reason.status_code == 422
    assert missing_reason.json()["detail"] == (
        "suggested preferences require a suggestion_reason"
    )


def test_preference_validation_rejects_non_temporary_workload_mode(client: TestClient) -> None:
    response = client.post(
        "/api/preferences",
        json={
            "kind": "workload_mode",
            "title": "Invalid permanent focus mode",
            "workload_mode": "focus",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "workload mode preferences require expires_at"


def test_sync_ledger_upserts_records_and_preserves_provenance(client: TestClient) -> None:
    connection_response = client.post(
        "/api/sync/connections",
        json={
            "provider": "fictional-calendar",
            "display_name": "Fictional calendar account",
        },
    )
    assert connection_response.status_code == 201, connection_response.text
    connection = connection_response.json()
    assert connection["profile_id"] == "local-default"
    assert connection["status"] == "active"

    checkpoint = client.put(
        f"/api/sync/connections/{connection['id']}/checkpoints/events",
        json={"cursor": "fictional-cursor-1"},
    )
    assert checkpoint.status_code == 200
    assert checkpoint.json()["cursor"] == "fictional-cursor-1"
    assert checkpoint.json()["last_synced_at"] == "2026-11-09T17:00:00Z"

    payload = {
        "connection_id": connection["id"],
        "resource_type": "event",
        "external_id": "fictional-event-100",
        "content_hash": "sha256:fictional-one",
        "source_created_at": "2026-11-01T12:00:00Z",
        "source_updated_at": "2026-11-08T12:00:00Z",
        "provenance_kind": "calendar-event",
        "provenance_reference": "https://example.invalid/events/100",
        "deduplication_key": "event:fictional-team-review:2026-11-12",
    }
    created = client.put("/api/sync/records", json=payload)
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["deduplication_status"] == "unique"
    assert record["first_seen_at"] == "2026-11-09T17:00:00Z"
    assert record["provenance_reference"] == payload["provenance_reference"]

    refreshed = client.put(
        "/api/sync/records",
        json={**payload, "content_hash": "sha256:fictional-two"},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["id"] == record["id"]
    assert refreshed.json()["content_hash"] == "sha256:fictional-two"

    tombstoned = client.post(f"/api/sync/records/{record['id']}/tombstone")
    assert tombstoned.status_code == 200
    assert tombstoned.json()["tombstoned_at"] == "2026-11-09T17:00:00Z"
    assert [
        item["id"]
        for item in client.get("/api/sync/records", params={"tombstoned": True}).json()
    ] == [record["id"]]
    restored = client.post(f"/api/sync/records/{record['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["tombstoned_at"] is None


def test_sync_ledger_tracks_duplicates_and_connection_boundaries(client: TestClient) -> None:
    first_connection = client.post(
        "/api/sync/connections",
        json={"provider": "fictional-mail", "display_name": "Fictional inbox"},
    ).json()
    second_connection = client.post(
        "/api/sync/connections",
        json={"provider": "fictional-mail", "display_name": "Other fictional inbox"},
    ).json()

    def create_record(connection_id: str, external_id: str) -> dict:
        response = client.put(
            "/api/sync/records",
            json={
                "connection_id": connection_id,
                "resource_type": "message",
                "external_id": external_id,
                "content_hash": f"sha256:{external_id}",
                "provenance_kind": "mail-message",
                "deduplication_key": "message:fictional-interview-invitation",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    canonical = create_record(first_connection["id"], "fictional-message-a")
    duplicate = create_record(first_connection["id"], "fictional-message-b")
    external = create_record(second_connection["id"], "fictional-message-c")

    marked = client.put(
        f"/api/sync/records/{duplicate['id']}/duplicate",
        json={"duplicate_of_id": canonical["id"]},
    )
    assert marked.status_code == 200
    assert marked.json()["deduplication_status"] == "duplicate"
    assert marked.json()["duplicate_of_id"] == canonical["id"]

    cross_connection = client.put(
        f"/api/sync/records/{external['id']}/duplicate",
        json={"duplicate_of_id": canonical["id"]},
    )
    assert cross_connection.status_code == 409
    assert "share a connection" in cross_connection.json()["detail"]

    disconnected = client.patch(
        f"/api/sync/connections/{first_connection['id']}",
        json={"status": "disconnected"},
    )
    assert disconnected.status_code == 200
    blocked = client.put(
        "/api/sync/records",
        json={
            "connection_id": first_connection["id"],
            "resource_type": "message",
            "external_id": "fictional-message-d",
            "content_hash": "sha256:fictional-message-d",
            "provenance_kind": "mail-message",
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "connection must be active to synchronize"


def test_proposal_confirmation_execution_and_audit_lifecycle(client: TestClient) -> None:
    headers = {"X-Aria-Actor": "fictional-operator"}
    created = client.post(
        "/api/proposals",
        headers=headers,
        json={
            "action_type": "task.reschedule",
            "target_type": "task",
            "target_id": "fictional-task-42",
            "payload": {"due_date": "2026-11-12"},
            "state_hash": "sha256:fictional-state-one",
            "expires_at": "2026-11-10T17:00:00Z",
            "correlation_id": "fictional-command-100",
            "evidence": [
                {
                    "source_type": "task",
                    "source_reference": "fictional-task-42",
                    "summary": "Fictional deadline evidence.",
                    "content_hash": "sha256:fictional-evidence",
                    "observed_at": "2026-11-09T16:30:00Z",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    proposal = created.json()
    assert proposal["status"] == "pending"
    assert proposal["evidence"][0]["source_type"] == "task"

    issued = client.post(
        f"/api/proposals/{proposal['id']}/confirmations",
        headers=headers,
        json={"lifetime_minutes": 10},
    )
    assert issued.status_code == 201, issued.text
    confirmation = issued.json()
    assert confirmation["token"]
    assert confirmation["confirmed_at"] is None

    changed_state = client.post(
        f"/api/confirmations/{confirmation['id']}/confirm",
        headers=headers,
        json={
            "token": confirmation["token"],
            "current_state_hash": "sha256:fictional-state-two",
        },
    )
    assert changed_state.status_code == 409
    assert changed_state.json()["detail"] == "target state has changed"

    confirmed = client.post(
        f"/api/confirmations/{confirmation['id']}/confirm",
        headers=headers,
        json={
            "token": confirmation["token"],
            "current_state_hash": proposal["state_hash"],
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["confirmed_at"] == "2026-11-09T17:00:00Z"

    executed = client.post(
        f"/api/proposals/{proposal['id']}/execution",
        headers=headers,
        json={
            "confirmation_id": confirmation["id"],
            "status": "succeeded",
            "summary": "Applied the fictional due-date change.",
        },
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["status"] == "succeeded"
    assert client.get(f"/api/proposals/{proposal['id']}").json()["status"] == "executed"

    replay = client.post(
        f"/api/proposals/{proposal['id']}/execution",
        headers=headers,
        json={
            "confirmation_id": confirmation["id"],
            "status": "succeeded",
            "summary": "Attempted fictional replay.",
        },
    )
    assert replay.status_code == 409

    audit_events = client.get("/api/audit-events").json()
    assert {item["action"] for item in audit_events} >= {
        "proposal.created",
        "confirmation.issued",
        "confirmation.confirmed",
        "proposal.executed",
    }
    created_event = next(item for item in audit_events if item["action"] == "proposal.created")
    assert created_event["actor_id"] == "fictional-operator"
    assert created_event["correlation_id"] == "fictional-command-100"


def test_notification_rule_lifecycle_is_profile_scoped_and_audited(client: TestClient) -> None:
    created = client.post(
        "/api/notification-rules",
        json={
            "name": "Fictional urgent deadline alerts",
            "event_type": "deadline.approaching",
            "channel": "local",
            "minimum_priority": 4,
            "quiet_hours_respected": True,
        },
    )
    assert created.status_code == 201, created.text
    rule = created.json()
    assert rule["profile_id"] == "local-default"

    updated = client.patch(
        f"/api/notification-rules/{rule['id']}", json={"enabled": False}
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    required_null = client.patch(
        f"/api/notification-rules/{rule['id']}", json={"enabled": None}
    )
    assert required_null.status_code == 422
    assert required_null.json()["detail"] == "enabled is required"
    assert [item["id"] for item in client.get("/api/notification-rules").json()] == [
        rule["id"]
    ]

    assert client.delete(f"/api/notification-rules/{rule['id']}").status_code == 204
    assert client.get("/api/notification-rules").json() == []
    actions = {item["action"] for item in client.get("/api/audit-events").json()}
    assert actions >= {
        "notification_rule.created",
        "notification_rule.updated",
        "notification_rule.deleted",
    }


def test_confirmation_expires_and_tokens_are_not_returned_after_issue(tmp_path) -> None:
    @dataclass
    class MutableClock:
        instant: datetime

        def now(self) -> datetime:
            return self.instant

        def today(self) -> date:
            return self.instant.date()

    clock = MutableClock(datetime(2026, 11, 9, 17, 0, tzinfo=UTC))
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'confirmation.db').as_posix()}",
        cors_origins="http://localhost:5173",
        time_zone="UTC",
        _env_file=None,
    )
    app = create_app(settings, clock=clock)
    with TestClient(app) as test_client:
        proposal = test_client.post(
            "/api/proposals",
            json={
                "action_type": "event.update",
                "target_type": "event",
                "target_id": "fictional-event-9",
                "state_hash": "sha256:fictional-event-state",
                "expires_at": "2026-11-09T18:00:00Z",
            },
        ).json()
        issued = test_client.post(
            f"/api/proposals/{proposal['id']}/confirmations",
            json={"lifetime_minutes": 5},
        ).json()
        clock.instant = datetime(2026, 11, 9, 17, 6, tzinfo=UTC)
        expired = test_client.post(
            f"/api/confirmations/{issued['id']}/confirm",
            json={
                "token": issued["token"],
                "current_state_hash": proposal["state_hash"],
            },
        )
        assert expired.status_code == 409
        assert expired.json()["detail"] == "confirmation has expired or been revoked"

        second_proposal = test_client.post(
            "/api/proposals",
            json={
                "action_type": "event.update",
                "target_type": "event",
                "target_id": "fictional-event-10",
                "state_hash": "sha256:second-fictional-event-state",
                "expires_at": "2026-11-09T18:00:00Z",
            },
        ).json()
        second_issued = test_client.post(
            f"/api/proposals/{second_proposal['id']}/confirmations",
            json={"lifetime_minutes": 5},
        ).json()
        assert test_client.post(
            f"/api/confirmations/{second_issued['id']}/confirm",
            json={
                "token": second_issued["token"],
                "current_state_hash": second_proposal["state_hash"],
            },
        ).status_code == 200
        clock.instant = datetime(2026, 11, 9, 17, 12, tzinfo=UTC)
        late_execution = test_client.post(
            f"/api/proposals/{second_proposal['id']}/execution",
            json={
                "confirmation_id": second_issued["id"],
                "status": "succeeded",
                "summary": "Late fictional execution.",
            },
        )
        assert late_execution.status_code == 409
        assert late_execution.json()["detail"] == "confirmation has expired"

        audit_text = test_client.get("/api/audit-events").text
        assert issued["token"] not in audit_text

