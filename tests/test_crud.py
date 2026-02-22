"""Unit tests for CRUD operations, calling the data layer directly.

The HTTP integration tests exercise CRUD through FastAPI's transport layer,
which doesn't attribute coverage back to the crud module's return statements
and branch paths. These tests call each function directly via a db_session
fixture to cover lines 16, 38, 47, 59-63, 67, and 81-84.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src import crud
from src.schemas import TaskCreate, TaskUpdate


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------


async def test_get_task_returns_none_when_not_found(db_session: AsyncSession) -> None:
    """get_task returns None for a non-existent ID."""
    result = await crud.get_task(db_session, 99999)
    assert result is None


async def test_get_task_returns_task_when_found(db_session: AsyncSession) -> None:
    """get_task returns the correct Task instance by primary key."""
    created = await crud.create_task(db_session, TaskCreate(title="Find me"))

    result = await crud.get_task(db_session, created.id)

    assert result is not None
    assert result.id == created.id
    assert result.title == "Find me"


# ---------------------------------------------------------------------------
# get_tasks
# ---------------------------------------------------------------------------


async def test_get_tasks_returns_list(db_session: AsyncSession) -> None:
    """get_tasks returns all tasks as a list."""
    await crud.create_task(db_session, TaskCreate(title="Alpha"))
    await crud.create_task(db_session, TaskCreate(title="Beta"))

    result = await crud.get_tasks(db_session)

    assert isinstance(result, list)
    assert len(result) == 2


async def test_get_tasks_filter_completed_true(db_session: AsyncSession) -> None:
    """get_tasks(completed=True) returns only completed tasks."""
    task = await crud.create_task(db_session, TaskCreate(title="Done"))
    await crud.update_task(db_session, task.id, TaskUpdate(completed=True))
    await crud.create_task(db_session, TaskCreate(title="Pending"))

    result = await crud.get_tasks(db_session, completed=True)

    assert len(result) == 1
    assert result[0].completed is True


async def test_get_tasks_filter_completed_false(db_session: AsyncSession) -> None:
    """get_tasks(completed=False) returns only incomplete tasks."""
    task = await crud.create_task(db_session, TaskCreate(title="Done"))
    await crud.update_task(db_session, task.id, TaskUpdate(completed=True))
    await crud.create_task(db_session, TaskCreate(title="Pending"))

    result = await crud.get_tasks(db_session, completed=False)

    assert len(result) == 1
    assert result[0].completed is False


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------


async def test_create_task_returns_persisted_task(db_session: AsyncSession) -> None:
    """create_task persists the task and returns it with all DB-generated fields."""
    task = await crud.create_task(
        db_session, TaskCreate(title="New task", description="Details")
    )

    assert task.id is not None
    assert task.title == "New task"
    assert task.description == "Details"
    assert task.completed is False
    assert task.created_at is not None
    assert task.updated_at is not None


# ---------------------------------------------------------------------------
# update_task
# ---------------------------------------------------------------------------


async def test_update_task_returns_none_when_not_found(
    db_session: AsyncSession,
) -> None:
    """update_task returns None when the task does not exist."""
    result = await crud.update_task(db_session, 99999, TaskUpdate(title="Ghost"))
    assert result is None


async def test_update_task_applies_partial_update(db_session: AsyncSession) -> None:
    """update_task writes only the supplied fields, leaving others unchanged."""
    task = await crud.create_task(
        db_session, TaskCreate(title="Original", description="Keep this")
    )

    updated = await crud.update_task(
        db_session, task.id, TaskUpdate(title="Revised", completed=True)
    )

    assert updated is not None
    assert updated.id == task.id
    assert updated.title == "Revised"
    assert updated.description == "Keep this"  # untouched
    assert updated.completed is True


async def test_update_task_with_no_fields_is_noop(db_session: AsyncSession) -> None:
    """update_task with an empty payload leaves the task unchanged."""
    task = await crud.create_task(db_session, TaskCreate(title="Stable"))

    updated = await crud.update_task(db_session, task.id, TaskUpdate())

    assert updated is not None
    assert updated.title == "Stable"
    assert updated.completed is False


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------


async def test_delete_task_returns_none_when_not_found(
    db_session: AsyncSession,
) -> None:
    """delete_task returns None when the task does not exist."""
    result = await crud.delete_task(db_session, 99999)
    assert result is None


async def test_delete_task_returns_deleted_instance(db_session: AsyncSession) -> None:
    """delete_task returns the deleted Task and removes it from the DB."""
    task = await crud.create_task(db_session, TaskCreate(title="Goodbye"))
    task_id = task.id

    deleted = await crud.delete_task(db_session, task_id)

    assert deleted is not None
    assert deleted.id == task_id

    # Verify the record is no longer retrievable
    gone = await crud.get_task(db_session, task_id)
    assert gone is None
