from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.application.authorization import AuthorizationContext
from app.application.contracts import (
    ActionProposal,
    ActorContext,
    ClarificationOption,
    ClarificationRequest,
    CommandEnvelope,
    CommandResult,
    ConfirmationRequirement,
    EvidenceReference,
    EvidenceSourceType,
    IntentKind,
    ProposedMutationIntent,
    ReadIntent,
    ResourceReference,
    ResultStatus,
    SourceChannel,
    WarningDetail,
)
from app.application.dispatcher import (
    CommandDispatcher,
    DuplicateCommandHandlerError,
    UnknownCommandError,
)

CORRELATION_ID = UUID("11111111-1111-4111-8111-111111111111")


def make_read_command(command_name: str = "tasks.list") -> CommandEnvelope:
    return CommandEnvelope(
        intent=ReadIntent(
            name=command_name,
            arguments={"completed": False, "tags": ["fictional"]},
        ),
        source_channel=SourceChannel.TEXT,
        actor=ActorContext(actor_id="local-user", profile_id="local-profile"),
        correlation_id=CORRELATION_ID,
        locale="en-US",
        time_zone="America/Phoenix",
    )


def make_mutation_command(command_name: str = "tasks.update") -> CommandEnvelope:
    return CommandEnvelope(
        intent=ProposedMutationIntent(
            name=command_name,
            target=ResourceReference(resource_type="task", resource_id="task:42"),
            arguments={"is_completed": True},
            reason="The user asked to complete the fictional task.",
        ),
        source_channel=SourceChannel.TEXT,
        actor=ActorContext(actor_id="local-user", profile_id="local-profile"),
        correlation_id=CORRELATION_ID,
        idempotency_key="fictional-request-1",
        locale="en-US",
        time_zone="America/Phoenix",
    )


def test_command_envelope_is_versioned_typed_and_channel_neutral() -> None:
    command = make_read_command()
    serialized = command.model_dump_json()
    restored = CommandEnvelope.model_validate_json(serialized)

    assert restored == command
    assert restored.schema_version == "1.0"
    assert restored.command_name == "tasks.list"
    assert isinstance(restored.intent, ReadIntent)
    assert {channel.value for channel in SourceChannel} == {
        "text",
        "voice",
        "web",
        "mobile",
        "device",
    }


def test_command_discriminates_reads_from_proposed_mutations() -> None:
    mutation = make_mutation_command()
    restored = CommandEnvelope.model_validate_json(mutation.model_dump_json())

    assert isinstance(restored.intent, ProposedMutationIntent)
    assert restored.intent.target == ResourceReference(
        resource_type="task", resource_id="task:42"
    )

    with pytest.raises(ValidationError, match="idempotency key"):
        CommandEnvelope.model_validate(mutation.model_dump(exclude={"idempotency_key"}))

    with pytest.raises(ValidationError, match="only valid for proposed mutations"):
        CommandEnvelope.model_validate(
            make_read_command().model_dump() | {"confirmation_token": "fictional-token"}
        )


def test_command_rejects_invalid_name_and_iana_time_zone() -> None:
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        ReadIntent(name="not a command")

    with pytest.raises(ValidationError, match="valid IANA time zone"):
        CommandEnvelope.model_validate(
            make_read_command().model_dump() | {"time_zone": "Not/AZone"}
        )


def test_result_carries_evidence_proposal_warning_and_confirmation() -> None:
    command = make_mutation_command()
    expires_at = datetime(2026, 11, 9, 18, 0, tzinfo=UTC)
    proposal_id = uuid4()
    result = CommandResult(
        command_name=command.command_name,
        correlation_id=command.correlation_id,
        status=ResultStatus.REQUIRES_CONFIRMATION,
        data={"task_id": 42},
        warnings=(WarningDetail(code="schedule-risk", message="Deadline is close."),),
        evidence=(
            EvidenceReference(
                source_type=EvidenceSourceType.LOCAL_TASK,
                reference_id="task:42",
                summary="Fictional task due tomorrow.",
                observed_at=datetime(2026, 11, 9, 17, 0, tzinfo=UTC),
            ),
        ),
        proposals=(
            ActionProposal(
                proposal_id=proposal_id,
                action="tasks.update",
                summary="Mark the fictional task complete.",
                target=ResourceReference(resource_type="task", resource_id="task:42"),
                arguments={"is_completed": True},
            ),
        ),
        confirmation=ConfirmationRequirement(
            confirmation_id=uuid4(),
            proposal_id=proposal_id,
            token="fictional-confirmation-token",
            expires_at=expires_at,
            reason="Completing a task changes saved state.",
        ),
        display_summary="Ready to complete one fictional task.",
        speakable_text="I can complete one task after you confirm.",
    )

    assert result.schema_version == "1.0"
    assert result.confirmation is not None
    assert result.confirmation.expires_at == expires_at


