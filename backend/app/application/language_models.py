import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class LanguageModelProviderKind(StrEnum):
    DISABLED = "disabled"
    CLOUD = "cloud"
    LOCAL = "local"


class LanguageModelError(RuntimeError):
    pass


class LanguageModelUnavailableError(LanguageModelError):
    pass


class LanguageModelContractError(LanguageModelError):
    pass


@dataclass(frozen=True)
class LanguageModelDescriptor:
    provider: str
    model: str
    kind: LanguageModelProviderKind

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model.strip():
            raise ValueError("language model provider and model must not be blank")


@dataclass(frozen=True)
class LanguageModelContextItem:
    source_type: str
    reference_id: str
    content: str

    def __post_init__(self) -> None:
        if not self.source_type.strip() or not self.reference_id.strip():
            raise ValueError("model context source and reference must not be blank")
        if not self.content.strip():
            raise ValueError("model context content must not be blank")
        if len(self.content) > 4_000:
            raise ValueError("model context content exceeds 4000 characters")


@dataclass(frozen=True)
class LanguageModelRequest:
    correlation_id: UUID
    system_instruction: str
    user_text: str
    allowed_command_names: tuple[str, ...]
    context: tuple[LanguageModelContextItem, ...] = ()
    max_output_characters: int = 4_000

    def __post_init__(self) -> None:
        if not self.system_instruction.strip() or not self.user_text.strip():
            raise ValueError("model instruction and user text must not be blank")
        if len(self.system_instruction) > 8_000:
            raise ValueError("model instruction exceeds 8000 characters")
        if len(self.user_text) > 16_000:
            raise ValueError("model user text exceeds 16000 characters")
        if not self.allowed_command_names:
            raise ValueError("at least one allowed command name is required")
        if len(set(self.allowed_command_names)) != len(self.allowed_command_names):
            raise ValueError("allowed command names must be unique")
        if any(not _valid_command_name(name) for name in self.allowed_command_names):
            raise ValueError("allowed command names must use dotted lowercase syntax")
        if len(self.context) > 50:
            raise ValueError("model context cannot exceed 50 items")
        if not 1 <= self.max_output_characters <= 16_000:
            raise ValueError("max_output_characters must be between 1 and 16000")


@dataclass(frozen=True)
class LanguageModelResponse:
    correlation_id: UUID
    content: str
    provider_request_id: str | None = None


class LanguageModelAdapter(Protocol):
    @property
    def descriptor(self) -> LanguageModelDescriptor: ...

    def generate(self, request: LanguageModelRequest) -> LanguageModelResponse: ...


class LanguageModelGateway:
    """Validates the bounded model port without granting execution authority."""

    def __init__(self, adapter: LanguageModelAdapter) -> None:
        self._adapter = adapter

    @property
    def descriptor(self) -> LanguageModelDescriptor:
        return self._adapter.descriptor

    def generate(self, request: LanguageModelRequest) -> LanguageModelResponse:
        response = self._adapter.generate(request)
        if response.correlation_id != request.correlation_id:
            raise LanguageModelContractError(
                "language model response correlation ID does not match the request"
            )
        if not response.content.strip():
            raise LanguageModelContractError("language model response must not be blank")
        if len(response.content) > request.max_output_characters:
            raise LanguageModelContractError(
                "language model response exceeds the requested output bound"
            )
        return response


def _valid_command_name(value: str) -> bool:
    return re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", value) is not None
