from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.application.applications import ApplicationFieldValue
from app.domain.applications import (
    Application,
    ApplicationContact,
    ApplicationFollowUp,
    ApplicationInterview,
    ApplicationStatus,
    InterviewStatus,
    NewApplication,
)
from app.infrastructure.models import (
    ApplicationContactRow,
    ApplicationFollowUpRow,
    ApplicationInterviewRow,
    ApplicationRow,
)


class SqlAlchemyApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _statement(self) -> Select[tuple[ApplicationRow]]:
        return select(ApplicationRow).options(
            selectinload(ApplicationRow.contacts),
            selectinload(ApplicationRow.interviews),
            selectinload(ApplicationRow.follow_ups),
        )

    def list(self, *, status: ApplicationStatus | None = None) -> list[Application]:
        statement = self._statement()
        if status is not None:
            statement = statement.where(ApplicationRow.status == status.value)
        statement = statement.order_by(
            ApplicationRow.deadline_at.asc(), ApplicationRow.id.asc()
        )
        return [self._to_domain(row) for row in self._session.scalars(statement).all()]

    def get(self, application_id: int) -> Application | None:
        row = self._session.scalar(
            self._statement().where(ApplicationRow.id == application_id)
        )
        return self._to_domain(row) if row else None

    def create(self, application: NewApplication, *, timestamp: datetime) -> Application:
        row = ApplicationRow(
            company=application.company,
            role=application.role,
            status=application.status.value,
            posting_url=application.posting_url,
            posting_source=application.posting_source,
            applied_at=application.applied_at,
            deadline_at=application.deadline_at,
            time_zone=application.time_zone,
            notes=application.notes,
            created_at=timestamp,
            updated_at=timestamp,
            contacts=[
                ApplicationContactRow(**contact.__dict__)
                for contact in application.contacts
            ],
            interviews=[
                ApplicationInterviewRow(
                    **{**interview.__dict__, "status": interview.status.value}
                )
                for interview in application.interviews
            ],
            follow_ups=[
                ApplicationFollowUpRow(**follow_up.__dict__)
                for follow_up in application.follow_ups
            ],
        )
        self._session.add(row)
        self._session.commit()
        self._session.expire_all()
        created = self.get(row.id)
        if created is None:  # pragma: no cover - committed row must be readable
            raise RuntimeError("Committed application could not be reloaded")
        return created

    def update(
        self,
        application_id: int,
        changes: dict[str, ApplicationFieldValue],
        *,
        timestamp: datetime,
    ) -> Application | None:
        row = self._session.get(ApplicationRow, application_id)
        if row is None:
            return None
        for field, value in changes.items():
            if isinstance(value, ApplicationStatus):
                value = value.value
            setattr(row, field, value)
        row.updated_at = timestamp
        self._session.commit()
        self._session.expire_all()
        return self.get(row.id)

    def delete(self, application_id: int) -> bool:
        row = self._session.get(ApplicationRow, application_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True

    @staticmethod
    def _to_domain(row: ApplicationRow) -> Application:
        return Application(
            id=row.id,
            company=row.company,
            role=row.role,
            status=ApplicationStatus(row.status),
            posting_url=row.posting_url,
            posting_source=row.posting_source,
            applied_at=row.applied_at,
            deadline_at=row.deadline_at,
            time_zone=row.time_zone,
            notes=row.notes,
            contacts=tuple(
                ApplicationContact(
                    id=item.id,
                    name=item.name,
                    role=item.role,
                    email=item.email,
                    phone=item.phone,
                    notes=item.notes,
                )
                for item in row.contacts
            ),
            interviews=tuple(
                ApplicationInterview(
                    id=item.id,
                    title=item.title,
                    start_at=item.start_at,
                    end_at=item.end_at,
                    time_zone=item.time_zone,
                    location=item.location,
                    status=InterviewStatus(item.status),
                    notes=item.notes,
                )
                for item in row.interviews
            ),
            follow_ups=tuple(
                ApplicationFollowUp(
                    id=item.id,
                    title=item.title,
                    due_date=item.due_date,
                    estimated_minutes=item.estimated_minutes,
                    importance=item.importance,
                    completed_at=item.completed_at,
                    notes=item.notes,
                )
                for item in row.follow_ups
            ),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
