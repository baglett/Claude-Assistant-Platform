# =============================================================================
# GitHub MCP Server
# =============================================================================
"""
FastMCP server providing GitHub API tools.

This server exposes MCP tools for:
- Issue management (list, get, create, update, comment)
- Pull request management (list, get, create, update, merge, review)
- Branch management (list, get, create, delete)
- Repository information and file access
- Rate limit monitoring

The server runs as a standalone HTTP service and can be called by the
orchestrator or other agents to interact with GitHub.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .client import (
    GitHubApiError,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubValidationError,
)
from .models import (
    IssueCreate,
    IssueUpdate,
    PullRequestCreate,
    PullRequestMerge,
    PullRequestReviewCreate,
    PullRequestUpdate,
)
from .models.pull_requests import MergeMethod, ReviewEvent

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
        github_token: GitHub personal access token (required).
        github_api_base_url: GitHub API base URL.
        github_request_timeout: Request timeout in seconds.
        github_max_retries: Max retries for rate limit errors.
        host: Server host address.
        port: Server port number.
        log_level: Logging level.
    """

    github_token: str = Field(
        default="",
        description="GitHub personal access token",
    )
    github_api_base_url: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL",
    )
    github_request_timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds",
    )
    github_max_retries: int = Field(
        default=3,
        description="Max retries for rate limit errors",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Server host address",
        alias="github_mcp_host",
    )
    port: int = Field(
        default=8083,
        description="Server port number",
        alias="github_mcp_port",
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
        populate_by_name=True,
    )


settings = Settings()


# -----------------------------------------------------------------------------
# Initialize GitHub Client and Context
# -----------------------------------------------------------------------------
github_client: Optional[GitHubClient] = None

# Cached context for the authenticated user and their repositories
_cached_user: Optional[dict[str, Any]] = None
_cached_repos: Optional[list[dict[str, Any]]] = None


def get_github_client() -> GitHubClient:
    """
    Get or create the GitHub client.

    Returns:
        Initialized GitHubClient instance.

    Raises:
        HTTPException: If token is not configured.
    """
    global github_client

    if not settings.github_token:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_TOKEN not configured",
        )

    if github_client is None:
        github_client = GitHubClient(
            token=settings.github_token,
            base_url=settings.github_api_base_url,
            timeout=settings.github_request_timeout,
            max_retries=settings.github_max_retries,
        )

    return github_client


# -----------------------------------------------------------------------------
# Error Handling
# -----------------------------------------------------------------------------
def handle_api_error(e: Exception) -> dict[str, Any]:
    """
    Convert GitHub API exceptions to a standardized error response.

    Args:
        e: The exception to handle.

    Returns:
        Dictionary with error details.
    """
    if isinstance(e, GitHubRateLimitError):
        return {
            "success": False,
            "error": "rate_limit_exceeded",
            "message": e.message,
            "reset_at": e.reset_at,
            "retry_after": e.retry_after,
        }
    elif isinstance(e, GitHubAuthenticationError):
        return {
            "success": False,
            "error": "authentication_error",
            "message": "Invalid GitHub token or unauthorized access",
        }
    elif isinstance(e, GitHubForbiddenError):
        return {
            "success": False,
            "error": "forbidden",
            "message": e.message,
        }
    elif isinstance(e, GitHubNotFoundError):
        return {
            "success": False,
            "error": "not_found",
            "message": e.message,
        }
    elif isinstance(e, GitHubValidationError):
        return {
            "success": False,
            "error": "validation_error",
            "message": e.message,
            "details": e.response_data,
        }
    elif isinstance(e, GitHubApiError):
        return {
            "success": False,
            "error": "api_error",
            "message": e.message,
            "status_code": e.status_code,
        }
    else:
        logger.error(f"Unexpected error: {e}")
        return {
            "success": False,
            "error": "unexpected_error",
            "message": str(e),
        }


# -----------------------------------------------------------------------------
# Repository Resolution Helpers
# -----------------------------------------------------------------------------
async def get_cached_user() -> dict[str, Any]:
    """
    Get the authenticated user, using cache if available.

    Returns:
        Dictionary with user information including 'login' (username).
    """
    global _cached_user

    if _cached_user is None:
        client = get_github_client()
        user = await client.get_authenticated_user()
        _cached_user = user.model_dump()
        logger.info(f"Cached authenticated user: {_cached_user.get('login')}")

    return _cached_user


async def get_cached_repos(refresh: bool = False) -> list[dict[str, Any]]:
    """
    Get all repositories accessible to the authenticated user.

    Args:
        refresh: Force refresh the cache.

    Returns:
        List of repository dictionaries.
    """
    global _cached_repos

    if _cached_repos is None or refresh:
        client = get_github_client()
        # Get all repos the user has access to (owned + member + collaborator)
        repos = await client.list_repositories(type="all", per_page=100)
        _cached_repos = [r.model_dump() for r in repos]
        logger.info(f"Cached {len(_cached_repos)} accessible repositories")

    return _cached_repos


