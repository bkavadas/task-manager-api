"""Comprehensive integration tests for the /tasks endpoints."""

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Health Endpoint
# ---------------------------------------------------------------------------


async def test_health_check_success(client: AsyncClient) -> None:
    """GET /health returns 200 with healthy status and database connected."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


# ---------------------------------------------------------------------------
# POST /tasks - Create Task
# ---------------------------------------------------------------------------


async def test_create_task_success(client: AsyncClient) -> None:
    """POST /tasks creates a task and returns 201 with complete task data."""
    payload = {"title": "Buy groceries", "description": "Milk, eggs, bread"}
    response = await client.post("/tasks", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert data["description"] == "Milk, eggs, bread"
    assert data["completed"] is False
    assert isinstance(data["id"], int)
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_task_without_description(client: AsyncClient) -> None:
    """POST /tasks succeeds when description is omitted."""
    response = await client.post("/tasks", json={"title": "Minimal task"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal task"
    assert data["description"] is None
    assert data["completed"] is False


async def test_create_task_missing_title_returns_422(client: AsyncClient) -> None:
    """POST /tasks rejects request with missing title field."""
    response = await client.post("/tasks", json={"description": "No title"})
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("title" in str(err).lower() for err in error_detail)


async def test_create_task_empty_title_returns_422(client: AsyncClient) -> None:
    """POST /tasks rejects an empty title string."""
    response = await client.post("/tasks", json={"title": ""})
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("title" in str(err).lower() for err in error_detail)


async def test_create_task_title_too_long_returns_422(client: AsyncClient) -> None:
    """POST /tasks rejects title exceeding 255 characters."""
    long_title = "a" * 256
    response = await client.post("/tasks", json={"title": long_title})
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any(
        "title" in str(err).lower() or "length" in str(err).lower()
        for err in error_detail
    )


async def test_create_task_description_too_long_returns_422(
    client: AsyncClient,
) -> None:
    """POST /tasks rejects description exceeding 1000 characters."""
    long_description = "a" * 1001
    response = await client.post(
        "/tasks", json={"title": "Valid title", "description": long_description}
    )
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any(
        "description" in str(err).lower() or "length" in str(err).lower()
        for err in error_detail
    )


async def test_create_task_title_whitespace_only_returns_422(
    client: AsyncClient,
) -> None:
    """POST /tasks rejects title with only whitespace characters."""
    response = await client.post("/tasks", json={"title": "   \t\n  "})
    assert response.status_code == 422
    # After stripping, empty string violates min_length=1


async def test_create_task_empty_json_returns_422(client: AsyncClient) -> None:
    """POST /tasks rejects empty JSON body."""
    response = await client.post("/tasks", json={})
    assert response.status_code == 422


async def test_create_task_invalid_json_returns_422(client: AsyncClient) -> None:
    """POST /tasks rejects invalid JSON structure."""
    response = await client.post("/tasks", json={"title": None})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /tasks - List Tasks
# ---------------------------------------------------------------------------


async def test_list_tasks_empty_returns_empty_list(client: AsyncClient) -> None:
    """GET /tasks returns empty list when no tasks exist."""
    response = await client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_tasks_returns_all_tasks(client: AsyncClient) -> None:
    """GET /tasks returns all tasks without pagination."""
    # Create multiple tasks
    await client.post("/tasks", json={"title": "Task 1"})
    await client.post("/tasks", json={"title": "Task 2"})
    await client.post("/tasks", json={"title": "Task 3"})

    response = await client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("id" in task and "title" in task for task in data)


async def test_list_tasks_pagination_skip(client: AsyncClient) -> None:
    """GET /tasks respects skip parameter for pagination."""
    # Create 5 tasks
    for i in range(5):
        await client.post("/tasks", json={"title": f"Task {i+1}"})

    # Skip first 2
    response = await client.get("/tasks?skip=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


async def test_list_tasks_pagination_limit(client: AsyncClient) -> None:
    """GET /tasks respects limit parameter for pagination."""
    # Create 5 tasks
    for i in range(5):
        await client.post("/tasks", json={"title": f"Task {i+1}"})

    # Limit to 2
    response = await client.get("/tasks?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_list_tasks_pagination_skip_and_limit(client: AsyncClient) -> None:
    """GET /tasks respects both skip and limit parameters."""
    # Create 10 tasks
    for i in range(10):
        await client.post("/tasks", json={"title": f"Task {i+1}"})

    # Skip 3, limit 4
    response = await client.get("/tasks?skip=3&limit=4")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4


async def test_list_tasks_filter_completed_true(client: AsyncClient) -> None:
    """GET /tasks filters by completed=True."""
    # Create completed and incomplete tasks
    await client.post("/tasks", json={"title": "Incomplete task"})

    task2 = await client.post("/tasks", json={"title": "Complete task"})
    task2_id = task2.json()["id"]
    await client.patch(f"/tasks/{task2_id}", json={"completed": True})

    # Filter for completed tasks
    response = await client.get("/tasks?completed=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == task2_id
    assert data[0]["completed"] is True


async def test_list_tasks_filter_completed_false(client: AsyncClient) -> None:
    """GET /tasks filters by completed=False."""
    # Create completed and incomplete tasks
    task1 = await client.post("/tasks", json={"title": "Incomplete task"})
    task1_id = task1.json()["id"]
    
    task2 = await client.post("/tasks", json={"title": "Complete task"})
    task2_id = task2.json()["id"]
    await client.patch(f"/tasks/{task2_id}", json={"completed": True})

    # Filter for incomplete tasks
    response = await client.get("/tasks?completed=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == task1_id
    assert data[0]["completed"] is False


async def test_list_tasks_no_filter_returns_all(client: AsyncClient) -> None:
    """GET /tasks without completed filter returns all tasks."""
    # Create completed and incomplete tasks
    await client.post("/tasks", json={"title": "Incomplete task"})
    task2 = await client.post("/tasks", json={"title": "Complete task"})
    task2_id = task2.json()["id"]
    await client.patch(f"/tasks/{task2_id}", json={"completed": True})

    # No filter
    response = await client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_list_tasks_invalid_skip_negative_returns_422(
    client: AsyncClient,
) -> None:
    """GET /tasks rejects negative skip value."""
    response = await client.get("/tasks?skip=-1")
    assert response.status_code == 422


async def test_list_tasks_invalid_limit_zero_returns_422(client: AsyncClient) -> None:
    """GET /tasks rejects limit=0."""
    response = await client.get("/tasks?limit=0")
    assert response.status_code == 422


async def test_list_tasks_invalid_limit_too_large_returns_422(
    client: AsyncClient,
) -> None:
    """GET /tasks rejects limit exceeding 1000."""
    response = await client.get("/tasks?limit=1001")
    assert response.status_code == 422


async def test_list_tasks_invalid_limit_negative_returns_422(
    client: AsyncClient,
) -> None:
    """GET /tasks rejects negative limit value."""
    response = await client.get("/tasks?limit=-1")
    assert response.status_code == 422


async def test_list_tasks_skip_exceeds_total_returns_empty(client: AsyncClient) -> None:
    """GET /tasks returns empty list when skip exceeds total tasks."""
    await client.post("/tasks", json={"title": "Only task"})
    
    response = await client.get("/tasks?skip=100")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_tasks_invalid_completed_value_returns_422(
    client: AsyncClient,
) -> None:
    """GET /tasks rejects invalid completed parameter value."""
    response = await client.get("/tasks?completed=maybe")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /tasks/{task_id} - Get Single Task
# ---------------------------------------------------------------------------


async def test_get_task_success(client: AsyncClient) -> None:
    """GET /tasks/{id} returns the correct task."""
    created = await client.post(
        "/tasks",
        json={"title": "Fetch me", "description": "Test description"},
    )
    task_id = created.json()["id"]

    response = await client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == "Fetch me"
    assert data["description"] == "Test description"
    assert data["completed"] is False
    assert "created_at" in data
    assert "updated_at" in data


async def test_get_task_not_found_returns_404(client: AsyncClient) -> None:
    """GET /tasks/{id} returns 404 for non-existent task."""
    response = await client.get("/tasks/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_get_task_invalid_id_format_returns_422(client: AsyncClient) -> None:
    """GET /tasks/{id} rejects non-integer task_id."""
    response = await client.get("/tasks/abc")
    assert response.status_code == 422


async def test_get_task_zero_id_returns_404(client: AsyncClient) -> None:
    """GET /tasks/0 returns 404 (valid format but non-existent)."""
    response = await client.get("/tasks/0")
    assert response.status_code == 404


async def test_get_task_negative_id_returns_422(client: AsyncClient) -> None:
    """GET /tasks/{id} rejects negative task_id."""
    response = await client.get("/tasks/-1")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /tasks/{task_id} - Update Task
# ---------------------------------------------------------------------------


async def test_update_task_success_partial(client: AsyncClient) -> None:
    """PATCH /tasks/{id} applies partial updates successfully."""
    created = await client.post(
        "/tasks",
        json={"title": "Original title", "description": "Original desc"},
    )
    task_id = created.json()["id"]

    response = await client.patch(
        f"/tasks/{task_id}",
        json={"title": "Updated title"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated title"
    assert data["description"] == "Original desc"  # Unchanged
    assert data["completed"] is False  # Unchanged


async def test_update_task_success_all_fields(client: AsyncClient) -> None:
    """PATCH /tasks/{id} updates all provided fields."""
    created = await client.post(
        "/tasks",
        json={"title": "Original", "description": "Original desc"},
    )
    task_id = created.json()["id"]

    response = await client.patch(
        f"/tasks/{task_id}",
        json={"title": "Updated", "description": "Updated desc", "completed": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated"
    assert data["description"] == "Updated desc"
    assert data["completed"] is True


async def test_update_task_title_only(client: AsyncClient) -> None:
    """PATCH /tasks/{id} updates only title field."""
    created = await client.post(
        "/tasks",
        json={"title": "Original", "description": "Keep this"},
    )
    task_id = created.json()["id"]

    response = await client.patch(f"/tasks/{task_id}", json={"title": "New title"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New title"
    assert data["description"] == "Keep this"


async def test_update_task_description_only(client: AsyncClient) -> None:
    """PATCH /tasks/{id} updates only description field."""
    created = await client.post(
        "/tasks",
        json={"title": "Keep this", "description": "Original"},
    )
    task_id = created.json()["id"]

    response = await client.patch(
        f"/tasks/{task_id}",
        json={"description": "New description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Keep this"
    assert data["description"] == "New description"


async def test_update_task_completed_only(client: AsyncClient) -> None:
    """PATCH /tasks/{id} updates only completed field."""
    created = await client.post("/tasks", json={"title": "Task"})
    task_id = created.json()["id"]

    response = await client.patch(f"/tasks/{task_id}", json={"completed": True})
    assert response.status_code == 200
    data = response.json()
    assert data["completed"] is True
    assert data["title"] == "Task"


async def test_update_task_set_description_to_null(client: AsyncClient) -> None:
    """PATCH /tasks/{id} can set description to null."""
    created = await client.post(
        "/tasks",
        json={"title": "Task", "description": "Has description"},
    )
    task_id = created.json()["id"]

    response = await client.patch(f"/tasks/{task_id}", json={"description": None})
    assert response.status_code == 200
    data = response.json()
    assert data["description"] is None


async def test_update_task_not_found_returns_404(client: AsyncClient) -> None:
    """PATCH /tasks/{id} returns 404 for non-existent task."""
    response = await client.patch("/tasks/99999", json={"title": "Updated"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_update_task_empty_title_returns_422(client: AsyncClient) -> None:
    """PATCH /tasks/{id} rejects empty title string."""
    created = await client.post("/tasks", json={"title": "Valid task"})
    task_id = created.json()["id"]

    response = await client.patch(f"/tasks/{task_id}", json={"title": ""})
    assert response.status_code == 422


async def test_update_task_title_too_long_returns_422(client: AsyncClient) -> None:
    """PATCH /tasks/{id} rejects title exceeding 255 characters."""
    created = await client.post("/tasks", json={"title": "Valid task"})
    task_id = created.json()["id"]

    long_title = "a" * 256
    response = await client.patch(f"/tasks/{task_id}", json={"title": long_title})
    assert response.status_code == 422


async def test_update_task_description_too_long_returns_422(
    client: AsyncClient,
) -> None:
    """PATCH /tasks/{id} rejects description exceeding 1000 characters."""
    created = await client.post("/tasks", json={"title": "Valid task"})
    task_id = created.json()["id"]

    long_description = "a" * 1001
    response = await client.patch(
        f"/tasks/{task_id}",
        json={"description": long_description},
    )
    assert response.status_code == 422


async def test_update_task_title_whitespace_only_returns_422(
    client: AsyncClient,
) -> None:
    """PATCH /tasks/{id} rejects title with only whitespace."""
    created = await client.post("/tasks", json={"title": "Valid task"})
    task_id = created.json()["id"]

    response = await client.patch(f"/tasks/{task_id}", json={"title": "   \t\n  "})
    assert response.status_code == 422


async def test_update_task_empty_json_succeeds(client: AsyncClient) -> None:
    """PATCH /tasks/{id} accepts empty JSON body (no-op update)."""
    created = await client.post("/tasks", json={"title": "Original"})
    task_id = created.json()["id"]
    original_data = created.json()

    response = await client.patch(f"/tasks/{task_id}", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == original_data["title"]


async def test_update_task_invalid_completed_type_returns_422(
    client: AsyncClient,
) -> None:
    """PATCH /tasks/{id} rejects invalid completed value type."""
    created = await client.post("/tasks", json={"title": "Task"})
    task_id = created.json()["id"]

    response = await client.patch(f"/tasks/{task_id}", json={"completed": "yes"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id} - Delete Task
# ---------------------------------------------------------------------------


async def test_delete_task_success_returns_204(client: AsyncClient) -> None:
    """DELETE /tasks/{id} removes the task and returns 204."""
    created = await client.post("/tasks", json={"title": "To be deleted"})
    task_id = created.json()["id"]

    response = await client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204
    assert response.content == b""  # 204 should have no body

    # Confirm it is gone
    get_response = await client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404


async def test_delete_task_not_found_returns_404(client: AsyncClient) -> None:
    """DELETE /tasks/{id} returns 404 for non-existent task."""
    response = await client.delete("/tasks/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_delete_task_invalid_id_format_returns_422(client: AsyncClient) -> None:
    """DELETE /tasks/{id} rejects non-integer task_id."""
    response = await client.delete("/tasks/abc")
    assert response.status_code == 422


async def test_delete_task_already_deleted_returns_404(client: AsyncClient) -> None:
    """DELETE /tasks/{id} returns 404 when deleting already deleted task."""
    created = await client.post("/tasks", json={"title": "Task"})
    task_id = created.json()["id"]

    # Delete once
    response1 = await client.delete(f"/tasks/{task_id}")
    assert response1.status_code == 204

    # Try to delete again
    response2 = await client.delete(f"/tasks/{task_id}")
    assert response2.status_code == 404
