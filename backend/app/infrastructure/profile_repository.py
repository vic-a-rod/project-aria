from datetime import datetime

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.domain.profiles import NewProfile, Profile
from app.infrastructure.models import ProfileRow


class SqlAlchemyProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[Profile]:
        rows = self._session.scalars(
            select(ProfileRow).order_by(
                case((ProfileRow.id == "local-default", 0), else_=1),
                ProfileRow.created_at,
                ProfileRow.display_name,
            )
        ).all()
        return [self._to_domain(row) for row in rows]

    def create(
        self, profile_id: str, profile: NewProfile, *, timestamp: datetime
    ) -> Profile:
        row = ProfileRow(
            id=profile_id,
            display_name=profile.display_name,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    @staticmethod
    def _to_domain(row: ProfileRow) -> Profile:
        return Profile(
            id=row.id,
            display_name=row.display_name,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
