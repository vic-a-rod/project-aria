from dataclasses import replace
from datetime import datetime, time
from typing import Protocol

from app.application.clock import Clock
from app.domain.preferences import (
    NewPreference,
    Preference,
    PreferenceKind,
    PreferenceStatus,
    WorkloadMode,
    is_preference_effective,
    validate_preference,
)

PreferenceFieldValue = (
    str
    | tuple[int, ...]
    | time
    | datetime
    | PreferenceKind
    | PreferenceStatus
    | WorkloadMode
    | None
)


class PreferenceRepository(Protocol):
    def list(self, *, status: PreferenceStatus | None = None) -> list[Preference]: ...
    def get(self, preference_id: int) -> Preference | None: ...
    def create(self, preference: NewPreference, *, timestamp: datetime) -> Preference: ...
    def update(
        self,
        preference_id: int,
        changes: dict[str, PreferenceFieldValue],
        *,
        timestamp: datetime,
    ) -> Preference | None: ...
    def delete(self, preference_id: int) -> bool: ...


class PreferenceNotFoundError(LookupError):
    pass


class PreferenceStateError(ValueError):
    pass


class PreferenceService:
    def __init__(self, repository: PreferenceRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def list(
        self,
        *,
        status: PreferenceStatus | None = None,
        effective_only: bool = False,
    ) -> list[Preference]:
        preferences = self._repository.list(status=status)
        if effective_only:
            now = self._clock.now()
            preferences = [item for item in preferences if is_preference_effective(item, now)]
        return preferences

    def get(self, preference_id: int) -> Preference:
        preference = self._repository.get(preference_id)
        if preference is None:
            raise PreferenceNotFoundError(preference_id)
        return preference

    def create(self, preference: NewPreference) -> Preference:
        validate_preference(preference)
        return self._repository.create(preference, timestamp=self._clock.now())

    def update(
        self, preference_id: int, changes: dict[str, PreferenceFieldValue]
    ) -> Preference:
        current = self.get(preference_id)
        if current.status == PreferenceStatus.DISMISSED:
            raise PreferenceStateError("dismissed preferences cannot be edited")
        candidate = replace(current, **changes)
        validate_preference(candidate)
        updated = self._repository.update(
            preference_id, changes, timestamp=self._clock.now()
        )
        if updated is None:
            raise PreferenceNotFoundError(preference_id)
        return updated

    def approve(self, preference_id: int) -> Preference:
        current = self.get(preference_id)
        if current.status != PreferenceStatus.SUGGESTED:
            raise PreferenceStateError("only suggested preferences can be approved")
        now = self._clock.now()
        updated = self._repository.update(
            preference_id,
            {"status": PreferenceStatus.ACTIVE, "approved_at": now},
            timestamp=now,
        )
        if updated is None:
            raise PreferenceNotFoundError(preference_id)
        return updated

    def dismiss(self, preference_id: int) -> Preference:
        current = self.get(preference_id)
        if current.status != PreferenceStatus.SUGGESTED:
            raise PreferenceStateError("only suggested preferences can be dismissed")
        updated = self._repository.update(
            preference_id,
            {"status": PreferenceStatus.DISMISSED},
            timestamp=self._clock.now(),
        )
        if updated is None:
            raise PreferenceNotFoundError(preference_id)
        return updated

    def delete(self, preference_id: int) -> None:
        if not self._repository.delete(preference_id):
            raise PreferenceNotFoundError(preference_id)
