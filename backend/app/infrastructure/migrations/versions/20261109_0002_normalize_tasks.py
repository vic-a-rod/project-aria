"""Normalize task categories, projects, tags, recurrence, and completion state.

Revision ID: 20261109_0002
Revises: 20261109_0001
Create Date: 2026-11-09
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_0002"
down_revision: str | None = "20261109_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def _timestamp(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is not None and parsed.utcoffset() is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_normalized_name", "projects", ["normalized_name"], unique=True)
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_categories_normalized_name",
        "categories",
        ["normalized_name"],
        unique=True,
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tags_normalized_name", "tags", ["normalized_name"], unique=True)
    op.create_table(
        "tasks_v2",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("is_fixed", sa.Boolean(), nullable=False),
        sa.Column("recurrence_rule", sa.Text(), nullable=True),
        sa.Column("recurrence_time_zone", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    connection = op.get_bind()
    legacy_tasks = connection.execute(sa.text("SELECT * FROM tasks ORDER BY id")).mappings().all()
    category_ids: dict[str, int] = {}
    tag_ids: dict[str, int] = {}
    task_tag_ids: list[tuple[int, int]] = []

    for legacy in legacy_tasks:
        created_at = _timestamp(legacy["created_at"])
        updated_at = _timestamp(legacy["updated_at"])
        created_value = created_at.isoformat(sep=" ")
        updated_value = updated_at.isoformat(sep=" ")
        category_name = str(legacy["category"] or "Personal").strip() or "Personal"
        category_key = _normalize_name(category_name)
        if category_key not in category_ids:
            result = connection.execute(
                sa.text(
                    "INSERT INTO categories (name, normalized_name, created_at, updated_at) "
                    "VALUES (:name, :normalized_name, :created_at, :updated_at)"
                ),
                {
                    "name": category_name,
                    "normalized_name": category_key,
                    "created_at": created_value,
                    "updated_at": updated_value,
                },
            )
            category_ids[category_key] = int(result.lastrowid)

        connection.execute(
            sa.text(
                "INSERT INTO tasks_v2 ("
                "id, title, description, category_id, project_id, start_date, due_date, "
                "estimated_minutes, importance, is_completed, completed_at, is_fixed, "
                "recurrence_rule, recurrence_time_zone, notes, created_at, updated_at"
                ") VALUES ("
                ":id, :title, :description, :category_id, NULL, :start_date, :due_date, "
                ":estimated_minutes, :importance, :is_completed, :completed_at, :is_fixed, "
                ":recurrence_rule, NULL, :notes, :created_at, :updated_at)"
            ),
            {
                "id": legacy["id"],
                "title": legacy["title"],
                "description": legacy["description"],
                "category_id": category_ids[category_key],
                "start_date": legacy["start_date"],
                "due_date": legacy["due_date"],
                "estimated_minutes": legacy["estimated_minutes"],
                "importance": legacy["importance"],
                "is_completed": legacy["is_completed"],
                "completed_at": updated_value if legacy["is_completed"] else None,
                "is_fixed": legacy["is_fixed"],
                "recurrence_rule": legacy["recurrence"],
                "notes": legacy["notes"],
                "created_at": created_value,
                "updated_at": updated_value,
            },
        )

        seen_task_tags: set[str] = set()
        for raw_tag in str(legacy["tags"] or "").split(","):
            tag_name = raw_tag.strip()
            tag_key = _normalize_name(tag_name)
            if not tag_key or tag_key in seen_task_tags:
                continue
            seen_task_tags.add(tag_key)
            if tag_key not in tag_ids:
                result = connection.execute(
                    sa.text(
                        "INSERT INTO tags (name, normalized_name, created_at, updated_at) "
                        "VALUES (:name, :normalized_name, :created_at, :updated_at)"
                    ),
                    {
                        "name": tag_name,
                        "normalized_name": tag_key,
                        "created_at": created_value,
                        "updated_at": updated_value,
                    },
                )
                tag_ids[tag_key] = int(result.lastrowid)
            task_tag_ids.append((int(legacy["id"]), tag_ids[tag_key]))

    op.drop_table("tasks")
    op.rename_table("tasks_v2", "tasks")
    op.create_index("ix_tasks_title", "tasks", ["title"], unique=False)
    op.create_index("ix_tasks_category_id", "tasks", ["category_id"], unique=False)
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"], unique=False)
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"], unique=False)
    op.create_index("ix_tasks_is_completed", "tasks", ["is_completed"], unique=False)
    op.create_table(
        "task_tags",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "tag_id"),
    )
    for task_id, tag_id in task_tag_ids:
        connection.execute(
            sa.text("INSERT INTO task_tags (task_id, tag_id) VALUES (:task_id, :tag_id)"),
            {"task_id": task_id, "tag_id": tag_id},
        )


def downgrade() -> None:
    raise NotImplementedError("D01 normalization is intentionally forward-only")

