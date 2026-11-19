"""Add lightweight local profiles and scope tasks and events.

Revision ID: 20261118_0008
Revises: 20261110_0007
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261118_0008"
down_revision: str | None = "20261110_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO profiles (id, display_name, created_at, updated_at) "
        "VALUES ('local-default', 'Local User', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )

    for table in ("tasks", "events"):
        op.add_column(
            table,
            sa.Column(
                "profile_id",
                sa.String(length=36),
                nullable=False,
                server_default="local-default",
            )
        )
        op.create_index(f"ix_{table}_profile_id", table, ["profile_id"])


def downgrade() -> None:
    for table in ("events", "tasks"):
        op.drop_index(f"ix_{table}_profile_id", table_name=table)
        op.drop_column(table, "profile_id")
    op.drop_table("profiles")
