"""Integration tests for the /tasks endpoints."""

from httpx import AsyncClient


async def test_health_check(client: AsyncClient) -> None:
    """GET /health returns 200 with a healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_task_returns_201(client: AsyncClient) -> None:
    """POST /tasks creates a task and returns 201 with the task body."""
    payload = {"title": "Buy groceries", "description": "Milk, eggs, bread"}
    response = await client.post("/tasks", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert data["description"] == "Milk, eggs, bread"
    assert data["completed"] is False
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_task_without_description(client: AsyncClient) -> None:
    """POST /tasks succeeds when description is omitted."""
    response = await client.post("/tasks", json={"title": "Minimal task"})
    assert response.status_code == 201
    assert response.json()["description"] is None


async def test_create_task_empty_title_returns_422(client: AsyncClient) -> None:
    """POST /tasks rejects an empty title with 422."""
    response = await client.post("/tasks", json={"title": ""})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


async def test_get_task(client: AsyncClient) -> None:
    """GET /tasks/{id} returns the correct task."""
    created = await client.post("/tasks", json={"title": "Fetch me"})
    task_id = created.json()["id"]

    response = await client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["id"] == task_id


async def test_get_task_not_found(client: AsyncClient) -> None:
    """GET /tasks/{id} returns 404 for a non-existent task."""
    response = await client.get("/tasks/99999")
    assert response.status_code == 404


async def test_list_tasks_returns_list(client: AsyncClient) -> None:
    """GET /tasks returns a JSON array."""
    response = await client.get("/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_task(client: AsyncClient) -> None:
    """PATCH /tasks/{id} applies partial updates and returns the updated task."""
    created = await client.post("/tasks", json={"title": "Original title"})
    task_id = created.json()["id"]

    response = await client.patch(
        f"/tasks/{task_id}",
        json={"title": "Updated title", "completed": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated title"
    assert data["completed"] is True


async def test_update_task_not_found(client: AsyncClient) -> None:
    """PATCH /tasks/{id} returns 404 for a non-existent task."""
    response = await client.patch("/tasks/99999", json={"completed": True})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


async def test_delete_task(client: AsyncClient) -> None:
    """DELETE /tasks/{id} removes the task and returns 204."""
    created = await client.post("/tasks", json={"title": "To be deleted"})
    task_id = created.json()["id"]

    response = await client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204

    # Confirm it is gone
    assert (await client.get(f"/tasks/{task_id}")).status_code == 404


async def test_delete_task_not_found(client: AsyncClient) -> None:
    """DELETE /tasks/{id} returns 404 for a non-existent task."""
    response = await client.delete("/tasks/99999")
    assert response.status_code == 404
