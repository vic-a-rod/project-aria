from uuid import UUID, uuid4

import pytest

from app.application.authorization import (
    ActorAccessDeniedError,
    AuthorizationContext,
    ProfileAccessDeniedError,
)
from app.application.contracts import (
    ActionProposal,
    ActorContext,
    CommandEnvelope,
    CommandResult,
    IntentKind,
    ProposedMutationIntent,
    ReadIntent,
    ResultStatus,
    SourceChannel,
)
from app.application.dispatcher import (
    CommandDispatcher,
    IntentKindMismatchError,
    UnsafeMutationResultError,
)

CORRELATION_ID = UUID("22222222-2222-4222-8222-222222222222")
AUTHORIZED = AuthorizationContext.local(
    actor_id="fictional-actor", profile_id="fictional-profile"
)


def read_command() -> CommandEnvelope:
    return CommandEnvelope(
        intent=ReadIntent(name="tasks.list"),
        source_channel=SourceChannel.TEXT,
        actor=ActorContext(
            actor_id="fictional-actor", profile_id="fictional-profile"
        ),
        correlation_id=CORRELATION_ID,
    )


def mutation_command(*, confirmation_token: str | None = None) -> CommandEnvelope:
    return CommandEnvelope(
        intent=ProposedMutationIntent(
            name="tasks.update",
            arguments={"task_id": "fictional-task", "is_completed": True},
            reason="The fictional actor requested the change.",
        ),
        source_channel=SourceChannel.TEXT,
        actor=ActorContext(
            actor_id="fictional-actor", profile_id="fictional-profile"
        ),
        correlation_id=CORRELATION_ID,
        idempotency_key="fictional-mutation-1",
        confirmation_token=confirmation_token,
    )


def successful(command: CommandEnvelope) -> CommandResult:
    return CommandResult(
        command_name=command.command_name,
        correlation_id=command.correlation_id,
        status=ResultStatus.SUCCEEDED,
        display_summary="The fictional command succeeded.",
        speakable_text="Done.",
    )


def test_safe_read_is_dispatched_with_trusted_scope() -> None:
    dispatcher = CommandDispatcher()
    command = read_command()
    dispatcher.register("tasks.list", IntentKind.READ, successful)

    assert dispatcher.dispatch(command, AUTHORIZED).status == ResultStatus.SUCCEEDED


def test_actor_and_profile_boundaries_fail_before_handler_execution() -> None:
    calls = 0

    def handler(command: CommandEnvelope) -> CommandResult:
        nonlocal calls
        calls += 1
        return successful(command)

    dispatcher = CommandDispatcher()
    dispatcher.register("tasks.list", IntentKind.READ, handler)

    with pytest.raises(ActorAccessDeniedError):
        dispatcher.dispatch(
            read_command(),
            AuthorizationContext.local(
                actor_id="different-actor", profile_id="fictional-profile"
            ),
        )
    with pytest.raises(ProfileAccessDeniedError):
        dispatcher.dispatch(
            read_command(),
            AuthorizationContext.local(
                actor_id="fictional-actor", profile_id="different-profile"
            ),
        )

    assert calls == 0


def test_route_rejects_the_wrong_intent_kind() -> None:
    dispatcher = CommandDispatcher()
    dispatcher.register("tasks.update", IntentKind.READ, successful)

    with pytest.raises(IntentKindMismatchError, match="expects a read intent"):
        dispatcher.dispatch(mutation_command(), AUTHORIZED)


def test_unconfirmed_mutation_cannot_report_successful_execution() -> None:
    dispatcher = CommandDispatcher()
    dispatcher.register("tasks.update", IntentKind.PROPOSED_MUTATION, successful)

    with pytest.raises(UnsafeMutationResultError, match="unconfirmed mutation"):
        dispatcher.dispatch(mutation_command(), AUTHORIZED)


def test_unconfirmed_mutation_may_return_a_proposal() -> None:
    dispatcher = CommandDispatcher()
    proposal_id = uuid4()

    def propose(command: CommandEnvelope) -> CommandResult:
        return CommandResult(
            command_name=command.command_name,
            correlation_id=command.correlation_id,
            status=ResultStatus.PROPOSED,
            proposals=(
                ActionProposal(
                    proposal_id=proposal_id,
                    action="tasks.update",
                    summary="Complete one fictional task.",
                ),
            ),
            display_summary="One change is ready for review.",
            speakable_text="I prepared one change.",
        )

    dispatcher.register("tasks.update", IntentKind.PROPOSED_MUTATION, propose)

    result = dispatcher.dispatch(mutation_command(), AUTHORIZED)
    assert result.proposals[0].proposal_id == proposal_id


def test_confirmed_mutation_may_report_success_after_handler_validation() -> None:
    dispatcher = CommandDispatcher()
    dispatcher.register("tasks.update", IntentKind.PROPOSED_MUTATION, successful)

    result = dispatcher.dispatch(
        mutation_command(confirmation_token="fictional-confirmation-token"),
        AUTHORIZED,
    )

    assert result.status == ResultStatus.SUCCEEDED


def test_authorization_context_rejects_empty_scope() -> None:
    with pytest.raises(ValueError, match="actor_id"):
        AuthorizationContext(actor_id=" ", profile_ids=frozenset({"profile"}))
    with pytest.raises(ValueError, match="profile_ids"):
        AuthorizationContext(actor_id="actor", profile_ids=frozenset())
