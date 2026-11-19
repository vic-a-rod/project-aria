from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import JsonValue

from app.application.actions import ActionService
from app.application.contracts import (
    ActionProposal,
    ClarificationRequest,
    CommandEnvelope,
    CommandResult,
    EvidenceReference,
    IntentKind,
    ProposedChange,
    ProposedMutationIntent,
    ReasoningDetail,
    ResultStatus,
    WarningDetail,
)
from app.domain.actions import NewActionProposal, NewProposalEvidence


class CommandPresentationError(ValueError):
    pass


@dataclass(frozen=True)
class ProposalEvidenceInput:
    reference: EvidenceReference
    content_hash: str | None = None

    def __post_init__(self) -> None:
        if self.reference.observed_at is None:
            raise ValueError("proposal evidence requires observed_at")
        if self.content_hash is not None and not self.content_hash.strip():
            raise ValueError("content_hash must not be blank")
        if self.content_hash is not None and len(self.content_hash) > 128:
            raise ValueError("content_hash cannot exceed 128 characters")


@dataclass(frozen=True)
class MutationPreview:
    summary: str
    changes: tuple[ProposedChange, ...]
    evidence: tuple[ProposalEvidenceInput, ...]
    reasoning: tuple[ReasoningDetail, ...]
    warnings: tuple[WarningDetail, ...]
    state_hash: str
    proposal_expires_at: datetime
    confirmation_reason: str
    display_summary: str
    speakable_text: str
    confirmation_lifetime_minutes: int = 10


class CommandResultPresenter:
    """Builds safe command results and persists previews without executing them."""

    def __init__(self, actions: ActionService) -> None:
        self._actions = actions

    def successful_read(
        self,
        command: CommandEnvelope,
        *,
        data: dict[str, JsonValue],
        evidence: tuple[EvidenceReference, ...],
        reasoning: tuple[ReasoningDetail, ...],
        warnings: tuple[WarningDetail, ...] = (),
        display_summary: str,
        speakable_text: str,
    ) -> CommandResult:
        if command.intent.kind != IntentKind.READ:
            raise CommandPresentationError("successful_read requires a read intent")
        return CommandResult(
            command_name=command.command_name,
            correlation_id=command.correlation_id,
            status=ResultStatus.SUCCEEDED,
            data=data,
            evidence=evidence,
            reasoning=reasoning,
            warnings=warnings,
            display_summary=display_summary,
            speakable_text=speakable_text,
        )

    def clarification(
        self,
        command: CommandEnvelope,
        request: ClarificationRequest,
        *,
        evidence: tuple[EvidenceReference, ...] = (),
        reasoning: tuple[ReasoningDetail, ...] = (),
        warnings: tuple[WarningDetail, ...] = (),
        display_summary: str,
        speakable_text: str,
    ) -> CommandResult:
        return CommandResult(
            command_name=command.command_name,
            correlation_id=command.correlation_id,
            status=ResultStatus.NEEDS_CLARIFICATION,
            evidence=evidence,
            reasoning=reasoning,
            warnings=warnings,
            clarification=request,
            display_summary=display_summary,
            speakable_text=speakable_text,
        )

    def proposed_mutation(
        self,
        command: CommandEnvelope,
        preview: MutationPreview,
    ) -> CommandResult:
        if not isinstance(command.intent, ProposedMutationIntent):
            raise CommandPresentationError(
                "proposed_mutation requires a proposed mutation intent"
            )
        if command.confirmation_token is not None:
            raise CommandPresentationError(
                "a confirmed command cannot create a new mutation preview"
            )
        self._validate_preview(preview)
        target = command.intent.target
        created = self._actions.create_proposal(
            NewActionProposal(
                profile_id=command.actor.profile_id,
                action_type=command.command_name,
                target_type=target.resource_type if target else None,
                target_id=target.resource_id if target else None,
                payload={
                    "arguments": command.intent.arguments,
                    "changes": [item.model_dump(mode="json") for item in preview.changes],
                    "reasoning": [
                        item.model_dump(mode="json") for item in preview.reasoning
                    ],
                    "warnings": [
                        item.model_dump(mode="json") for item in preview.warnings
                    ],
                },
                state_hash=preview.state_hash,
                expires_at=preview.proposal_expires_at,
                evidence=tuple(
                    NewProposalEvidence(
                        source_type=item.reference.source_type.value,
                        source_reference=item.reference.reference_id,
                        summary=item.reference.summary,
                        content_hash=item.content_hash,
                        observed_at=item.reference.observed_at,
                    )
                    for item in preview.evidence
                    if item.reference.observed_at is not None
                ),
            ),
            actor_id=command.actor.actor_id,
            correlation_id=str(command.correlation_id),
        )
        issued = self._actions.issue_confirmation(
            created.id,
            lifetime_minutes=preview.confirmation_lifetime_minutes,
            actor_id=command.actor.actor_id,
        )
        proposal_id = UUID(created.id)
        confirmation_id = UUID(issued.confirmation.id)
        return CommandResult(
            command_name=command.command_name,
            correlation_id=command.correlation_id,
            status=ResultStatus.REQUIRES_CONFIRMATION,
            evidence=tuple(item.reference for item in preview.evidence),
            reasoning=preview.reasoning,
            warnings=preview.warnings,
            proposals=(
                ActionProposal(
                    proposal_id=proposal_id,
                    action=command.command_name,
                    summary=preview.summary,
                    target=target,
                    arguments=command.intent.arguments,
                    changes=preview.changes,
                ),
            ),
            confirmation={
                "confirmation_id": confirmation_id,
                "proposal_id": proposal_id,
                "token": issued.token,
                "expires_at": issued.confirmation.expires_at,
                "reason": preview.confirmation_reason,
            },
            display_summary=preview.display_summary,
            speakable_text=preview.speakable_text,
        )

    @staticmethod
    def _validate_preview(preview: MutationPreview) -> None:
        if not preview.summary.strip():
            raise CommandPresentationError("preview summary must not be blank")
        if len(preview.summary) > 1_000:
            raise CommandPresentationError("preview summary cannot exceed 1000 characters")
        if not preview.changes:
            raise CommandPresentationError("mutation preview requires proposed changes")
        if not preview.evidence:
            raise CommandPresentationError("mutation preview requires evidence")
        if not preview.reasoning:
            raise CommandPresentationError("mutation preview requires reasoning")
        if not preview.state_hash.strip():
            raise CommandPresentationError("mutation preview requires a state hash")
        if len(preview.state_hash) > 128:
            raise CommandPresentationError("state hash cannot exceed 128 characters")
        if not preview.confirmation_reason.strip():
            raise CommandPresentationError("confirmation reason must not be blank")
        if len(preview.confirmation_reason) > 1_000:
            raise CommandPresentationError(
                "confirmation reason cannot exceed 1000 characters"
            )
        if not preview.display_summary.strip() or len(preview.display_summary) > 2_000:
            raise CommandPresentationError(
                "display summary must contain between 1 and 2000 characters"
            )
        if not preview.speakable_text.strip() or len(preview.speakable_text) > 500:
            raise CommandPresentationError(
                "speakable text must contain between 1 and 500 characters"
            )
        if not 1 <= preview.confirmation_lifetime_minutes <= 60:
            raise CommandPresentationError(
                "confirmation lifetime must be between 1 and 60 minutes"
            )
