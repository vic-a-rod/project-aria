from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

ContractVersion = Literal["1.0"]


class SourceChannel(StrEnum):
    TEXT = "text"
    VOICE = "voice"
    WEB = "web"
    MOBILE = "mobile"
    DEVICE = "device"


class ResultStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PROPOSED = "proposed"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    NEEDS_CLARIFICATION = "needs_clarification"
    REJECTED = "rejected"
    FAILED = "failed"


class WarningSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ActorContext(BaseModel):
    actor_id: str = Field(min_length=1, max_length=200)
    profile_id: str = Field(min_length=1, max_length=200)

    model_config = ConfigDict(frozen=True)


class CommandEnvelope(BaseModel):
    schema_version: ContractVersion = "1.0"
    command_name: str = Field(min_length=1, max_length=200)
    source_channel: SourceChannel
    actor: ActorContext
    correlation_id: UUID
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)
    locale: str = Field(default="en-US", min_length=2, max_length=35)
    time_zone: str = Field(default="UTC", min_length=1, max_length=100)
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    confirmation_token: str | None = Field(default=None, min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True)

    @field_validator("time_zone")
    @classmethod
    def validate_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("must be a valid IANA time zone") from error
        return value


class WarningDetail(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)
    severity: WarningSeverity = WarningSeverity.WARNING

    model_config = ConfigDict(frozen=True)


class EvidenceReference(BaseModel):
    source_type: str = Field(min_length=1, max_length=100)
    reference_id: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(frozen=True)


class ActionProposal(BaseModel):
    proposal_id: UUID
    action: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1000)
    arguments: dict[str, JsonValue] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class ConfirmationRequirement(BaseModel):
    token: str = Field(min_length=1, max_length=500)
    expires_at: datetime
    reason: str = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(frozen=True)


class CommandResult(BaseModel):
    schema_version: ContractVersion = "1.0"
    command_name: str = Field(min_length=1, max_length=200)
    correlation_id: UUID
    status: ResultStatus
    data: dict[str, JsonValue] = Field(default_factory=dict)
    warnings: tuple[WarningDetail, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()
    proposals: tuple[ActionProposal, ...] = ()
    confirmation: ConfirmationRequirement | None = None
    display_summary: str = Field(min_length=1, max_length=2000)
    speakable_text: str = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_confirmation_state(self) -> "CommandResult":
        requires_confirmation = self.status == ResultStatus.REQUIRES_CONFIRMATION
        if requires_confirmation != (self.confirmation is not None):
            raise ValueError(
                "confirmation must be present exactly when status requires confirmation"
            )
        return self

