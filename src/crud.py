"""CRUD operations for the Task resource."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Task
from .schemas import TaskCreate, TaskUpdate


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    """Fetch a single task by its primary key.

    Returns the Task instance or None if not found.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_tasks(
    db: AsyncSession, skip: int = 0, limit: int = 100, completed: bool | None = None
) -> list[Task]:
    """Fetch a paginated list of tasks with optional status filter.

    Args:
        db: The async database session.
        skip: Number of records to skip (offset).
        limit: Maximum number of records to return.
        completed: Optional filter by completion status. None returns all tasks.

    Returns:
        List of Task instances matching the criteria.
    """
    query = select(Task)
    if completed is not None:
        query = query.where(Task.completed == completed)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_task(db: AsyncSession, task: TaskCreate) -> Task:
    """Persist a new task and return the instance with all DB-generated fields."""
    db_task = Task(**task.model_dump())
    db.add(db_task)
    await db.flush()
    await db.refresh(db_task)
    return db_task


async def update_task(
    db: AsyncSession, task_id: int, task_update: TaskUpdate
) -> Task | None:
    """Apply a partial update to an existing task.

    Only fields explicitly set in task_update are written to the database.
    Returns the updated Task, or None if the task does not exist.
    """
    db_task = await get_task(db, task_id)
    if db_task is None:
        return None

    for field, value in task_update.model_dump(exclude_unset=True).items():
        setattr(db_task, field, value)

    await db.flush()
    await db.refresh(db_task)
    return db_task


async def delete_task(db: AsyncSession, task_id: int) -> Task | None:
    """Delete a task by ID.

    Args:
        db: The async database session.
        task_id: The ID of the task to delete.

    Returns:
        The deleted Task instance, or None if the task does not exist.
    """
    db_task = await get_task(db, task_id)
    if db_task is None:
        return None
    await db.delete(db_task)
    return db_task
