# =============================================================================
# GitHub MCP Server - Models Package
# =============================================================================
"""
Pydantic models for GitHub API data structures.

This package exports all models used by the GitHub MCP server for
request/response validation and serialization.
"""

from .branches import Branch, BranchProtection, Commit, Ref
from .common import FileContent, Label, Milestone, RateLimitResponse, Repository, User
from .issues import (
    Issue,
    IssueComment,
    IssueCommentCreate,
    IssueCreate,
    IssueListResponse,
    IssueUpdate,
)
from .pull_requests import (
    PullRequest,
    PullRequestCreate,
    PullRequestFile,
    PullRequestListResponse,
    PullRequestMerge,
    PullRequestReview,
    PullRequestReviewCreate,
    PullRequestUpdate,
)

__all__ = [
    # Common
    "User",
    "Label",
    "Milestone",
    "Repository",
    "FileContent",
    "RateLimitResponse",
    # Issues
    "Issue",
    "IssueCreate",
    "IssueUpdate",
    "IssueComment",
    "IssueCommentCreate",
    "IssueListResponse",
    # Pull Requests
    "PullRequest",
    "PullRequestCreate",
    "PullRequestUpdate",
    "PullRequestMerge",
    "PullRequestFile",
    "PullRequestReview",
    "PullRequestReviewCreate",
    "PullRequestListResponse",
    # Branches
    "Branch",
    "BranchProtection",
    "Commit",
    "Ref",
]
