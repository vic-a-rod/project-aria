from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.application.actions import ActionService
from app.application.command_results import (
    CommandPresentationError,
    CommandResultPresenter,
    MutationPreview,
    ProposalEvidenceInput,
)
from app.application.contracts import (
    ActorContext,
    ClarificationOption,
    ClarificationRequest,
    CommandEnvelope,
    EvidenceReference,
    EvidenceSourceType,
    ProposedChange,
    ProposedMutationIntent,
    ReadIntent,
    ReasoningDetail,
    ResourceReference,
    ResultStatus,
    SourceChannel,
    WarningDetail,
    WarningSeverity,
)
from app.domain.actions import ProposalStatus
from app.infrastructure.action_repository import SqlAlchemyActionRepository
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.migrations_runner import upgrade_database
from app.infrastructure.models import ConfirmationRecordRow

NOW = datetime(2026, 11, 18, 19, 0, tzinfo=UTC)
CORRELATION_ID = UUID("66666666-6666-4666-8666-666666666666")


@dataclass(frozen=True)
class FixedClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant

    def today(self) -> date:
        return self.instant.date()


def mutation_command(*, confirmation_token: str | None = None) -> CommandEnvelope:
    return CommandEnvelope(
        intent=ProposedMutationIntent(
            name="events.update",
            target=ResourceReference(resource_type="event", resource_id="event:42"),
            arguments={"start_at": "2026-11-20T18:00:00Z"},
            reason="The user asked to move the fictional event.",
        ),
        source_channel=SourceChannel.TEXT,
        actor=ActorContext(
            actor_id="fictional-actor", profile_id="fictional-profile"
        ),
        correlation_id=CORRELATION_ID,
        idempotency_key="fictional-preview-request",
        confirmation_token=confirmation_token,
    )


def read_command() -> CommandEnvelope:
    return CommandEnvelope(
        intent=ReadIntent(name="calendar.show", arguments={"range": "week"}),
        source_channel=SourceChannel.TEXT,
        actor=ActorContext(
            actor_id="fictional-actor", profile_id="fictional-profile"
        ),
        correlation_id=CORRELATION_ID,
    )


def evidence() -> EvidenceReference:
    return EvidenceReference(
        source_type=EvidenceSourceType.USER_INPUT,
        reference_id="request:fictional",
        summary="The user requested a fictional event change.",
        observed_at=NOW,
    )


def preview() -> MutationPreview:
    return MutationPreview(
        summary="Move the fictional event by one hour.",
        changes=(
            ProposedChange(
                field="start_at",
                before="2026-11-20T17:00:00Z",
                after="2026-11-20T18:00:00Z",
            ),
        ),
        evidence=(
            ProposalEvidenceInput(
                reference=evidence(), content_hash="sha256:fictional-evidence"
            ),
        ),
        reasoning=(
            ReasoningDetail(
                code="user_requested_time_change",
                summary="The requested start time is one hour later.",
                details={"offset_minutes": 60},
            ),
        ),
        warnings=(
            WarningDetail(
                code="schedule_conflict",
                message="The new time may overlap a fictional commitment.",
                severity=WarningSeverity.WARNING,
            ),
        ),
        state_hash="sha256:fictional-current-event",
        proposal_expires_at=NOW + timedelta(hours=1),
        confirmation_reason="Moving an event changes saved calendar state.",
        display_summary="Review the event time change and conflict warning.",
        speakable_text="I can move the event after you confirm.",
        confirmation_lifetime_minutes=10,
    )


