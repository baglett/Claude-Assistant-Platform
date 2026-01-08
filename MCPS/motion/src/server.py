# =============================================================================
# Motion MCP Server
# =============================================================================
"""
FastMCP server providing Motion API tools for task and project management.

This server exposes MCP tools for:
- Task management (create, read, update, delete, move, unassign)
- Project management (list, get, create)
- Workspace management (list)
- User management (list, get current)
- Rate limit monitoring

The server includes robust rate limiting to prevent exceeding Motion's
API limits (12 req/min individual, 120 req/min team).

CRITICAL: Rate limiting is strictly enforced to prevent account suspension.
"""

import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.client import (
    MotionApiError,
    MotionAuthenticationError,
    MotionClient,
    MotionNotFoundError,
)
from src.models.projects import ProjectCreate
from src.models.tasks import Priority, TaskCreate, TaskUpdate
from src.rate_limiter import AccountType, RateLimitExceededError

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
class Settings(BaseSettings):
    """
    Server settings loaded from environment variables.

    Attributes:
        motion_api_key: Motion API key (required).
        motion_api_base_url: Base URL for Motion API.
        motion_account_type: Account type for rate limiting.
        motion_rate_limit_override: Override default rate limit.
        motion_rate_limit_window: Rate limit window in seconds.
        motion_rate_limit_db: Path to rate limit SQLite database.
        motion_request_timeout: Request timeout in seconds.
        host: Server host address.
        port: Server port number.
        log_level: Logging level.
    """

    motion_api_key: str = Field(
        default="",
        description="Motion API key",
    )
    motion_api_base_url: str = Field(
        default="https://api.usemotion.com/v1",
        description="Motion API base URL",
    )
    motion_account_type: str = Field(
        default="individual",
        description="Account type: individual, team, or enterprise",
    )
    motion_rate_limit_override: int = Field(
        default=0,
        description="Override rate limit (0 = use default)",
    )
    motion_rate_limit_window: int = Field(
        default=60,
        description="Rate limit window in seconds",
    )
    motion_rate_limit_db: str = Field(
        default="motion_rate_limit.db",
        description="Path to rate limit database",
    )
    motion_request_timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Server host address",
    )
    port: int = Field(
        default=8081,
        description="Server port number",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def account_type_enum(self) -> AccountType:
        """Convert account type string to enum."""
        try:
            return AccountType(self.motion_account_type.lower())
        except ValueError:
            logger.warning(
                f"Invalid account type '{self.motion_account_type}', using 'individual'"
            )
            return AccountType.INDIVIDUAL


settings = Settings()


# -----------------------------------------------------------------------------
# Initialize Motion Client
# -----------------------------------------------------------------------------
motion_client: Optional[MotionClient] = None


def get_motion_client() -> MotionClient:
    """
    Get or create the Motion client.

    Returns:
        Initialized MotionClient instance.

    Raises:
        HTTPException: If API key is not configured.
    """
    global motion_client

    if not settings.motion_api_key:
        raise HTTPException(
            status_code=500,
            detail="MOTION_API_KEY not configured",
        )

    if motion_client is None:
        motion_client = MotionClient(
            api_key=settings.motion_api_key,
            base_url=settings.motion_api_base_url,
            account_type=settings.account_type_enum,
            rate_limit_override=settings.motion_rate_limit_override,
            rate_limit_window=settings.motion_rate_limit_window,
            rate_limit_db=settings.motion_rate_limit_db,
            timeout=settings.motion_request_timeout,
        )

    return motion_client


# -----------------------------------------------------------------------------
# Pydantic Models for HTTP API
# -----------------------------------------------------------------------------
class TaskCreateRequest(BaseModel):
    """Request model for creating a task via HTTP."""

    name: str = Field(..., description="Task name")
    workspace_id: str = Field(..., description="Workspace ID")
    due_date: Optional[str] = Field(default=None, description="Due date (ISO 8601)")
    duration: Optional[int] = Field(default=None, description="Duration in minutes")
    project_id: Optional[str] = Field(default=None, description="Project ID")
    description: Optional[str] = Field(default=None, description="Task description")
    priority: Optional[str] = Field(default=None, description="Priority level")
    assignee_id: Optional[str] = Field(default=None, description="Assignee user ID")
    labels: Optional[list[str]] = Field(default=None, description="Label names")


class TaskUpdateRequest(BaseModel):
    """Request model for updating a task via HTTP."""

    name: Optional[str] = Field(default=None, description="Task name")
    due_date: Optional[str] = Field(default=None, description="Due date")
    duration: Optional[int] = Field(default=None, description="Duration in minutes")
    project_id: Optional[str] = Field(default=None, description="Project ID")
    description: Optional[str] = Field(default=None, description="Description")
    priority: Optional[str] = Field(default=None, description="Priority level")
    status: Optional[str] = Field(default=None, description="Status name")
    assignee_id: Optional[str] = Field(default=None, description="Assignee user ID")
    labels: Optional[list[str]] = Field(default=None, description="Label names")


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def handle_api_error(e: Exception) -> dict[str, Any]:
    """
    Convert API exceptions to a standardized error response.

    Args:
        e: The exception to handle.

    Returns:
        Dictionary with error details.
    """
    if isinstance(e, RateLimitExceededError):
        return {
            "success": False,
            "error": "rate_limit_exceeded",
            "message": e.message,
            "wait_seconds": e.wait_seconds,
        }
    elif isinstance(e, MotionAuthenticationError):
        return {
            "success": False,
            "error": "authentication_error",
            "message": "Invalid API key or unauthorized access",
        }
    elif isinstance(e, MotionNotFoundError):
        return {
            "success": False,
            "error": "not_found",
            "message": e.message,
        }
    elif isinstance(e, MotionApiError):
        return {
            "success": False,
            "error": "api_error",
            "message": e.message,
            "status_code": e.status_code,
            "details": e.details,
        }
    else:
        logger.error(f"Unexpected error: {e}")
        return {
            "success": False,
            "error": "unexpected_error",
            "message": str(e),
        }


# -----------------------------------------------------------------------------
# FastMCP Server
# -----------------------------------------------------------------------------
mcp = FastMCP("motion-mcp")


# -----------------------------------------------------------------------------
# Task Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def motion_list_tasks(
    workspace_id: Optional[str] = None,
    project_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    """
    List tasks from Motion with optional filters.

    Filter tasks by workspace, project, assignee, or status.
    Results include task details like name, due date, priority, and assignees.

    Args:
        workspace_id: Filter by workspace ID.
        project_id: Filter by project ID.
        assignee_id: Filter by assignee user ID.
        status: Filter by status name (e.g., "To Do", "In Progress", "Done").

    Returns:
        Dictionary with list of tasks and metadata.
    """
    try:
        client = get_motion_client()
        response = await client.list_tasks(
            workspace_id=workspace_id,
            project_id=project_id,
            assignee_id=assignee_id,
            status=status,
        )
        return {
            "success": True,
            "tasks": [t.model_dump() for t in response.tasks],
            "count": len(response.tasks),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_get_task(task_id: str) -> dict[str, Any]:
    """
    Get a specific task by ID.

    Retrieves full task details including scheduling information,
    assignees, labels, and custom fields.

    Args:
        task_id: The unique task identifier.

    Returns:
        Dictionary with task details or error.
    """
    try:
        client = get_motion_client()
        task = await client.get_task(task_id)
        return {
            "success": True,
            "task": task.model_dump(),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_create_task(
    name: str,
    workspace_id: str,
    due_date: Optional[str] = None,
    duration: Optional[int] = None,
    project_id: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Create a new task in Motion.

    Creates a task with the specified properties. The task will be
    automatically scheduled by Motion based on the due date and duration.

    Args:
        name: Task name/title (required).
        workspace_id: Workspace ID to create task in (required).
        due_date: Due date in ISO 8601 format (e.g., "2024-12-31T23:59:59Z").
        duration: Duration in minutes (or "NONE" / "REMINDER").
        project_id: Project ID to add task to.
        description: Task description (GitHub-flavored Markdown supported).
        priority: Priority level (ASAP, HIGH, MEDIUM, LOW).
        assignee_id: User ID to assign task to.
        labels: List of label names to add.

    Returns:
        Dictionary with created task details or error.
    """
    try:
        client = get_motion_client()

        # Build task create model
        task_data = TaskCreate(
            name=name,
            workspaceId=workspace_id,
            dueDate=due_date,
            duration=duration,
            projectId=project_id,
            description=description,
            priority=Priority(priority) if priority else None,
            assigneeId=assignee_id,
            labels=labels,
        )

        task = await client.create_task(task_data)
        return {
            "success": True,
            "task": task.model_dump(),
            "message": f"Task '{name}' created successfully",
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_update_task(
    task_id: str,
    name: Optional[str] = None,
    due_date: Optional[str] = None,
    duration: Optional[int] = None,
    project_id: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Update an existing task in Motion.

    Only provided fields will be updated. Omit fields to keep current values.

    Args:
        task_id: The task ID to update (required).
        name: New task name.
        due_date: New due date (ISO 8601 format).
        duration: New duration in minutes.
        project_id: New project ID.
        description: New description.
        priority: New priority (ASAP, HIGH, MEDIUM, LOW).
        status: New status name.
        assignee_id: New assignee user ID.
        labels: New label names (replaces existing).

    Returns:
        Dictionary with updated task details or error.
    """
    try:
        client = get_motion_client()

        updates = TaskUpdate(
            name=name,
            dueDate=due_date,
            duration=duration,
            projectId=project_id,
            description=description,
            priority=Priority(priority) if priority else None,
            status=status,
            assigneeId=assignee_id,
            labels=labels,
        )

        task = await client.update_task(task_id, updates)
        return {
            "success": True,
            "task": task.model_dump(),
            "message": "Task updated successfully",
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_delete_task(task_id: str) -> dict[str, Any]:
    """
    Delete a task from Motion.

    WARNING: This permanently deletes the task and cannot be undone.

    Args:
        task_id: The task ID to delete.

    Returns:
        Dictionary with success status or error.
    """
    try:
        client = get_motion_client()
        await client.delete_task(task_id)
        return {
            "success": True,
            "message": f"Task {task_id} deleted successfully",
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_move_task(
    task_id: str,
    workspace_id: str,
    project_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Move a task to a different workspace or project.

    Args:
        task_id: The task ID to move.
        workspace_id: Target workspace ID.
        project_id: Target project ID (optional).

    Returns:
        Dictionary with updated task details or error.
    """
    try:
        client = get_motion_client()
        task = await client.move_task(task_id, workspace_id, project_id)
        return {
            "success": True,
            "task": task.model_dump(),
            "message": "Task moved successfully",
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_unassign_task(task_id: str) -> dict[str, Any]:
    """
    Remove the assignee from a task.

    Args:
        task_id: The task ID to unassign.

    Returns:
        Dictionary with updated task details or error.
    """
    try:
        client = get_motion_client()
        task = await client.unassign_task(task_id)
        return {
            "success": True,
            "task": task.model_dump(),
            "message": "Task unassigned successfully",
        }
    except Exception as e:
        return handle_api_error(e)


# -----------------------------------------------------------------------------
# Project Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def motion_list_projects(
    workspace_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    List projects from Motion.

    Args:
        workspace_id: Filter by workspace ID (optional).

    Returns:
        Dictionary with list of projects.
    """
    try:
        client = get_motion_client()
        response = await client.list_projects(workspace_id=workspace_id)
        return {
            "success": True,
            "projects": [p.model_dump() for p in response.projects],
            "count": len(response.projects),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_get_project(project_id: str) -> dict[str, Any]:
    """
    Get a specific project by ID.

    Args:
        project_id: The project ID.

    Returns:
        Dictionary with project details or error.
    """
    try:
        client = get_motion_client()
        project = await client.get_project(project_id)
        return {
            "success": True,
            "project": project.model_dump(),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_create_project(
    name: str,
    workspace_id: str,
    description: Optional[str] = None,
    status: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Create a new project in Motion.

    Args:
        name: Project name (required).
        workspace_id: Workspace ID (required).
        description: Project description.
        status: Initial status name.
        labels: Label names to add.

    Returns:
        Dictionary with created project details or error.
    """
    try:
        client = get_motion_client()

        project_data = ProjectCreate(
            name=name,
            workspaceId=workspace_id,
            description=description,
            status=status,
            labels=labels,
        )

        project = await client.create_project(project_data)
        return {
            "success": True,
            "project": project.model_dump(),
            "message": f"Project '{name}' created successfully",
        }
    except Exception as e:
        return handle_api_error(e)


# -----------------------------------------------------------------------------
# Workspace Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def motion_list_workspaces() -> dict[str, Any]:
    """
    List all accessible workspaces.

    Returns:
        Dictionary with list of workspaces.
    """
    try:
        client = get_motion_client()
        response = await client.list_workspaces()
        return {
            "success": True,
            "workspaces": [w.model_dump() for w in response.workspaces],
            "count": len(response.workspaces),
        }
    except Exception as e:
        return handle_api_error(e)


# -----------------------------------------------------------------------------
# User Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def motion_list_users(
    workspace_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    List users in a workspace.

    Args:
        workspace_id: Workspace ID to list users from.

    Returns:
        Dictionary with list of users.
    """
    try:
        client = get_motion_client()
        response = await client.list_users(workspace_id=workspace_id)
        return {
            "success": True,
            "users": [u.model_dump() for u in response.users],
            "count": len(response.users),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def motion_get_current_user() -> dict[str, Any]:
    """
    Get the current authenticated user.

    Returns:
        Dictionary with current user details.
    """
    try:
        client = get_motion_client()
        user = await client.get_current_user()
        return {
            "success": True,
            "user": user.model_dump(),
        }
    except Exception as e:
        return handle_api_error(e)


# -----------------------------------------------------------------------------
# Rate Limit Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def motion_get_rate_limit_status() -> dict[str, Any]:
    """
    Get current rate limit status.

    Use this to check remaining API requests before making calls.
    Helps prevent rate limit errors.

    Returns:
        Dictionary with rate limit statistics including:
        - max_requests: Maximum requests allowed per window
        - remaining_requests: Requests remaining in current window
        - wait_seconds: Seconds to wait if rate limited
        - can_proceed: Whether requests can be made now
    """
    try:
        client = get_motion_client()
        stats = await client.get_rate_limit_status()
        return {
            "success": True,
            **stats,
        }
    except Exception as e:
        return handle_api_error(e)


# -----------------------------------------------------------------------------
# FastAPI Application (for HTTP access)
# -----------------------------------------------------------------------------
fastapi_app = FastAPI(
    title="Motion MCP Server",
    description="MCP server providing Motion API tools for task and project management",
    version="0.1.0",
)


@fastapi_app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Dictionary with service status.
    """
    configured = bool(settings.motion_api_key)
    return {
        "status": "healthy" if configured else "unconfigured",
        "service": "motion-mcp",
        "api_configured": configured,
        "rate_limit_type": settings.motion_account_type,
    }


@fastapi_app.get("/rate-limit")
async def get_rate_limit() -> dict[str, Any]:
    """
    Get rate limit status via HTTP.

    Returns:
        Rate limit statistics.
    """
    return await motion_get_rate_limit_status()


# -----------------------------------------------------------------------------
# HTTP Tool Endpoints (for agent access)
# -----------------------------------------------------------------------------
class ListTasksRequest(BaseModel):
    """Request model for listing tasks."""

    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[str] = None


class GetTaskRequest(BaseModel):
    """Request model for getting a single task."""

    task_id: str


class DeleteTaskRequest(BaseModel):
    """Request model for deleting a task."""

    task_id: str


class MoveTaskRequest(BaseModel):
    """Request model for moving a task."""

    task_id: str
    workspace_id: str
    project_id: Optional[str] = None


class UnassignTaskRequest(BaseModel):
    """Request model for unassigning a task."""

    task_id: str


class TaskUpdateHttpRequest(BaseModel):
    """Request model for updating a task via HTTP."""

    task_id: str
    name: Optional[str] = None
    due_date: Optional[str] = None
    duration: Optional[int] = None
    project_id: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    labels: Optional[list[str]] = None


class ListProjectsRequest(BaseModel):
    """Request model for listing projects."""

    workspace_id: Optional[str] = None


class GetProjectRequest(BaseModel):
    """Request model for getting a single project."""

    project_id: str


class ProjectCreateRequest(BaseModel):
    """Request model for creating a project."""

    name: str
    workspace_id: str
    description: Optional[str] = None
    status: Optional[str] = None
    labels: Optional[list[str]] = None


class ListUsersRequest(BaseModel):
    """Request model for listing users."""

    workspace_id: Optional[str] = None


@fastapi_app.post("/tools/motion_list_tasks")
async def http_list_tasks(request: ListTasksRequest) -> dict[str, Any]:
    """HTTP endpoint for listing tasks."""
    return await motion_list_tasks(
        workspace_id=request.workspace_id,
        project_id=request.project_id,
        assignee_id=request.assignee_id,
        status=request.status,
    )


@fastapi_app.post("/tools/motion_get_task")
async def http_get_task(request: GetTaskRequest) -> dict[str, Any]:
    """HTTP endpoint for getting a task."""
    return await motion_get_task(task_id=request.task_id)


@fastapi_app.post("/tools/motion_create_task")
async def http_create_task(request: TaskCreateRequest) -> dict[str, Any]:
    """HTTP endpoint for creating a task."""
    return await motion_create_task(
        name=request.name,
        workspace_id=request.workspace_id,
        due_date=request.due_date,
        duration=request.duration,
        project_id=request.project_id,
        description=request.description,
        priority=request.priority,
        assignee_id=request.assignee_id,
        labels=request.labels,
    )


@fastapi_app.post("/tools/motion_update_task")
async def http_update_task(request: TaskUpdateHttpRequest) -> dict[str, Any]:
    """HTTP endpoint for updating a task."""
    return await motion_update_task(
        task_id=request.task_id,
        name=request.name,
        due_date=request.due_date,
        duration=request.duration,
        project_id=request.project_id,
        description=request.description,
        priority=request.priority,
        status=request.status,
        assignee_id=request.assignee_id,
        labels=request.labels,
    )


@fastapi_app.post("/tools/motion_delete_task")
async def http_delete_task(request: DeleteTaskRequest) -> dict[str, Any]:
    """HTTP endpoint for deleting a task."""
    return await motion_delete_task(task_id=request.task_id)


@fastapi_app.post("/tools/motion_move_task")
async def http_move_task(request: MoveTaskRequest) -> dict[str, Any]:
    """HTTP endpoint for moving a task."""
    return await motion_move_task(
        task_id=request.task_id,
        workspace_id=request.workspace_id,
        project_id=request.project_id,
    )


@fastapi_app.post("/tools/motion_unassign_task")
async def http_unassign_task(request: UnassignTaskRequest) -> dict[str, Any]:
    """HTTP endpoint for unassigning a task."""
    return await motion_unassign_task(task_id=request.task_id)


@fastapi_app.post("/tools/motion_list_projects")
async def http_list_projects(request: ListProjectsRequest) -> dict[str, Any]:
    """HTTP endpoint for listing projects."""
    return await motion_list_projects(workspace_id=request.workspace_id)


@fastapi_app.post("/tools/motion_get_project")
async def http_get_project(request: GetProjectRequest) -> dict[str, Any]:
    """HTTP endpoint for getting a project."""
    return await motion_get_project(project_id=request.project_id)


@fastapi_app.post("/tools/motion_create_project")
async def http_create_project(request: ProjectCreateRequest) -> dict[str, Any]:
    """HTTP endpoint for creating a project."""
    return await motion_create_project(
        name=request.name,
        workspace_id=request.workspace_id,
        description=request.description,
        status=request.status,
        labels=request.labels,
    )


@fastapi_app.post("/tools/motion_list_workspaces")
async def http_list_workspaces() -> dict[str, Any]:
    """HTTP endpoint for listing workspaces."""
    return await motion_list_workspaces()


@fastapi_app.post("/tools/motion_list_users")
async def http_list_users(request: ListUsersRequest) -> dict[str, Any]:
    """HTTP endpoint for listing users."""
    return await motion_list_users(workspace_id=request.workspace_id)


@fastapi_app.post("/tools/motion_get_current_user")
async def http_get_current_user() -> dict[str, Any]:
    """HTTP endpoint for getting current user."""
    return await motion_get_current_user()


@fastapi_app.post("/tools/motion_get_rate_limit_status")
async def http_get_rate_limit_status() -> dict[str, Any]:
    """HTTP endpoint for getting rate limit status."""
    return await motion_get_rate_limit_status()


@fastapi_app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    global motion_client
    if motion_client:
        await motion_client.close()
        motion_client = None
    logger.info("Motion client closed")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Run the server."""
    import uvicorn

    # Set log level
    logging.getLogger().setLevel(settings.log_level.upper())

    logger.info(f"Starting Motion MCP Server on {settings.host}:{settings.port}")
    logger.info(f"Rate limit type: {settings.motion_account_type}")

    if not settings.motion_api_key:
        logger.warning("MOTION_API_KEY not set - server will not function properly")

    uvicorn.run(
        fastapi_app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
