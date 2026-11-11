"""Add proposals, confirmations, notifications, and audit.

Revision ID: 20261110_0007
Revises: 20261110_0006
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0007"
down_revision: str | None = "20261110_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "action_proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=100), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("state_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'executed', 'failed', 'rejected', 'expired')",
            name="ck_action_proposals_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("profile_id", "action_type", "status", "expires_at"):
        op.create_index(f"ix_action_proposals_{column}", "action_proposals", [column])

    op.create_table(
        "proposal_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_reference", sa.String(length=1000), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["action_proposals.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proposal_evidence_proposal_id", "proposal_evidence", ["proposal_id"])

    op.create_table(
        "confirmation_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("state_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["action_proposals.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_confirmation_records_proposal_id", "confirmation_records", ["proposal_id"]
    )
    op.create_index(
        "ix_confirmation_records_expires_at", "confirmation_records", ["expires_at"]
    )

    op.create_table(
        "execution_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("confirmation_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed')", name="ck_execution_results_status"
        ),
        sa.ForeignKeyConstraint(
            ["confirmation_id"], ["confirmation_records.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["action_proposals.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "confirmation_id", name="uq_execution_results_confirmation_id"
        ),
    )
    for column in ("proposal_id", "confirmation_id", "status", "executed_at"):
        op.create_index(f"ix_execution_results_{column}", "execution_results", [column])

    op.create_table(
        "notification_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=False),
        sa.Column("minimum_priority", sa.Integer(), nullable=False),
        sa.Column("quiet_hours_respected", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "minimum_priority BETWEEN 1 AND 5",
            name="ck_notification_rules_minimum_priority",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("profile_id", "event_type", "enabled"):
        op.create_index(f"ix_notification_rules_{column}", "notification_rules", [column])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=100), nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "profile_id",
        "actor_id",
        "action",
        "entity_type",
        "entity_id",
        "correlation_id",
        "occurred_at",
    ):
        op.create_index(f"ix_audit_events_{column}", "audit_events", [column])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("notification_rules")
    op.drop_table("execution_results")
    op.drop_table("confirmation_records")
    op.drop_table("proposal_evidence")
    op.drop_table("action_proposals")
