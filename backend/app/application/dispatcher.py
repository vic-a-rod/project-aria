from collections.abc import Callable

from app.application.contracts import CommandEnvelope, CommandResult

CommandHandler = Callable[[CommandEnvelope], CommandResult]


class UnknownCommandError(LookupError):
    pass


class DuplicateCommandHandlerError(ValueError):
    pass


class CommandDispatcher:
    """Routes validated envelopes without knowing their transport or implementation."""

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command_name: str, handler: CommandHandler) -> None:
        if command_name in self._handlers:
            raise DuplicateCommandHandlerError(command_name)
        self._handlers[command_name] = handler

    def dispatch(self, command: CommandEnvelope) -> CommandResult:
        try:
            handler = self._handlers[command.command_name]
        except KeyError as error:
            raise UnknownCommandError(command.command_name) from error
        result = handler(command)
        if result.command_name != command.command_name:
            raise ValueError("handler returned a result for a different command")
        if result.correlation_id != command.correlation_id:
            raise ValueError("handler returned a result for a different correlation ID")
        return result

