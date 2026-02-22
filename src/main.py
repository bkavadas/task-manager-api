"""FastAPI application entry point and route definitions."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .config import settings
from .database import Base, engine, get_db
from .schemas import TaskCreate, TaskResponse, TaskUpdate


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create database tables on startup and dispose the engine on shutdown.

    In production, prefer Alembic migrations over auto-creation.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="A task management REST API built with FastAPI and async SQLAlchemy.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return a simple liveness probe response."""
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["tasks"],
)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a new task."""
    return await crud.create_task(db, task)


@app.get("/tasks", response_model=list[TaskResponse], tags=["tasks"])
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    """Return a paginated list of all tasks."""
    return await crud.get_tasks(db, skip=skip, limit=limit)


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Return a single task by ID."""
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return task


@app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Partially update an existing task."""
    task = await crud.update_task(db, task_id, task_update)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tasks"],
)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a task by ID."""
    deleted = await crud.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
