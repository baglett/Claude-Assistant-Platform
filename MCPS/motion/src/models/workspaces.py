# =============================================================================
# Motion MCP Server - Workspace Models
# =============================================================================
"""
Pydantic models for Motion Workspace API.

These models represent workspaces and their properties as defined by
the Motion API.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Workspace Models
# -----------------------------------------------------------------------------
class Workspace(BaseModel):
    """
    Complete workspace representation from Motion API.

    Attributes:
        id: Unique workspace identifier.
        name: Workspace name.
        teamId: Associated team ID (for team workspaces).
        type: Workspace type (e.g., "INDIVIDUAL", "TEAM").
    """

    id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")
    teamId: Optional[str] = Field(default=None, description="Team ID")
    type: Optional[str] = Field(default=None, description="Workspace type")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------
class WorkspaceListResponse(BaseModel):
    """
    Response model for listing workspaces.

    Attributes:
        workspaces: List of workspaces.
        meta: Pagination metadata.
    """

    workspaces: list[Workspace] = Field(
        default_factory=list, description="List of workspaces"
    )
    meta: Optional[dict[str, Any]] = Field(
        default=None, description="Pagination metadata"
    )
