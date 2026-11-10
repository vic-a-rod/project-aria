from collections.abc import Callable, Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.clock import Clock
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.task_service import create_task, delete_task, get_task, list_tasks, update_task

SessionDependency = Callable[[], Generator[Session, None, None]]
ClockDependency = Callable[[], Clock]


def create_api_router(
    session_dependency: SessionDependency,
    clock_dependency: ClockDependency,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/api/tasks", response_model=list[TaskRead])
    def tasks_index(
        search: str | None = Query(default=None, max_length=200),
        category: str | None = Query(default=None, max_length=80),
        completed: bool | None = None,
        session: Session = Depends(session_dependency),
        clock: Clock = Depends(clock_dependency),
    ) -> list[TaskRead]:
        return list_tasks(
            session,
            clock,
            search=search,
            category=category,
            completed=completed,
        )

    @router.post("/api/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
    def tasks_create(
        payload: TaskCreate,
        session: Session = Depends(session_dependency),
        clock: Clock = Depends(clock_dependency),
    ) -> TaskRead:
        return create_task(session, clock, payload)

    @router.patch("/api/tasks/{task_id}", response_model=TaskRead)
    def tasks_update(
        task_id: int,
        payload: TaskUpdate,
        session: Session = Depends(session_dependency),
        clock: Clock = Depends(clock_dependency),
    ) -> TaskRead:
        task = get_task(session, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return update_task(session, clock, task, payload)

    @router.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def tasks_delete(task_id: int, session: Session = Depends(session_dependency)) -> Response:
        task = get_task(session, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        delete_task(session, task)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router

