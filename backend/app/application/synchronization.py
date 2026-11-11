from datetime import datetime
from typing import Protocol
from uuid import uuid4

from app.application.clock import Clock
from app.domain.synchronization import (
    ConnectionStatus,
    DeduplicationStatus,
    ExternalConnection,
    ExternalRecord,
    NewExternalConnection,
    NewExternalRecord,
    SyncCheckpoint,
    validate_connection,
    validate_external_record,
)


class SynchronizationRepository(Protocol):
    def list_connections(self, *, profile_id: str) -> list[ExternalConnection]: ...
    def get_connection(self, connection_id: str) -> ExternalConnection | None: ...
    def create_connection(
        self, connection_id: str, connection: NewExternalConnection, *, timestamp: datetime
    ) -> ExternalConnection: ...
    def update_connection_status(
        self, connection_id: str, status: ConnectionStatus, *, timestamp: datetime
    ) -> ExternalConnection | None: ...
    def get_checkpoint(
        self, connection_id: str, resource_type: str
    ) -> SyncCheckpoint | None: ...
    def upsert_checkpoint(
        self,
        connection_id: str,
        resource_type: str,
        cursor: str | None,
        *,
        timestamp: datetime,
    ) -> SyncCheckpoint: ...
    def list_records(
        self,
        *,
        connection_id: str | None = None,
        resource_type: str | None = None,
        tombstoned: bool | None = None,
        deduplication_key: str | None = None,
    ) -> list[ExternalRecord]: ...
    def get_record(self, record_id: str) -> ExternalRecord | None: ...
    def get_record_by_external_identity(
        self, connection_id: str, resource_type: str, external_id: str
    ) -> ExternalRecord | None: ...
    def create_record(
        self, record_id: str, record: NewExternalRecord, *, timestamp: datetime
    ) -> ExternalRecord: ...
    def refresh_record(
        self, record_id: str, record: NewExternalRecord, *, timestamp: datetime
    ) -> ExternalRecord: ...
    def set_tombstone(
        self, record_id: str, tombstoned_at: datetime | None, *, timestamp: datetime
    ) -> ExternalRecord | None: ...
    def set_duplicate(
        self,
        record_id: str,
        duplicate_of_id: str | None,
        status: DeduplicationStatus,
        *,
        timestamp: datetime,
    ) -> ExternalRecord | None: ...


class SynchronizationNotFoundError(LookupError):
    pass


class SynchronizationConflictError(ValueError):
    pass


class SynchronizationService:
    def __init__(self, repository: SynchronizationRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def list_connections(self, *, profile_id: str = "local-default") -> list[ExternalConnection]:
        return self._repository.list_connections(profile_id=profile_id)

    def get_connection(self, connection_id: str) -> ExternalConnection:
        connection = self._repository.get_connection(connection_id)
        if connection is None:
            raise SynchronizationNotFoundError(connection_id)
        return connection

    def _get_active_connection(self, connection_id: str) -> ExternalConnection:
        connection = self.get_connection(connection_id)
        if connection.status != ConnectionStatus.ACTIVE:
            raise SynchronizationConflictError("connection must be active to synchronize")
        return connection

    def create_connection(self, connection: NewExternalConnection) -> ExternalConnection:
        validate_connection(connection)
        return self._repository.create_connection(
            str(uuid4()), connection, timestamp=self._clock.now()
        )

    def set_connection_status(
        self, connection_id: str, status: ConnectionStatus
    ) -> ExternalConnection:
        self.get_connection(connection_id)
        updated = self._repository.update_connection_status(
            connection_id, status, timestamp=self._clock.now()
        )
        if updated is None:
            raise SynchronizationNotFoundError(connection_id)
        return updated

    def checkpoint(
        self, connection_id: str, resource_type: str, cursor: str | None
    ) -> SyncCheckpoint:
        self._get_active_connection(connection_id)
        if not resource_type.strip():
            raise ValueError("resource_type must not be blank")
        return self._repository.upsert_checkpoint(
            connection_id, resource_type, cursor, timestamp=self._clock.now()
        )

    def get_checkpoint(self, connection_id: str, resource_type: str) -> SyncCheckpoint:
        self.get_connection(connection_id)
        checkpoint = self._repository.get_checkpoint(connection_id, resource_type)
        if checkpoint is None:
            raise SynchronizationNotFoundError(resource_type)
        return checkpoint

    def list_records(
        self,
        *,
        connection_id: str | None = None,
        resource_type: str | None = None,
        tombstoned: bool | None = None,
        deduplication_key: str | None = None,
    ) -> list[ExternalRecord]:
        return self._repository.list_records(
            connection_id=connection_id,
            resource_type=resource_type,
            tombstoned=tombstoned,
            deduplication_key=deduplication_key,
        )

    def get_record(self, record_id: str) -> ExternalRecord:
        record = self._repository.get_record(record_id)
        if record is None:
            raise SynchronizationNotFoundError(record_id)
        return record

    def upsert_record(self, record: NewExternalRecord) -> tuple[ExternalRecord, bool]:
        validate_external_record(record)
        self._get_active_connection(record.connection_id)
        existing = self._repository.get_record_by_external_identity(
            record.connection_id, record.resource_type, record.external_id
        )
        now = self._clock.now()
        if existing is not None:
            return self._repository.refresh_record(existing.id, record, timestamp=now), False
        return self._repository.create_record(str(uuid4()), record, timestamp=now), True

    def tombstone(self, record_id: str) -> ExternalRecord:
        self.get_record(record_id)
        now = self._clock.now()
        updated = self._repository.set_tombstone(
            record_id, now, timestamp=now
        )
        if updated is None:
            raise SynchronizationNotFoundError(record_id)
        return updated

    def restore(self, record_id: str) -> ExternalRecord:
        self.get_record(record_id)
        updated = self._repository.set_tombstone(
            record_id, None, timestamp=self._clock.now()
        )
        if updated is None:
            raise SynchronizationNotFoundError(record_id)
        return updated

    def mark_duplicate(self, record_id: str, duplicate_of_id: str) -> ExternalRecord:
        record = self.get_record(record_id)
        canonical = self.get_record(duplicate_of_id)
        if record.id == canonical.id:
            raise SynchronizationConflictError("a record cannot duplicate itself")
        if (
            record.connection_id != canonical.connection_id
            or record.resource_type != canonical.resource_type
        ):
            raise SynchronizationConflictError(
                "duplicate records must share a connection and resource_type"
            )
        if canonical.deduplication_status == DeduplicationStatus.DUPLICATE:
            raise SynchronizationConflictError("duplicate target must be canonical")
        updated = self._repository.set_duplicate(
            record_id,
            canonical.id,
            DeduplicationStatus.DUPLICATE,
            timestamp=self._clock.now(),
        )
        if updated is None:
            raise SynchronizationNotFoundError(record_id)
        return updated

    def clear_duplicate(self, record_id: str) -> ExternalRecord:
        self.get_record(record_id)
        updated = self._repository.set_duplicate(
            record_id,
            None,
            DeduplicationStatus.UNIQUE,
            timestamp=self._clock.now(),
        )
        if updated is None:
            raise SynchronizationNotFoundError(record_id)
        return updated
