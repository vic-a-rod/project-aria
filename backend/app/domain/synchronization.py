from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ConnectionStatus(StrEnum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    REVOKED = "revoked"


class DeduplicationStatus(StrEnum):
    UNIQUE = "unique"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"


@dataclass(frozen=True)
class ExternalConnection:
    id: str
    profile_id: str
    provider: str
    display_name: str
    status: ConnectionStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewExternalConnection:
    profile_id: str
    provider: str
    display_name: str


@dataclass(frozen=True)
class SyncCheckpoint:
    connection_id: str
    resource_type: str
    cursor: str | None
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ExternalRecord:
    id: str
    connection_id: str
    resource_type: str
    external_id: str
    content_hash: str
    first_seen_at: datetime
    last_seen_at: datetime
    source_created_at: datetime | None
    source_updated_at: datetime | None
    tombstoned_at: datetime | None
    provenance_kind: str
    provenance_reference: str | None
    deduplication_key: str | None
    deduplication_status: DeduplicationStatus
    duplicate_of_id: str | None
    local_record_type: str | None
    local_record_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewExternalRecord:
    connection_id: str
    resource_type: str
    external_id: str
    content_hash: str
    source_created_at: datetime | None
    source_updated_at: datetime | None
    provenance_kind: str
    provenance_reference: str | None
    deduplication_key: str | None
    local_record_type: str | None
    local_record_id: str | None


def _required(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be blank")


def _aware(value: datetime | None, field: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field} must be timezone-aware")


def validate_connection(connection: ExternalConnection | NewExternalConnection) -> None:
    _required(connection.profile_id, "profile_id")
    _required(connection.provider, "provider")
    _required(connection.display_name, "display_name")
    if isinstance(connection, ExternalConnection) and not isinstance(
        connection.status, ConnectionStatus
    ):
        raise ValueError("status is required")


def validate_external_record(record: ExternalRecord | NewExternalRecord) -> None:
    _required(record.connection_id, "connection_id")
    _required(record.resource_type, "resource_type")
    _required(record.external_id, "external_id")
    _required(record.content_hash, "content_hash")
    _required(record.provenance_kind, "provenance_kind")
    _aware(record.source_created_at, "source_created_at")
    _aware(record.source_updated_at, "source_updated_at")
    if (
        record.source_created_at is not None
        and record.source_updated_at is not None
        and record.source_updated_at < record.source_created_at
    ):
        raise ValueError("source_updated_at cannot be before source_created_at")
    if bool(record.local_record_type) != bool(record.local_record_id):
        raise ValueError("local_record_type and local_record_id must be set together")