async def resolve_repository(
    repo_name: str,
    owner: Optional[str] = None,
) -> tuple[str, str]:
    """
    Resolve a repository name to owner/repo pair.

    If owner is provided, uses it directly. Otherwise, searches the user's
    accessible repositories for a match.

    Args:
        repo_name: Repository name (can be just name or owner/name format).
        owner: Optional explicit owner. If not provided, will attempt to resolve.

    Returns:
        Tuple of (owner, repo_name).

    Raises:
        ValueError: If repository cannot be resolved.
    """
    # If repo_name contains a slash, it's already in owner/repo format
    if "/" in repo_name:
        parts = repo_name.split("/", 1)
        return (parts[0], parts[1])

    # If owner is explicitly provided, use it
    if owner:
        return (owner, repo_name)

    # Try to find the repo in user's accessible repositories
    repos = await get_cached_repos()

    # Case-insensitive search
    repo_name_lower = repo_name.lower()
    matches = []

    for repo in repos:
        if repo.get("name", "").lower() == repo_name_lower:
            matches.append(repo)

    if len(matches) == 1:
        # Exactly one match - use it
        match = matches[0]
        owner_login = match.get("owner", {}).get("login", "")
        logger.info(f"Resolved '{repo_name}' to '{owner_login}/{repo_name}'")
        return (owner_login, match.get("name", repo_name))

    elif len(matches) > 1:
        # Multiple matches - need clarification
        match_list = [
            f"{m.get('owner', {}).get('login')}/{m.get('name')}" for m in matches
        ]
        raise ValueError(
            f"Multiple repositories found with name '{repo_name}': {', '.join(match_list)}. "
            "Please specify the owner explicitly."
        )

    else:
        # No matches found - try authenticated user as owner
        user = await get_cached_user()
        username = user.get("login", "")

        if username:
            logger.info(
                f"No cached repo found for '{repo_name}', "
                f"defaulting to authenticated user: {username}"
            )
            return (username, repo_name)

        raise ValueError(
            f"Could not resolve repository '{repo_name}'. "
            "Please specify the owner explicitly (e.g., 'owner/repo' or provide owner parameter)."
        )


def clear_context_cache() -> None:
    """Clear the cached user and repository context."""
    global _cached_user, _cached_repos
    _cached_user = None
    _cached_repos = None
    logger.info("Context cache cleared")


# -----------------------------------------------------------------------------
# FastMCP Server
# -----------------------------------------------------------------------------
mcp = FastMCP("github-mcp")


# =============================================================================
# Issue Tools
# =============================================================================


