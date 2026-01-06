# =============================================================================
# Todo Pydantic Models
# =============================================================================
"""
Pydantic models for Todo API requests and responses.

These models handle validation, serialization, and documentation
for all todo-related API operations. They are separate from the
SQLAlchemy ORM models in src/database/models.py.

Usage:
    from src.models.todo import TodoCreate, TodoResponse, TodoStatus

    # Create a new todo
    data = TodoCreate(title="Review PR", assigned_agent=AgentType.GITHUB)

    # Validate response
    response = TodoResponse.model_validate(todo_orm_instance)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------
class TodoStatus(str, Enum):
    """
    Valid status values for todos.

    The status follows a lifecycle:
    - pending: Initial state, waiting for execution
    - in_progress: Currently being executed by an agent
    - completed: Successfully finished
    - failed: Execution encountered an error
    - cancelled: Manually cancelled by user
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """
    Valid agent types for task assignment.

    Each agent has specific capabilities:
    - github: Repository management, issues, PRs
    - email: Read, draft, send emails
    - calendar: Event management, availability
    - obsidian: Note-taking, vault search
    - orchestrator: General tasks, coordination
    """

    GITHUB = "github"
    EMAIL = "email"
    CALENDAR = "calendar"
    OBSIDIAN = "obsidian"
    ORCHESTRATOR = "orchestrator"


