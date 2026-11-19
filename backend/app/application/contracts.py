from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

ContractVersion = Literal["1.0"]
CommandName = Annotated[
    str,
    Field(
        min_length=3,
        max_length=200,
        pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$",
    ),
]


class SourceChannel(StrEnum):
    TEXT = "text"
    VOICE = "voice"
    WEB = "web"
    MOBILE = "mobile"
    DEVICE = "device"


class IntentKind(StrEnum):
    READ = "read"
    PROPOSED_MUTATION = "proposed_mutation"


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


class EvidenceSourceType(StrEnum):
    USER_INPUT = "user_input"
    LOCAL_TASK = "local_task"
    LOCAL_EVENT = "local_event"
    LOCAL_APPLICATION = "local_application"
    LOCAL_PREFERENCE = "local_preference"
    EXTERNAL_EMAIL = "external_email"
    EXTERNAL_CALENDAR = "external_calendar"
    CALCULATION = "calculation"


class ActorContext(BaseModel):
    actor_id: str = Field(min_length=1, max_length=200)
    profile_id: str = Field(min_length=1, max_length=200)

    model_config = ConfigDict(frozen=True)


class ResourceReference(BaseModel):
    resource_type: str = Field(min_length=1, max_length=100)
    resource_id: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True)


class ReadIntent(BaseModel):
    kind: Literal[IntentKind.READ] = IntentKind.READ
    name: CommandName
    arguments: dict[str, JsonValue] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class ProposedMutationIntent(BaseModel):
    kind: Literal[IntentKind.PROPOSED_MUTATION] = IntentKind.PROPOSED_MUTATION
    name: CommandName
    target: ResourceReference | None = None
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(frozen=True)


CommandIntent = Annotated[
    ReadIntent | ProposedMutationIntent,
    Field(discriminator="kind"),
]


class CommandEnvelope(BaseModel):
    schema_version: ContractVersion = "1.0"
    intent: CommandIntent
    source_channel: SourceChannel
    actor: ActorContext
    correlation_id: UUID
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)
    locale: str = Field(default="en-US", min_length=2, max_length=35)
    time_zone: str = Field(default="UTC", min_length=1, max_length=100)
    confirmation_token: str | None = Field(default=None, min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True)

    @property
    def command_name(self) -> str:
        return self.intent.name

    @field_validator("time_zone")
    @classmethod
    def validate_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("must be a valid IANA time zone") from error
        return value

    @model_validator(mode="after")
    def validate_mutation_metadata(self) -> "CommandEnvelope":
        is_mutation = self.intent.kind == IntentKind.PROPOSED_MUTATION
        if is_mutation and self.idempotency_key is None:
            raise ValueError("proposed mutations require an idempotency key")
        if not is_mutation and self.confirmation_token is not None:
            raise ValueError("confirmation tokens are only valid for proposed mutations")
        return self


class WarningDetail(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)
    severity: WarningSeverity = WarningSeverity.WARNING

    model_config = ConfigDict(frozen=True)


class EvidenceReference(BaseModel):
    source_type: EvidenceSourceType
    reference_id: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=1000)
    observed_at: datetime | None = None

    model_config = ConfigDict(frozen=True)

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class ActionProposal(BaseModel):
    proposal_id: UUID
    action: CommandName
    summary: str = Field(min_length=1, max_length=1000)
    target: ResourceReference | None = None
    arguments: dict[str, JsonValue] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class ConfirmationRequirement(BaseModel):
    proposal_id: UUID
    token: str = Field(min_length=1, max_length=500)
    expires_at: datetime
    reason: str = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(frozen=True)

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        return value


class ClarificationOption(BaseModel):
    value: str = Field(min_length=1, max_length=500)
    label: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True)


class ClarificationRequest(BaseModel):
    field: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)
    options: tuple[ClarificationOption, ...] = ()
    allow_free_text: bool = True

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_answer_modes(self) -> "ClarificationRequest":
        if not self.options and not self.allow_free_text:
            raise ValueError("clarification must allow an option or free-text answer")
        values = [option.value for option in self.options]
        if len(values) != len(set(values)):
            raise ValueError("clarification option values must be unique")
        return self


class CommandResult(BaseModel):
    schema_version: ContractVersion = "1.0"
    command_name: CommandName
    correlation_id: UUID
    status: ResultStatus
    data: dict[str, JsonValue] = Field(default_factory=dict)
    warnings: tuple[WarningDetail, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()
    proposals: tuple[ActionProposal, ...] = ()
    clarification: ClarificationRequest | None = None
    confirmation: ConfirmationRequirement | None = None
    display_summary: str = Field(min_length=1, max_length=2000)
    speakable_text: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_lifecycle_state(self) -> "CommandResult":
        needs_clarification = self.status == ResultStatus.NEEDS_CLARIFICATION
        if needs_clarification != (self.clarification is not None):
            raise ValueError(
                "clarification must be present exactly when status needs clarification"
            )

        requires_confirmation = self.status == ResultStatus.REQUIRES_CONFIRMATION
        if requires_confirmation != (self.confirmation is not None):
            raise ValueError(
                "confirmation must be present exactly when status requires confirmation"
            )

        has_proposal_status = self.status in {
            ResultStatus.PROPOSED,
            ResultStatus.REQUIRES_CONFIRMATION,
        }
        if has_proposal_status != bool(self.proposals):
            raise ValueError(
                "proposals must be present exactly when status is proposed or requires confirmation"
            )

        if self.confirmation is not None and all(
            proposal.proposal_id != self.confirmation.proposal_id
            for proposal in self.proposals
        ):
            raise ValueError("confirmation must reference one of the result proposals")
        return self
