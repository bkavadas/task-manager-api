"""Pydantic schemas for request validation and response serialization."""

from datetime import datetime

from pydantic import BaseModel, Field, StrictBool, field_validator


class TaskBase(BaseModel):
    """Shared fields for task creation and updates."""

    title: str = Field(..., min_length=1, max_length=255, examples=["Buy groceries"])
    description: str | None = Field(
        None, max_length=1000, examples=["Milk, eggs, bread"]
    )

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, v: str) -> str:
        """Strip surrounding whitespace; min_length=1 then rejects blank strings."""
        if isinstance(v, str):
            return v.strip()
        return v


class TaskCreate(TaskBase):
    """Schema for creating a new task."""


class TaskUpdate(BaseModel):
    """Schema for partially updating an existing task.

    All fields are optional; only provided fields are applied.
    """

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    completed: StrictBool | None = None

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        """Strip surrounding whitespace; min_length=1 then rejects blank strings."""
        if isinstance(v, str):
            return v.strip()
        return v


class TaskResponse(TaskBase):
    """Schema returned in API responses."""

    id: int
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

class TaskV2Base(BaseModel):
    """
    Shared fields for TaskV2 creation and update.
    """
    title: str = Field(..., min_length=1, max_length=200, examples=["Buy groceries"])
    description: Optional[str] = Field(None, max_length=10000, examples=["Milk, eggs, bread"])
    status: str = Field(..., pattern="^(todo|in_progress|done)$", examples=["todo"])
    priority: str = Field(..., pattern="^(low|medium|high)$", examples=["medium"])
    due_date: Optional[datetime] = Field(
        None,
        description="Optional due date for the task; must not be in the past if provided."
    )

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            now = datetime.now(timezone.utc)
            # If naive datetime, assume UTC
            if v.tzinfo is None:
                v_local = v.replace(tzinfo=timezone.utc)
            else:
                v_local = v
            if v_local < now:
                raise ValueError("due_date must not be in the past.")
        return v

class TaskV2Create(TaskV2Base):
    """
    Schema for creating a new TaskV2.
    """

class TaskV2Update(BaseModel):
    """
    Schema for partially updating an existing TaskV2.
    All fields are optional; only provided fields are applied.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=10000)
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    due_date: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip()
        return v

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            now = datetime.now(timezone.utc)
            # If naive datetime, assume UTC
            if v.tzinfo is None:
                v_local = v.replace(tzinfo=timezone.utc)
            else:
                v_local = v
            if v_local < now:
                raise ValueError("due_date must not be in the past.")
        return v

class TaskV2Response(TaskV2Base):
    """
    Schema returned in API responses for TaskV2.
    """
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
