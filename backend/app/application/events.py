from dataclasses import replace
from datetime import date, datetime
from typing import Protocol

from app.application.clock import Clock
from app.domain.events import Event, EventKind, EventSource, NewEvent, validate_event

EventFieldValue = str | bool | date | datetime | EventKind | EventSource | None


class EventRepository(Protocol):
    def list(
        self,
        *,
        kind: EventKind | None = None,
        fixed: bool | None = None,
        source: EventSource | None = None,
    ) -> list[Event]: ...

    def get(self, event_id: int) -> Event | None: ...
    def create(self, event: NewEvent, *, timestamp: datetime) -> Event: ...
    def update(
        self,
        event_id: int,
        changes: dict[str, EventFieldValue],
        *,
        timestamp: datetime,
    ) -> Event | None: ...
    def delete(self, event_id: int) -> bool: ...


class EventNotFoundError(LookupError):
    pass


class EventService:
    def __init__(self, repository: EventRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def list(
        self,
        *,
        kind: EventKind | None = None,
        fixed: bool | None = None,
        source: EventSource | None = None,
    ) -> list[Event]:
        return self._repository.list(kind=kind, fixed=fixed, source=source)

    def create(self, event: NewEvent) -> Event:
        validate_event(event)
        return self._repository.create(event, timestamp=self._clock.now())

    def update(self, event_id: int, changes: dict[str, EventFieldValue]) -> Event:
        current = self._repository.get(event_id)
        if current is None:
            raise EventNotFoundError(event_id)
        candidate = replace(current, **changes)
        validate_event(candidate)
        updated = self._repository.update(event_id, changes, timestamp=self._clock.now())
        if updated is None:
            raise EventNotFoundError(event_id)
        return updated

    def delete(self, event_id: int) -> None:
        if not self._repository.delete(event_id):
            raise EventNotFoundError(event_id)
