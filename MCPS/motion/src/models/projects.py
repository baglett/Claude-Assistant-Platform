# =============================================================================
# Motion MCP Server - Project Models
# =============================================================================
"""
Pydantic models for Motion Project API.

These models represent projects and their properties as defined by
the Motion API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Nested Models
# -----------------------------------------------------------------------------
class WorkspaceRef(BaseModel):
    """
    Reference to a workspace.

    Attributes:
        id: Workspace ID.
        name: Workspace name.
    """

    id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")


class ProjectStatus(BaseModel):
    """
    Project status information.

    Attributes:
        name: Status name.
        isDefaultStatus: Whether this is the default status.
        isResolvedStatus: Whether this status marks project as resolved.
    """

    name: str = Field(..., description="Status name")
    isDefaultStatus: bool = Field(default=False, description="Default status flag")
    isResolvedStatus: bool = Field(default=False, description="Resolved status flag")


# -----------------------------------------------------------------------------
# Project Models
# -----------------------------------------------------------------------------
class Project(BaseModel):
    """
    Complete project representation from Motion API.

    Attributes:
        id: Unique project identifier.
        name: Project name.
        description: Project description.
        status: Project status information.
        workspace: Workspace containing the project.
        createdTime: When the project was created.
        updatedTime: When the project was last updated.
        labels: Project labels.
    """

    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    status: Optional[ProjectStatus] = Field(default=None, description="Project status")
    workspace: WorkspaceRef = Field(..., description="Workspace reference")
    createdTime: Optional[datetime] = Field(default=None, description="Creation time")
    updatedTime: Optional[datetime] = Field(
        default=None, description="Last update time"
    )
    labels: list[str] = Field(default_factory=list, description="Project labels")


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------
class ProjectCreate(BaseModel):
    """
    Request model for creating a new project.

    Attributes:
        name: Project name (required).
        workspaceId: Workspace ID (required).
        description: Project description.
        status: Initial status name.
        labels: Label names to add.
    """

    name: str = Field(..., description="Project name", min_length=1)
    workspaceId: str = Field(..., description="Workspace ID")
    description: Optional[str] = Field(default=None, description="Description")
    status: Optional[str] = Field(default=None, description="Status name")
    labels: Optional[list[str]] = Field(default=None, description="Label names")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------
class ProjectListResponse(BaseModel):
    """
    Response model for listing projects.

    Attributes:
        projects: List of projects.
        meta: Pagination metadata.
    """

    projects: list[Project] = Field(
        default_factory=list, description="List of projects"
    )
    meta: Optional[dict[str, Any]] = Field(
        default=None, description="Pagination metadata"
    )
