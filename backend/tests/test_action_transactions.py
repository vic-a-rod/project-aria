from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.application.actions import ActionService
from app.domain.actions import ExecutionStatus, NewActionProposal, ProposalStatus
from app.infrastructure.action_repository import SqlAlchemyActionRepository
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.migrations_runner import upgrade_database
from app.infrastructure.models import (
    ActionProposalRow,
    ConfirmationRecordRow,
    ExecutionResultRow,
)


@dataclass(frozen=True)
class FixedClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant

    def today(self) -> date:
        return self.instant.date()


def test_execution_transition_rolls_back_as_one_unit_when_audit_fails(
    tmp_path, monkeypatch
) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'atomic-actions.db').as_posix()}"
    )
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 11, 9, 17, 0, tzinfo=UTC))

    with sessions() as session:
        repository = SqlAlchemyActionRepository(session)
        service = ActionService(repository, clock)
        proposal = service.create_proposal(
            NewActionProposal(
                profile_id="local-default",
                action_type="task.update",
                target_type="task",
                target_id="fictional-task-atomic",
                payload={"importance": 4},
                state_hash="sha256:fictional-atomic-state",
                expires_at=datetime(2026, 11, 9, 18, 0, tzinfo=UTC),
                evidence=(),
            )
        )
        issued = service.issue_confirmation(proposal.id, actor_id="fictional-operator")
        service.confirm(
            issued.confirmation.id,
            token=issued.token,
            current_state_hash=proposal.state_hash,
            actor_id="fictional-operator",
        )

        def fail_audit(_event) -> None:
            raise RuntimeError("fictional audit write failure")

        monkeypatch.setattr(repository, "append_audit_event", fail_audit)
        with pytest.raises(RuntimeError, match="fictional audit write failure"):
            service.record_execution(
                proposal.id,
                issued.confirmation.id,
                status=ExecutionStatus.SUCCEEDED,
                summary="Fictional execution that must roll back.",
                error_code=None,
                actor_id="fictional-operator",
            )
        session.rollback()

        proposal_row = session.get(ActionProposalRow, proposal.id)
        confirmation_row = session.get(ConfirmationRecordRow, issued.confirmation.id)
        execution_rows = session.scalars(select(ExecutionResultRow)).all()
        assert proposal_row is not None
        assert proposal_row.status == ProposalStatus.CONFIRMED.value
        assert confirmation_row is not None
        assert confirmation_row.consumed_at is None
        assert execution_rows == []

    engine.dispose()
