# =============================================================================
# GitHub MCP Server - Issue Models
# =============================================================================
"""
Pydantic models for GitHub Issues API.

These models handle issue creation, updates, comments, and responses
from the GitHub REST API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .common import Label, Milestone, User


class Issue(BaseModel):
    """
    GitHub issue model.

    Represents a GitHub issue with all its metadata.

    Attributes:
        id: Unique identifier for the issue.
        number: Issue number within the repository.
        title: Issue title.
        body: Issue body/description (Markdown).
        state: Current state (open, closed).
        state_reason: Reason for state (completed, not_planned, reopened).
        user: User who created the issue.
        labels: List of labels attached to the issue.
        assignees: List of users assigned to the issue.
        milestone: Optional milestone the issue belongs to.
        comments: Number of comments on the issue.
        html_url: URL to view the issue on GitHub.
        created_at: Issue creation timestamp.
        updated_at: Last update timestamp.
        closed_at: When the issue was closed (if applicable).
        closed_by: User who closed the issue (if applicable).
    """

    id: int = Field(..., description="Issue ID")
    number: int = Field(..., description="Issue number")
    title: str = Field(..., description="Issue title")
    body: Optional[str] = Field(default=None, description="Issue body (Markdown)")
    state: str = Field(default="open", description="State (open/closed)")
    state_reason: Optional[str] = Field(
        default=None, description="State reason (completed, not_planned, reopened)"
    )
    user: Optional[User] = Field(default=None, description="Issue creator")
    labels: list[Label] = Field(default_factory=list, description="Attached labels")
    assignees: list[User] = Field(default_factory=list, description="Assigned users")
    milestone: Optional[Milestone] = Field(default=None, description="Milestone")
    comments: int = Field(default=0, description="Comment count")
    html_url: Optional[str] = Field(default=None, description="Issue URL")
    created_at: Optional[datetime] = Field(default=None, description="Created at")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at")
    closed_at: Optional[datetime] = Field(default=None, description="Closed at")
    closed_by: Optional[User] = Field(default=None, description="Closed by user")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class IssueCreate(BaseModel):
    """
    Model for creating a new GitHub issue.

    Attributes:
        title: Issue title (required).
        body: Issue body/description in Markdown.
        labels: List of label names to attach.
        assignees: List of usernames to assign.
        milestone: Milestone number to associate.
    """

    title: str = Field(..., description="Issue title", min_length=1)
    body: Optional[str] = Field(default=None, description="Issue body (Markdown)")
    labels: Optional[list[str]] = Field(default=None, description="Label names")
    assignees: Optional[list[str]] = Field(default=None, description="Assignee logins")
    milestone: Optional[int] = Field(default=None, description="Milestone number")


class IssueUpdate(BaseModel):
    """
    Model for updating an existing GitHub issue.

    All fields are optional - only provided fields will be updated.

    Attributes:
        title: New issue title.
        body: New issue body.
        state: New state (open, closed).
        state_reason: Reason for closing (completed, not_planned, reopened).
        labels: New list of label names (replaces existing).
        assignees: New list of assignee usernames (replaces existing).
        milestone: New milestone number (null to remove).
    """

    title: Optional[str] = Field(default=None, description="New title")
    body: Optional[str] = Field(default=None, description="New body")
    state: Optional[str] = Field(default=None, description="New state (open/closed)")
    state_reason: Optional[str] = Field(
        default=None, description="State reason (completed, not_planned, reopened)"
    )
    labels: Optional[list[str]] = Field(default=None, description="New label names")
    assignees: Optional[list[str]] = Field(
        default=None, description="New assignee logins"
    )
    milestone: Optional[int] = Field(default=None, description="New milestone number")


class IssueComment(BaseModel):
    """
    GitHub issue comment model.

    Represents a comment on an issue.

    Attributes:
        id: Unique identifier for the comment.
        body: Comment body in Markdown.
        user: User who created the comment.
        html_url: URL to view the comment on GitHub.
        created_at: Comment creation timestamp.
        updated_at: Last update timestamp.
    """

    id: int = Field(..., description="Comment ID")
    body: str = Field(..., description="Comment body (Markdown)")
    user: Optional[User] = Field(default=None, description="Comment author")
    html_url: Optional[str] = Field(default=None, description="Comment URL")
    created_at: Optional[datetime] = Field(default=None, description="Created at")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class IssueCommentCreate(BaseModel):
    """
    Model for creating a new comment on an issue.

    Attributes:
        body: Comment body in Markdown (required).
    """

    body: str = Field(..., description="Comment body (Markdown)", min_length=1)


class IssueListResponse(BaseModel):
    """
    Response model for listing issues.

    Attributes:
        issues: List of issues.
        count: Number of issues returned.
    """

    issues: list[Issue] = Field(default_factory=list, description="List of issues")
    count: int = Field(default=0, description="Number of issues")
