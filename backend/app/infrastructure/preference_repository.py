from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.preferences import PreferenceFieldValue
from app.domain.preferences import (
    NewPreference,
    Preference,
    PreferenceKind,
    PreferenceStatus,
    WorkloadMode,
)
from app.infrastructure.models import PreferenceRow


class SqlAlchemyPreferenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, *, status: PreferenceStatus | None = None) -> list[Preference]:
        statement = select(PreferenceRow)
        if status is not None:
            statement = statement.where(PreferenceRow.status == status.value)
        statement = statement.order_by(PreferenceRow.kind.asc(), PreferenceRow.id.asc())
        return [self._to_domain(row) for row in self._session.scalars(statement).all()]

    def get(self, preference_id: int) -> Preference | None:
        row = self._session.get(PreferenceRow, preference_id)
        return self._to_domain(row) if row else None

    def create(self, preference: NewPreference, *, timestamp: datetime) -> Preference:
        row = PreferenceRow(
            **self._to_row_values(preference.__dict__),
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def update(
        self,
        preference_id: int,
        changes: dict[str, PreferenceFieldValue],
        *,
        timestamp: datetime,
    ) -> Preference | None:
        row = self._session.get(PreferenceRow, preference_id)
        if row is None:
            return None
        for field, value in self._to_row_values(changes).items():
            setattr(row, field, value)
        row.updated_at = timestamp
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def delete(self, preference_id: int) -> bool:
        row = self._session.get(PreferenceRow, preference_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True

    @staticmethod
    def _to_row_values(values: dict[str, PreferenceFieldValue]) -> dict[str, object]:
        result: dict[str, object] = {}
        for field, value in values.items():
            if field == "days_of_week":
                value = ",".join(str(day) for day in value) if value else ""
            elif isinstance(value, (PreferenceKind, PreferenceStatus, WorkloadMode)):
                value = value.value
            result[field] = value
        return result

    @staticmethod
    def _to_domain(row: PreferenceRow) -> Preference:
        return Preference(
            id=row.id,
            kind=PreferenceKind(row.kind),
            title=row.title,
            key=row.key,
            value=row.value,
            days_of_week=tuple(int(day) for day in row.days_of_week.split(",") if day),
            start_time=row.start_time,
            end_time=row.end_time,
            time_zone=row.time_zone,
            workload_mode=WorkloadMode(row.workload_mode) if row.workload_mode else None,
            effective_from=row.effective_from,
            expires_at=row.expires_at,
            status=PreferenceStatus(row.status),
            suggestion_reason=row.suggestion_reason,
            approved_at=row.approved_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
