from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.application.events import EventFieldValue
from app.domain.events import Event, EventKind, EventSource, NewEvent
from app.infrastructure.models import EventRow


class SqlAlchemyEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        *,
        kind: EventKind | None = None,
        fixed: bool | None = None,
        source: EventSource | None = None,
    ) -> list[Event]:
        statement: Select[tuple[EventRow]] = select(EventRow)
        if kind is not None:
            statement = statement.where(EventRow.kind == kind.value)
        if fixed is not None:
            statement = statement.where(EventRow.is_fixed == fixed)
        if source is not None:
            statement = statement.where(EventRow.source_type == source.value)
        statement = statement.order_by(
            EventRow.start_date.asc(), EventRow.start_at.asc(), EventRow.id.asc()
        )
        return [self._to_domain(row) for row in self._session.scalars(statement).all()]

    def get(self, event_id: int) -> Event | None:
        row = self._session.get(EventRow, event_id)
        return self._to_domain(row) if row else None

    def create(self, event: NewEvent, *, timestamp: datetime) -> Event:
        values = event.__dict__.copy()
        values["kind"] = event.kind.value
        values["source_type"] = event.source_type.value
        row = EventRow(**values, created_at=timestamp, updated_at=timestamp)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def update(
        self,
        event_id: int,
        changes: dict[str, EventFieldValue],
        *,
        timestamp: datetime,
    ) -> Event | None:
        row = self._session.get(EventRow, event_id)
        if row is None:
            return None
        for field, value in changes.items():
            if isinstance(value, (EventKind, EventSource)):
                value = value.value
            setattr(row, field, value)
        row.updated_at = timestamp
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def delete(self, event_id: int) -> bool:
        row = self._session.get(EventRow, event_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True

    @staticmethod
    def _to_domain(row: EventRow) -> Event:
        return Event(
            id=row.id,
            title=row.title,
            description=row.description,
            kind=EventKind(row.kind),
            all_day=row.all_day,
            start_at=row.start_at,
            end_at=row.end_at,
            start_date=row.start_date,
            end_date=row.end_date,
            time_zone=row.time_zone,
            is_fixed=row.is_fixed,
            blocks_time=row.blocks_time,
            recurrence_rule=row.recurrence_rule,
            recurrence_time_zone=row.recurrence_time_zone,
            location=row.location,
            calendar_name=row.calendar_name,
            source_type=EventSource(row.source_type),
            source_reference=row.source_reference,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
