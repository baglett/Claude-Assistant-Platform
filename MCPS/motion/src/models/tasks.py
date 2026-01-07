# =============================================================================
# Motion MCP Server - Task Models
# =============================================================================
"""
Pydantic models for Motion Task API.

These models represent tasks, their properties, and related structures
as defined by the Motion API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------
class Priority(str, Enum):
    """
    Task priority levels.

    Attributes:
        ASAP: Urgent/immediate priority.
        HIGH: High priority.
        MEDIUM: Medium priority.
        LOW: Low priority.
    """

    ASAP = "ASAP"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DeadlineType(str, Enum):
    """
    Task deadline types.

    Attributes:
        HARD: Hard deadline that cannot be missed.
        SOFT: Soft deadline that can be adjusted.
        NONE: No deadline.
    """

    HARD = "HARD"
    SOFT = "SOFT"
    NONE = "NONE"


# -----------------------------------------------------------------------------
# Nested Models
# -----------------------------------------------------------------------------
class TaskStatus(BaseModel):
    """
    Task status information.

    Attributes:
        name: Status name (e.g., "To Do", "In Progress", "Done").
        isDefaultStatus: Whether this is the default status.
        isResolvedStatus: Whether this status marks the task as resolved.
    """

    name: str = Field(..., description="Status name")
    isDefaultStatus: bool = Field(
        default=False, description="Whether this is the default status"
    )
    isResolvedStatus: bool = Field(
        default=False, description="Whether this status marks task as resolved"
    )


class Assignee(BaseModel):
    """
    Task assignee (user) information.

    Attributes:
        id: User ID.
        name: User's display name.
        email: User's email address.
    """

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="User's display name")
    email: Optional[str] = Field(default=None, description="User's email")


class SchedulingChunk(BaseModel):
    """
    A scheduling chunk representing a time block for the task.

    Motion may split tasks into multiple chunks across different time blocks.

    Attributes:
        id: Chunk ID.
        duration: Duration in minutes.
        scheduledStart: Scheduled start time.
        scheduledEnd: Scheduled end time.
        completedTime: When the chunk was completed.
        isFixed: Whether this chunk is fixed in time.
    """

    id: str = Field(..., description="Chunk ID")
    duration: int = Field(..., description="Duration in minutes")
    scheduledStart: Optional[datetime] = Field(
        default=None, description="Scheduled start time"
    )
    scheduledEnd: Optional[datetime] = Field(
        default=None, description="Scheduled end time"
    )
    completedTime: Optional[datetime] = Field(
        default=None, description="When chunk was completed"
    )
    isFixed: bool = Field(default=False, description="Whether chunk is fixed")


class ProjectRef(BaseModel):
    """
    Reference to a project.

    Attributes:
        id: Project ID.
        name: Project name.
    """

    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")


class WorkspaceRef(BaseModel):
    """
    Reference to a workspace.

    Attributes:
        id: Workspace ID.
        name: Workspace name.
    """

    id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")


class CreatorRef(BaseModel):
    """
    Reference to the task creator.

    Attributes:
        id: User ID.
        name: User's display name.
    """

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="User's display name")


class Label(BaseModel):
    """
    Task label.

    Attributes:
        name: Label name.
    """

    name: str = Field(..., description="Label name")


# -----------------------------------------------------------------------------
# Auto-Scheduling Configuration
# -----------------------------------------------------------------------------
class AutoScheduledConfig(BaseModel):
    """
    Auto-scheduling configuration for a task.

    Attributes:
        startDate: Earliest date Motion can schedule the task.
        deadlineType: Type of deadline (HARD, SOFT, NONE).
        schedule: Schedule ID to use for auto-scheduling.
    """

    startDate: Optional[str] = Field(
        default=None,
        description="Earliest date to schedule (YYYY-MM-DD)",
    )
    deadlineType: DeadlineType = Field(
        default=DeadlineType.SOFT,
        description="Deadline type",
    )
    schedule: Optional[str] = Field(
        default=None,
        description="Schedule ID for auto-scheduling",
    )


# -----------------------------------------------------------------------------
# Task Models
# -----------------------------------------------------------------------------
class Task(BaseModel):
    """
    Complete task representation from Motion API.

    Attributes:
        id: Unique task identifier.
        name: Task title/name.
        description: Task description (HTML).
        duration: Duration in minutes, "NONE", or "REMINDER".
        dueDate: Due date for the task.
        deadlineType: Type of deadline.
        completed: Whether the task is completed.
        completedTime: When the task was completed.
        createdTime: When the task was created.
        updatedTime: When the task was last updated.
        priority: Task priority level.
        status: Task status information.
        labels: List of labels attached to the task.
        assignees: List of users assigned to the task.
        project: Associated project (if any).
        workspace: Workspace containing the task.
        creator: User who created the task.
        scheduledStart: When Motion scheduled the task to start.
        scheduledEnd: When Motion scheduled the task to end.
        schedulingIssue: Whether there are scheduling issues.
        parentRecurringTaskId: Parent recurring task ID (if applicable).
        chunks: Scheduling chunks for the task.
        customFieldValues: Custom field values.
        lastInteractedTime: Last interaction time.
    """

    id: str = Field(..., description="Task ID")
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(default=None, description="Task description")
    duration: Optional[str | int] = Field(
        default=None, description="Duration (minutes, 'NONE', or 'REMINDER')"
    )
    dueDate: Optional[datetime] = Field(default=None, description="Due date")
    deadlineType: DeadlineType = Field(
        default=DeadlineType.SOFT, description="Deadline type"
    )
    completed: bool = Field(default=False, description="Whether task is completed")
    completedTime: Optional[datetime] = Field(
        default=None, description="Completion time"
    )
    createdTime: datetime = Field(..., description="Creation time")
    updatedTime: Optional[datetime] = Field(
        default=None, description="Last update time"
    )
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority level")
    status: TaskStatus = Field(..., description="Task status")
    labels: list[Label] = Field(default_factory=list, description="Labels")
    assignees: list[Assignee] = Field(default_factory=list, description="Assignees")
    project: Optional[ProjectRef] = Field(default=None, description="Project reference")
    workspace: WorkspaceRef = Field(..., description="Workspace reference")
    creator: Optional[CreatorRef] = Field(default=None, description="Creator reference")
    scheduledStart: Optional[datetime] = Field(
        default=None, description="Scheduled start"
    )
    scheduledEnd: Optional[datetime] = Field(default=None, description="Scheduled end")
    schedulingIssue: bool = Field(
        default=False, description="Whether there are scheduling issues"
    )
    parentRecurringTaskId: Optional[str] = Field(
        default=None, description="Parent recurring task ID"
    )
    chunks: list[SchedulingChunk] = Field(
        default_factory=list, description="Scheduling chunks"
    )
    customFieldValues: Optional[dict[str, Any]] = Field(
        default=None, description="Custom field values"
    )
    lastInteractedTime: Optional[datetime] = Field(
        default=None, description="Last interaction time"
    )


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------
class TaskCreate(BaseModel):
    """
    Request model for creating a new task.

    Attributes:
        name: Task name (required).
        workspaceId: Workspace ID (required).
        dueDate: Due date (required for scheduled tasks).
        duration: Duration in minutes, "NONE", or "REMINDER".
        status: Task status name.
        autoScheduled: Auto-scheduling configuration.
        projectId: Project ID to add task to.
        description: Task description (GitHub-flavored Markdown).
        priority: Task priority.
        labels: Label names to add.
        assigneeId: User ID to assign task to.
    """

    name: str = Field(..., description="Task name", min_length=1)
    workspaceId: str = Field(..., description="Workspace ID")
    dueDate: Optional[str] = Field(
        default=None, description="Due date (ISO 8601 format)"
    )
    duration: Optional[str | int] = Field(
        default=None, description="Duration (minutes, 'NONE', or 'REMINDER')"
    )
    status: Optional[str] = Field(default=None, description="Status name")
    autoScheduled: Optional[AutoScheduledConfig] = Field(
        default=None, description="Auto-scheduling config"
    )
    projectId: Optional[str] = Field(default=None, description="Project ID")
    description: Optional[str] = Field(default=None, description="Task description")
    priority: Optional[Priority] = Field(default=None, description="Priority level")
    labels: Optional[list[str]] = Field(default=None, description="Label names")
    assigneeId: Optional[str] = Field(default=None, description="Assignee user ID")


class TaskUpdate(BaseModel):
    """
    Request model for updating an existing task.

    All fields are optional - only provided fields will be updated.

    Attributes:
        name: New task name.
        dueDate: New due date.
        duration: New duration.
        status: New status name.
        projectId: New project ID.
        description: New description.
        priority: New priority.
        labels: New label names (replaces existing).
        assigneeId: New assignee user ID.
    """

    name: Optional[str] = Field(default=None, description="Task name")
    dueDate: Optional[str] = Field(default=None, description="Due date")
    duration: Optional[str | int] = Field(default=None, description="Duration")
    status: Optional[str] = Field(default=None, description="Status name")
    projectId: Optional[str] = Field(default=None, description="Project ID")
    description: Optional[str] = Field(default=None, description="Description")
    priority: Optional[Priority] = Field(default=None, description="Priority")
    labels: Optional[list[str]] = Field(default=None, description="Label names")
    assigneeId: Optional[str] = Field(default=None, description="Assignee user ID")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------
class TaskListResponse(BaseModel):
    """
    Response model for listing tasks.

    Attributes:
        tasks: List of tasks.
        meta: Pagination metadata.
    """

    tasks: list[Task] = Field(default_factory=list, description="List of tasks")
    meta: Optional[dict[str, Any]] = Field(
        default=None, description="Pagination metadata"
    )
