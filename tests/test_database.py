"""Unit tests for the get_db dependency.

All HTTP tests override get_db entirely via dependency_overrides, so the
function body (commit / rollback logic) is never reached from that path.
These tests drive the async generator directly with a mocked session to
cover lines 28-34.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.database import get_db


async def test_get_db_yields_session() -> None:
    """get_db yields the session produced by AsyncSessionLocal."""
    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = False

    with patch("src.database.AsyncSessionLocal", return_value=mock_cm):
        gen = get_db()
        session = await gen.__anext__()

    assert session is mock_session


async def test_get_db_commits_on_success() -> None:
    """get_db commits the session when the caller completes without error."""
    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = False

    with patch("src.database.AsyncSessionLocal", return_value=mock_cm):
        gen = get_db()
        await gen.__anext__()  # advance to yield

        # Resume after the yield (simulates a request completing normally)
        try:
            await gen.asend(None)
        except StopAsyncIteration:
            pass

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


async def test_get_db_rolls_back_on_exception() -> None:
    """get_db rolls back the session and re-raises when an exception occurs."""
    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = False

    with patch("src.database.AsyncSessionLocal", return_value=mock_cm):
        gen = get_db()
        await gen.__anext__()  # advance to yield

        # Throw an exception into the generator (simulates a request failure)
        with pytest.raises(RuntimeError, match="simulated db error"):
            await gen.athrow(RuntimeError("simulated db error"))

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
