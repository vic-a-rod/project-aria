from collections.abc import Callable, Generator

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.event_schemas import EventCreate, EventRead, EventUpdate
from app.application.events import EventNotFoundError, EventService
from app.domain.events import EventKind, EventSource

EventServiceDependency = Callable[[], Generator[EventService, None, None]]


def create_event_router(event_service_dependency: EventServiceDependency) -> APIRouter:
    router = APIRouter(prefix="/api/events", tags=["events"])

    @router.get("", response_model=list[EventRead])
    def events_index(
        kind: EventKind | None = None,
        fixed: bool | None = None,
        source: EventSource | None = None,
        service: EventService = Depends(event_service_dependency),
    ) -> list[EventRead]:
        return [
            EventRead.from_domain(event)
            for event in service.list(kind=kind, fixed=fixed, source=source)
        ]

    @router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
    def events_create(
        payload: EventCreate,
        service: EventService = Depends(event_service_dependency),
    ) -> EventRead:
        try:
            return EventRead.from_domain(service.create(payload.to_domain()))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.patch("/{event_id}", response_model=EventRead)
    def events_update(
        event_id: int,
        payload: EventUpdate,
        service: EventService = Depends(event_service_dependency),
    ) -> EventRead:
        try:
            return EventRead.from_domain(service.update(event_id, payload.to_changes()))
        except EventNotFoundError as error:
            raise HTTPException(status_code=404, detail="Event not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
    def events_delete(
        event_id: int,
        service: EventService = Depends(event_service_dependency),
    ) -> Response:
        try:
            service.delete(event_id)
        except EventNotFoundError as error:
            raise HTTPException(status_code=404, detail="Event not found") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
