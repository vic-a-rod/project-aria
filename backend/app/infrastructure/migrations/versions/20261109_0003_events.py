"""Add local events, appointments, and commitments.

Revision ID: 20261109_0003
Revises: 20261109_0002
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_0003"
down_revision: str | None = "20261109_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=True),
        sa.Column("end_at", sa.DateTime(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("time_zone", sa.String(length=100), nullable=False),
        sa.Column("is_fixed", sa.Boolean(), nullable=False),
        sa.Column("blocks_time", sa.Boolean(), nullable=False),
        sa.Column("recurrence_rule", sa.Text(), nullable=True),
        sa.Column("recurrence_time_zone", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=300), nullable=False),
        sa.Column("calendar_name", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(all_day = 1 AND start_date IS NOT NULL AND end_date IS NOT NULL "
            "AND start_at IS NULL AND end_at IS NULL) OR "
            "(all_day = 0 AND start_at IS NOT NULL AND end_at IS NOT NULL "
            "AND start_date IS NULL AND end_date IS NULL)",
            name="ck_events_bound_shape",
        ),
        sa.CheckConstraint(
            "kind IN ('event', 'appointment', 'commitment')",
            name="ck_events_kind",
        ),
        sa.CheckConstraint(
            "source_type IN ('local', 'calendar', 'email', 'import')",
            name="ck_events_source_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_title", "events", ["title"], unique=False)
    op.create_index("ix_events_kind", "events", ["kind"], unique=False)
    op.create_index("ix_events_start_at", "events", ["start_at"], unique=False)
    op.create_index("ix_events_start_date", "events", ["start_date"], unique=False)
    op.create_index("ix_events_is_fixed", "events", ["is_fixed"], unique=False)
    op.create_index("ix_events_source_type", "events", ["source_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_events_source_type", table_name="events")
    op.drop_index("ix_events_is_fixed", table_name="events")
    op.drop_index("ix_events_start_date", table_name="events")
    op.drop_index("ix_events_start_at", table_name="events")
    op.drop_index("ix_events_kind", table_name="events")
    op.drop_index("ix_events_title", table_name="events")
    op.drop_table("events")
