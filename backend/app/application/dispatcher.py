from collections.abc import Callable
from dataclasses import dataclass

from app.application.authorization import (
    AuthorizationContext,
    CommandAuthorizationPolicy,
)
from app.application.contracts import (
    CommandEnvelope,
    CommandResult,
    IntentKind,
    ResultStatus,
)

CommandHandler = Callable[[CommandEnvelope], CommandResult]


class UnknownCommandError(LookupError):
    pass


class DuplicateCommandHandlerError(ValueError):
    pass


class IntentKindMismatchError(ValueError):
    pass


class UnsafeMutationResultError(ValueError):
    pass


@dataclass(frozen=True)
class CommandRoute:
    intent_kind: IntentKind
    handler: CommandHandler


class CommandDispatcher:
    """Routes validated envelopes without knowing their transport or implementation."""

    def __init__(self, authorization_policy: CommandAuthorizationPolicy | None = None) -> None:
        self._authorization_policy = authorization_policy or CommandAuthorizationPolicy()
        self._routes: dict[str, CommandRoute] = {}

    def register(
        self,
        command_name: str,
        intent_kind: IntentKind,
        handler: CommandHandler,
    ) -> None:
        if command_name in self._routes:
            raise DuplicateCommandHandlerError(command_name)
        self._routes[command_name] = CommandRoute(intent_kind, handler)

    def dispatch(
        self,
        command: CommandEnvelope,
        authorization: AuthorizationContext,
    ) -> CommandResult:
        self._authorization_policy.authorize(command, authorization)
        try:
            route = self._routes[command.command_name]
        except KeyError as error:
            raise UnknownCommandError(command.command_name) from error
        if route.intent_kind != command.intent.kind:
            raise IntentKindMismatchError(
                f"{command.command_name} expects a {route.intent_kind.value} intent"
            )

        result = route.handler(command)
        if result.command_name != command.command_name:
            raise ValueError("handler returned a result for a different command")
        if result.correlation_id != command.correlation_id:
            raise ValueError("handler returned a result for a different correlation ID")
        if (
            command.intent.kind == IntentKind.PROPOSED_MUTATION
            and command.confirmation_token is None
            and result.status == ResultStatus.SUCCEEDED
        ):
            raise UnsafeMutationResultError(
                "an unconfirmed mutation cannot report successful execution"
            )
        return result

