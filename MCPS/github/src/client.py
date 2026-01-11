# =============================================================================
# GitHub MCP Server - API Client
# =============================================================================
"""
Async HTTP client for GitHub REST API.

This module provides a high-level client for interacting with GitHub's REST API,
including error handling, rate limiting awareness, and response parsing.
"""

import asyncio
import base64
import logging
from typing import Any, Optional

import httpx

from .models import (
    Branch,
    Commit,
    FileContent,
    Issue,
    IssueComment,
    IssueCreate,
    IssueUpdate,
    Label,
    PullRequest,
    PullRequestCreate,
    PullRequestFile,
    PullRequestMerge,
    PullRequestReview,
    PullRequestReviewCreate,
    PullRequestUpdate,
    RateLimitResponse,
    Ref,
    Repository,
    User,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class GitHubApiError(Exception):
    """
    Base exception for GitHub API errors.

    Attributes:
        message: Error description.
        status_code: HTTP status code.
        response_data: Raw response data from GitHub.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_data: Optional[dict] = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: Error description.
            status_code: HTTP status code.
            response_data: Raw response data.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}


class GitHubAuthenticationError(GitHubApiError):
    """Raised when authentication fails (401)."""

    pass


class GitHubForbiddenError(GitHubApiError):
    """Raised when access is forbidden (403) - often rate limiting."""

    pass


class GitHubNotFoundError(GitHubApiError):
    """Raised when a resource is not found (404)."""

    pass


class GitHubValidationError(GitHubApiError):
    """Raised when request validation fails (422)."""

    pass


class GitHubRateLimitError(GitHubApiError):
    """
    Raised when rate limit is exceeded.

    Attributes:
        reset_at: Unix timestamp when rate limit resets.
        retry_after: Seconds to wait before retrying.
    """

    def __init__(
        self,
        message: str,
        reset_at: int = 0,
        retry_after: int = 0,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the rate limit exception.

        Args:
            message: Error description.
            reset_at: Unix timestamp when limit resets.
            retry_after: Seconds to wait.
            **kwargs: Additional arguments for parent.
        """
        super().__init__(message, **kwargs)
        self.reset_at = reset_at
        self.retry_after = retry_after


# =============================================================================
# GitHub Client
# =============================================================================


class GitHubClient:
    """
    Async client for GitHub REST API.

    Provides methods for interacting with GitHub's Issues, Pull Requests,
    Branches, and Repository APIs with built-in error handling and
    rate limit awareness.

    Attributes:
        token: GitHub personal access token.
        base_url: GitHub API base URL.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        token: str,
        base_url: str = "https://api.github.com",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the GitHub client.

        Args:
            token: GitHub personal access token.
            base_url: GitHub API base URL.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for rate limits.
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Create httpx client with default headers
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Claude-Assistant-GitHub-MCP/0.1.0",
            },
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "GitHubClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # -------------------------------------------------------------------------
    # HTTP Request Helpers
    # -------------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        retry_count: int = 0,
    ) -> dict | list | None:
        """
        Make an HTTP request to the GitHub API.

        Handles error responses and rate limiting with automatic retry.

        Args:
            method: HTTP method (GET, POST, PATCH, PUT, DELETE).
            path: API path (e.g., /repos/owner/repo/issues).
            params: Query parameters.
            json: JSON body for POST/PATCH/PUT.
            retry_count: Current retry attempt.

        Returns:
            Parsed JSON response or None for 204 responses.

        Raises:
            GitHubAuthenticationError: For 401 responses.
            GitHubForbiddenError: For 403 responses.
            GitHubNotFoundError: For 404 responses.
            GitHubValidationError: For 422 responses.
            GitHubRateLimitError: When rate limit is exceeded.
            GitHubApiError: For other error responses.
        """
        try:
            response = await self._client.request(
                method=method,
                url=path,
                params=params,
                json=json,
            )

            # Handle successful responses
            if response.status_code == 204:
                return None
            if response.status_code in (200, 201):
                return response.json()

            # Handle errors
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass

            error_message = error_data.get("message", response.text)

            # Check for rate limiting
            if response.status_code == 403:
                # Check if it's a rate limit error
                remaining = response.headers.get("X-RateLimit-Remaining", "1")
                if remaining == "0" or "rate limit" in error_message.lower():
                    reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
                    retry_after = int(response.headers.get("Retry-After", "60"))

                    # Retry if we haven't exceeded max retries
                    if retry_count < self.max_retries:
                        wait_time = min(retry_after, 60)  # Cap at 60 seconds
                        logger.warning(
                            f"Rate limited. Waiting {wait_time}s before retry "
                            f"({retry_count + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        return await self._request(
                            method, path, params, json, retry_count + 1
                        )

                    raise GitHubRateLimitError(
                        message=f"Rate limit exceeded: {error_message}",
                        status_code=403,
                        response_data=error_data,
                        reset_at=reset_at,
                        retry_after=retry_after,
                    )

                raise GitHubForbiddenError(
                    message=error_message,
                    status_code=403,
                    response_data=error_data,
                )

            if response.status_code == 401:
                raise GitHubAuthenticationError(
                    message=f"Authentication failed: {error_message}",
                    status_code=401,
                    response_data=error_data,
                )

            if response.status_code == 404:
                raise GitHubNotFoundError(
                    message=f"Resource not found: {error_message}",
                    status_code=404,
                    response_data=error_data,
                )

            if response.status_code == 422:
                raise GitHubValidationError(
                    message=f"Validation failed: {error_message}",
                    status_code=422,
                    response_data=error_data,
                )

            raise GitHubApiError(
                message=f"GitHub API error: {error_message}",
                status_code=response.status_code,
                response_data=error_data,
            )

        except httpx.TimeoutException as e:
            raise GitHubApiError(
                message=f"Request timed out: {str(e)}",
                status_code=0,
            )
        except httpx.RequestError as e:
            raise GitHubApiError(
                message=f"Request failed: {str(e)}",
                status_code=0,
            )

    async def _get(
        self, path: str, params: Optional[dict] = None
    ) -> dict | list | None:
        """Make a GET request."""
        return await self._request("GET", path, params=params)

    async def _post(
        self, path: str, json: Optional[dict] = None
    ) -> dict | list | None:
        """Make a POST request."""
        return await self._request("POST", path, json=json)

    async def _patch(
        self, path: str, json: Optional[dict] = None
    ) -> dict | list | None:
        """Make a PATCH request."""
        return await self._request("PATCH", path, json=json)

    async def _put(
        self, path: str, json: Optional[dict] = None
    ) -> dict | list | None:
        """Make a PUT request."""
        return await self._request("PUT", path, json=json)

    async def _delete(self, path: str) -> dict | list | None:
        """Make a DELETE request."""
        return await self._request("DELETE", path)

    # -------------------------------------------------------------------------
    # User Methods
    # -------------------------------------------------------------------------

    async def get_authenticated_user(self) -> User:
        """
        Get the authenticated user's information.

        Returns:
            User model for the authenticated user.
        """
        data = await self._get("/user")
        return User.model_validate(data)

    # -------------------------------------------------------------------------
    # Rate Limit Methods
    # -------------------------------------------------------------------------

    async def get_rate_limit(self) -> RateLimitResponse:
        """
        Get the current rate limit status.

        Returns:
            RateLimitResponse with current limits.
        """
        data = await self._get("/rate_limit")
        return RateLimitResponse.model_validate(data)

    # -------------------------------------------------------------------------
    # Repository Methods
    # -------------------------------------------------------------------------

    async def get_repository(self, owner: str, repo: str) -> Repository:
        """
        Get repository information.

        Args:
            owner: Repository owner username.
            repo: Repository name.

        Returns:
            Repository model.
        """
        data = await self._get(f"/repos/{owner}/{repo}")
        return Repository.model_validate(data)

    async def list_repositories(
        self,
        owner: Optional[str] = None,
        type: str = "all",
        per_page: int = 30,
    ) -> list[Repository]:
        """
        List repositories for a user or the authenticated user.

        Args:
            owner: Repository owner (None for authenticated user).
            type: Repository type filter (all, owner, member).
            per_page: Results per page (max 100).

        Returns:
            List of Repository models.
        """
        if owner:
            path = f"/users/{owner}/repos"
        else:
            path = "/user/repos"

        params = {"type": type, "per_page": min(per_page, 100)}
        data = await self._get(path, params=params)
        return [Repository.model_validate(r) for r in data]

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> FileContent:
        """
        Get file content from a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: File path within the repository.
            ref: Git reference (branch, tag, SHA). Defaults to default branch.

        Returns:
            FileContent model with base64 encoded content.
        """
        params = {}
        if ref:
            params["ref"] = ref

        data = await self._get(f"/repos/{owner}/{repo}/contents/{path}", params=params)
        return FileContent.model_validate(data)

    async def get_file_content_decoded(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> str:
        """
        Get decoded file content from a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: File path within the repository.
            ref: Git reference. Defaults to default branch.

        Returns:
            Decoded file content as string.
        """
        file_content = await self.get_file_content(owner, repo, path, ref)
        if file_content.content and file_content.encoding == "base64":
            return base64.b64decode(file_content.content).decode("utf-8")
        return file_content.content or ""

    # -------------------------------------------------------------------------
    # Issue Methods
    # -------------------------------------------------------------------------

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[list[str]] = None,
        assignee: Optional[str] = None,
        creator: Optional[str] = None,
        mentioned: Optional[str] = None,
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
    ) -> list[Issue]:
        """
        List issues in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: Issue state (open, closed, all).
            labels: Filter by label names.
            assignee: Filter by assignee username.
            creator: Filter by creator username.
            mentioned: Filter by mentioned username.
            sort: Sort field (created, updated, comments).
            direction: Sort direction (asc, desc).
            per_page: Results per page (max 100).

        Returns:
            List of Issue models.
        """
        params: dict[str, Any] = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
        }
        if labels:
            params["labels"] = ",".join(labels)
        if assignee:
            params["assignee"] = assignee
        if creator:
            params["creator"] = creator
        if mentioned:
            params["mentioned"] = mentioned

        data = await self._get(f"/repos/{owner}/{repo}/issues", params=params)
        # Filter out pull requests (they appear in issues endpoint)
        return [Issue.model_validate(i) for i in data if "pull_request" not in i]

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> Issue:
        """
        Get a specific issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            Issue model.
        """
        data = await self._get(f"/repos/{owner}/{repo}/issues/{issue_number}")
        return Issue.model_validate(data)

    async def create_issue(
        self, owner: str, repo: str, issue: IssueCreate
    ) -> Issue:
        """
        Create a new issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue: Issue creation data.

        Returns:
            Created Issue model.
        """
        payload = issue.model_dump(exclude_none=True)
        data = await self._post(f"/repos/{owner}/{repo}/issues", json=payload)
        return Issue.model_validate(data)

    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        update: IssueUpdate,
    ) -> Issue:
        """
        Update an existing issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.
            update: Issue update data.

        Returns:
            Updated Issue model.
        """
        payload = update.model_dump(exclude_none=True)
        data = await self._patch(
            f"/repos/{owner}/{repo}/issues/{issue_number}", json=payload
        )
        return Issue.model_validate(data)

    async def list_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        per_page: int = 30,
    ) -> list[IssueComment]:
        """
        List comments on an issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.
            per_page: Results per page (max 100).

        Returns:
            List of IssueComment models.
        """
        params = {"per_page": min(per_page, 100)}
        data = await self._get(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments", params=params
        )
        return [IssueComment.model_validate(c) for c in data]

    async def add_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> IssueComment:
        """
        Add a comment to an issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.
            body: Comment body (Markdown).

        Returns:
            Created IssueComment model.
        """
        data = await self._post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        return IssueComment.model_validate(data)

    async def list_labels(self, owner: str, repo: str) -> list[Label]:
        """
        List labels in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            List of Label models.
        """
        data = await self._get(f"/repos/{owner}/{repo}/labels")
        return [Label.model_validate(label) for label in data]

    # -------------------------------------------------------------------------
    # Pull Request Methods
    # -------------------------------------------------------------------------

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        head: Optional[str] = None,
        base: Optional[str] = None,
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
    ) -> list[PullRequest]:
        """
        List pull requests in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: PR state (open, closed, all).
            head: Filter by head branch (user:branch).
            base: Filter by base branch name.
            sort: Sort field (created, updated, popularity, long-running).
            direction: Sort direction (asc, desc).
            per_page: Results per page (max 100).

        Returns:
            List of PullRequest models.
        """
        params: dict[str, Any] = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
        }
        if head:
            params["head"] = head
        if base:
            params["base"] = base

        data = await self._get(f"/repos/{owner}/{repo}/pulls", params=params)
        return [PullRequest.model_validate(pr) for pr in data]

    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> PullRequest:
        """
        Get a specific pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            PullRequest model.
        """
        data = await self._get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return PullRequest.model_validate(data)

    async def create_pull_request(
        self, owner: str, repo: str, pr: PullRequestCreate
    ) -> PullRequest:
        """
        Create a new pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr: Pull request creation data.

        Returns:
            Created PullRequest model.
        """
        payload = pr.model_dump(exclude_none=True)
        data = await self._post(f"/repos/{owner}/{repo}/pulls", json=payload)
        return PullRequest.model_validate(data)

    async def update_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        update: PullRequestUpdate,
    ) -> PullRequest:
        """
        Update an existing pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            update: Pull request update data.

        Returns:
            Updated PullRequest model.
        """
        payload = update.model_dump(exclude_none=True)
        data = await self._patch(
            f"/repos/{owner}/{repo}/pulls/{pr_number}", json=payload
        )
        return PullRequest.model_validate(data)

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        merge: Optional[PullRequestMerge] = None,
    ) -> dict:
        """
        Merge a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            merge: Merge options.

        Returns:
            Merge result with sha and merged status.
        """
        payload = {}
        if merge:
            payload = merge.model_dump(exclude_none=True)
            # API expects merge_method as a string value
            if "merge_method" in payload:
                payload["merge_method"] = payload["merge_method"].value

        data = await self._put(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", json=payload
        )
        return data

    async def list_pull_request_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        per_page: int = 30,
    ) -> list[PullRequestFile]:
        """
        List files changed in a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            per_page: Results per page (max 100).

        Returns:
            List of PullRequestFile models.
        """
        params = {"per_page": min(per_page, 100)}
        data = await self._get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files", params=params
        )
        return [PullRequestFile.model_validate(f) for f in data]

    async def list_pull_request_reviews(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[PullRequestReview]:
        """
        List reviews on a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            List of PullRequestReview models.
        """
        data = await self._get(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
        return [PullRequestReview.model_validate(r) for r in data]

    async def create_pull_request_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review: PullRequestReviewCreate,
    ) -> PullRequestReview:
        """
        Create a review on a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            review: Review creation data.

        Returns:
            Created PullRequestReview model.
        """
        payload = review.model_dump(exclude_none=True)
        # Convert enum to string
        if "event" in payload:
            payload["event"] = payload["event"].value

        data = await self._post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews", json=payload
        )
        return PullRequestReview.model_validate(data)

    async def add_pull_request_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> IssueComment:
        """
        Add a comment to a pull request (issue-level comment).

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            body: Comment body (Markdown).

        Returns:
            Created IssueComment model.
        """
        # PR comments use the issues endpoint
        return await self.add_issue_comment(owner, repo, pr_number, body)

    # -------------------------------------------------------------------------
    # Branch Methods
    # -------------------------------------------------------------------------

    async def list_branches(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
    ) -> list[Branch]:
        """
        List branches in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            per_page: Results per page (max 100).

        Returns:
            List of Branch models.
        """
        params = {"per_page": min(per_page, 100)}
        data = await self._get(f"/repos/{owner}/{repo}/branches", params=params)
        return [Branch.model_validate(b) for b in data]

    async def get_branch(self, owner: str, repo: str, branch: str) -> Branch:
        """
        Get a specific branch.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Branch name.

        Returns:
            Branch model.
        """
        data = await self._get(f"/repos/{owner}/{repo}/branches/{branch}")
        return Branch.model_validate(data)

    async def get_ref(self, owner: str, repo: str, ref: str) -> Ref:
        """
        Get a Git reference.

        Args:
            owner: Repository owner.
            repo: Repository name.
            ref: Reference name (e.g., heads/main, tags/v1.0).

        Returns:
            Ref model.
        """
        data = await self._get(f"/repos/{owner}/{repo}/git/ref/{ref}")
        return Ref.model_validate(data)

    async def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        source_sha: str,
    ) -> Ref:
        """
        Create a new branch.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch_name: Name for the new branch.
            source_sha: SHA to branch from.

        Returns:
            Created Ref model.
        """
        data = await self._post(
            f"/repos/{owner}/{repo}/git/refs",
            json={
                "ref": f"refs/heads/{branch_name}",
                "sha": source_sha,
            },
        )
        return Ref.model_validate(data)

    async def create_branch_from_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        source_branch: str,
    ) -> Ref:
        """
        Create a new branch from an existing branch.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch_name: Name for the new branch.
            source_branch: Branch to create from.

        Returns:
            Created Ref model.
        """
        # Get the SHA of the source branch
        source = await self.get_branch(owner, repo, source_branch)
        source_sha = source.commit.sha if source.commit else ""

        if not source_sha:
            raise GitHubApiError(
                message=f"Could not get SHA for branch '{source_branch}'",
                status_code=0,
            )

        return await self.create_branch(owner, repo, branch_name, source_sha)

    async def delete_branch(self, owner: str, repo: str, branch: str) -> None:
        """
        Delete a branch.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Branch name to delete.
        """
        await self._delete(f"/repos/{owner}/{repo}/git/refs/heads/{branch}")

    async def get_default_branch(self, owner: str, repo: str) -> str:
        """
        Get the repository's default branch name.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Default branch name.
        """
        repository = await self.get_repository(owner, repo)
        return repository.default_branch

    # -------------------------------------------------------------------------
    # Commit Methods
    # -------------------------------------------------------------------------

    async def get_commit(self, owner: str, repo: str, sha: str) -> Commit:
        """
        Get a specific commit.

        Args:
            owner: Repository owner.
            repo: Repository name.
            sha: Commit SHA.

        Returns:
            Commit model.
        """
        data = await self._get(f"/repos/{owner}/{repo}/commits/{sha}")
        return Commit.model_validate(data)

    async def list_commits(
        self,
        owner: str,
        repo: str,
        sha: Optional[str] = None,
        path: Optional[str] = None,
        author: Optional[str] = None,
        per_page: int = 30,
    ) -> list[Commit]:
        """
        List commits in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            sha: SHA or branch to start from.
            path: Only commits affecting this path.
            author: Only commits by this author.
            per_page: Results per page (max 100).

        Returns:
            List of Commit models.
        """
        params: dict[str, Any] = {"per_page": min(per_page, 100)}
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        if author:
            params["author"] = author

        data = await self._get(f"/repos/{owner}/{repo}/commits", params=params)
        return [Commit.model_validate(c) for c in data]
