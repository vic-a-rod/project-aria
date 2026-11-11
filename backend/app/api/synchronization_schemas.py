from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.synchronization import (
    ConnectionStatus,
    DeduplicationStatus,
    ExternalConnection,
    ExternalRecord,
    NewExternalConnection,
    NewExternalRecord,
)


class ConnectionCreate(BaseModel):
    profile_id: str = Field(default="local-default", min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)

    def to_domain(self) -> NewExternalConnection:
        return NewExternalConnection(**self.model_dump())


class ConnectionStatusUpdate(BaseModel):
    status: ConnectionStatus


class ConnectionRead(BaseModel):
    id: str
    profile_id: str
    provider: str
    display_name: str
    status: ConnectionStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, connection: ExternalConnection) -> "ConnectionRead":
        return cls.model_validate(connection)


class CheckpointUpdate(BaseModel):
    cursor: str | None = None


class CheckpointRead(BaseModel):
    connection_id: str
    resource_type: str
    cursor: str | None
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExternalRecordUpsert(BaseModel):
    connection_id: str = Field(min_length=1, max_length=36)
    resource_type: str = Field(min_length=1, max_length=100)
    external_id: str = Field(min_length=1, max_length=500)
    content_hash: str = Field(min_length=1, max_length=128)
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None
    provenance_kind: str = Field(min_length=1, max_length=100)
    provenance_reference: str | None = Field(default=None, max_length=1000)
    deduplication_key: str | None = Field(default=None, max_length=500)
    local_record_type: str | None = Field(default=None, max_length=100)
    local_record_id: str | None = Field(default=None, max_length=100)

    def to_domain(self) -> NewExternalRecord:
        return NewExternalRecord(**self.model_dump())


class DuplicateUpdate(BaseModel):
    duplicate_of_id: str = Field(min_length=1, max_length=36)


class ExternalRecordRead(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, record: ExternalRecord) -> "ExternalRecordRead":
        return cls.model_validate(record)
