from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.synchronization import (
    ConnectionStatus,
    DeduplicationStatus,
    ExternalConnection,
    ExternalRecord,
    NewExternalConnection,
    NewExternalRecord,
    SyncCheckpoint,
)
from app.infrastructure.models import (
    ExternalConnectionRow,
    ExternalRecordRow,
    SyncCheckpointRow,
)


class SqlAlchemySynchronizationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_connections(self, *, profile_id: str) -> list[ExternalConnection]:
        rows = self._session.scalars(
            select(ExternalConnectionRow)
            .where(ExternalConnectionRow.profile_id == profile_id)
            .order_by(ExternalConnectionRow.provider, ExternalConnectionRow.id)
        ).all()
        return [self._connection(row) for row in rows]

    def get_connection(self, connection_id: str) -> ExternalConnection | None:
        row = self._session.get(ExternalConnectionRow, connection_id)
        return self._connection(row) if row else None

    def create_connection(
        self, connection_id: str, connection: NewExternalConnection, *, timestamp: datetime
    ) -> ExternalConnection:
        row = ExternalConnectionRow(
            id=connection_id,
            profile_id=connection.profile_id,
            provider=connection.provider,
            display_name=connection.display_name,
            status=ConnectionStatus.ACTIVE.value,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._connection(row)

    def update_connection_status(
        self, connection_id: str, status: ConnectionStatus, *, timestamp: datetime
    ) -> ExternalConnection | None:
        row = self._session.get(ExternalConnectionRow, connection_id)
        if row is None:
            return None
        row.status = status.value
        row.updated_at = timestamp
        self._session.commit()
        self._session.refresh(row)
        return self._connection(row)

    def get_checkpoint(
        self, connection_id: str, resource_type: str
    ) -> SyncCheckpoint | None:
        row = self._session.scalar(
            select(SyncCheckpointRow).where(
                SyncCheckpointRow.connection_id == connection_id,
                SyncCheckpointRow.resource_type == resource_type,
            )
        )
        return self._checkpoint(row) if row else None

    def upsert_checkpoint(
        self,
        connection_id: str,
        resource_type: str,
        cursor: str | None,
        *,
        timestamp: datetime,
    ) -> SyncCheckpoint:
        row = self._session.scalar(
            select(SyncCheckpointRow).where(
                SyncCheckpointRow.connection_id == connection_id,
                SyncCheckpointRow.resource_type == resource_type,
            )
        )
        if row is None:
            row = SyncCheckpointRow(
                connection_id=connection_id,
                resource_type=resource_type,
                cursor=cursor,
                last_synced_at=timestamp,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self._session.add(row)
        else:
            row.cursor = cursor
            row.last_synced_at = timestamp
            row.updated_at = timestamp
        self._session.commit()
        self._session.refresh(row)
        return self._checkpoint(row)

    def list_records(
        self,
        *,
        connection_id: str | None = None,
        resource_type: str | None = None,
        tombstoned: bool | None = None,
        deduplication_key: str | None = None,
    ) -> list[ExternalRecord]:
        statement = select(ExternalRecordRow)
        if connection_id is not None:
            statement = statement.where(ExternalRecordRow.connection_id == connection_id)
        if resource_type is not None:
            statement = statement.where(ExternalRecordRow.resource_type == resource_type)
        if tombstoned is True:
            statement = statement.where(ExternalRecordRow.tombstoned_at.is_not(None))
        elif tombstoned is False:
            statement = statement.where(ExternalRecordRow.tombstoned_at.is_(None))
        if deduplication_key is not None:
            statement = statement.where(
                ExternalRecordRow.deduplication_key == deduplication_key
            )
        rows = self._session.scalars(
            statement.order_by(ExternalRecordRow.first_seen_at, ExternalRecordRow.id)
        ).all()
        return [self._record(row) for row in rows]

    def get_record(self, record_id: str) -> ExternalRecord | None:
        row = self._session.get(ExternalRecordRow, record_id)
        return self._record(row) if row else None

    def get_record_by_external_identity(
        self, connection_id: str, resource_type: str, external_id: str
    ) -> ExternalRecord | None:
        row = self._session.scalar(
            select(ExternalRecordRow).where(
                ExternalRecordRow.connection_id == connection_id,
                ExternalRecordRow.resource_type == resource_type,
                ExternalRecordRow.external_id == external_id,
            )
        )
        return self._record(row) if row else None

    def create_record(
        self, record_id: str, record: NewExternalRecord, *, timestamp: datetime
    ) -> ExternalRecord:
        row = ExternalRecordRow(
            id=record_id,
            **record.__dict__,
            first_seen_at=timestamp,
            last_seen_at=timestamp,
            tombstoned_at=None,
            deduplication_status=DeduplicationStatus.UNIQUE.value,
            duplicate_of_id=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._record(row)

    def refresh_record(
        self, record_id: str, record: NewExternalRecord, *, timestamp: datetime
    ) -> ExternalRecord:
        row = self._session.get(ExternalRecordRow, record_id)
        if row is None:  # pragma: no cover - guarded by service lookup
            raise LookupError(record_id)
        for field, value in record.__dict__.items():
            setattr(row, field, value)
        row.last_seen_at = timestamp
        row.tombstoned_at = None
        row.updated_at = timestamp
        self._session.commit()
        self._session.refresh(row)
        return self._record(row)

    def set_tombstone(
        self, record_id: str, tombstoned_at: datetime | None, *, timestamp: datetime
    ) -> ExternalRecord | None:
        row = self._session.get(ExternalRecordRow, record_id)
        if row is None:
            return None
        row.tombstoned_at = tombstoned_at
        row.updated_at = timestamp
        self._session.commit()
        self._session.refresh(row)
        return self._record(row)

    def set_duplicate(
        self,
        record_id: str,
        duplicate_of_id: str | None,
        status: DeduplicationStatus,
        *,
        timestamp: datetime,
    ) -> ExternalRecord | None:
        row = self._session.get(ExternalRecordRow, record_id)
        if row is None:
            return None
        row.duplicate_of_id = duplicate_of_id
        row.deduplication_status = status.value
        row.updated_at = timestamp
        self._session.commit()
        self._session.refresh(row)
        return self._record(row)

    @staticmethod
    def _connection(row: ExternalConnectionRow) -> ExternalConnection:
        return ExternalConnection(
            id=row.id,
            profile_id=row.profile_id,
            provider=row.provider,
            display_name=row.display_name,
            status=ConnectionStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _checkpoint(row: SyncCheckpointRow) -> SyncCheckpoint:
        return SyncCheckpoint(
            connection_id=row.connection_id,
            resource_type=row.resource_type,
            cursor=row.cursor,
            last_synced_at=row.last_synced_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _record(row: ExternalRecordRow) -> ExternalRecord:
        return ExternalRecord(
            id=row.id,
            connection_id=row.connection_id,
            resource_type=row.resource_type,
            external_id=row.external_id,
            content_hash=row.content_hash,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
            source_created_at=row.source_created_at,
            source_updated_at=row.source_updated_at,
            tombstoned_at=row.tombstoned_at,
            provenance_kind=row.provenance_kind,
            provenance_reference=row.provenance_reference,
            deduplication_key=row.deduplication_key,
            deduplication_status=DeduplicationStatus(row.deduplication_status),
            duplicate_of_id=row.duplicate_of_id,
            local_record_type=row.local_record_type,
            local_record_id=row.local_record_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
