"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Task(Base):
    """Represents a task in the database."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


from enum import Enum as PyEnum
from sqlalchemy import Enum, Text, Date, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from sqlalchemy.orm import Mapped, mapped_column


class TaskStatus(PyEnum):
    """Enumeration for the status of a task."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
class TaskPriority(PyEnum):
    """Enumeration for the priority of a task."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
class TaskV2(Base):
    """Represents a task with UUID, enums for status and priority, and due date."""
    __tablename__ = "tasks_v2"
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        doc="Primary UUID key for the task",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Title of the task (required, max 200 chars).",
    )
    description: Mapped[str | None] = mapped_column(
        String(10000),
        nullable=True,
        doc="Optional detailed description (max 10k chars).",
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.TODO,
        doc="Status of the task (todo, in_progress, done)."
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
        doc="Priority of the task (low, medium, high)."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the task was created."
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the task was last updated."
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        doc="Optional due date for the task."
    )
