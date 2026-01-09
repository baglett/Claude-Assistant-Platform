# =============================================================================
# Motion MCP Server - Models Package
# =============================================================================
"""
Pydantic models for Motion API data structures.

This package contains all the data models used for request/response
serialization when interacting with the Motion API.
"""

from src.models.common import (
    MotionApiError,
    MotionResponse,
    PaginatedResponse,
)
from src.models.projects import (
    Project,
    ProjectCreate,
    ProjectListResponse,
)
from src.models.tasks import (
    Assignee,
    DeadlineType,
    Priority,
    SchedulingChunk,
    Task,
    TaskCreate,
    TaskListResponse,
    TaskStatus,
    TaskUpdate,
)
from src.models.users import (
    User,
    UserListResponse,
)
from src.models.workspaces import (
    Workspace,
    WorkspaceListResponse,
)

__all__ = [
    # Common
    "MotionApiError",
    "MotionResponse",
    "PaginatedResponse",
    # Tasks
    "Assignee",
    "DeadlineType",
    "Priority",
    "SchedulingChunk",
    "Task",
    "TaskCreate",
    "TaskListResponse",
    "TaskStatus",
    "TaskUpdate",
    # Projects
    "Project",
    "ProjectCreate",
    "ProjectListResponse",
    # Workspaces
    "Workspace",
    "WorkspaceListResponse",
    # Users
    "User",
    "UserListResponse",
]
