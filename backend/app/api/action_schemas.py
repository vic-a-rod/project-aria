from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.actions import NotificationFieldValue
from app.domain.actions import (
    ActionProposal,
    AuditEvent,
    ExecutionResult,
    ExecutionStatus,
    IssuedConfirmation,
    NewActionProposal,
    NewNotificationRule,
    NewProposalEvidence,
    NotificationRule,
    ProposalStatus,
)


class EvidenceInput(BaseModel):
    source_type: str = Field(min_length=1, max_length=100)
    source_reference: str | None = Field(default=None, max_length=1000)
    summary: str = Field(min_length=1)
    content_hash: str | None = Field(default=None, max_length=128)
    observed_at: datetime


class EvidenceRead(EvidenceInput):
    id: str
    model_config = ConfigDict(from_attributes=True)


class ProposalCreate(BaseModel):
    profile_id: str = Field(default="local-default", min_length=1, max_length=100)
    action_type: str = Field(min_length=1, max_length=100)
    target_type: str | None = Field(default=None, max_length=100)
    target_id: str | None = Field(default=None, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    state_hash: str = Field(min_length=1, max_length=128)
    expires_at: datetime
    evidence: list[EvidenceInput] = Field(default_factory=list)
    correlation_id: str | None = Field(default=None, max_length=100)

    def to_domain(self) -> NewActionProposal:
        values = self.model_dump(exclude={"evidence", "correlation_id"})
        return NewActionProposal(
            **values,
            evidence=tuple(
                NewProposalEvidence(**item.model_dump()) for item in self.evidence
            ),
        )


class ProposalRead(BaseModel):
    id: str
    profile_id: str
    action_type: str
    target_type: str | None
    target_id: str | None
    payload: dict[str, Any]
    state_hash: str
    status: ProposalStatus
    expires_at: datetime
    evidence: list[EvidenceRead]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, proposal: ActionProposal) -> "ProposalRead":
        return cls.model_validate(proposal)


class ConfirmationIssue(BaseModel):
    lifetime_minutes: int = Field(default=10, ge=1, le=60)


class ConfirmationRead(BaseModel):
    id: str
    proposal_id: str
    state_hash: str
    expires_at: datetime
    confirmed_at: datetime | None
    consumed_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ConfirmationIssued(ConfirmationRead):
    token: str

    @classmethod
    def from_domain(cls, issued: IssuedConfirmation) -> "ConfirmationIssued":
        return cls.model_validate({**issued.confirmation.__dict__, "token": issued.token})


class ConfirmationConfirm(BaseModel):
    token: str = Field(min_length=1)
    current_state_hash: str = Field(min_length=1, max_length=128)


class ExecutionCreate(BaseModel):
    confirmation_id: str = Field(min_length=1, max_length=36)
    status: ExecutionStatus
    summary: str = Field(min_length=1)
    error_code: str | None = Field(default=None, max_length=100)


class ExecutionRead(BaseModel):
    id: str
    proposal_id: str
    confirmation_id: str
    status: ExecutionStatus
    summary: str
    error_code: str | None
    executed_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, result: ExecutionResult) -> "ExecutionRead":
        return cls.model_validate(result)


class NotificationRuleCreate(BaseModel):
    profile_id: str = Field(default="local-default", min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=100)
    channel: str = Field(default="local", min_length=1, max_length=100)
    minimum_priority: int = Field(default=3, ge=1, le=5)
    quiet_hours_respected: bool = True
    enabled: bool = True

    def to_domain(self) -> NewNotificationRule:
        return NewNotificationRule(**self.model_dump())


class NotificationRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    event_type: str | None = Field(default=None, min_length=1, max_length=100)
    channel: str | None = Field(default=None, min_length=1, max_length=100)
    minimum_priority: int | None = Field(default=None, ge=1, le=5)
    quiet_hours_respected: bool | None = None
    enabled: bool | None = None

    def to_changes(self) -> dict[str, NotificationFieldValue]:
        return self.model_dump(exclude_unset=True)


class NotificationRuleRead(BaseModel):
    id: str
    profile_id: str
    name: str
    event_type: str
    channel: str
    minimum_priority: int
    quiet_hours_respected: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, rule: NotificationRule) -> "NotificationRuleRead":
        return cls.model_validate(rule)


class AuditEventRead(BaseModel):
    id: str
    profile_id: str
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    outcome: str
    correlation_id: str | None
    details: dict[str, Any]
    occurred_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, event: AuditEvent) -> "AuditEventRead":
        return cls.model_validate(event)
