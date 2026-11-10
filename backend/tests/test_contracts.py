from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.application.contracts import (
    ActionProposal,
    ActorContext,
    CommandEnvelope,
    CommandResult,
    ConfirmationRequirement,
    EvidenceReference,
    ResultStatus,
    SourceChannel,
    WarningDetail,
)
from app.application.dispatcher import (
    CommandDispatcher,
    DuplicateCommandHandlerError,
    UnknownCommandError,
)


def make_command(command_name: str = "tasks.list") -> CommandEnvelope:
    return CommandEnvelope(
        command_name=command_name,
        source_channel=SourceChannel.TEXT,
        actor=ActorContext(actor_id="local-user", profile_id="local-profile"),
        correlation_id=UUID("11111111-1111-4111-8111-111111111111"),
        idempotency_key="fictional-request-1",
        locale="en-US",
        time_zone="America/Phoenix",
        arguments={"completed": False, "tags": ["fictional"]},
    )


def test_command_envelope_is_versioned_and_channel_neutral() -> None:
    command = make_command()
    serialized = command.model_dump_json()
    restored = CommandEnvelope.model_validate_json(serialized)

    assert restored == command
    assert restored.schema_version == "1.0"
    assert {channel.value for channel in SourceChannel} == {
        "text",
        "voice",
        "web",
        "mobile",
        "device",
    }


def test_command_rejects_invalid_iana_time_zone() -> None:
    with pytest.raises(ValidationError, match="valid IANA time zone"):
        make_command().model_copy(update={"time_zone": "Not/AZone"}).model_validate(
            make_command().model_dump() | {"time_zone": "Not/AZone"}
        )


def test_result_carries_evidence_proposal_warning_and_confirmation() -> None:
    command = make_command("tasks.update")
    expires_at = datetime(2026, 11, 9, 18, 0, tzinfo=UTC)
    result = CommandResult(
        command_name=command.command_name,
        correlation_id=command.correlation_id,
        status=ResultStatus.REQUIRES_CONFIRMATION,
        data={"task_id": 42},
        warnings=(WarningDetail(code="schedule-risk", message="Deadline is close."),),
        evidence=(
            EvidenceReference(
                source_type="local_task",
                reference_id="task:42",
                summary="Fictional task due tomorrow.",
            ),
        ),
        proposals=(
            ActionProposal(
                proposal_id=uuid4(),
                action="task.update",
                summary="Mark the fictional task complete.",
                arguments={"task_id": 42, "is_completed": True},
            ),
        ),
        confirmation=ConfirmationRequirement(
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


def test_confirmation_metadata_matches_result_status() -> None:
    command = make_command()
    with pytest.raises(ValidationError, match="confirmation must be present"):
        CommandResult(
            command_name=command.command_name,
            correlation_id=command.correlation_id,
            status=ResultStatus.REQUIRES_CONFIRMATION,
            display_summary="Confirmation is missing.",
            speakable_text="Confirmation is missing.",
        )

    with pytest.raises(ValidationError, match="confirmation must be present"):
        CommandResult(
            command_name=command.command_name,
            correlation_id=command.correlation_id,
            status=ResultStatus.SUCCEEDED,
            confirmation=ConfirmationRequirement(
                token="fictional-token",
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
                reason="This metadata does not belong on a successful result.",
            ),
            display_summary="Done.",
            speakable_text="Done.",
        )


def test_dispatcher_preserves_command_identity() -> None:
    dispatcher = CommandDispatcher()
    command = make_command()

    def handler(envelope: CommandEnvelope) -> CommandResult:
        return CommandResult(
            command_name=envelope.command_name,
            correlation_id=envelope.correlation_id,
            status=ResultStatus.SUCCEEDED,
            data={"tasks": []},
            display_summary="No fictional tasks matched.",
            speakable_text="No tasks matched.",
        )

    dispatcher.register("tasks.list", handler)
    result = dispatcher.dispatch(command)

    assert result.correlation_id == command.correlation_id
    assert result.data == {"tasks": []}

    with pytest.raises(DuplicateCommandHandlerError):
        dispatcher.register("tasks.list", handler)
    with pytest.raises(UnknownCommandError):
        dispatcher.dispatch(make_command("tasks.unknown"))

