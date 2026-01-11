# =============================================================================
# GitHub MCP Server - Pull Request Models
# =============================================================================
"""
Pydantic models for GitHub Pull Requests API.

These models handle PR creation, updates, reviews, merges, and responses
from the GitHub REST API.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .common import Label, Milestone, User


class MergeMethod(str, Enum):
    """
    Available merge methods for pull requests.

    Attributes:
        MERGE: Create a merge commit.
        SQUASH: Squash all commits into one.
        REBASE: Rebase commits onto base branch.
    """

    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class ReviewEvent(str, Enum):
    """
    Review event types for pull request reviews.

    Attributes:
        APPROVE: Approve the pull request.
        REQUEST_CHANGES: Request changes before merging.
        COMMENT: Leave a comment without approval.
    """

    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


class PullRequestHead(BaseModel):
    """
    Pull request head (source) branch information.

    Attributes:
        ref: Branch name.
        sha: Commit SHA at the head.
        label: Full label (user:branch).
        user: Owner of the head repository.
    """

    ref: str = Field(..., description="Branch name")
    sha: str = Field(..., description="Commit SHA")
    label: Optional[str] = Field(default=None, description="Full label (user:branch)")
    user: Optional[User] = Field(default=None, description="Head repo owner")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class PullRequestBase(BaseModel):
    """
    Pull request base (target) branch information.

    Attributes:
        ref: Branch name.
        sha: Commit SHA at the base.
        label: Full label (user:branch).
        user: Owner of the base repository.
    """

    ref: str = Field(..., description="Branch name")
    sha: str = Field(..., description="Commit SHA")
    label: Optional[str] = Field(default=None, description="Full label (user:branch)")
    user: Optional[User] = Field(default=None, description="Base repo owner")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class PullRequest(BaseModel):
    """
    GitHub pull request model.

    Represents a pull request with all its metadata.

    Attributes:
        id: Unique identifier for the pull request.
        number: PR number within the repository.
        title: Pull request title.
        body: Pull request body/description (Markdown).
        state: Current state (open, closed).
        user: User who created the pull request.
        labels: List of labels attached to the PR.
        assignees: List of users assigned to the PR.
        milestone: Optional milestone the PR belongs to.
        head: Source branch information.
        base: Target branch information.
        draft: Whether this is a draft PR.
        merged: Whether the PR has been merged.
        mergeable: Whether the PR can be merged (null if unknown).
        mergeable_state: Mergeable state details.
        merged_by: User who merged the PR.
        merged_at: When the PR was merged.
        merge_commit_sha: SHA of the merge commit.
        comments: Number of comments.
        review_comments: Number of review comments.
        commits: Number of commits in the PR.
        additions: Lines added.
        deletions: Lines deleted.
        changed_files: Number of files changed.
        html_url: URL to view the PR on GitHub.
        created_at: PR creation timestamp.
        updated_at: Last update timestamp.
        closed_at: When the PR was closed.
    """

    id: int = Field(..., description="Pull request ID")
    number: int = Field(..., description="PR number")
    title: str = Field(..., description="PR title")
    body: Optional[str] = Field(default=None, description="PR body (Markdown)")
    state: str = Field(default="open", description="State (open/closed)")
    user: Optional[User] = Field(default=None, description="PR creator")
    labels: list[Label] = Field(default_factory=list, description="Attached labels")
    assignees: list[User] = Field(default_factory=list, description="Assigned users")
    milestone: Optional[Milestone] = Field(default=None, description="Milestone")
    head: Optional[PullRequestHead] = Field(default=None, description="Source branch")
    base: Optional[PullRequestBase] = Field(default=None, description="Target branch")
    draft: bool = Field(default=False, description="Is draft PR")
    merged: bool = Field(default=False, description="Is merged")
    mergeable: Optional[bool] = Field(default=None, description="Can be merged")
    mergeable_state: Optional[str] = Field(
        default=None, description="Mergeable state details"
    )
    merged_by: Optional[User] = Field(default=None, description="Merged by user")
    merged_at: Optional[datetime] = Field(default=None, description="Merged at")
    merge_commit_sha: Optional[str] = Field(
        default=None, description="Merge commit SHA"
    )
    comments: int = Field(default=0, description="Comment count")
    review_comments: int = Field(default=0, description="Review comment count")
    commits: int = Field(default=0, description="Commit count")
    additions: int = Field(default=0, description="Lines added")
    deletions: int = Field(default=0, description="Lines deleted")
    changed_files: int = Field(default=0, description="Files changed")
    html_url: Optional[str] = Field(default=None, description="PR URL")
    created_at: Optional[datetime] = Field(default=None, description="Created at")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at")
    closed_at: Optional[datetime] = Field(default=None, description="Closed at")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class PullRequestCreate(BaseModel):
    """
    Model for creating a new pull request.

    Attributes:
        title: PR title (required).
        head: Name of the branch with changes (required).
        base: Name of the branch to merge into (required).
        body: PR body/description in Markdown.
        draft: Create as draft PR.
        maintainer_can_modify: Allow maintainers to modify.
    """

    title: str = Field(..., description="PR title", min_length=1)
    head: str = Field(..., description="Source branch name")
    base: str = Field(..., description="Target branch name")
    body: Optional[str] = Field(default=None, description="PR body (Markdown)")
    draft: bool = Field(default=False, description="Create as draft")
    maintainer_can_modify: bool = Field(
        default=True, description="Allow maintainer edits"
    )


class PullRequestUpdate(BaseModel):
    """
    Model for updating an existing pull request.

    All fields are optional - only provided fields will be updated.

    Attributes:
        title: New PR title.
        body: New PR body.
        state: New state (open, closed).
        base: New target branch.
        maintainer_can_modify: Allow maintainer edits.
    """

    title: Optional[str] = Field(default=None, description="New title")
    body: Optional[str] = Field(default=None, description="New body")
    state: Optional[str] = Field(default=None, description="New state (open/closed)")
    base: Optional[str] = Field(default=None, description="New target branch")
    maintainer_can_modify: Optional[bool] = Field(
        default=None, description="Allow maintainer edits"
    )


class PullRequestMerge(BaseModel):
    """
    Model for merging a pull request.

    Attributes:
        commit_title: Title for the merge commit.
        commit_message: Message for the merge commit.
        merge_method: Method to use (merge, squash, rebase).
        sha: Expected SHA of the PR head (for safety).
    """

    commit_title: Optional[str] = Field(default=None, description="Merge commit title")
    commit_message: Optional[str] = Field(
        default=None, description="Merge commit message"
    )
    merge_method: MergeMethod = Field(
        default=MergeMethod.MERGE, description="Merge method"
    )
    sha: Optional[str] = Field(default=None, description="Expected head SHA")


class PullRequestFile(BaseModel):
    """
    File changed in a pull request.

    Attributes:
        filename: Path to the file.
        status: Change status (added, removed, modified, renamed, etc.).
        additions: Lines added.
        deletions: Lines deleted.
        changes: Total line changes.
        patch: Unified diff patch.
        sha: Blob SHA of the file.
        previous_filename: Previous filename if renamed.
    """

    filename: str = Field(..., description="File path")
    status: str = Field(..., description="Change status")
    additions: int = Field(default=0, description="Lines added")
    deletions: int = Field(default=0, description="Lines deleted")
    changes: int = Field(default=0, description="Total changes")
    patch: Optional[str] = Field(default=None, description="Diff patch")
    sha: Optional[str] = Field(default=None, description="Blob SHA")
    previous_filename: Optional[str] = Field(
        default=None, description="Previous filename"
    )

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class PullRequestReviewComment(BaseModel):
    """
    Inline comment for a pull request review.

    Attributes:
        path: File path to comment on.
        position: Deprecated - use line instead.
        line: Line number in the diff to comment on.
        side: Side of the diff (LEFT, RIGHT).
        body: Comment body.
    """

    path: str = Field(..., description="File path")
    line: Optional[int] = Field(default=None, description="Line number")
    side: Optional[str] = Field(default=None, description="Diff side (LEFT/RIGHT)")
    body: str = Field(..., description="Comment body")


class PullRequestReview(BaseModel):
    """
    Pull request review model.

    Attributes:
        id: Review ID.
        user: Reviewer.
        body: Review body.
        state: Review state (APPROVED, CHANGES_REQUESTED, COMMENTED, etc.).
        html_url: URL to the review.
        submitted_at: When the review was submitted.
    """

    id: int = Field(..., description="Review ID")
    user: Optional[User] = Field(default=None, description="Reviewer")
    body: Optional[str] = Field(default=None, description="Review body")
    state: str = Field(..., description="Review state")
    html_url: Optional[str] = Field(default=None, description="Review URL")
    submitted_at: Optional[datetime] = Field(default=None, description="Submitted at")

    class Config:
        """Pydantic configuration."""

        extra = "ignore"


class PullRequestReviewCreate(BaseModel):
    """
    Model for creating a pull request review.

    Attributes:
        body: Review body/summary.
        event: Review action (APPROVE, REQUEST_CHANGES, COMMENT).
        comments: Inline comments to add with the review.
    """

    body: Optional[str] = Field(default=None, description="Review body")
    event: ReviewEvent = Field(..., description="Review action")
    comments: Optional[list[PullRequestReviewComment]] = Field(
        default=None, description="Inline comments"
    )


class PullRequestListResponse(BaseModel):
    """
    Response model for listing pull requests.

    Attributes:
        pull_requests: List of pull requests.
        count: Number of pull requests returned.
    """

    pull_requests: list[PullRequest] = Field(
        default_factory=list, description="List of PRs"
    )
    count: int = Field(default=0, description="Number of PRs")
