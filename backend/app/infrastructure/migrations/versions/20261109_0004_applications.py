"""Add internship and job application tracking.

Revision ID: 20261109_0004
Revises: 20261109_0003
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_0004"
down_revision: str | None = "20261109_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("posting_url", sa.String(length=1000), nullable=True),
        sa.Column("posting_source", sa.String(length=200), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(), nullable=True),
        sa.Column("time_zone", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('saved', 'preparing', 'applied', 'interviewing', 'offer', "
            "'accepted', 'rejected', 'withdrawn')",
            name="ck_applications_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_company", "applications", ["company"], unique=False)
    op.create_index("ix_applications_role", "applications", ["role"], unique=False)
    op.create_index("ix_applications_status", "applications", ["status"], unique=False)
    op.create_index(
        "ix_applications_deadline_at", "applications", ["deadline_at"], unique=False
    )

    op.create_table(
        "application_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_contacts_application_id",
        "application_contacts",
        ["application_id"],
        unique=False,
    )
    op.create_table(
        "application_interviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("time_zone", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_interviews_application_id",
        "application_interviews",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        "ix_application_interviews_start_at",
        "application_interviews",
        ["start_at"],
        unique=False,
    )
    op.create_table(
        "application_follow_ups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_follow_ups_application_id",
        "application_follow_ups",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        "ix_application_follow_ups_due_date",
        "application_follow_ups",
        ["due_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("application_follow_ups")
    op.drop_table("application_interviews")
    op.drop_table("application_contacts")
    op.drop_table("applications")
