from dataclasses import replace
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from typing import Any, Protocol
from uuid import uuid4

from app.application.clock import Clock
from app.domain.actions import (
    ActionProposal,
    AuditEvent,
    ConfirmationRecord,
    ExecutionResult,
    ExecutionStatus,
    IssuedConfirmation,
    NewActionProposal,
    NewNotificationRule,
    NotificationRule,
    ProposalStatus,
    validate_notification_rule,
    validate_proposal,
)

NotificationFieldValue = str | int | bool


class ActionRepository(Protocol):
    def list_proposals(
        self, *, profile_id: str, status: ProposalStatus | None = None
    ) -> list[ActionProposal]: ...
    def get_proposal(self, proposal_id: str) -> ActionProposal | None: ...
    def create_proposal(
        self, proposal_id: str, proposal: NewActionProposal, *, timestamp: datetime
    ) -> ActionProposal: ...
    def set_proposal_status(
        self, proposal_id: str, status: ProposalStatus, *, timestamp: datetime
    ) -> ActionProposal | None: ...
    def create_confirmation(
        self,
        confirmation_id: str,
        proposal_id: str,
        token_hash: str,
        state_hash: str,
        expires_at: datetime,
        *,
        timestamp: datetime,
    ) -> ConfirmationRecord: ...
    def get_confirmation_with_hash(
        self, confirmation_id: str
    ) -> tuple[ConfirmationRecord, str] | None: ...
    def confirm_confirmation(
        self, confirmation_id: str, *, timestamp: datetime
    ) -> ConfirmationRecord | None: ...
    def consume_confirmation(
        self, confirmation_id: str, *, timestamp: datetime
    ) -> ConfirmationRecord | None: ...
    def create_execution_result(
        self,
        result_id: str,
        proposal_id: str,
        confirmation_id: str,
        status: ExecutionStatus,
        summary: str,
        error_code: str | None,
        *,
        timestamp: datetime,
    ) -> ExecutionResult: ...
    def list_notification_rules(self, *, profile_id: str) -> list[NotificationRule]: ...
    def get_notification_rule(self, rule_id: str) -> NotificationRule | None: ...
    def create_notification_rule(
        self, rule_id: str, rule: NewNotificationRule, *, timestamp: datetime
    ) -> NotificationRule: ...
    def update_notification_rule(
        self,
        rule_id: str,
        changes: dict[str, NotificationFieldValue],
        *,
        timestamp: datetime,
    ) -> NotificationRule | None: ...
    def delete_notification_rule(self, rule_id: str) -> bool: ...
    def append_audit_event(self, event: AuditEvent) -> None: ...
    def list_audit_events(self, *, profile_id: str, limit: int) -> list[AuditEvent]: ...


class ActionNotFoundError(LookupError):
    pass


class ActionStateError(ValueError):
    pass