class TodoPriority(int, Enum):
    """
    Priority levels for todos.

    Lower numbers = higher priority:
    - CRITICAL (1): Urgent, do immediately
    - HIGH (2): Important, do soon
    - MEDIUM (3): Normal priority (default)
    - LOW (4): Can wait
    - LOWEST (5): Backlog items
    """

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------
class TodoCreate(BaseModel):
    """
    Schema for creating a new todo.

    Only title is required. All other fields have sensible defaults.

    Attributes:
        title: Short description of the task (required, 1-500 chars).
        description: Detailed task information (optional).
        assigned_agent: Sub-agent to handle execution (optional).
        priority: Execution priority, 1-5 (default: 3/MEDIUM).
        scheduled_at: When to execute (optional, None = manual).
        parent_todo_id: Parent task ID for subtasks (optional).
        metadata: Additional flexible data (optional).

    Example:
        TodoCreate(
            title="Create GitHub issue for bug fix",
            description="Create an issue in repo/name for the login timeout bug",
            assigned_agent=AgentType.GITHUB,
            priority=TodoPriority.HIGH,
            metadata={"repo": "owner/repo", "labels": ["bug"]}
        )
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Short description of the task",
        examples=["Review PR #123", "Send weekly report email"],
    )
    description: Optional[str] = Field(
        None,
        description="Detailed task information and context",
        examples=["Check the authentication changes in PR #123 for security issues"],
    )
    assigned_agent: Optional[AgentType] = Field(
        None,
        description="Sub-agent responsible for execution",
    )
    priority: TodoPriority = Field(
        TodoPriority.MEDIUM,
        description="Execution priority (1=highest, 5=lowest)",
    )
    scheduled_at: Optional[datetime] = Field(
        None,
        description="Scheduled execution time (None for manual trigger)",
    )
    parent_todo_id: Optional[UUID] = Field(
        None,
        description="Parent task ID for creating subtasks",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible JSON storage for agent-specific parameters",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Create GitHub issue for bug fix",
                "description": "Create an issue in repo/name for the login timeout bug",
                "assigned_agent": "github",
                "priority": 2,
                "metadata": {"repo": "owner/repo", "labels": ["bug", "high-priority"]},
            }
        }
    )


class TodoUpdate(BaseModel):
    """
    Schema for updating an existing todo.

    All fields are optional - only provided fields will be updated.
    This allows partial updates without needing to send the full object.

    Attributes:
        title: Updated task title (1-500 chars if provided).
        description: Updated task description.
        assigned_agent: Updated agent assignment.
        priority: Updated priority level.
        scheduled_at: Updated scheduled time.
        metadata: Updated metadata (replaces existing, not merged).

    Example:
        TodoUpdate(priority=TodoPriority.CRITICAL)  # Only update priority
    """

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Updated task title",
    )
    description: Optional[str] = Field(
        None,
        description="Updated task description",
    )
    assigned_agent: Optional[AgentType] = Field(
        None,
        description="Updated agent assignment",
    )
    priority: Optional[TodoPriority] = Field(
        None,
        description="Updated priority",
    )
    scheduled_at: Optional[datetime] = Field(
        None,
        description="Updated scheduled time",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Updated metadata (replaces existing)",
    )


class TodoExecuteRequest(BaseModel):
    """
    Schema for manually triggering todo execution.

    Attributes:
        force: Force execution even if already attempted or in wrong state.
        timeout_seconds: Maximum time to wait for execution (10-3600s).

    Example:
        TodoExecuteRequest(force=True, timeout_seconds=600)
    """

    force: bool = Field(
        False,
        description="Force execution even if already attempted",
    )
    timeout_seconds: int = Field(
        300,
        ge=10,
        le=3600,
        description="Execution timeout in seconds",
    )


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------
class TodoResponse(BaseModel):
    """
    Schema for todo responses.

    Includes all todo fields plus computed properties like subtask info.
    Used for single todo retrieval and as items in list responses.

    Attributes:
        id: Unique identifier (UUID).
        title: Task title.
        description: Task description (may be None).
        status: Current status (pending, in_progress, completed, failed, cancelled).
        assigned_agent: Assigned agent (may be None).
        priority: Priority level (1-5).
        scheduled_at: Scheduled execution time (may be None).
        result: Execution result (may be None).
        error_message: Error details if failed (may be None).
        execution_attempts: Number of execution attempts.
        chat_id: Linked conversation ID (may be None).
        parent_todo_id: Parent task ID (may be None).
        metadata: Additional data dictionary.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        started_at: Execution start timestamp (may be None).
        completed_at: Completion timestamp (may be None).
        created_by: Creator identifier (may be None).
        has_subtasks: Whether this todo has child tasks.
        subtask_count: Number of subtasks.
    """

    id: UUID = Field(..., description="Unique identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TodoStatus = Field(..., description="Current status")
    assigned_agent: Optional[AgentType] = Field(None, description="Assigned agent")
    priority: TodoPriority = Field(..., description="Priority level")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled time")
    result: Optional[str] = Field(None, description="Execution result")
    error_message: Optional[str] = Field(None, description="Error if failed")
    execution_attempts: int = Field(..., description="Attempt count")
    chat_id: Optional[UUID] = Field(None, description="Linked conversation")
    parent_todo_id: Optional[UUID] = Field(None, description="Parent task")
    metadata: dict[str, Any] = Field(..., description="Additional data")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    started_at: Optional[datetime] = Field(None, description="Execution start")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    created_by: Optional[str] = Field(None, description="Creator identifier")

    # Computed fields (set by service layer)
    has_subtasks: bool = Field(False, description="Whether task has subtasks")
    subtask_count: int = Field(0, description="Number of subtasks")

    model_config = ConfigDict(from_attributes=True)


class TodoListResponse(BaseModel):
    """
    Schema for paginated todo list responses.

    Provides pagination metadata alongside the list of todos.

    Attributes:
        items: List of todos for the current page.
        total: Total count of todos matching the filters.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        has_next: Whether more pages exist after this one.

    Example:
        {
            "items": [...],
            "total": 42,
            "page": 1,
            "page_size": 20,
            "has_next": true
        }
    """

    items: list[TodoResponse] = Field(..., description="List of todos")
    total: int = Field(..., description="Total count matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether more pages exist")


class TodoExecuteResponse(BaseModel):
    """
    Schema for execution response.

    Returned after manually triggering todo execution.

    Attributes:
        todo_id: The executed todo's ID.
        status: Status after execution attempt.
        result: Execution result (if successful).
        error_message: Error details (if failed).
        execution_time_ms: How long execution took in milliseconds.

    Example:
        {
            "todo_id": "...",
            "status": "completed",
            "result": "Created issue #123 successfully",
            "error_message": null,
            "execution_time_ms": 1523
        }
    """

    todo_id: UUID = Field(..., description="Executed todo ID")
    status: TodoStatus = Field(..., description="Status after execution")
    result: Optional[str] = Field(None, description="Execution result")
    error_message: Optional[str] = Field(None, description="Error if failed")
    execution_time_ms: int = Field(..., description="Execution duration in ms")


class TodoStats(BaseModel):
    """
    Schema for todo statistics.

    Provides aggregate counts for dashboard and reporting.

    Attributes:
        total: Total number of todos.
        pending: Count of pending todos.
        in_progress: Count of in-progress todos.
        completed: Count of completed todos.
        failed: Count of failed todos.
        cancelled: Count of cancelled todos.
        by_agent: Count breakdown by assigned agent.
        by_priority: Count breakdown by priority level.

    Example:
        {
            "total": 42,
            "pending": 10,
            "in_progress": 2,
            "completed": 25,
            "failed": 3,
            "cancelled": 2,
            "by_agent": {"github": 15, "email": 10},
            "by_priority": {1: 5, 2: 10, 3: 20, 4: 5, 5: 2}
        }
    """

    total: int = Field(..., description="Total todos")
    pending: int = Field(..., description="Pending count")
    in_progress: int = Field(..., description="In progress count")
    completed: int = Field(..., description="Completed count")
    failed: int = Field(..., description="Failed count")
    cancelled: int = Field(..., description="Cancelled count")
    by_agent: dict[str, int] = Field(..., description="Count by assigned agent")
    by_priority: dict[int, int] = Field(..., description="Count by priority")
