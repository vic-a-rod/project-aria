from collections.abc import Callable, Generator
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.application.actions import ActionNotFoundError, ActionStateError
from app.application.assistant import (
    AssistantConfirmation,
    AssistantConfirmationError,
    AssistantRequest,
    AssistantRequestError,
    LocalAssistantService,
)
from app.application.contracts import CommandResult

AssistantServiceDependency = Callable[
    [], Generator[LocalAssistantService, None, None]
]


class AssistantMessage(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)
    locale: str = Field(default="en-US", min_length=2, max_length=35)
    time_zone: str = Field(default="UTC", min_length=1, max_length=100)


class AssistantConfirmationPayload(BaseModel):
    proposal_id: UUID
    confirmation_id: UUID
    token: str = Field(min_length=1, max_length=500)


def create_assistant_router(
    assistant_service_dependency: AssistantServiceDependency,
) -> APIRouter:
    router = APIRouter(prefix="/api/assistant", tags=["assistant"])

    @router.post("/messages", response_model=CommandResult)
    def messages_create(
        payload: AssistantMessage,
        profile_id: str = Header(default="local-default", alias="X-Aria-Profile-ID"),
        actor_id: str = Header(default="local-user", alias="X-Aria-Actor"),
        service: LocalAssistantService = Depends(assistant_service_dependency),
    ) -> CommandResult:
        try:
            return service.submit(
                AssistantRequest(
                    text=payload.text,
                    profile_id=profile_id,
                    actor_id=actor_id,
                    locale=payload.locale,
                    time_zone=payload.time_zone,
                )
            )
        except AssistantRequestError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

    @router.post("/confirmations", response_model=CommandResult)
    def confirmations_create(
        payload: AssistantConfirmationPayload,
        profile_id: str = Header(default="local-default", alias="X-Aria-Profile-ID"),
        actor_id: str = Header(default="local-user", alias="X-Aria-Actor"),
        service: LocalAssistantService = Depends(assistant_service_dependency),
    ) -> CommandResult:
        try:
            return service.confirm(
                AssistantConfirmation(
                    proposal_id=payload.proposal_id,
                    confirmation_id=payload.confirmation_id,
                    token=payload.token,
                    profile_id=profile_id,
                    actor_id=actor_id,
                )
            )
        except ActionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Assistant proposal not found") from error
        except (ActionStateError, AssistantConfirmationError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    return router
