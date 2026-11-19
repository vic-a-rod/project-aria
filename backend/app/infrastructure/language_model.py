from app.application.language_models import (
    LanguageModelDescriptor,
    LanguageModelProviderKind,
    LanguageModelRequest,
    LanguageModelResponse,
    LanguageModelUnavailableError,
)


class DisabledLanguageModelAdapter:
    """Default local adapter that keeps Aria usable without any model service."""

    @property
    def descriptor(self) -> LanguageModelDescriptor:
        return LanguageModelDescriptor(
            provider="disabled",
            model="none",
            kind=LanguageModelProviderKind.DISABLED,
        )

    def generate(self, request: LanguageModelRequest) -> LanguageModelResponse:
        raise LanguageModelUnavailableError(
            "natural-language interpretation is unavailable because no model is configured"
        )
