from collections.abc import Callable, Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.synchronization_schemas import (
    CheckpointRead,
    CheckpointUpdate,
    ConnectionCreate,
    ConnectionRead,
    ConnectionStatusUpdate,
    DuplicateUpdate,
    ExternalRecordRead,
    ExternalRecordUpsert,
)
from app.application.synchronization import (
    SynchronizationConflictError,
    SynchronizationNotFoundError,
    SynchronizationService,
)

SynchronizationServiceDependency = Callable[
    [], Generator[SynchronizationService, None, None]
]


def create_synchronization_router(
    synchronization_service_dependency: SynchronizationServiceDependency,
) -> APIRouter:
    router = APIRouter(prefix="/api/sync", tags=["synchronization"])

    @router.get("/connections", response_model=list[ConnectionRead])
    def connections_index(
        profile_id: str = "local-default",
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> list[ConnectionRead]:
        return [
            ConnectionRead.from_domain(item)
            for item in service.list_connections(profile_id=profile_id)
        ]

    @router.post(
        "/connections", response_model=ConnectionRead, status_code=status.HTTP_201_CREATED
    )
    def connections_create(
        payload: ConnectionCreate,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> ConnectionRead:
        try:
            return ConnectionRead.from_domain(service.create_connection(payload.to_domain()))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.patch("/connections/{connection_id}", response_model=ConnectionRead)
    def connections_update(
        connection_id: str,
        payload: ConnectionStatusUpdate,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> ConnectionRead:
        try:
            return ConnectionRead.from_domain(
                service.set_connection_status(connection_id, payload.status)
            )
        except SynchronizationNotFoundError as error:
            raise HTTPException(status_code=404, detail="Connection not found") from error

    @router.get(
        "/connections/{connection_id}/checkpoints/{resource_type}",
        response_model=CheckpointRead,
    )
    def checkpoints_show(
        connection_id: str,
        resource_type: str,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> CheckpointRead:
        try:
            return CheckpointRead.model_validate(
                service.get_checkpoint(connection_id, resource_type)
            )
        except SynchronizationNotFoundError as error:
            raise HTTPException(status_code=404, detail="Checkpoint not found") from error

    @router.put(
        "/connections/{connection_id}/checkpoints/{resource_type}",
        response_model=CheckpointRead,
    )
    def checkpoints_update(
        connection_id: str,
        resource_type: str,
        payload: CheckpointUpdate,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> CheckpointRead:
        try:
            return CheckpointRead.model_validate(
                service.checkpoint(connection_id, resource_type, payload.cursor)
            )
        except SynchronizationNotFoundError as error:
            raise HTTPException(status_code=404, detail="Connection not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.get("/records", response_model=list[ExternalRecordRead])
    def records_index(
        connection_id: str | None = None,
        resource_type: str | None = None,
        tombstoned: bool | None = None,
        deduplication_key: str | None = Query(default=None, alias="dedup_key"),
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> list[ExternalRecordRead]:
        return [
            ExternalRecordRead.from_domain(item)
            for item in service.list_records(
                connection_id=connection_id,
                resource_type=resource_type,
                tombstoned=tombstoned,
                deduplication_key=deduplication_key,
            )
        ]

    @router.put("/records", response_model=ExternalRecordRead)
    def records_upsert(
        payload: ExternalRecordUpsert,
        response: Response,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> ExternalRecordRead:
        try:
            record, created = service.upsert_record(payload.to_domain())
        except SynchronizationNotFoundError as error:
            raise HTTPException(status_code=404, detail="Connection not found") from error
        except SynchronizationConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return ExternalRecordRead.from_domain(record)

    @router.post("/records/{record_id}/tombstone", response_model=ExternalRecordRead)
    def records_tombstone(
        record_id: str,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> ExternalRecordRead:
        try:
            return ExternalRecordRead.from_domain(service.tombstone(record_id))
        except SynchronizationNotFoundError as error:
            raise HTTPException(status_code=404, detail="External record not found") from error

    @router.post("/records/{record_id}/restore", response_model=ExternalRecordRead)
    def records_restore(
        record_id: str,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> ExternalRecordRead:
        try:
            return ExternalRecordRead.from_domain(service.restore(record_id))
        except SynchronizationNotFoundError as error:
            raise HTTPException(status_code=404, detail="External record not found") from error

    @router.put("/records/{record_id}/duplicate", response_model=ExternalRecordRead)
    def records_duplicate(
        record_id: str,
        payload: DuplicateUpdate,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> ExternalRecordRead:
        try:
            return ExternalRecordRead.from_domain(
                service.mark_duplicate(record_id, payload.duplicate_of_id)
            )
        except SynchronizationNotFoundError as error:
            raise HTTPException(status_code=404, detail="External record not found") from error
        except SynchronizationConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.delete("/records/{record_id}/duplicate", response_model=ExternalRecordRead)
    def records_duplicate_clear(
        record_id: str,
        service: SynchronizationService = Depends(synchronization_service_dependency),
    ) -> ExternalRecordRead:
        try:
            return ExternalRecordRead.from_domain(service.clear_duplicate(record_id))
        except SynchronizationNotFoundError as error:
            raise HTTPException(status_code=404, detail="External record not found") from error

    return router
