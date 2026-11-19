from dataclasses import dataclass

from app.application.contracts import CommandEnvelope


class CommandAuthorizationError(PermissionError):
    pass


class ActorAccessDeniedError(CommandAuthorizationError):
    pass


class ProfileAccessDeniedError(CommandAuthorizationError):
    pass


@dataclass(frozen=True)
class AuthorizationContext:
    """Trusted transport context used to verify envelope identity and scope."""

    actor_id: str
    profile_ids: frozenset[str]

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise ValueError("authorization actor_id must not be blank")
        if not self.profile_ids or any(not item.strip() for item in self.profile_ids):
            raise ValueError("authorization profile_ids must contain nonblank values")

    @classmethod
    def local(cls, *, actor_id: str, profile_id: str) -> "AuthorizationContext":
        return cls(actor_id=actor_id, profile_ids=frozenset({profile_id}))


class CommandAuthorizationPolicy:
    """Fail-closed actor and profile boundary independent of any transport."""

    def authorize(
        self, command: CommandEnvelope, context: AuthorizationContext
    ) -> None:
        if command.actor.actor_id != context.actor_id:
            raise ActorAccessDeniedError("command actor does not match trusted actor")
        if command.actor.profile_id not in context.profile_ids:
            raise ProfileAccessDeniedError(
                "command profile is outside the actor's authorized profiles"
            )