@mcp.tool()
async def github_list_issues(
    repo: str,
    owner: Optional[str] = None,
    state: str = "open",
    labels: Optional[str] = None,
    assignee: Optional[str] = None,
    per_page: int = 30,
) -> dict[str, Any]:
    """
    List issues in a GitHub repository.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        owner: Repository owner (optional - will be auto-resolved if not provided).
        state: Issue state filter (open, closed, all). Default: open.
        labels: Comma-separated list of label names to filter by.
        assignee: Filter by assignee username.
        per_page: Number of results per page (max 100). Default: 30.

    Returns:
        Dictionary with list of issues and count.
    """
    try:
        # Resolve owner if not provided
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)

        client = get_github_client()
        label_list = labels.split(",") if labels else None
        issues = await client.list_issues(
            owner=resolved_owner,
            repo=resolved_repo,
            state=state,
            labels=label_list,
            assignee=assignee,
            per_page=per_page,
        )
        return {
            "success": True,
            "issues": [i.model_dump() for i in issues],
            "count": len(issues),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {
            "success": False,
            "error": "resolution_error",
            "message": str(e),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_get_issue(
    repo: str,
    issue_number: int,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get a specific issue by number.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        issue_number: Issue number.
        owner: Repository owner (optional - will be auto-resolved if not provided).

    Returns:
        Dictionary with issue details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        issue = await client.get_issue(resolved_owner, resolved_repo, issue_number)
        return {
            "success": True,
            "issue": issue.model_dump(),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_create_issue(
    repo: str,
    title: str,
    owner: Optional[str] = None,
    body: Optional[str] = None,
    labels: Optional[str] = None,
    assignees: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a new issue in a repository.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        title: Issue title (required).
        owner: Repository owner (optional - will be auto-resolved if not provided).
        body: Issue body/description in Markdown.
        labels: Comma-separated list of label names to add.
        assignees: Comma-separated list of usernames to assign.

    Returns:
        Dictionary with created issue details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        issue_data = IssueCreate(
            title=title,
            body=body,
            labels=labels.split(",") if labels else None,
            assignees=assignees.split(",") if assignees else None,
        )
        issue = await client.create_issue(resolved_owner, resolved_repo, issue_data)
        return {
            "success": True,
            "issue": issue.model_dump(),
            "message": f"Issue #{issue.number} created successfully",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_update_issue(
    repo: str,
    issue_number: int,
    owner: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[str] = None,
    labels: Optional[str] = None,
    assignees: Optional[str] = None,
) -> dict[str, Any]:
    """
    Update an existing issue.

    Only provided fields will be updated.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        issue_number: Issue number to update.
        owner: Repository owner (optional - will be auto-resolved if not provided).
        title: New issue title.
        body: New issue body.
        state: New state (open, closed).
        labels: Comma-separated label names (replaces existing).
        assignees: Comma-separated usernames (replaces existing).

    Returns:
        Dictionary with updated issue details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        update_data = IssueUpdate(
            title=title,
            body=body,
            state=state,
            labels=labels.split(",") if labels else None,
            assignees=assignees.split(",") if assignees else None,
        )
        issue = await client.update_issue(
            resolved_owner, resolved_repo, issue_number, update_data
        )
        return {
            "success": True,
            "issue": issue.model_dump(),
            "message": f"Issue #{issue.number} updated successfully",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_add_issue_comment(
    repo: str,
    issue_number: int,
    body: str,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Add a comment to an issue.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        issue_number: Issue number.
        body: Comment body in Markdown.
        owner: Repository owner (optional - will be auto-resolved if not provided).

    Returns:
        Dictionary with created comment details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        comment = await client.add_issue_comment(
            resolved_owner, resolved_repo, issue_number, body
        )
        return {
            "success": True,
            "comment": comment.model_dump(),
            "message": "Comment added successfully",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_list_issue_comments(
    repo: str,
    issue_number: int,
    owner: Optional[str] = None,
    per_page: int = 30,
) -> dict[str, Any]:
    """
    List comments on an issue.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        issue_number: Issue number.
        owner: Repository owner (optional - will be auto-resolved if not provided).
        per_page: Number of results per page (max 100).

    Returns:
        Dictionary with list of comments.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        comments = await client.list_issue_comments(
            resolved_owner, resolved_repo, issue_number, per_page
        )
        return {
            "success": True,
            "comments": [c.model_dump() for c in comments],
            "count": len(comments),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


# =============================================================================
# Pull Request Tools
# =============================================================================


@mcp.tool()
async def github_list_pull_requests(
    repo: str,
    owner: Optional[str] = None,
    state: str = "open",
    head: Optional[str] = None,
    base: Optional[str] = None,
    per_page: int = 30,
) -> dict[str, Any]:
    """
    List pull requests in a repository.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        owner: Repository owner (optional - will be auto-resolved if not provided).
        state: PR state filter (open, closed, all). Default: open.
        head: Filter by head branch (format: user:branch).
        base: Filter by base/target branch name.
        per_page: Number of results per page (max 100).

    Returns:
        Dictionary with list of pull requests.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        prs = await client.list_pull_requests(
            owner=resolved_owner,
            repo=resolved_repo,
            state=state,
            head=head,
            base=base,
            per_page=per_page,
        )
        return {
            "success": True,
            "pull_requests": [pr.model_dump() for pr in prs],
            "count": len(prs),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_get_pull_request(
    repo: str,
    pr_number: int,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get a specific pull request by number.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        pr_number: Pull request number.
        owner: Repository owner (optional - will be auto-resolved if not provided).

    Returns:
        Dictionary with pull request details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        pr = await client.get_pull_request(resolved_owner, resolved_repo, pr_number)
        return {
            "success": True,
            "pull_request": pr.model_dump(),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_create_pull_request(
    repo: str,
    title: str,
    head: str,
    base: str,
    owner: Optional[str] = None,
    body: Optional[str] = None,
    draft: bool = False,
) -> dict[str, Any]:
    """
    Create a new pull request.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        title: Pull request title.
        head: Name of the branch with your changes.
        base: Name of the branch you want to merge into.
        owner: Repository owner (optional - will be auto-resolved if not provided).
        body: Pull request description in Markdown.
        draft: Create as draft PR. Default: False.

    Returns:
        Dictionary with created pull request details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        pr_data = PullRequestCreate(
            title=title,
            head=head,
            base=base,
            body=body,
            draft=draft,
        )
        pr = await client.create_pull_request(resolved_owner, resolved_repo, pr_data)
        return {
            "success": True,
            "pull_request": pr.model_dump(),
            "message": f"Pull request #{pr.number} created successfully",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_update_pull_request(
    repo: str,
    pr_number: int,
    owner: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[str] = None,
    base: Optional[str] = None,
) -> dict[str, Any]:
    """
    Update an existing pull request.

    Only provided fields will be updated.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        pr_number: Pull request number.
        owner: Repository owner (optional - will be auto-resolved if not provided).
        title: New title.
        body: New description.
        state: New state (open, closed).
        base: New target branch.

    Returns:
        Dictionary with updated pull request details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        update_data = PullRequestUpdate(
            title=title,
            body=body,
            state=state,
            base=base,
        )
        pr = await client.update_pull_request(
            resolved_owner, resolved_repo, pr_number, update_data
        )
        return {
            "success": True,
            "pull_request": pr.model_dump(),
            "message": f"Pull request #{pr.number} updated successfully",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_merge_pull_request(
    repo: str,
    pr_number: int,
    owner: Optional[str] = None,
    merge_method: str = "merge",
    commit_title: Optional[str] = None,
    commit_message: Optional[str] = None,
) -> dict[str, Any]:
    """
    Merge a pull request.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        pr_number: Pull request number.
        owner: Repository owner (optional - will be auto-resolved if not provided).
        merge_method: Merge method (merge, squash, rebase). Default: merge.
        commit_title: Custom merge commit title.
        commit_message: Custom merge commit message.

    Returns:
        Dictionary with merge result.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()

        # Validate merge method
        try:
            method = MergeMethod(merge_method)
        except ValueError:
            return {
                "success": False,
                "error": "validation_error",
                "message": f"Invalid merge method: {merge_method}. Use: merge, squash, rebase",
            }

        merge_data = PullRequestMerge(
            merge_method=method,
            commit_title=commit_title,
            commit_message=commit_message,
        )
        result = await client.merge_pull_request(
            resolved_owner, resolved_repo, pr_number, merge_data
        )
        return {
            "success": True,
            "merged": result.get("merged", True),
            "sha": result.get("sha"),
            "message": result.get("message", f"PR #{pr_number} merged successfully"),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_list_pr_files(
    repo: str,
    pr_number: int,
    owner: Optional[str] = None,
    per_page: int = 30,
) -> dict[str, Any]:
    """
    List files changed in a pull request.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        pr_number: Pull request number.
        owner: Repository owner (optional - will be auto-resolved if not provided).
        per_page: Number of results per page (max 100).

    Returns:
        Dictionary with list of changed files.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        files = await client.list_pull_request_files(
            resolved_owner, resolved_repo, pr_number, per_page
        )
        return {
            "success": True,
            "files": [f.model_dump() for f in files],
            "count": len(files),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_add_pr_comment(
    repo: str,
    pr_number: int,
    body: str,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Add a comment to a pull request.

    This adds an issue-level comment (not a review comment).

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        pr_number: Pull request number.
        body: Comment body in Markdown.
    Returns:
        Dictionary with created comment details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        comment = await client.add_pull_request_comment(
            resolved_owner, resolved_repo, pr_number, body
        )
        return {
            "success": True,
            "comment": comment.model_dump(),
            "message": "Comment added successfully",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_create_pr_review(
    repo: str,
    pr_number: int,
    event: str,
    owner: Optional[str] = None,
    body: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a review on a pull request.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        pr_number: Pull request number.
        event: Review action (APPROVE, REQUEST_CHANGES, COMMENT).
        owner: Repository owner (optional - will be auto-resolved if not provided).
        body: Review body/summary in Markdown.

    Returns:
        Dictionary with created review details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()

        # Validate event
        try:
            review_event = ReviewEvent(event.upper())
        except ValueError:
            return {
                "success": False,
                "error": "validation_error",
                "message": f"Invalid event: {event}. Use: APPROVE, REQUEST_CHANGES, COMMENT",
            }

        review_data = PullRequestReviewCreate(
            event=review_event,
            body=body,
        )
        review = await client.create_pull_request_review(
            resolved_owner, resolved_repo, pr_number, review_data
        )
        return {
            "success": True,
            "review": review.model_dump(),
            "message": f"Review submitted with {event}",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


# =============================================================================
# Branch Tools
# =============================================================================


@mcp.tool()
async def github_list_branches(
    repo: str,
    owner: Optional[str] = None,
    per_page: int = 30,
) -> dict[str, Any]:
    """
    List branches in a repository.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        owner: Repository owner (optional - will be auto-resolved if not provided).
        per_page: Number of results per page (max 100).

    Returns:
        Dictionary with list of branches.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        branches = await client.list_branches(resolved_owner, resolved_repo, per_page)
        return {
            "success": True,
            "branches": [b.model_dump() for b in branches],
            "count": len(branches),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_get_branch(
    repo: str,
    branch: str,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get details about a specific branch.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        branch: Branch name.
        owner: Repository owner (optional - will be auto-resolved if not provided).

    Returns:
        Dictionary with branch details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        branch_data = await client.get_branch(resolved_owner, resolved_repo, branch)
        return {
            "success": True,
            "branch": branch_data.model_dump(),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_create_branch(
    repo: str,
    branch_name: str,
    owner: Optional[str] = None,
    source_branch: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a new branch in a repository.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        branch_name: Name for the new branch.
        owner: Repository owner (optional - will be auto-resolved if not provided).
        source_branch: Branch to create from. Defaults to the default branch.

    Returns:
        Dictionary with created branch reference.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()

        # If no source branch specified, use default branch
        if not source_branch:
            source_branch = await client.get_default_branch(
                resolved_owner, resolved_repo
            )

        ref = await client.create_branch_from_branch(
            resolved_owner, resolved_repo, branch_name, source_branch
        )
        return {
            "success": True,
            "ref": ref.model_dump(),
            "message": f"Branch '{branch_name}' created from '{source_branch}'",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_delete_branch(
    repo: str,
    branch: str,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Delete a branch from a repository.

    WARNING: This cannot be undone.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        branch: Branch name to delete.
        owner: Repository owner (optional - will be auto-resolved if not provided).

    Returns:
        Dictionary with success status.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        await client.delete_branch(resolved_owner, resolved_repo, branch)
        return {
            "success": True,
            "message": f"Branch '{branch}' deleted successfully",
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_get_default_branch(
    repo: str,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get the default branch name for a repository.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        owner: Repository owner (optional - will be auto-resolved if not provided).

    Returns:
        Dictionary with default branch name.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        default_branch = await client.get_default_branch(resolved_owner, resolved_repo)
        return {
            "success": True,
            "default_branch": default_branch,
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


# =============================================================================
# Repository Tools
# =============================================================================


@mcp.tool()
async def github_get_repository(
    repo: str,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get repository information.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        owner: Repository owner (optional - will be auto-resolved if not provided).

    Returns:
        Dictionary with repository details.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        repository = await client.get_repository(resolved_owner, resolved_repo)
        return {
            "success": True,
            "repository": repository.model_dump(),
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_list_repositories(
    owner: Optional[str] = None,
    type: str = "all",
    per_page: int = 30,
) -> dict[str, Any]:
    """
    List repositories for a user or the authenticated user.

    NOTE: For listing your own accessible repos, prefer github_list_my_repositories()
    which provides a simplified view and uses caching.

    Args:
        owner: Username to list repos for. If None, lists authenticated user's repos.
        type: Repo type filter (all, owner, member). Default: all.
        per_page: Number of results per page (max 100).

    Returns:
        Dictionary with list of repositories.
    """
    try:
        client = get_github_client()
        repos = await client.list_repositories(owner, type, per_page)
        return {
            "success": True,
            "repositories": [r.model_dump() for r in repos],
            "count": len(repos),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_get_file_content(
    repo: str,
    path: str,
    owner: Optional[str] = None,
    ref: Optional[str] = None,
    decode: bool = True,
) -> dict[str, Any]:
    """
    Get file content from a repository.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        path: File path within the repository.
        owner: Repository owner (optional - will be auto-resolved if not provided).
        ref: Git reference (branch, tag, SHA). Defaults to default branch.
        decode: If True, decode base64 content to string. Default: True.

    Returns:
        Dictionary with file content.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()

        if decode:
            content = await client.get_file_content_decoded(
                resolved_owner, resolved_repo, path, ref
            )
            return {
                "success": True,
                "path": path,
                "content": content,
                "encoding": "utf-8",
                "repository": f"{resolved_owner}/{resolved_repo}",
            }
        else:
            file_content = await client.get_file_content(
                resolved_owner, resolved_repo, path, ref
            )
            return {
                "success": True,
                "file": file_content.model_dump(),
                "repository": f"{resolved_owner}/{resolved_repo}",
            }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


# =============================================================================
# Utility Tools
# =============================================================================


@mcp.tool()
async def github_get_authenticated_user() -> dict[str, Any]:
    """
    Get information about the authenticated user.

    This is often the first call to make - it establishes who you are
    and caches the username for subsequent operations.

    Returns:
        Dictionary with authenticated user details including:
        - login: GitHub username
        - name: Display name
        - email: Email address (if public)
        - public_repos: Number of public repositories
    """
    try:
        # Use cached version to avoid repeated API calls
        user = await get_cached_user()
        return {
            "success": True,
            "user": user,
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_find_repository(
    repo: str,
) -> dict[str, Any]:
    """
    Find and resolve a repository by name.

    Use this when you only have the repository name (not the full owner/repo path).
    This will search the authenticated user's accessible repositories and return
    the full repository details including the owner.

    Args:
        repo: Repository name to find. Can be:
              - Just the name (e.g., "Claude-Assistant-Platform")
              - Full path (e.g., "username/Claude-Assistant-Platform")

    Returns:
        Dictionary with:
        - success: Whether the repository was found
        - repository: Full repository details including owner
        - resolved_path: The full "owner/repo" path for use in other tools
    """
    try:
        owner, repo_name = await resolve_repository(repo)

        # Fetch full repository details
        client = get_github_client()
        repository = await client.get_repository(owner, repo_name)

        return {
            "success": True,
            "repository": repository.model_dump(),
            "resolved_path": f"{owner}/{repo_name}",
            "owner": owner,
            "repo": repo_name,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": "resolution_error",
            "message": str(e),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_list_my_repositories(
    type: str = "all",
    refresh: bool = False,
) -> dict[str, Any]:
    """
    List all repositories accessible to the authenticated user.

    This is useful for discovering available repositories without needing
    to know the exact owner/repo path. Returns repositories you own,
    are a member of, or have collaborator access to.

    Args:
        type: Filter by repository relationship:
              - "all": All accessible repos (default)
              - "owner": Only repos you own
              - "member": Repos you're a member of (org repos)
        refresh: If True, refresh the cache from GitHub API.

    Returns:
        Dictionary with list of repositories and their full paths.
    """
    try:
        repos = await get_cached_repos(refresh=refresh)

        # Filter by type if specified
        if type == "owner":
            user = await get_cached_user()
            username = user.get("login", "")
            repos = [r for r in repos if r.get("owner", {}).get("login") == username]
        elif type == "member":
            user = await get_cached_user()
            username = user.get("login", "")
            repos = [r for r in repos if r.get("owner", {}).get("login") != username]

        # Format for easy consumption
        repo_list = [
            {
                "full_name": r.get("full_name"),
                "name": r.get("name"),
                "owner": r.get("owner", {}).get("login"),
                "private": r.get("private"),
                "description": r.get("description"),
                "default_branch": r.get("default_branch"),
            }
            for r in repos
        ]

        return {
            "success": True,
            "repositories": repo_list,
            "count": len(repo_list),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_check_rate_limit() -> dict[str, Any]:
    """
    Check the current GitHub API rate limit status.

    Use this to monitor API usage and avoid hitting rate limits.

    Returns:
        Dictionary with rate limit information including:
        - core: Main API rate limit
        - search: Search API rate limit
        - graphql: GraphQL API rate limit
    """
    try:
        client = get_github_client()
        rate_limit = await client.get_rate_limit()

        # Format resources for easier reading
        resources = {}
        for name, resource in rate_limit.resources.items():
            resources[name] = {
                "limit": resource.limit,
                "remaining": resource.remaining,
                "used": resource.used,
                "reset_at": resource.reset,
            }

        return {
            "success": True,
            "rate_limit": resources,
            "core_remaining": resources.get("core", {}).get("remaining", 0),
        }
    except Exception as e:
        return handle_api_error(e)


@mcp.tool()
async def github_list_labels(
    repo: str,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    List all labels in a repository.

    Args:
        repo: Repository name (e.g., "my-repo" or "owner/my-repo").
        owner: Repository owner (optional - will be auto-resolved if not provided).

    Returns:
        Dictionary with list of labels.
    """
    try:
        resolved_owner, resolved_repo = await resolve_repository(repo, owner)
        client = get_github_client()
        labels = await client.list_labels(resolved_owner, resolved_repo)
        return {
            "success": True,
            "labels": [label.model_dump() for label in labels],
            "count": len(labels),
            "repository": f"{resolved_owner}/{resolved_repo}",
        }
    except ValueError as e:
        return {"success": False, "error": "resolution_error", "message": str(e)}
    except Exception as e:
        return handle_api_error(e)


# =============================================================================
# FastAPI Application (for HTTP access)
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events for the GitHub client.

    Args:
        app: The FastAPI application instance.

    Yields:
        None during the application's lifespan.
    """
    # Startup: nothing special needed, client is created lazily
    logger.info("GitHub MCP FastAPI application starting")
    yield
    # Shutdown: close the GitHub client
    global github_client
    if github_client:
        await github_client.close()
        github_client = None
        logger.info("GitHub client closed")
    logger.info("GitHub MCP FastAPI application shutdown complete")


fastapi_app = FastAPI(
    title="GitHub MCP Server",
    description="MCP server providing GitHub API tools for issues, PRs, and branches",
    version="0.1.0",
    lifespan=lifespan,
)


@fastapi_app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Dictionary with service status.
    """
    configured = bool(settings.github_token)

    status_info = {
        "status": "healthy" if configured else "unconfigured",
        "service": "github-mcp",
        "api_configured": configured,
    }

    # Try to get authenticated user if configured
    if configured:
        try:
            client = get_github_client()
            user = await client.get_authenticated_user()
            status_info["authenticated_as"] = user.login
        except Exception as e:
            status_info["auth_error"] = str(e)

    return status_info


# -----------------------------------------------------------------------------
# HTTP Request Models
# -----------------------------------------------------------------------------
class FindRepositoryRequest(BaseModel):
    """Request model for finding a repository."""

    repo: str


class ListMyRepositoriesRequest(BaseModel):
    """Request model for listing user's repositories."""

    type: str = "all"
    refresh: bool = False


class ListIssuesRequest(BaseModel):
    """Request model for listing issues."""

    repo: str
    owner: Optional[str] = None
    state: str = "open"
    labels: Optional[str] = None
    assignee: Optional[str] = None
    per_page: int = 30


class CreateIssueRequest(BaseModel):
    """Request model for creating an issue."""

    repo: str
    title: str
    owner: Optional[str] = None
    body: Optional[str] = None
    labels: Optional[str] = None
    assignees: Optional[str] = None


class ListPullRequestsRequest(BaseModel):
    """Request model for listing pull requests."""

    repo: str
    owner: Optional[str] = None
    state: str = "open"
    head: Optional[str] = None
    base: Optional[str] = None
    per_page: int = 30


class CreatePullRequestRequest(BaseModel):
    """Request model for creating a pull request."""

    repo: str
    title: str
    head: str
    base: str
    owner: Optional[str] = None
    body: Optional[str] = None
    draft: bool = False


class MergePullRequestRequest(BaseModel):
    """Request model for merging a pull request."""

    repo: str
    pr_number: int
    owner: Optional[str] = None
    merge_method: str = "merge"
    commit_title: Optional[str] = None
    commit_message: Optional[str] = None


class CreateBranchRequest(BaseModel):
    """Request model for creating a branch."""

    repo: str
    branch_name: str
    owner: Optional[str] = None
    source_branch: Optional[str] = None


class GetIssueRequest(BaseModel):
    """Request model for getting a single issue."""

    repo: str
    issue_number: int
    owner: Optional[str] = None


class UpdateIssueRequest(BaseModel):
    """Request model for updating an issue."""

    repo: str
    issue_number: int
    owner: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    state: Optional[str] = None
    labels: Optional[str] = None
    assignees: Optional[str] = None


class AddIssueCommentRequest(BaseModel):
    """Request model for adding a comment to an issue."""

    repo: str
    issue_number: int
    body: str
    owner: Optional[str] = None


class ListIssueCommentsRequest(BaseModel):
    """Request model for listing issue comments."""

    repo: str
    issue_number: int
    owner: Optional[str] = None
    per_page: int = 30


class GetPullRequestRequest(BaseModel):
    """Request model for getting a single pull request."""

    repo: str
    pr_number: int
    owner: Optional[str] = None


class UpdatePullRequestRequest(BaseModel):
    """Request model for updating a pull request."""

    repo: str
    pr_number: int
    owner: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    state: Optional[str] = None
    base: Optional[str] = None


class ListPrFilesRequest(BaseModel):
    """Request model for listing files changed in a PR."""

    repo: str
    pr_number: int
    owner: Optional[str] = None
    per_page: int = 30


class AddPrCommentRequest(BaseModel):
    """Request model for adding a comment to a PR."""

    repo: str
    pr_number: int
    body: str
    owner: Optional[str] = None


class CreatePrReviewRequest(BaseModel):
    """Request model for creating a PR review."""

    repo: str
    pr_number: int
    event: str
    owner: Optional[str] = None
    body: Optional[str] = None


class ListBranchesRequest(BaseModel):
    """Request model for listing branches."""

    repo: str
    owner: Optional[str] = None
    per_page: int = 30


class GetBranchRequest(BaseModel):
    """Request model for getting a branch."""

    repo: str
    branch: str
    owner: Optional[str] = None


class DeleteBranchRequest(BaseModel):
    """Request model for deleting a branch."""

    repo: str
    branch: str
    owner: Optional[str] = None


class GetDefaultBranchRequest(BaseModel):
    """Request model for getting the default branch."""

    repo: str
    owner: Optional[str] = None


class GetRepositoryRequest(BaseModel):
    """Request model for getting repository info."""

    repo: str
    owner: Optional[str] = None


class ListRepositoriesRequest(BaseModel):
    """Request model for listing repositories."""

    owner: Optional[str] = None
    type: str = "all"
    per_page: int = 30


class GetFileContentRequest(BaseModel):
    """Request model for getting file content."""

    repo: str
    path: str
    owner: Optional[str] = None
    ref: Optional[str] = None
    decode: bool = True


class ListLabelsRequest(BaseModel):
    """Request model for listing labels."""

    repo: str
    owner: Optional[str] = None


# -----------------------------------------------------------------------------
# HTTP Tool Endpoints
# -----------------------------------------------------------------------------
@fastapi_app.post("/tools/github_find_repository")
async def http_find_repository(request: FindRepositoryRequest) -> dict[str, Any]:
    """HTTP endpoint for finding a repository."""
    return await github_find_repository(repo=request.repo)


@fastapi_app.post("/tools/github_list_my_repositories")
async def http_list_my_repositories(request: ListMyRepositoriesRequest) -> dict[str, Any]:
    """HTTP endpoint for listing user's repositories."""
    return await github_list_my_repositories(type=request.type, refresh=request.refresh)


@fastapi_app.post("/tools/github_list_issues")
async def http_list_issues(request: ListIssuesRequest) -> dict[str, Any]:
    """HTTP endpoint for listing issues."""
    return await github_list_issues(
        repo=request.repo,
        owner=request.owner,
        state=request.state,
        labels=request.labels,
        assignee=request.assignee,
        per_page=request.per_page,
    )


@fastapi_app.post("/tools/github_create_issue")
async def http_create_issue(request: CreateIssueRequest) -> dict[str, Any]:
    """HTTP endpoint for creating an issue."""
    return await github_create_issue(
        owner=request.owner,
        repo=request.repo,
        title=request.title,
        body=request.body,
        labels=request.labels,
        assignees=request.assignees,
    )


@fastapi_app.post("/tools/github_list_pull_requests")
async def http_list_pull_requests(request: ListPullRequestsRequest) -> dict[str, Any]:
    """HTTP endpoint for listing pull requests."""
    return await github_list_pull_requests(
        owner=request.owner,
        repo=request.repo,
        state=request.state,
        head=request.head,
        base=request.base,
        per_page=request.per_page,
    )


@fastapi_app.post("/tools/github_create_pull_request")
async def http_create_pull_request(request: CreatePullRequestRequest) -> dict[str, Any]:
    """HTTP endpoint for creating a pull request."""
    return await github_create_pull_request(
        owner=request.owner,
        repo=request.repo,
        title=request.title,
        head=request.head,
        base=request.base,
        body=request.body,
        draft=request.draft,
    )


@fastapi_app.post("/tools/github_merge_pull_request")
async def http_merge_pull_request(request: MergePullRequestRequest) -> dict[str, Any]:
    """HTTP endpoint for merging a pull request."""
    return await github_merge_pull_request(
        owner=request.owner,
        repo=request.repo,
        pr_number=request.pr_number,
        merge_method=request.merge_method,
        commit_title=request.commit_title,
        commit_message=request.commit_message,
    )


@fastapi_app.post("/tools/github_create_branch")
async def http_create_branch(request: CreateBranchRequest) -> dict[str, Any]:
    """HTTP endpoint for creating a branch."""
    return await github_create_branch(
        owner=request.owner,
        repo=request.repo,
        branch_name=request.branch_name,
        source_branch=request.source_branch,
    )


@fastapi_app.post("/tools/github_check_rate_limit")
async def http_check_rate_limit() -> dict[str, Any]:
    """HTTP endpoint for checking rate limit."""
    return await github_check_rate_limit()


@fastapi_app.post("/tools/github_get_authenticated_user")
async def http_get_authenticated_user() -> dict[str, Any]:
    """HTTP endpoint for getting authenticated user."""
    return await github_get_authenticated_user()


@fastapi_app.post("/tools/github_get_issue")
async def http_get_issue(request: GetIssueRequest) -> dict[str, Any]:
    """HTTP endpoint for getting a single issue."""
    return await github_get_issue(
        owner=request.owner,
        repo=request.repo,
        issue_number=request.issue_number,
    )


@fastapi_app.post("/tools/github_update_issue")
async def http_update_issue(request: UpdateIssueRequest) -> dict[str, Any]:
    """HTTP endpoint for updating an issue."""
    return await github_update_issue(
        owner=request.owner,
        repo=request.repo,
        issue_number=request.issue_number,
        title=request.title,
        body=request.body,
        state=request.state,
        labels=request.labels,
        assignees=request.assignees,
    )


@fastapi_app.post("/tools/github_add_issue_comment")
async def http_add_issue_comment(request: AddIssueCommentRequest) -> dict[str, Any]:
    """HTTP endpoint for adding a comment to an issue."""
    return await github_add_issue_comment(
        owner=request.owner,
        repo=request.repo,
        issue_number=request.issue_number,
        body=request.body,
    )


@fastapi_app.post("/tools/github_list_issue_comments")
async def http_list_issue_comments(request: ListIssueCommentsRequest) -> dict[str, Any]:
    """HTTP endpoint for listing issue comments."""
    return await github_list_issue_comments(
        owner=request.owner,
        repo=request.repo,
        issue_number=request.issue_number,
        per_page=request.per_page,
    )


@fastapi_app.post("/tools/github_get_pull_request")
async def http_get_pull_request(request: GetPullRequestRequest) -> dict[str, Any]:
    """HTTP endpoint for getting a single pull request."""
    return await github_get_pull_request(
        owner=request.owner,
        repo=request.repo,
        pr_number=request.pr_number,
    )


@fastapi_app.post("/tools/github_update_pull_request")
async def http_update_pull_request(request: UpdatePullRequestRequest) -> dict[str, Any]:
    """HTTP endpoint for updating a pull request."""
    return await github_update_pull_request(
        owner=request.owner,
        repo=request.repo,
        pr_number=request.pr_number,
        title=request.title,
        body=request.body,
        state=request.state,
        base=request.base,
    )


@fastapi_app.post("/tools/github_list_pr_files")
async def http_list_pr_files(request: ListPrFilesRequest) -> dict[str, Any]:
    """HTTP endpoint for listing files changed in a PR."""
    return await github_list_pr_files(
        owner=request.owner,
        repo=request.repo,
        pr_number=request.pr_number,
        per_page=request.per_page,
    )


@fastapi_app.post("/tools/github_add_pr_comment")
async def http_add_pr_comment(request: AddPrCommentRequest) -> dict[str, Any]:
    """HTTP endpoint for adding a comment to a PR."""
    return await github_add_pr_comment(
        owner=request.owner,
        repo=request.repo,
        pr_number=request.pr_number,
        body=request.body,
    )


@fastapi_app.post("/tools/github_create_pr_review")
async def http_create_pr_review(request: CreatePrReviewRequest) -> dict[str, Any]:
    """HTTP endpoint for creating a PR review."""
    return await github_create_pr_review(
        owner=request.owner,
        repo=request.repo,
        pr_number=request.pr_number,
        event=request.event,
        body=request.body,
    )


@fastapi_app.post("/tools/github_list_branches")
async def http_list_branches(request: ListBranchesRequest) -> dict[str, Any]:
    """HTTP endpoint for listing branches."""
    return await github_list_branches(
        owner=request.owner,
        repo=request.repo,
        per_page=request.per_page,
    )


@fastapi_app.post("/tools/github_get_branch")
async def http_get_branch(request: GetBranchRequest) -> dict[str, Any]:
    """HTTP endpoint for getting a branch."""
    return await github_get_branch(
        owner=request.owner,
        repo=request.repo,
        branch=request.branch,
    )


@fastapi_app.post("/tools/github_delete_branch")
async def http_delete_branch(request: DeleteBranchRequest) -> dict[str, Any]:
    """HTTP endpoint for deleting a branch."""
    return await github_delete_branch(
        owner=request.owner,
        repo=request.repo,
        branch=request.branch,
    )


@fastapi_app.post("/tools/github_get_default_branch")
async def http_get_default_branch(request: GetDefaultBranchRequest) -> dict[str, Any]:
    """HTTP endpoint for getting the default branch."""
    return await github_get_default_branch(
        owner=request.owner,
        repo=request.repo,
    )


@fastapi_app.post("/tools/github_get_repository")
async def http_get_repository(request: GetRepositoryRequest) -> dict[str, Any]:
    """HTTP endpoint for getting repository info."""
    return await github_get_repository(
        owner=request.owner,
        repo=request.repo,
    )


@fastapi_app.post("/tools/github_list_repositories")
async def http_list_repositories(request: ListRepositoriesRequest) -> dict[str, Any]:
    """HTTP endpoint for listing repositories."""
    return await github_list_repositories(
        owner=request.owner,
        type=request.type,
        per_page=request.per_page,
    )


@fastapi_app.post("/tools/github_get_file_content")
async def http_get_file_content(request: GetFileContentRequest) -> dict[str, Any]:
    """HTTP endpoint for getting file content."""
    return await github_get_file_content(
        owner=request.owner,
        repo=request.repo,
        path=request.path,
        ref=request.ref,
        decode=request.decode,
    )


@fastapi_app.post("/tools/github_list_labels")
async def http_list_labels(request: ListLabelsRequest) -> dict[str, Any]:
    """HTTP endpoint for listing labels."""
    return await github_list_labels(
        owner=request.owner,
        repo=request.repo,
    )


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Run the server."""
    import uvicorn

    # Set log level
    logging.getLogger().setLevel(settings.log_level.upper())

    logger.info(f"Starting GitHub MCP Server on {settings.host}:{settings.port}")

    if not settings.github_token:
        logger.warning("GITHUB_TOKEN not set - server will not function properly")
        logger.warning("Set GITHUB_TOKEN to a fine-grained personal access token")
    else:
        logger.info("GitHub token configured")

    uvicorn.run(
        fastapi_app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
