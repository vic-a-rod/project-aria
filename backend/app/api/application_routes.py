from collections.abc import Callable, Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.application_schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    WorkloadItemRead,
)
from app.application.applications import ApplicationNotFoundError, ApplicationService
from app.domain.applications import ApplicationStatus

ApplicationServiceDependency = Callable[[], Generator[ApplicationService, None, None]]


def create_application_router(
    application_service_dependency: ApplicationServiceDependency,
) -> APIRouter:
    router = APIRouter(prefix="/api/applications", tags=["applications"])

    @router.get("", response_model=list[ApplicationRead])
    def applications_index(
        status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
        service: ApplicationService = Depends(application_service_dependency),
    ) -> list[ApplicationRead]:
        return [
            ApplicationRead.from_domain(item)
            for item in service.list(status=status_filter)
        ]

    @router.get("/{application_id}", response_model=ApplicationRead)
    def applications_show(
        application_id: int,
        service: ApplicationService = Depends(application_service_dependency),
    ) -> ApplicationRead:
        try:
            return ApplicationRead.from_domain(service.get(application_id))
        except ApplicationNotFoundError as error:
            raise HTTPException(status_code=404, detail="Application not found") from error

    @router.get("/{application_id}/workload", response_model=list[WorkloadItemRead])
    def applications_workload(
        application_id: int,
        service: ApplicationService = Depends(application_service_dependency),
    ) -> list[WorkloadItemRead]:
        try:
            return [
                WorkloadItemRead.model_validate(item)
                for item in service.workload(application_id)
            ]
        except ApplicationNotFoundError as error:
            raise HTTPException(status_code=404, detail="Application not found") from error

    @router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
    def applications_create(
        payload: ApplicationCreate,
        service: ApplicationService = Depends(application_service_dependency),
    ) -> ApplicationRead:
        try:
            return ApplicationRead.from_domain(service.create(payload.to_domain()))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.patch("/{application_id}", response_model=ApplicationRead)
    def applications_update(
        application_id: int,
        payload: ApplicationUpdate,
        service: ApplicationService = Depends(application_service_dependency),
    ) -> ApplicationRead:
        try:
            return ApplicationRead.from_domain(
                service.update(application_id, payload.to_changes())
            )
        except ApplicationNotFoundError as error:
            raise HTTPException(status_code=404, detail="Application not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
    def applications_delete(
        application_id: int,
        service: ApplicationService = Depends(application_service_dependency),
    ) -> Response:
        try:
            service.delete(application_id)
        except ApplicationNotFoundError as error:
            raise HTTPException(status_code=404, detail="Application not found") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
