from uuid import UUID

import pytest

from app.application.contracts import (
    ActorContext,
    IntentKind,
    ProposedMutationIntent,
    ReadIntent,
    SourceChannel,
)
from app.application.interpretation import (
    IntentCatalog,
    NaturalLanguageInterpretationError,
    NaturalLanguageInterpreter,
    NaturalLanguageRequest,
    UnsupportedIntentError,
)
from app.application.language_models import (
    LanguageModelDescriptor,
    LanguageModelGateway,
    LanguageModelProviderKind,
    LanguageModelRequest,
    LanguageModelResponse,
)

CORRELATION_ID = UUID("55555555-5555-4555-8555-555555555555")


class RecordingAdapter:
    descriptor = LanguageModelDescriptor(
        provider="fictional-provider",
        model="fictional-model",
        kind=LanguageModelProviderKind.CLOUD,
    )

    def __init__(self, content: str) -> None:
        self.content = content
        self.requests: list[LanguageModelRequest] = []

    def generate(self, request: LanguageModelRequest) -> LanguageModelResponse:
        self.requests.append(request)
        return LanguageModelResponse(
            correlation_id=request.correlation_id,
            content=self.content,
        )


def natural_request(
    *, idempotency_key: str | None = "fictional-request-1"
) -> NaturalLanguageRequest:
    return NaturalLanguageRequest(
        text="Please interpret this fictional request.",
        actor=ActorContext(
            actor_id="fictional-actor", profile_id="fictional-profile"
        ),
        source_channel=SourceChannel.TEXT,
        correlation_id=CORRELATION_ID,
        locale="en-US",
        time_zone="America/Phoenix",
        idempotency_key=idempotency_key,
    )


@pytest.mark.parametrize(
    ("content", "expected_name", "expected_kind"),
    [
        ('{"kind":"read","name":"tasks.list","arguments":{}}', "tasks.list", IntentKind.READ),
        (
            '{"kind":"proposed_mutation","name":"events.create",'
            '"arguments":{"title":"Fictional appointment"},'
            '"reason":"The user requested an event."}',
            "events.create",
            IntentKind.PROPOSED_MUTATION,
        ),
        (
            '{"kind":"proposed_mutation","name":"applications.update",'
            '"arguments":{"status":"interviewing"},'
            '"reason":"The user reported an interview."}',
            "applications.update",
            IntentKind.PROPOSED_MUTATION,
        ),
        (
            '{"kind":"read","name":"priorities.explain","arguments":{}}',
            "priorities.explain",
            IntentKind.READ,
        ),
        ('{"kind":"read","name":"calendar.show","arguments":{}}', "calendar.show", IntentKind.READ),
        (
            '{"kind":"read","name":"schedule.simulate","arguments":{}}',
            "schedule.simulate",
            IntentKind.READ,
        ),
        (
            '{"kind":"proposed_mutation","name":"workload.set_mode",'
            '"arguments":{"mode":"lighter"},'
            '"reason":"The user requested a temporary lighter mode."}',
            "workload.set_mode",
            IntentKind.PROPOSED_MUTATION,
        ),
        ('{"kind":"read","name":"email.search","arguments":{}}', "email.search", IntentKind.READ),
        (
            '{"kind":"read","name":"external_calendar.search","arguments":{}}',
            "external_calendar.search",
            IntentKind.READ,
        ),
    ],
)
def test_required_request_families_become_typed_commands(
    content: str,
    expected_name: str,
    expected_kind: IntentKind,
) -> None:
    adapter = RecordingAdapter(content)
    interpreter = NaturalLanguageInterpreter(LanguageModelGateway(adapter))

    command = interpreter.interpret(natural_request())

    assert command.command_name == expected_name
    assert command.intent.kind == expected_kind
    assert command.actor.profile_id == "fictional-profile"
    assert command.time_zone == "America/Phoenix"
    if expected_kind == IntentKind.READ:
        assert isinstance(command.intent, ReadIntent)
        assert command.idempotency_key is None
    else:
        assert isinstance(command.intent, ProposedMutationIntent)
        assert command.idempotency_key == "fictional-request-1"


def test_interpreter_limits_provider_to_catalog_and_preserves_source_channel() -> None:
    adapter = RecordingAdapter(
        '{"kind":"read","name":"calendar.show","arguments":{"range":"week"}}'
    )
    interpreter = NaturalLanguageInterpreter(LanguageModelGateway(adapter))
    request = natural_request()
    voice_request = NaturalLanguageRequest(
        text=request.text,
        actor=request.actor,
        source_channel=SourceChannel.VOICE,
        correlation_id=request.correlation_id,
        locale=request.locale,
        time_zone=request.time_zone,
        idempotency_key=request.idempotency_key,
    )

    command = interpreter.interpret(voice_request)

    assert command.source_channel == SourceChannel.VOICE
    assert adapter.requests[0].allowed_command_names == IntentCatalog().command_names
    assert "Return only a JSON object" in adapter.requests[0].system_instruction


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        "[]",
        '```json\n{"kind":"read","name":"tasks.list"}\n```',
        '{"kind":"read","name":"tasks.list","actor_id":"attacker"}',
    ],
)
def test_malformed_or_extra_provider_output_is_rejected(content: str) -> None:
    interpreter = NaturalLanguageInterpreter(
        LanguageModelGateway(RecordingAdapter(content))
    )

    with pytest.raises(NaturalLanguageInterpretationError):
        interpreter.interpret(natural_request())


def test_unknown_command_and_kind_mismatch_are_rejected() -> None:
    unknown = NaturalLanguageInterpreter(
        LanguageModelGateway(
            RecordingAdapter('{"kind":"read","name":"unknown.command"}')
        )
    )
    with pytest.raises(UnsupportedIntentError, match="unsupported command"):
        unknown.interpret(natural_request())

    mismatched = NaturalLanguageInterpreter(
        LanguageModelGateway(
            RecordingAdapter('{"kind":"read","name":"tasks.create"}')
        )
    )
    with pytest.raises(NaturalLanguageInterpretationError, match="proposed_mutation"):
        mismatched.interpret(natural_request())


def test_mutation_requires_transport_idempotency_and_never_gains_confirmation() -> None:
    interpreter = NaturalLanguageInterpreter(
        LanguageModelGateway(
            RecordingAdapter(
                '{"kind":"proposed_mutation","name":"tasks.create",'
                '"arguments":{"title":"Fictional task"},'
                '"reason":"The user requested it."}'
            )
        )
    )

    with pytest.raises(NaturalLanguageInterpretationError, match="idempotency key"):
        interpreter.interpret(natural_request(idempotency_key=None))

    command = interpreter.interpret(natural_request())
    assert command.confirmation_token is None


def test_request_validates_text_and_time_zone_before_calling_model() -> None:
    actor = ActorContext(actor_id="fictional-actor", profile_id="fictional-profile")
    with pytest.raises(ValueError, match="must not be blank"):
        NaturalLanguageRequest(
            text=" ",
            actor=actor,
            source_channel=SourceChannel.TEXT,
            correlation_id=CORRELATION_ID,
        )
    with pytest.raises(ValueError, match="valid IANA"):
        NaturalLanguageRequest(
            text="Show fictional tasks.",
            actor=actor,
            source_channel=SourceChannel.TEXT,
            correlation_id=CORRELATION_ID,
            time_zone="Not/AZone",
        )
    with pytest.raises(ValueError, match="idempotency_key"):
        NaturalLanguageRequest(
            text="Create a fictional task.",
            actor=actor,
            source_channel=SourceChannel.TEXT,
            correlation_id=CORRELATION_ID,
            idempotency_key="",
        )
