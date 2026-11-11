from datetime import UTC, date, datetime, time

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base
from app.infrastructure.types import UtcDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class CategoryRow(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    normalized_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class TagRow(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    normalized_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    importance: Mapped[int] = mapped_column(Integer, default=3)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurrence_time_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)

    category: Mapped[CategoryRow] = relationship()
    project: Mapped[ProjectRow | None] = relationship()
    tags: Mapped[list[TagRow]] = relationship(secondary=task_tags, order_by=TagRow.normalized_name)


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(32), index=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    start_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True, index=True)
    end_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    time_zone: Mapped[str] = mapped_column(String(100))
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    blocks_time: Mapped[bool] = mapped_column(Boolean, default=True)
    recurrence_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurrence_time_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str] = mapped_column(String(300), default="")
    calendar_name: Mapped[str] = mapped_column(String(200), default="Aria")
    source_type: Mapped[str] = mapped_column(String(32), default="local", index=True)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class ApplicationRow(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    posting_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    posting_source: Mapped[str] = mapped_column(String(200), default="")
    applied_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True, index=True)
    time_zone: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)
    contacts: Mapped[list["ApplicationContactRow"]] = relationship(
        cascade="all, delete-orphan", order_by="ApplicationContactRow.id"
    )
    interviews: Mapped[list["ApplicationInterviewRow"]] = relationship(
        cascade="all, delete-orphan", order_by="ApplicationInterviewRow.start_at"
    )
    follow_ups: Mapped[list["ApplicationFollowUpRow"]] = relationship(
        cascade="all, delete-orphan", order_by="ApplicationFollowUpRow.due_date"
    )


class ApplicationContactRow(Base):
    __tablename__ = "application_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    phone: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class ApplicationInterviewRow(Base):
    __tablename__ = "application_interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    start_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)
    end_at: Mapped[datetime] = mapped_column(UtcDateTime())
    time_zone: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    notes: Mapped[str] = mapped_column(Text, default="")


class ApplicationFollowUpRow(Base):
    __tablename__ = "application_follow_ups"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=15)
    importance: Mapped[int] = mapped_column(Integer, default=3)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class PreferenceRow(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(200))
    key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    days_of_week: Mapped[str] = mapped_column(String(32), default="")
    start_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    time_zone: Mapped[str] = mapped_column(String(100))
    workload_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    suggestion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class ExternalConnectionRow(Base):
    __tablename__ = "external_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(100), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class SyncCheckpointRow(Base):
    __tablename__ = "sync_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "resource_type", name="uq_sync_checkpoint_identity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("external_connections.id", ondelete="CASCADE"), index=True
    )
    resource_type: Mapped[str] = mapped_column(String(100))
    cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class ExternalRecordRow(Base):
    __tablename__ = "external_records"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "resource_type",
            "external_id",
            name="uq_external_record_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("external_connections.id", ondelete="CASCADE"), index=True
    )
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    external_id: Mapped[str] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)
    source_created_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    tombstoned_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True, index=True)
    provenance_kind: Mapped[str] = mapped_column(String(100))
    provenance_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    deduplication_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    deduplication_status: Mapped[str] = mapped_column(String(32), index=True)
    duplicate_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("external_records.id", ondelete="SET NULL"), nullable=True
    )
    local_record_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    local_record_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class ActionProposalRow(Base):
    __tablename__ = "action_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(100), index=True)
    action_type: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text)
    state_hash: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), index=True)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)
    evidence: Mapped[list["ProposalEvidenceRow"]] = relationship(
        cascade="all, delete-orphan", order_by="ProposalEvidenceRow.observed_at"
    )


class ProposalEvidenceRow(Base):
    __tablename__ = "proposal_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("action_proposals.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(100))
    source_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(UtcDateTime())


class ConfirmationRecordRow(Base):
    __tablename__ = "confirmation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("action_proposals.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64))
    state_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)


class ExecutionResultRow(Base):
    __tablename__ = "execution_results"
    __table_args__ = (
        UniqueConstraint("confirmation_id", name="uq_execution_results_confirmation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("action_proposals.id", ondelete="CASCADE"), index=True
    )
    confirmation_id: Mapped[str] = mapped_column(
        ForeignKey("confirmation_records.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    summary: Mapped[str] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)


class NotificationRuleRow(Base):
    __tablename__ = "notification_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    channel: Mapped[str] = mapped_column(String(100))
    minimum_priority: Mapped[int] = mapped_column(Integer)
    quiet_hours_respected: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utc_now, onupdate=utc_now)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(100), index=True)
    actor_id: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[str] = mapped_column(String(100), index=True)
    outcome: Mapped[str] = mapped_column(String(32))
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    details_json: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)

