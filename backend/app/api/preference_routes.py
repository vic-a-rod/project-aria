from collections.abc import Callable, Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.preference_schemas import PreferenceCreate, PreferenceRead, PreferenceUpdate
from app.application.preferences import (
    PreferenceNotFoundError,
    PreferenceService,
    PreferenceStateError,
)
from app.domain.preferences import PreferenceStatus

PreferenceServiceDependency = Callable[[], Generator[PreferenceService, None, None]]


def create_preference_router(
    preference_service_dependency: PreferenceServiceDependency,
) -> APIRouter:
    router = APIRouter(prefix="/api/preferences", tags=["preferences"])

    def handle_state_error(error: Exception) -> HTTPException:
        return HTTPException(status_code=409, detail=str(error))

    @router.get("", response_model=list[PreferenceRead])
    def preferences_index(
        status_filter: PreferenceStatus | None = Query(default=None, alias="status"),
        effective: bool = False,
        service: PreferenceService = Depends(preference_service_dependency),
    ) -> list[PreferenceRead]:
        return [
            PreferenceRead.from_domain(item)
            for item in service.list(status=status_filter, effective_only=effective)
        ]

    @router.get("/{preference_id}", response_model=PreferenceRead)
    def preferences_show(
        preference_id: int,
        service: PreferenceService = Depends(preference_service_dependency),
    ) -> PreferenceRead:
        try:
            return PreferenceRead.from_domain(service.get(preference_id))
        except PreferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Preference not found") from error

    @router.post("", response_model=PreferenceRead, status_code=status.HTTP_201_CREATED)
    def preferences_create(
        payload: PreferenceCreate,
        service: PreferenceService = Depends(preference_service_dependency),
    ) -> PreferenceRead:
        try:
            return PreferenceRead.from_domain(service.create(payload.to_domain()))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.patch("/{preference_id}", response_model=PreferenceRead)
    def preferences_update(
        preference_id: int,
        payload: PreferenceUpdate,
        service: PreferenceService = Depends(preference_service_dependency),
    ) -> PreferenceRead:
        try:
            return PreferenceRead.from_domain(
                service.update(preference_id, payload.to_changes())
            )
        except PreferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Preference not found") from error
        except PreferenceStateError as error:
            raise handle_state_error(error) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.post("/{preference_id}/approve", response_model=PreferenceRead)
    def preferences_approve(
        preference_id: int,
        service: PreferenceService = Depends(preference_service_dependency),
    ) -> PreferenceRead:
        try:
            return PreferenceRead.from_domain(service.approve(preference_id))
        except PreferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Preference not found") from error
        except PreferenceStateError as error:
            raise handle_state_error(error) from error

    @router.post("/{preference_id}/dismiss", response_model=PreferenceRead)
    def preferences_dismiss(
        preference_id: int,
        service: PreferenceService = Depends(preference_service_dependency),
    ) -> PreferenceRead:
        try:
            return PreferenceRead.from_domain(service.dismiss(preference_id))
        except PreferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Preference not found") from error
        except PreferenceStateError as error:
            raise handle_state_error(error) from error

    @router.delete("/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
    def preferences_delete(
        preference_id: int,
        service: PreferenceService = Depends(preference_service_dependency),
    ) -> Response:
        try:
            service.delete(preference_id)
        except PreferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail="Preference not found") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
