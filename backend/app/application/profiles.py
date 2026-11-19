from datetime import datetime
from typing import Protocol
from uuid import uuid4

from app.application.clock import Clock
from app.domain.profiles import NewProfile, Profile, validate_profile


class ProfileRepository(Protocol):
    def list(self) -> list[Profile]: ...
    def create(
        self, profile_id: str, profile: NewProfile, *, timestamp: datetime
    ) -> Profile: ...


class ProfileService:
    def __init__(self, repository: ProfileRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def list(self) -> list[Profile]:
        return self._repository.list()

    def create(self, profile: NewProfile) -> Profile:
        validate_profile(profile)
        return self._repository.create(
            str(uuid4()),
            NewProfile(display_name=profile.display_name.strip()),
            timestamp=self._clock.now(),
        )
