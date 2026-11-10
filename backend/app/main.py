from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base, engine, get_session
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.task_service import create_task, delete_task, get_task, list_tasks, update_task


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Project Jarvis API", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DatabaseSession = Annotated[Session, Depends(get_session)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tasks", response_model=list[TaskRead])
def tasks_index(
    session: DatabaseSession,
    search: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=80),
    completed: bool | None = None,
) -> list[TaskRead]:
    return list_tasks(session, search=search, category=category, completed=completed)


@app.post("/api/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def tasks_create(payload: TaskCreate, session: DatabaseSession) -> TaskRead:
    return create_task(session, payload)


@app.patch("/api/tasks/{task_id}", response_model=TaskRead)
def tasks_update(task_id: int, payload: TaskUpdate, session: DatabaseSession) -> TaskRead:
    task = get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return update_task(session, task, payload)


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def tasks_delete(task_id: int, session: DatabaseSession) -> Response:
    task = get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    delete_task(session, task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