class ActionService:
    def __init__(self, repository: ActionRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def _audit(
        self,
        *,
        profile_id: str,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        outcome: str = "success",
        correlation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._repository.append_audit_event(
            AuditEvent(
                id=str(uuid4()),
                profile_id=profile_id,
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                outcome=outcome,
                correlation_id=correlation_id,
                details=details or {},
                occurred_at=self._clock.now(),
            )
        )

    def create_proposal(
        self,
        proposal: NewActionProposal,
        *,
        actor_id: str = "local-user",
        correlation_id: str | None = None,
    ) -> ActionProposal:
        validate_proposal(proposal)
        now = self._clock.now()
        if proposal.expires_at <= now:
            raise ValueError("expires_at must be in the future")
        created = self._repository.create_proposal(
            str(uuid4()), proposal, timestamp=now
        )
        self._audit(
            profile_id=created.profile_id,
            actor_id=actor_id,
            action="proposal.created",
            entity_type="proposal",
            entity_id=created.id,
            correlation_id=correlation_id,
            details={"action_type": created.action_type},
        )
        return created

    def get_proposal(self, proposal_id: str) -> ActionProposal:
        proposal = self._repository.get_proposal(proposal_id)
        if proposal is None:
            raise ActionNotFoundError(proposal_id)
        if proposal.status == ProposalStatus.PENDING and proposal.expires_at <= self._clock.now():
            expired = self._repository.set_proposal_status(
                proposal.id, ProposalStatus.EXPIRED, timestamp=self._clock.now()
            )
            if expired is not None:
                self._audit(
                    profile_id=proposal.profile_id,
                    actor_id="system",
                    action="proposal.expired",
                    entity_type="proposal",
                    entity_id=proposal.id,
                )
                return expired
        return proposal

    def list_proposals(
        self, *, profile_id: str = "local-default", status: ProposalStatus | None = None
    ) -> list[ActionProposal]:
        proposals = self._repository.list_proposals(profile_id=profile_id, status=status)
        return [self.get_proposal(item.id) for item in proposals]

    def reject_proposal(self, proposal_id: str, *, actor_id: str) -> ActionProposal:
        proposal = self.get_proposal(proposal_id)
        if proposal.status != ProposalStatus.PENDING:
            raise ActionStateError("only pending proposals can be rejected")
        updated = self._repository.set_proposal_status(
            proposal.id, ProposalStatus.REJECTED, timestamp=self._clock.now()
        )
        if updated is None:
            raise ActionNotFoundError(proposal_id)
        self._audit(
            profile_id=proposal.profile_id,
            actor_id=actor_id,
            action="proposal.rejected",
            entity_type="proposal",
            entity_id=proposal.id,
        )
        return updated

    def issue_confirmation(
        self, proposal_id: str, *, lifetime_minutes: int = 10, actor_id: str
    ) -> IssuedConfirmation:
        proposal = self.get_proposal(proposal_id)
        if proposal.status != ProposalStatus.PENDING:
            raise ActionStateError("only pending proposals can be confirmed")
        if not 1 <= lifetime_minutes <= 60:
            raise ValueError("lifetime_minutes must be between 1 and 60")
        now = self._clock.now()
        expires_at = min(proposal.expires_at, now + timedelta(minutes=lifetime_minutes))
        token = token_urlsafe(32)
        record = self._repository.create_confirmation(
            str(uuid4()),
            proposal.id,
            sha256(token.encode()).hexdigest(),
            proposal.state_hash,
            expires_at,
            timestamp=now,
        )
        self._audit(
            profile_id=proposal.profile_id,
            actor_id=actor_id,
            action="confirmation.issued",
            entity_type="confirmation",
            entity_id=record.id,
            details={"proposal_id": proposal.id},
        )
        return IssuedConfirmation(record, token)

    def confirm(
        self,
        confirmation_id: str,
        *,
        token: str,
        current_state_hash: str,
        actor_id: str,
    ) -> ConfirmationRecord:
        loaded = self._repository.get_confirmation_with_hash(confirmation_id)
        if loaded is None:
            raise ActionNotFoundError(confirmation_id)
        confirmation, stored_hash = loaded
        proposal = self.get_proposal(confirmation.proposal_id)
        now = self._clock.now()
        if confirmation.confirmed_at is not None:
            raise ActionStateError("confirmation has already been used")
        if confirmation.revoked_at is not None or confirmation.expires_at <= now:
            raise ActionStateError("confirmation has expired or been revoked")
        if proposal.status != ProposalStatus.PENDING:
            raise ActionStateError("proposal is no longer pending")
        if current_state_hash != confirmation.state_hash:
            raise ActionStateError("target state has changed")
        if not compare_digest(sha256(token.encode()).hexdigest(), stored_hash):
            raise ActionStateError("confirmation token is invalid")
        updated = self._repository.confirm_confirmation(confirmation.id, timestamp=now)
        proposal_updated = self._repository.set_proposal_status(
            proposal.id, ProposalStatus.CONFIRMED, timestamp=now
        )
        if updated is None or proposal_updated is None:
            raise ActionNotFoundError(confirmation_id)
        self._audit(
            profile_id=proposal.profile_id,
            actor_id=actor_id,
            action="confirmation.confirmed",
            entity_type="confirmation",
            entity_id=confirmation.id,
            details={"proposal_id": proposal.id},
        )
        return updated

    def record_execution(
        self,
        proposal_id: str,
        confirmation_id: str,
        *,
        status: ExecutionStatus,
        summary: str,
        error_code: str | None,
        actor_id: str,
    ) -> ExecutionResult:
        if not summary.strip():
            raise ValueError("summary must not be blank")
        proposal = self.get_proposal(proposal_id)
        loaded = self._repository.get_confirmation_with_hash(confirmation_id)
        if loaded is None:
            raise ActionNotFoundError(confirmation_id)
        confirmation, _ = loaded
        if confirmation.proposal_id != proposal.id:
            raise ActionStateError("confirmation does not belong to proposal")
        if proposal.status != ProposalStatus.CONFIRMED or confirmation.confirmed_at is None:
            raise ActionStateError("proposal must be confirmed before execution")
        if confirmation.consumed_at is not None:
            raise ActionStateError("confirmation has already been consumed")
        now = self._clock.now()
        if confirmation.expires_at <= now:
            raise ActionStateError("confirmation has expired")
        consumed = self._repository.consume_confirmation(confirmation.id, timestamp=now)
        if consumed is None:
            raise ActionNotFoundError(confirmation_id)
        result = self._repository.create_execution_result(
            str(uuid4()),
            proposal.id,
            confirmation.id,
            status,
            summary,
            error_code,
            timestamp=now,
        )
        final_status = (
            ProposalStatus.EXECUTED
            if status == ExecutionStatus.SUCCEEDED
            else ProposalStatus.FAILED
        )
        self._repository.set_proposal_status(proposal.id, final_status, timestamp=now)
        self._audit(
            profile_id=proposal.profile_id,
            actor_id=actor_id,
            action="proposal.executed",
            entity_type="proposal",
            entity_id=proposal.id,
            outcome=status.value,
            details={"execution_result_id": result.id},
        )
        return result

    def list_notification_rules(
        self, *, profile_id: str = "local-default"
    ) -> list[NotificationRule]:
        return self._repository.list_notification_rules(profile_id=profile_id)

    def create_notification_rule(
        self, rule: NewNotificationRule, *, actor_id: str
    ) -> NotificationRule:
        validate_notification_rule(rule)
        created = self._repository.create_notification_rule(
            str(uuid4()), rule, timestamp=self._clock.now()
        )
        self._audit(
            profile_id=created.profile_id,
            actor_id=actor_id,
            action="notification_rule.created",
            entity_type="notification_rule",
            entity_id=created.id,
        )
        return created

    def update_notification_rule(
        self,
        rule_id: str,
        changes: dict[str, NotificationFieldValue],
        *,
        actor_id: str,
    ) -> NotificationRule:
        current = self._repository.get_notification_rule(rule_id)
        if current is None:
            raise ActionNotFoundError(rule_id)
        candidate = replace(current, **changes)
        validate_notification_rule(candidate)
        updated = self._repository.update_notification_rule(
            rule_id, changes, timestamp=self._clock.now()
        )
        if updated is None:
            raise ActionNotFoundError(rule_id)
        self._audit(
            profile_id=current.profile_id,
            actor_id=actor_id,
            action="notification_rule.updated",
            entity_type="notification_rule",
            entity_id=current.id,
        )
        return updated

    def delete_notification_rule(self, rule_id: str, *, actor_id: str) -> None:
        current = self._repository.get_notification_rule(rule_id)
        if current is None or not self._repository.delete_notification_rule(rule_id):
            raise ActionNotFoundError(rule_id)
        self._audit(
            profile_id=current.profile_id,
            actor_id=actor_id,
            action="notification_rule.deleted",
            entity_type="notification_rule",
            entity_id=current.id,
        )

    def list_audit_events(
        self, *, profile_id: str = "local-default", limit: int = 100
    ) -> list[AuditEvent]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        return self._repository.list_audit_events(profile_id=profile_id, limit=limit)
