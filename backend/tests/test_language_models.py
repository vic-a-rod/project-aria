from dataclasses import fields
from uuid import UUID

import pytest

from app.application.language_models import (
    LanguageModelContextItem,
    LanguageModelContractError,
    LanguageModelDescriptor,
    LanguageModelGateway,
    LanguageModelProviderKind,
    LanguageModelRequest,
    LanguageModelResponse,
    LanguageModelUnavailableError,
)
from app.config import Settings
from app.factory import create_app
from app.infrastructure.language_model import DisabledLanguageModelAdapter

CORRELATION_ID = UUID("33333333-3333-4333-8333-333333333333")


def request(*, max_output_characters: int = 4_000) -> LanguageModelRequest:
    return LanguageModelRequest(
        correlation_id=CORRELATION_ID,
        system_instruction="Return one validated fictional command as JSON.",
        user_text="Show my fictional tasks for tomorrow.",
        allowed_command_names=("tasks.list", "calendar.show"),
        context=(
            LanguageModelContextItem(
                source_type="user_input",
                reference_id="request:fictional",
                content="The requested date is 2026-11-20.",
            ),
        ),
        max_output_characters=max_output_characters,
    )


class FakeLanguageModelAdapter:
    def __init__(self, kind: LanguageModelProviderKind) -> None:
        self._descriptor = LanguageModelDescriptor(
            provider=f"fictional-{kind.value}",
            model="fictional-model",
            kind=kind,
        )
        self.requests: list[LanguageModelRequest] = []
        self.response = LanguageModelResponse(
            correlation_id=CORRELATION_ID,
            content='{"kind":"read","name":"tasks.list"}',
            provider_request_id="fictional-provider-request",
        )

    @property
    def descriptor(self) -> LanguageModelDescriptor:
        return self._descriptor

    def generate(self, model_request: LanguageModelRequest) -> LanguageModelResponse:
        self.requests.append(model_request)
        return self.response


@pytest.mark.parametrize(
    "kind", [LanguageModelProviderKind.CLOUD, LanguageModelProviderKind.LOCAL]
)
def test_cloud_and_local_adapters_use_the_same_bounded_port(
    kind: LanguageModelProviderKind,
) -> None:
    adapter = FakeLanguageModelAdapter(kind)
    gateway = LanguageModelGateway(adapter)

    response = gateway.generate(request())

    assert gateway.descriptor.kind == kind
    assert response.provider_request_id == "fictional-provider-request"
    assert adapter.requests == [request()]


def test_default_adapter_keeps_model_optional() -> None:
    gateway = LanguageModelGateway(DisabledLanguageModelAdapter())

    assert gateway.descriptor.kind == LanguageModelProviderKind.DISABLED
    with pytest.raises(LanguageModelUnavailableError, match="no model is configured"):
        gateway.generate(request())


def test_gateway_rejects_malformed_provider_responses() -> None:
    adapter = FakeLanguageModelAdapter(LanguageModelProviderKind.CLOUD)
    gateway = LanguageModelGateway(adapter)

    adapter.response = LanguageModelResponse(
        correlation_id=UUID("44444444-4444-4444-8444-444444444444"),
        content="{}",
    )
    with pytest.raises(LanguageModelContractError, match="correlation ID"):
        gateway.generate(request())

    adapter.response = LanguageModelResponse(
        correlation_id=CORRELATION_ID,
        content=" ",
    )
    with pytest.raises(LanguageModelContractError, match="must not be blank"):
        gateway.generate(request())

    adapter.response = LanguageModelResponse(
        correlation_id=CORRELATION_ID,
        content="12345",
    )
    with pytest.raises(LanguageModelContractError, match="output bound"):
        gateway.generate(request(max_output_characters=4))


def test_request_enforces_prompt_context_command_and_output_bounds() -> None:
    with pytest.raises(ValueError, match="at least one allowed command"):
        LanguageModelRequest(
            correlation_id=CORRELATION_ID,
            system_instruction="Interpret the request.",
            user_text="Show fictional tasks.",
            allowed_command_names=(),
        )
    with pytest.raises(ValueError, match="dotted lowercase"):
        LanguageModelRequest(
            correlation_id=CORRELATION_ID,
            system_instruction="Interpret the request.",
            user_text="Show fictional tasks.",
            allowed_command_names=("invalid command",),
        )
    with pytest.raises(ValueError, match="must be unique"):
        LanguageModelRequest(
            correlation_id=CORRELATION_ID,
            system_instruction="Interpret the request.",
            user_text="Show fictional tasks.",
            allowed_command_names=("tasks.list", "tasks.list"),
        )
    with pytest.raises(ValueError, match="between 1 and 16000"):
        request(max_output_characters=0)


def test_model_request_has_no_execution_database_or_credential_capability() -> None:
    assert {field.name for field in fields(LanguageModelRequest)} == {
        "correlation_id",
        "system_instruction",
        "user_text",
        "allowed_command_names",
        "context",
        "max_output_characters",
    }


def test_factory_accepts_an_injected_model_without_provider_sdk(tmp_path) -> None:
    adapter = FakeLanguageModelAdapter(LanguageModelProviderKind.LOCAL)
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'model-injection.db').as_posix()}",
        _env_file=None,
    )

    app = create_app(settings, language_model=adapter)
    try:
        assert app.state.language_model.descriptor == adapter.descriptor
    finally:
        app.state.engine.dispose()
