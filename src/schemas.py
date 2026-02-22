"""Pydantic schemas for request validation and response serialization."""

from datetime import datetime

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """Shared fields for task creation and updates."""

    title: str = Field(..., min_length=1, max_length=255, examples=["Buy groceries"])
    description: str | None = Field(
        None, max_length=1000, examples=["Milk, eggs, bread"]
    )


class TaskCreate(TaskBase):
    """Schema for creating a new task."""


class TaskUpdate(BaseModel):
    """Schema for partially updating an existing task.

    All fields are optional; only provided fields are applied.
    """

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    completed: bool | None = None


class TaskResponse(TaskBase):
    """Schema returned in API responses."""

    id: int
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
