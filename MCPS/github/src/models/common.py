# =============================================================================
# GitHub MCP Server - Common Models
# =============================================================================
"""
Common Pydantic models shared across GitHub API resources.

These models represent fundamental GitHub entities like users, labels,
milestones, and repositories that are referenced by other resources.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """
    GitHub user model.

    Represents a GitHub user account, which can be the author of issues,
    pull requests, comments, or an assignee.

    Attributes:
        login: The user's GitHub username.
        id: Unique identifier for the user.
        avatar_url: URL to the user's avatar image.
        html_url: URL to the user's GitHub profile page.
        type: Account type (User, Organization, Bot).
    """

    login: str = Field(..., description="GitHub username")
    id: int = Field(..., description="User ID")
    avatar_url: Optional[str] = Field(default=None, description="Avatar URL")
    html_url: Optional[str] = Field(default=None, description="Profile URL")
    type: Optional[str] = Field(default="User", description="Account type")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class Label(BaseModel):
    """
    GitHub label model.

    Labels are used to categorize issues and pull requests.

    Attributes:
        id: Unique identifier for the label.
        name: Display name of the label.
        color: Hex color code (without #).
        description: Optional description of the label's purpose.
    """

    id: int = Field(..., description="Label ID")
    name: str = Field(..., description="Label name")
    color: Optional[str] = Field(default=None, description="Hex color code")
    description: Optional[str] = Field(default=None, description="Label description")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class Milestone(BaseModel):
    """
    GitHub milestone model.

    Milestones group issues and pull requests into larger goals.

    Attributes:
        id: Unique identifier for the milestone.
        number: Milestone number within the repository.
        title: Display title of the milestone.
        description: Optional description of the milestone.
        state: Current state (open, closed).
        due_on: Optional due date for the milestone.
        open_issues: Count of open issues in the milestone.
        closed_issues: Count of closed issues in the milestone.
    """

    id: int = Field(..., description="Milestone ID")
    number: int = Field(..., description="Milestone number")
    title: str = Field(..., description="Milestone title")
    description: Optional[str] = Field(default=None, description="Description")
    state: str = Field(default="open", description="State (open/closed)")
    due_on: Optional[datetime] = Field(default=None, description="Due date")
    open_issues: int = Field(default=0, description="Open issue count")
    closed_issues: int = Field(default=0, description="Closed issue count")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class Repository(BaseModel):
    """
    GitHub repository model.

    Represents a GitHub repository with its metadata.

    Attributes:
        id: Unique identifier for the repository.
        name: Repository name (without owner).
        full_name: Full repository name (owner/repo).
        owner: Repository owner (User model).
        private: Whether the repository is private.
        html_url: URL to the repository page.
        description: Optional repository description.
        fork: Whether this is a fork of another repository.
        default_branch: Name of the default branch.
        language: Primary programming language.
        stargazers_count: Number of stars.
        forks_count: Number of forks.
        open_issues_count: Number of open issues.
        created_at: Repository creation timestamp.
        updated_at: Last update timestamp.
        pushed_at: Last push timestamp.
    """

    id: int = Field(..., description="Repository ID")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full name (owner/repo)")
    owner: User = Field(..., description="Repository owner")
    private: bool = Field(default=False, description="Is private")
    html_url: Optional[str] = Field(default=None, description="Repository URL")
    description: Optional[str] = Field(default=None, description="Description")
    fork: bool = Field(default=False, description="Is a fork")
    default_branch: str = Field(default="main", description="Default branch name")
    language: Optional[str] = Field(default=None, description="Primary language")
    stargazers_count: int = Field(default=0, description="Star count")
    forks_count: int = Field(default=0, description="Fork count")
    open_issues_count: int = Field(default=0, description="Open issues count")
    created_at: Optional[datetime] = Field(default=None, description="Created at")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at")
    pushed_at: Optional[datetime] = Field(default=None, description="Last push at")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class RateLimitResource(BaseModel):
    """
    Rate limit information for a specific resource.

    Attributes:
        limit: Maximum requests allowed.
        remaining: Requests remaining in current window.
        reset: Unix timestamp when the limit resets.
        used: Requests used in current window.
    """

    limit: int = Field(..., description="Maximum requests")
    remaining: int = Field(..., description="Remaining requests")
    reset: int = Field(..., description="Reset timestamp (Unix)")
    used: int = Field(..., description="Used requests")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class RateLimitResponse(BaseModel):
    """
    GitHub API rate limit response.

    Attributes:
        resources: Rate limits by resource type.
        rate: Overall rate limit (deprecated but still returned).
    """

    resources: dict[str, RateLimitResource] = Field(
        ..., description="Rate limits by resource"
    )
    rate: Optional[RateLimitResource] = Field(
        default=None, description="Overall rate limit"
    )

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class FileContent(BaseModel):
    """
    GitHub file content model.

    Represents a file's content retrieved from a repository.

    Attributes:
        name: File name.
        path: Full path within repository.
        sha: Git SHA of the file.
        size: File size in bytes.
        type: Content type (file, dir, symlink, submodule).
        content: Base64 encoded file content.
        encoding: Content encoding (base64).
        html_url: URL to view file on GitHub.
        download_url: Direct download URL.
    """

    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path")
    sha: str = Field(..., description="Git SHA")
    size: int = Field(..., description="File size in bytes")
    type: str = Field(..., description="Content type")
    content: Optional[str] = Field(default=None, description="Base64 content")
    encoding: Optional[str] = Field(default=None, description="Content encoding")
    html_url: Optional[str] = Field(default=None, description="View URL")
    download_url: Optional[str] = Field(default=None, description="Download URL")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"
