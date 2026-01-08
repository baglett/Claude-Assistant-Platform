# =============================================================================
# Motion MCP Server - User Models
# =============================================================================
"""
Pydantic models for Motion User API.

These models represent users and their properties as defined by
the Motion API.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# User Models
# -----------------------------------------------------------------------------
class User(BaseModel):
    """
    Complete user representation from Motion API.

    Attributes:
        id: Unique user identifier.
        name: User's display name.
        email: User's email address.
    """

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="User's display name")
    email: Optional[str] = Field(default=None, description="User's email")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------
class UserListResponse(BaseModel):
    """
    Response model for listing users.

    Attributes:
        users: List of users.
        meta: Pagination metadata.
    """

    users: list[User] = Field(default_factory=list, description="List of users")
    meta: Optional[dict[str, Any]] = Field(
        default=None, description="Pagination metadata"
    )
