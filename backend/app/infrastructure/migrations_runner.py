from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlalchemy.engine import Connection

INITIAL_REVISION = "20261109_0001"
CURRENT_REVISION = "20261109_0003"
LEGACY_TASK_COLUMNS = {
    "id",
    "title",
    "description",
    "category",
    "tags",
    "start_date",
    "due_date",
    "estimated_minutes",
    "importance",
    "is_completed",
    "is_fixed",
    "recurrence",
    "notes",
    "created_at",
    "updated_at",
}


def _migration_config(connection: Connection) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parent / "migrations"),
    )
    config.attributes["connection"] = connection
    return config


def upgrade_database(engine: Engine, revision: str = "head") -> None:
    """Upgrade an injected engine and safely adopt the pre-Alembic task schema."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        config = _migration_config(connection)

        if "tasks" in tables and "alembic_version" not in tables:
            task_columns = {column["name"] for column in inspector.get_columns("tasks")}
            if task_columns != LEGACY_TASK_COLUMNS:
                raise RuntimeError(
                    "Existing task schema does not match the known pre-Alembic schema"
                )
            command.stamp(config, INITIAL_REVISION)

        command.upgrade(config, revision)