def test_mutation_preview_persists_evidence_and_issues_expiring_confirmation(
    tmp_path,
) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'command-results.db').as_posix()}"
    )
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            actions = ActionService(SqlAlchemyActionRepository(session), FixedClock(NOW))
            presenter = CommandResultPresenter(actions)

            result = presenter.proposed_mutation(mutation_command(), preview())

            assert result.status == ResultStatus.REQUIRES_CONFIRMATION
            assert result.proposals[0].changes[0].field == "start_at"
            assert result.evidence == (evidence(),)
            assert result.reasoning[0].code == "user_requested_time_change"
            assert result.warnings[0].code == "schedule_conflict"
            assert result.confirmation is not None
            assert result.confirmation.expires_at == NOW + timedelta(minutes=10)

            proposal = actions.get_proposal(str(result.proposals[0].proposal_id))
            assert proposal.profile_id == "fictional-profile"
            assert proposal.state_hash == "sha256:fictional-current-event"
            assert proposal.payload["changes"][0]["field"] == "start_at"
            assert proposal.evidence[0].source_reference == "request:fictional"

            confirmation_row = session.get(
                ConfirmationRecordRow, str(result.confirmation.confirmation_id)
            )
            assert confirmation_row is not None
            assert confirmation_row.token_hash != result.confirmation.token

            actions.confirm(
                str(result.confirmation.confirmation_id),
                token=result.confirmation.token,
                current_state_hash=proposal.state_hash,
                actor_id="fictional-actor",
            )
            assert actions.get_proposal(proposal.id).status == ProposalStatus.CONFIRMED
    finally:
        engine.dispose()


def test_clarification_and_read_results_carry_reasoning_and_sources(tmp_path) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'presentation-only.db').as_posix()}"
    )
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            presenter = CommandResultPresenter(
                ActionService(SqlAlchemyActionRepository(session), FixedClock(NOW))
            )
            reasoning = (
                ReasoningDetail(
                    code="ambiguous_range",
                    summary="The request did not identify a calendar week.",
                ),
            )
            clarification = presenter.clarification(
                read_command(),
                ClarificationRequest(
                    field="range",
                    question="Which week should I show?",
                    reason="A date range is required.",
                    options=(
                        ClarificationOption(value="this_week", label="This week"),
                        ClarificationOption(value="next_week", label="Next week"),
                    ),
                ),
                evidence=(evidence(),),
                reasoning=reasoning,
                display_summary="Choose a week to continue.",
                speakable_text="Which week should I show?",
            )
            assert clarification.status == ResultStatus.NEEDS_CLARIFICATION
            assert clarification.reasoning == reasoning

            successful = presenter.successful_read(
                read_command(),
                data={"events": []},
                evidence=(evidence(),),
                reasoning=(
                    ReasoningDetail(
                        code="no_matching_events",
                        summary="No fictional events matched the selected week.",
                    ),
                ),
                display_summary="No events matched.",
                speakable_text="You have no matching events.",
            )
            assert successful.status == ResultStatus.SUCCEEDED
            assert successful.evidence == (evidence(),)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("changes", (), "proposed changes"),
        ("evidence", (), "requires evidence"),
        ("reasoning", (), "requires reasoning"),
        ("state_hash", " ", "state hash"),
        ("display_summary", " ", "display summary"),
        ("confirmation_lifetime_minutes", 0, "confirmation lifetime"),
    ],
)
def test_incomplete_mutation_preview_fails_before_persistence(
    tmp_path, field: str, value, message: str
) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / f'invalid-{field}.db').as_posix()}"
    )
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            presenter = CommandResultPresenter(
                ActionService(SqlAlchemyActionRepository(session), FixedClock(NOW))
            )
            with pytest.raises(CommandPresentationError, match=message):
                presenter.proposed_mutation(
                    mutation_command(), replace(preview(), **{field: value})
                )
    finally:
        engine.dispose()


def test_preview_rejects_read_and_already_confirmed_commands(tmp_path) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'invalid-commands.db').as_posix()}"
    )
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            presenter = CommandResultPresenter(
                ActionService(SqlAlchemyActionRepository(session), FixedClock(NOW))
            )
            with pytest.raises(CommandPresentationError, match="proposed mutation intent"):
                presenter.proposed_mutation(read_command(), preview())
            with pytest.raises(CommandPresentationError, match="confirmed command"):
                presenter.proposed_mutation(
                    mutation_command(confirmation_token="fictional-token"), preview()
                )
    finally:
        engine.dispose()


def test_proposed_change_requires_an_actual_difference() -> None:
    with pytest.raises(ValidationError, match="must differ"):
        ProposedChange(field="title", before="Same", after="Same")
