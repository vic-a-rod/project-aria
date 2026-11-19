from collections.abc import Callable, Generator

from fastapi import APIRouter, Depends, status

from app.api.profile_schemas import ProfileCreate, ProfileRead
from app.application.profiles import ProfileService

ProfileServiceDependency = Callable[[], Generator[ProfileService, None, None]]


def create_profile_router(profile_service_dependency: ProfileServiceDependency) -> APIRouter:
    router = APIRouter(prefix="/api/profiles", tags=["profiles"])

    @router.get("", response_model=list[ProfileRead])
    def profiles_index(
        service: ProfileService = Depends(profile_service_dependency),
    ) -> list[ProfileRead]:
        return [ProfileRead.from_domain(profile) for profile in service.list()]

    @router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
    def profiles_create(
        payload: ProfileCreate,
        service: ProfileService = Depends(profile_service_dependency),
    ) -> ProfileRead:
        return ProfileRead.from_domain(service.create(payload.to_domain()))

    return router
