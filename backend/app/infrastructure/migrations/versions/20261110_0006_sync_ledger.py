"""Add provider-neutral synchronization ledger.

Revision ID: 20261110_0006
Revises: 20261110_0005
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0006"
down_revision: str | None = "20261110_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'disconnected', 'revoked')",
            name="ck_external_connections_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_external_connections_profile_id", "external_connections", ["profile_id"])
    op.create_index("ix_external_connections_provider", "external_connections", ["provider"])
    op.create_index("ix_external_connections_status", "external_connections", ["status"])

    op.create_table(
        "sync_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["external_connections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id", "resource_type", name="uq_sync_checkpoint_identity"
        ),
    )
    op.create_index("ix_sync_checkpoints_connection_id", "sync_checkpoints", ["connection_id"])

    op.create_table(
        "external_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("source_created_at", sa.DateTime(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        sa.Column("tombstoned_at", sa.DateTime(), nullable=True),
        sa.Column("provenance_kind", sa.String(length=100), nullable=False),
        sa.Column("provenance_reference", sa.String(length=1000), nullable=True),
        sa.Column("deduplication_key", sa.String(length=500), nullable=True),
        sa.Column("deduplication_status", sa.String(length=32), nullable=False),
        sa.Column("duplicate_of_id", sa.String(length=36), nullable=True),
        sa.Column("local_record_type", sa.String(length=100), nullable=True),
        sa.Column("local_record_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "deduplication_status IN ('unique', 'duplicate', 'ignored')",
            name="ck_external_records_deduplication_status",
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["external_connections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_id"], ["external_records.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id",
            "resource_type",
            "external_id",
            name="uq_external_record_identity",
        ),
    )
    for column in (
        "connection_id",
        "resource_type",
        "content_hash",
        "first_seen_at",
        "last_seen_at",
        "tombstoned_at",
        "deduplication_key",
        "deduplication_status",
    ):
        op.create_index(f"ix_external_records_{column}", "external_records", [column])


def downgrade() -> None:
    op.drop_table("external_records")
    op.drop_table("sync_checkpoints")
    op.drop_table("external_connections")
