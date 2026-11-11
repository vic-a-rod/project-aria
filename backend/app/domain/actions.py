from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class ProposalStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXECUTED = "executed"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class ProposalEvidence:
    id: str
    source_type: str
    source_reference: str | None
    summary: str
    content_hash: str | None
    observed_at: datetime


@dataclass(frozen=True)
class NewProposalEvidence:
    source_type: str
    source_reference: str | None
    summary: str
    content_hash: str | None
    observed_at: datetime


@dataclass(frozen=True)
class ActionProposal:
    id: str
    profile_id: str
    action_type: str
    target_type: str | None
    target_id: str | None
    payload: dict[str, Any]
    state_hash: str
    status: ProposalStatus
    expires_at: datetime
    evidence: tuple[ProposalEvidence, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewActionProposal:
    profile_id: str
    action_type: str
    target_type: str | None
    target_id: str | None
    payload: dict[str, Any]
    state_hash: str
    expires_at: datetime
    evidence: tuple[NewProposalEvidence, ...]


@dataclass(frozen=True)
class ConfirmationRecord:
    id: str
    proposal_id: str
    state_hash: str
    expires_at: datetime
    confirmed_at: datetime | None
    consumed_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class IssuedConfirmation:
    confirmation: ConfirmationRecord
    token: str


@dataclass(frozen=True)
class ExecutionResult:
    id: str
    proposal_id: str
    confirmation_id: str
    status: ExecutionStatus
    summary: str
    error_code: str | None
    executed_at: datetime


@dataclass(frozen=True)
class NotificationRule:
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


@dataclass(frozen=True)
class NewNotificationRule:
    profile_id: str
    name: str
    event_type: str
    channel: str
    minimum_priority: int
    quiet_hours_respected: bool
    enabled: bool


@dataclass(frozen=True)
class AuditEvent:
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


def _required(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be blank")


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def validate_proposal(proposal: NewActionProposal) -> None:
    _required(proposal.profile_id, "profile_id")
    _required(proposal.action_type, "action_type")
    _required(proposal.state_hash, "state_hash")
    _aware(proposal.expires_at, "expires_at")
    if bool(proposal.target_type) != bool(proposal.target_id):
        raise ValueError("target_type and target_id must be set together")
    for evidence in proposal.evidence:
        _required(evidence.source_type, "evidence source_type")
        _required(evidence.summary, "evidence summary")
        _aware(evidence.observed_at, "evidence observed_at")


def validate_notification_rule(rule: NotificationRule | NewNotificationRule) -> None:
    _required(rule.profile_id, "profile_id")
    _required(rule.name, "name")
    _required(rule.event_type, "event_type")
    _required(rule.channel, "channel")
    if not isinstance(rule.minimum_priority, int) or not 1 <= rule.minimum_priority <= 5:
        raise ValueError("minimum_priority must be between 1 and 5")
    if not isinstance(rule.quiet_hours_respected, bool):
        raise ValueError("quiet_hours_respected is required")
    if not isinstance(rule.enabled, bool):
        raise ValueError("enabled is required")
