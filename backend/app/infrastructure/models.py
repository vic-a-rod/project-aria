from datetime import UTC, date, datetime, time

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Table, Text, Time
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

