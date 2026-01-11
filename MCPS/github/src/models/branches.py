# =============================================================================
# GitHub MCP Server - Branch Models
# =============================================================================
"""
Pydantic models for GitHub Branches and Refs API.

These models handle branch listing, creation, and reference management
from the GitHub REST API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .common import User


class CommitAuthor(BaseModel):
    """
    Git commit author/committer information.

    Attributes:
        name: Author name.
        email: Author email.
        date: Commit date.
    """

    name: Optional[str] = Field(default=None, description="Author name")
    email: Optional[str] = Field(default=None, description="Author email")
    date: Optional[datetime] = Field(default=None, description="Commit date")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class CommitData(BaseModel):
    """
    Git commit data (message, tree, author).

    Attributes:
        message: Commit message.
        author: Commit author.
        committer: Commit committer.
        tree: Tree SHA.
    """

    message: Optional[str] = Field(default=None, description="Commit message")
    author: Optional[CommitAuthor] = Field(default=None, description="Author")
    committer: Optional[CommitAuthor] = Field(default=None, description="Committer")
    tree: Optional[dict] = Field(default=None, description="Tree reference")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class Commit(BaseModel):
    """
    GitHub commit model.

    Represents a commit in a repository.

    Attributes:
        sha: Full commit SHA.
        node_id: GraphQL node ID.
        commit: Git commit data (message, author, etc.).
        author: GitHub user who authored the commit.
        committer: GitHub user who committed.
        html_url: URL to view the commit on GitHub.
        parents: Parent commit references.
    """

    sha: str = Field(..., description="Commit SHA")
    node_id: Optional[str] = Field(default=None, description="GraphQL node ID")
    commit: Optional[CommitData] = Field(default=None, description="Git commit data")
    author: Optional[User] = Field(default=None, description="GitHub author")
    committer: Optional[User] = Field(default=None, description="GitHub committer")
    html_url: Optional[str] = Field(default=None, description="Commit URL")
    parents: list[dict] = Field(default_factory=list, description="Parent commits")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class BranchProtection(BaseModel):
    """
    Branch protection rules.

    Attributes:
        enabled: Whether protection is enabled.
        required_status_checks: Required status check settings.
    """

    enabled: bool = Field(default=False, description="Protection enabled")
    required_status_checks: Optional[dict] = Field(
        default=None, description="Status check requirements"
    )

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class Branch(BaseModel):
    """
    GitHub branch model.

    Represents a branch in a repository.

    Attributes:
        name: Branch name.
        commit: Latest commit on the branch.
        protected: Whether the branch is protected.
        protection: Branch protection rules (if protected).
        protection_url: URL to protection settings.
    """

    name: str = Field(..., description="Branch name")
    commit: Optional[Commit] = Field(default=None, description="Latest commit")
    protected: bool = Field(default=False, description="Is protected")
    protection: Optional[BranchProtection] = Field(
        default=None, description="Protection rules"
    )
    protection_url: Optional[str] = Field(
        default=None, description="Protection settings URL"
    )

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class RefObject(BaseModel):
    """
    Git reference object (what a ref points to).

    Attributes:
        sha: Object SHA.
        type: Object type (commit, tag, tree, blob).
        url: API URL for the object.
    """

    sha: str = Field(..., description="Object SHA")
    type: str = Field(..., description="Object type")
    url: Optional[str] = Field(default=None, description="Object API URL")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class Ref(BaseModel):
    """
    GitHub reference model.

    Represents a Git reference (branch, tag, etc.).

    Attributes:
        ref: Full reference name (e.g., refs/heads/main).
        node_id: GraphQL node ID.
        url: API URL for the reference.
        object: Object the reference points to.
    """

    ref: str = Field(..., description="Full reference name")
    node_id: Optional[str] = Field(default=None, description="GraphQL node ID")
    url: Optional[str] = Field(default=None, description="Reference API URL")
    object: RefObject = Field(..., description="Referenced object")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class BranchListResponse(BaseModel):
    """
    Response model for listing branches.

    Attributes:
        branches: List of branches.
        count: Number of branches returned.
    """

    branches: list[Branch] = Field(default_factory=list, description="List of branches")
    count: int = Field(default=0, description="Number of branches")
