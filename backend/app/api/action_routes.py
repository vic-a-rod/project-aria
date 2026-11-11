from collections.abc import Callable, Generator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from app.api.action_schemas import (
    AuditEventRead,
    ConfirmationConfirm,
    ConfirmationIssue,
    ConfirmationIssued,
    ConfirmationRead,
    ExecutionCreate,
    ExecutionRead,
    NotificationRuleCreate,
    NotificationRuleRead,
    NotificationRuleUpdate,
    ProposalCreate,
    ProposalRead,
)
from app.application.actions import ActionNotFoundError, ActionService, ActionStateError
from app.domain.actions import ProposalStatus

ActionServiceDependency = Callable[[], Generator[ActionService, None, None]]


def create_action_router(action_service_dependency: ActionServiceDependency) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["safe actions"])

    def actor(x_aria_actor: str = Header(default="local-user")) -> str:
        return x_aria_actor

    @router.get("/proposals", response_model=list[ProposalRead])
    def proposals_index(
        profile_id: str = "local-default",
        status_filter: ProposalStatus | None = Query(default=None, alias="status"),
        service: ActionService = Depends(action_service_dependency),
    ) -> list[ProposalRead]:
        return [
            ProposalRead.from_domain(item)
            for item in service.list_proposals(profile_id=profile_id, status=status_filter)
        ]

    @router.get("/proposals/{proposal_id}", response_model=ProposalRead)
    def proposals_show(
        proposal_id: str,
        service: ActionService = Depends(action_service_dependency),
    ) -> ProposalRead:
        try:
            return ProposalRead.from_domain(service.get_proposal(proposal_id))
        except ActionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Proposal not found") from error

    @router.post(
        "/proposals", response_model=ProposalRead, status_code=status.HTTP_201_CREATED
    )
    def proposals_create(
        payload: ProposalCreate,
        actor_id: str = Depends(actor),
        service: ActionService = Depends(action_service_dependency),
    ) -> ProposalRead:
        try:
            return ProposalRead.from_domain(
                service.create_proposal(
                    payload.to_domain(),
                    actor_id=actor_id,
                    correlation_id=payload.correlation_id,
                )
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.post("/proposals/{proposal_id}/reject", response_model=ProposalRead)
    def proposals_reject(
        proposal_id: str,
        actor_id: str = Depends(actor),
        service: ActionService = Depends(action_service_dependency),
    ) -> ProposalRead:
        try:
            return ProposalRead.from_domain(
                service.reject_proposal(proposal_id, actor_id=actor_id)
            )
        except ActionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Proposal not found") from error
        except ActionStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post(
        "/proposals/{proposal_id}/confirmations",
        response_model=ConfirmationIssued,
        status_code=status.HTTP_201_CREATED,
    )
    def confirmations_issue(
        proposal_id: str,
        payload: ConfirmationIssue,
        actor_id: str = Depends(actor),
        service: ActionService = Depends(action_service_dependency),
    ) -> ConfirmationIssued:
        try:
            return ConfirmationIssued.from_domain(
                service.issue_confirmation(
                    proposal_id,
                    lifetime_minutes=payload.lifetime_minutes,
                    actor_id=actor_id,
                )
            )
        except ActionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Proposal not found") from error
        except (ActionStateError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post(
        "/confirmations/{confirmation_id}/confirm", response_model=ConfirmationRead
    )
    def confirmations_confirm(
        confirmation_id: str,
        payload: ConfirmationConfirm,
        actor_id: str = Depends(actor),
        service: ActionService = Depends(action_service_dependency),
    ) -> ConfirmationRead:
        try:
            return ConfirmationRead.model_validate(
                service.confirm(
                    confirmation_id,
                    token=payload.token,
                    current_state_hash=payload.current_state_hash,
                    actor_id=actor_id,
                )
            )
        except ActionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Confirmation not found") from error
        except ActionStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post(
        "/proposals/{proposal_id}/execution",
        response_model=ExecutionRead,
        status_code=status.HTTP_201_CREATED,
    )
    def executions_create(
        proposal_id: str,
        payload: ExecutionCreate,
        actor_id: str = Depends(actor),
        service: ActionService = Depends(action_service_dependency),
    ) -> ExecutionRead:
        try:
            return ExecutionRead.from_domain(
                service.record_execution(
                    proposal_id,
                    payload.confirmation_id,
                    status=payload.status,
                    summary=payload.summary,
                    error_code=payload.error_code,
                    actor_id=actor_id,
                )
            )
        except ActionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Action record not found") from error
        except ActionStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.get("/notification-rules", response_model=list[NotificationRuleRead])
    def notification_rules_index(
        profile_id: str = "local-default",
        service: ActionService = Depends(action_service_dependency),
    ) -> list[NotificationRuleRead]:
        return [
            NotificationRuleRead.from_domain(item)
            for item in service.list_notification_rules(profile_id=profile_id)
        ]

    @router.post(
        "/notification-rules",
        response_model=NotificationRuleRead,
        status_code=status.HTTP_201_CREATED,
    )
    def notification_rules_create(
        payload: NotificationRuleCreate,
        actor_id: str = Depends(actor),
        service: ActionService = Depends(action_service_dependency),
    ) -> NotificationRuleRead:
        try:
            return NotificationRuleRead.from_domain(
                service.create_notification_rule(payload.to_domain(), actor_id=actor_id)
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.patch("/notification-rules/{rule_id}", response_model=NotificationRuleRead)
    def notification_rules_update(
        rule_id: str,
        payload: NotificationRuleUpdate,
        actor_id: str = Depends(actor),
        service: ActionService = Depends(action_service_dependency),
    ) -> NotificationRuleRead:
        try:
            return NotificationRuleRead.from_domain(
                service.update_notification_rule(
                    rule_id, payload.to_changes(), actor_id=actor_id
                )
            )
        except ActionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Notification rule not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.delete("/notification-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
    def notification_rules_delete(
        rule_id: str,
        actor_id: str = Depends(actor),
        service: ActionService = Depends(action_service_dependency),
    ) -> Response:
        try:
            service.delete_notification_rule(rule_id, actor_id=actor_id)
        except ActionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Notification rule not found") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/audit-events", response_model=list[AuditEventRead])
    def audit_events_index(
        profile_id: str = "local-default",
        limit: int = Query(default=100, ge=1, le=500),
        service: ActionService = Depends(action_service_dependency),
    ) -> list[AuditEventRead]:
        return [
            AuditEventRead.from_domain(item)
            for item in service.list_audit_events(profile_id=profile_id, limit=limit)
        ]

    return router