def test_result_carries_structured_clarification() -> None:
    command = make_read_command("calendar.show")
    result = CommandResult(
        command_name=command.command_name,
        correlation_id=command.correlation_id,
        status=ResultStatus.NEEDS_CLARIFICATION,
        clarification=ClarificationRequest(
            field="range",
            question="Which fictional week should I show?",
            reason="The request did not identify a date range.",
            options=(
                ClarificationOption(value="this_week", label="This week"),
                ClarificationOption(value="next_week", label="Next week"),
            ),
            allow_free_text=True,
        ),
        display_summary="I need a date range before showing the calendar.",
        speakable_text="Which week should I show?",
    )

    assert result.clarification is not None
    assert result.clarification.options[0].value == "this_week"


def test_result_lifecycle_metadata_matches_status() -> None:
    command = make_read_command()
    with pytest.raises(ValidationError, match="clarification must be present"):
        CommandResult(
            command_name=command.command_name,
            correlation_id=command.correlation_id,
            status=ResultStatus.NEEDS_CLARIFICATION,
            display_summary="A clarification is missing.",
            speakable_text="I need more information.",
        )

    with pytest.raises(ValidationError, match="confirmation must be present"):
        CommandResult(
            command_name="tasks.update",
            correlation_id=command.correlation_id,
            status=ResultStatus.REQUIRES_CONFIRMATION,
            proposals=(
                ActionProposal(
                    proposal_id=uuid4(),
                    action="tasks.update",
                    summary="Complete a fictional task.",
                ),
            ),
            display_summary="Confirmation is missing.",
            speakable_text="Confirmation is missing.",
        )

    with pytest.raises(ValidationError, match="proposals must be present"):
        CommandResult(
            command_name="tasks.update",
            correlation_id=command.correlation_id,
            status=ResultStatus.PROPOSED,
            display_summary="The proposal is missing.",
            speakable_text="The proposal is missing.",
        )


def test_contract_rejects_unsafe_temporal_and_clarification_metadata() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        EvidenceReference(
            source_type=EvidenceSourceType.LOCAL_EVENT,
            reference_id="event:fictional",
            summary="A fictional event.",
            observed_at=datetime(2026, 11, 9, 12, 0),
        )

    with pytest.raises(ValidationError, match="option values must be unique"):
        ClarificationRequest(
            field="choice",
            question="Which option?",
            reason="Two records matched.",
            options=(
                ClarificationOption(value="same", label="First"),
                ClarificationOption(value="same", label="Second"),
            ),
        )

    with pytest.raises(ValidationError, match="option or free-text"):
        ClarificationRequest(
            field="choice",
            question="Which option?",
            reason="No answer mode was configured.",
            allow_free_text=False,
        )


def test_dispatcher_preserves_command_identity() -> None:
    dispatcher = CommandDispatcher()
    command = make_read_command()

    def handler(envelope: CommandEnvelope) -> CommandResult:
        return CommandResult(
            command_name=envelope.command_name,
            correlation_id=envelope.correlation_id,
            status=ResultStatus.SUCCEEDED,
            data={"tasks": []},
            display_summary="No fictional tasks matched.",
            speakable_text="No tasks matched.",
        )

    authorization = AuthorizationContext.local(
        actor_id="local-user", profile_id="local-profile"
    )
    dispatcher.register("tasks.list", IntentKind.READ, handler)
    result = dispatcher.dispatch(command, authorization)

    assert result.correlation_id == command.correlation_id
    assert result.data == {"tasks": []}

    with pytest.raises(DuplicateCommandHandlerError):
        dispatcher.register("tasks.list", IntentKind.READ, handler)
    with pytest.raises(UnknownCommandError):
        dispatcher.dispatch(make_read_command("tasks.unknown"), authorization)


def test_confirmation_requires_a_matching_proposal() -> None:
    with pytest.raises(ValidationError, match="reference one of the result proposals"):
        CommandResult(
            command_name="tasks.update",
            correlation_id=CORRELATION_ID,
            status=ResultStatus.REQUIRES_CONFIRMATION,
            proposals=(
                ActionProposal(
                    proposal_id=uuid4(),
                    action="tasks.update",
                    summary="Complete a fictional task.",
                ),
            ),
            confirmation=ConfirmationRequirement(
                confirmation_id=uuid4(),
                proposal_id=uuid4(),
                token="fictional-token",
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
                reason="The saved task would change.",
            ),
            display_summary="A mismatched confirmation was returned.",
            speakable_text="The confirmation did not match.",
        )
