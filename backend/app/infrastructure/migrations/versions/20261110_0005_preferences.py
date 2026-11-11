"""Add preferences and temporary workload overrides.

Revision ID: 20261110_0005
Revises: 20261109_0004
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0005"
down_revision: str | None = "20261109_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("days_of_week", sa.String(length=32), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("time_zone", sa.String(length=100), nullable=False),
        sa.Column("workload_mode", sa.String(length=32), nullable=True),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("suggestion_reason", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('general', 'protected_time', 'quiet_hours', 'workload_mode')",
            name="ck_preferences_kind",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suggested', 'dismissed')",
            name="ck_preferences_status",
        ),
        sa.CheckConstraint(
            "workload_mode IS NULL OR workload_mode IN ('focus', 'lighter')",
            name="ck_preferences_workload_mode",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preferences_kind", "preferences", ["kind"], unique=False)
    op.create_index("ix_preferences_key", "preferences", ["key"], unique=False)
    op.create_index("ix_preferences_status", "preferences", ["status"], unique=False)
    op.create_index("ix_preferences_expires_at", "preferences", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_table("preferences")
