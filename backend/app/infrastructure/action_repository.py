import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.application.actions import NotificationFieldValue
from app.domain.actions import (
    ActionProposal,
    AuditEvent,
    ConfirmationRecord,
    ExecutionResult,
    ExecutionStatus,
    NewActionProposal,
    NewNotificationRule,
    NotificationRule,
    ProposalEvidence,
    ProposalStatus,
)
from app.infrastructure.models import (
    ActionProposalRow,
    AuditEventRow,
    ConfirmationRecordRow,
    ExecutionResultRow,
    NotificationRuleRow,
    ProposalEvidenceRow,
)


def _dump(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class SqlAlchemyActionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()

    def _proposal_statement(self):
        return select(ActionProposalRow).options(
            selectinload(ActionProposalRow.evidence)
        )

    def list_proposals(
        self, *, profile_id: str, status: ProposalStatus | None = None
    ) -> list[ActionProposal]:
        statement = self._proposal_statement().where(
            ActionProposalRow.profile_id == profile_id
        )
        if status is not None:
            statement = statement.where(ActionProposalRow.status == status.value)
        rows = self._session.scalars(
            statement.order_by(ActionProposalRow.created_at.desc())
        ).all()
        return [self._proposal(row) for row in rows]

    def get_proposal(self, proposal_id: str) -> ActionProposal | None:
        row = self._session.scalar(
            self._proposal_statement().where(ActionProposalRow.id == proposal_id)
        )
        return self._proposal(row) if row else None

    def create_proposal(
        self, proposal_id: str, proposal: NewActionProposal, *, timestamp: datetime
    ) -> ActionProposal:
        row = ActionProposalRow(
            id=proposal_id,
            profile_id=proposal.profile_id,
            action_type=proposal.action_type,
            target_type=proposal.target_type,
            target_id=proposal.target_id,
            payload_json=_dump(proposal.payload),
            state_hash=proposal.state_hash,
            status=ProposalStatus.PENDING.value,
            expires_at=proposal.expires_at,
            created_at=timestamp,
            updated_at=timestamp,
            evidence=[
                ProposalEvidenceRow(
                    id=str(uuid4()),
                    source_type=item.source_type,
                    source_reference=item.source_reference,
                    summary=item.summary,
                    content_hash=item.content_hash,
                    observed_at=item.observed_at,
                )
                for item in proposal.evidence
            ],
        )
        self._session.add(row)
        self._session.flush()
        created = self.get_proposal(row.id)
        if created is None:  # pragma: no cover
            raise RuntimeError("Proposal could not be reloaded")
        return created

    def set_proposal_status(
        self, proposal_id: str, status: ProposalStatus, *, timestamp: datetime
    ) -> ActionProposal | None:
        row = self._session.get(ActionProposalRow, proposal_id)
        if row is None:
            return None
        row.status = status.value
        row.updated_at = timestamp
        self._session.flush()
        return self.get_proposal(proposal_id)

    def create_confirmation(
        self,
        confirmation_id: str,
        proposal_id: str,
        token_hash: str,
        state_hash: str,
        expires_at: datetime,
        *,
        timestamp: datetime,
    ) -> ConfirmationRecord:
        row = ConfirmationRecordRow(
            id=confirmation_id,
            proposal_id=proposal_id,
            token_hash=token_hash,
            state_hash=state_hash,
            expires_at=expires_at,
            confirmed_at=None,
            consumed_at=None,
            revoked_at=None,
            created_at=timestamp,
        )
        self._session.add(row)
        self._session.flush()
        return self._confirmation(row)

    def get_confirmation_with_hash(
        self, confirmation_id: str
    ) -> tuple[ConfirmationRecord, str] | None:
        row = self._session.get(ConfirmationRecordRow, confirmation_id)
        return (self._confirmation(row), row.token_hash) if row else None

    def confirm_confirmation(
        self, confirmation_id: str, *, timestamp: datetime
    ) -> ConfirmationRecord | None:
        row = self._session.get(ConfirmationRecordRow, confirmation_id)
        if row is None:
            return None
        row.confirmed_at = timestamp
        self._session.flush()
        return self._confirmation(row)

    def consume_confirmation(
        self, confirmation_id: str, *, timestamp: datetime
    ) -> ConfirmationRecord | None:
        row = self._session.get(ConfirmationRecordRow, confirmation_id)
        if row is None:
            return None
        row.consumed_at = timestamp
        self._session.flush()
        return self._confirmation(row)

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
    ) -> ExecutionResult:
        row = ExecutionResultRow(
            id=result_id,
            proposal_id=proposal_id,
            confirmation_id=confirmation_id,
            status=status.value,
            summary=summary,
            error_code=error_code,
            executed_at=timestamp,
        )
        self._session.add(row)
        self._session.flush()
        return self._execution(row)

    def list_notification_rules(self, *, profile_id: str) -> list[NotificationRule]:
        rows = self._session.scalars(
            select(NotificationRuleRow)
            .where(NotificationRuleRow.profile_id == profile_id)
            .order_by(NotificationRuleRow.name, NotificationRuleRow.id)
        ).all()
        return [self._notification_rule(row) for row in rows]

    def get_notification_rule(self, rule_id: str) -> NotificationRule | None:
        row = self._session.get(NotificationRuleRow, rule_id)
        return self._notification_rule(row) if row else None

    def create_notification_rule(
        self, rule_id: str, rule: NewNotificationRule, *, timestamp: datetime
    ) -> NotificationRule:
        row = NotificationRuleRow(
            id=rule_id, **rule.__dict__, created_at=timestamp, updated_at=timestamp
        )
        self._session.add(row)
        self._session.flush()
        return self._notification_rule(row)

    def update_notification_rule(
        self,
        rule_id: str,
        changes: dict[str, NotificationFieldValue],
        *,
        timestamp: datetime,
    ) -> NotificationRule | None:
        row = self._session.get(NotificationRuleRow, rule_id)
        if row is None:
            return None
        for field, value in changes.items():
            setattr(row, field, value)
        row.updated_at = timestamp
        self._session.flush()
        return self._notification_rule(row)

    def delete_notification_rule(self, rule_id: str) -> bool:
        row = self._session.get(NotificationRuleRow, rule_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def append_audit_event(self, event: AuditEvent) -> None:
        self._session.add(
            AuditEventRow(
                id=event.id,
                profile_id=event.profile_id,
                actor_id=event.actor_id,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                outcome=event.outcome,
                correlation_id=event.correlation_id,
                details_json=_dump(event.details),
                occurred_at=event.occurred_at,
            )
        )
        self._session.flush()

    def list_audit_events(self, *, profile_id: str, limit: int) -> list[AuditEvent]:
        rows = self._session.scalars(
            select(AuditEventRow)
            .where(AuditEventRow.profile_id == profile_id)
            .order_by(AuditEventRow.occurred_at.desc(), AuditEventRow.id.desc())
            .limit(limit)
        ).all()
        return [self._audit_event(row) for row in rows]

    @staticmethod
    def _proposal(row: ActionProposalRow) -> ActionProposal:
        return ActionProposal(
            id=row.id,
            profile_id=row.profile_id,
            action_type=row.action_type,
            target_type=row.target_type,
            target_id=row.target_id,
            payload=json.loads(row.payload_json),
            state_hash=row.state_hash,
            status=ProposalStatus(row.status),
            expires_at=row.expires_at,
            evidence=tuple(
                ProposalEvidence(
                    id=item.id,
                    source_type=item.source_type,
                    source_reference=item.source_reference,
                    summary=item.summary,
                    content_hash=item.content_hash,
                    observed_at=item.observed_at,
                )
                for item in row.evidence
            ),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _confirmation(row: ConfirmationRecordRow) -> ConfirmationRecord:
        return ConfirmationRecord(
            id=row.id,
            proposal_id=row.proposal_id,
            state_hash=row.state_hash,
            expires_at=row.expires_at,
            confirmed_at=row.confirmed_at,
            consumed_at=row.consumed_at,
            revoked_at=row.revoked_at,
            created_at=row.created_at,
        )

    @staticmethod
    def _execution(row: ExecutionResultRow) -> ExecutionResult:
        return ExecutionResult(
            id=row.id,
            proposal_id=row.proposal_id,
            confirmation_id=row.confirmation_id,
            status=ExecutionStatus(row.status),
            summary=row.summary,
            error_code=row.error_code,
            executed_at=row.executed_at,
        )

    @staticmethod
    def _notification_rule(row: NotificationRuleRow) -> NotificationRule:
        return NotificationRule(
            id=row.id,
            profile_id=row.profile_id,
            name=row.name,
            event_type=row.event_type,
            channel=row.channel,
            minimum_priority=row.minimum_priority,
            quiet_hours_respected=row.quiet_hours_respected,
            enabled=row.enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _audit_event(row: AuditEventRow) -> AuditEvent:
        return AuditEvent(
            id=row.id,
            profile_id=row.profile_id,
            actor_id=row.actor_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            outcome=row.outcome,
            correlation_id=row.correlation_id,
            details=json.loads(row.details_json),
            occurred_at=row.occurred_at,
        )
