from collections.abc import Callable, Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.schemas import TaskCreate, TaskRead, TaskUpdate
from app.application.tasks import (
    SortDirection,
    TaskNotFoundError,
    TaskService,
    TaskSort,
)

TaskServiceDependency = Callable[[], Generator[TaskService, None, None]]


def create_api_router(task_service_dependency: TaskServiceDependency) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/api/tasks", response_model=list[TaskRead])
    def tasks_index(
        search: str | None = Query(default=None, max_length=200),
        category: str | None = Query(default=None, max_length=80),
        project: str | None = Query(default=None, max_length=200),
        tag: str | None = Query(default=None, max_length=80),
        completed: bool | None = None,
        sort: TaskSort = TaskSort.PRIORITY,
        direction: SortDirection = SortDirection.DESC,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=200),
        service: TaskService = Depends(task_service_dependency),
    ) -> list[TaskRead]:
        views = service.list(
            search=search,
            category=category,
            project=project,
            tag=tag,
            completed=completed,
            sort=sort,
            direction=direction,
            offset=offset,
            limit=limit,
        )
        return [TaskRead.from_view(view) for view in views]

    @router.post("/api/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
    def tasks_create(
        payload: TaskCreate,
        service: TaskService = Depends(task_service_dependency),
    ) -> TaskRead:
        return TaskRead.from_view(service.create(payload.to_domain()))

    @router.patch("/api/tasks/{task_id}", response_model=TaskRead)
    def tasks_update(
        task_id: int,
        payload: TaskUpdate,
        service: TaskService = Depends(task_service_dependency),
    ) -> TaskRead:
        try:
            return TaskRead.from_view(service.update(task_id, payload.to_changes()))
        except TaskNotFoundError as error:
            raise HTTPException(status_code=404, detail="Task not found") from error

    @router.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def tasks_delete(
        task_id: int,
        service: TaskService = Depends(task_service_dependency),
    ) -> Response:
        try:
            service.delete(task_id)
        except TaskNotFoundError as error:
            raise HTTPException(status_code=404, detail="Task not found") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router

