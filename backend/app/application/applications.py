from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Protocol

from app.application.clock import Clock
from app.domain.applications import (
    Application,
    ApplicationStatus,
    InterviewStatus,
    NewApplication,
    validate_application,
)

ApplicationFieldValue = str | datetime | ApplicationStatus | None


@dataclass(frozen=True)
class ApplicationWorkloadItem:
    kind: str
    reference_id: int
    title: str
    start_at: datetime | None
    end_at: datetime | None
    due_date: date | None
    estimated_minutes: int
    is_fixed: bool


class ApplicationRepository(Protocol):
    def list(self, *, status: ApplicationStatus | None = None) -> list[Application]: ...
    def get(self, application_id: int) -> Application | None: ...
    def create(self, application: NewApplication, *, timestamp: datetime) -> Application: ...
    def update(
        self,
        application_id: int,
        changes: dict[str, ApplicationFieldValue],
        *,
        timestamp: datetime,
    ) -> Application | None: ...
    def delete(self, application_id: int) -> bool: ...


class ApplicationNotFoundError(LookupError):
    pass


class ApplicationService:
    def __init__(self, repository: ApplicationRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def list(self, *, status: ApplicationStatus | None = None) -> list[Application]:
        return self._repository.list(status=status)

    def get(self, application_id: int) -> Application:
        application = self._repository.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(application_id)
        return application

    def create(self, application: NewApplication) -> Application:
        validate_application(application)
        return self._repository.create(application, timestamp=self._clock.now())

    def update(
        self, application_id: int, changes: dict[str, ApplicationFieldValue]
    ) -> Application:
        current = self.get(application_id)
        candidate = replace(current, **changes)
        validate_application(candidate)
        updated = self._repository.update(
            application_id, changes, timestamp=self._clock.now()
        )
        if updated is None:
            raise ApplicationNotFoundError(application_id)
        return updated

    def delete(self, application_id: int) -> None:
        if not self._repository.delete(application_id):
            raise ApplicationNotFoundError(application_id)

    def workload(self, application_id: int) -> list[ApplicationWorkloadItem]:
        application = self.get(application_id)
        items: list[ApplicationWorkloadItem] = []
        if application.deadline_at is not None:
            items.append(
                ApplicationWorkloadItem(
                    kind="application_deadline",
                    reference_id=application.id,
                    title=f"{application.company} — {application.role} deadline",
                    start_at=application.deadline_at,
                    end_at=application.deadline_at,
                    due_date=None,
                    estimated_minutes=0,
                    is_fixed=True,
                )
            )
        for interview in application.interviews:
            if interview.status != InterviewStatus.CANCELLED:
                items.append(
                    ApplicationWorkloadItem(
                        kind="interview",
                        reference_id=interview.id,
                        title=interview.title,
                        start_at=interview.start_at,
                        end_at=interview.end_at,
                        due_date=None,
                        estimated_minutes=int(
                            (interview.end_at - interview.start_at).total_seconds() // 60
                        ),
                        is_fixed=True,
                    )
                )
        for follow_up in application.follow_ups:
            if follow_up.completed_at is None:
                items.append(
                    ApplicationWorkloadItem(
                        kind="follow_up",
                        reference_id=follow_up.id,
                        title=follow_up.title,
                        start_at=None,
                        end_at=None,
                        due_date=follow_up.due_date,
                        estimated_minutes=follow_up.estimated_minutes,
                        is_fixed=False,
                    )
                )
        return items
