import os
from pathlib import Path

os.environ["ARIA_DATABASE_URL"] = "sqlite:///./test_aria.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


def test_task_lifecycle() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            json={
                "title": "Submit fictional scholarship form",
                "category": "Education",
                "tags": ["school", "forms"],
                "importance": 4,
                "estimated_minutes": 25,
            },
        )
        assert created.status_code == 201
        task = created.json()
        assert task["priority"]["score"] > 0

        listed = client.get("/api/tasks", params={"category": "Education"})
        assert listed.status_code == 200
        assert any(item["id"] == task["id"] for item in listed.json())

        completed = client.patch(f"/api/tasks/{task['id']}", json={"is_completed": True})
        assert completed.status_code == 200
        assert completed.json()["priority"]["score"] == 0

        deleted = client.delete(f"/api/tasks/{task['id']}")
        assert deleted.status_code == 204


def teardown_module() -> None:
    engine.dispose()
    Path("test_aria.db").unlink(missing_ok=True)

