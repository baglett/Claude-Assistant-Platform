# =============================================================================
# Motion MCP Server - Motion API Client
# =============================================================================
"""
Async HTTP client for Motion API with integrated rate limiting.

This client handles all communication with the Motion API, including:
- Authentication via API key
- Automatic rate limiting to prevent account suspension
- Error handling and retry logic
- Request/response serialization

CRITICAL: The rate limiter is strictly enforced to prevent API abuse.
"""

import logging
from typing import Any, Optional

import httpx

from src.models.projects import Project, ProjectCreate, ProjectListResponse
from src.models.tasks import Task, TaskCreate, TaskListResponse, TaskUpdate
from src.models.users import User, UserListResponse
from src.models.workspaces import Workspace, WorkspaceListResponse
from src.rate_limiter import (
    AccountType,
    RateLimiter,
    RateLimitExceededError,
    create_rate_limiter,
)

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------
class MotionApiError(Exception):
    """
    Exception raised for Motion API errors.

    Attributes:
        status_code: HTTP status code.
        message: Error message from API.
        details: Additional error details.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            status_code: HTTP status code.
            message: Error message.
            details: Additional error details.
        """
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"Motion API Error ({status_code}): {message}")


class MotionAuthenticationError(MotionApiError):
    """Exception raised for authentication failures."""

    pass


class MotionNotFoundError(MotionApiError):
    """Exception raised when a resource is not found."""

    pass


# -----------------------------------------------------------------------------
# Motion API Client
# -----------------------------------------------------------------------------
class MotionClient:
    """
    Async HTTP client for Motion API with rate limiting.

    This client provides methods for all Motion API endpoints and handles
    rate limiting automatically to prevent account suspension.

    Attributes:
        api_key: Motion API key.
        base_url: Base URL for Motion API.
        rate_limiter: Rate limiter instance.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.usemotion.com/v1",
        account_type: AccountType = AccountType.INDIVIDUAL,
        rate_limit_override: int = 0,
        rate_limit_window: int = 60,
        rate_limit_db: str = "motion_rate_limit.db",
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the Motion API client.

        Args:
            api_key: Motion API key for authentication.
            base_url: Base URL for Motion API.
            account_type: Account type for rate limiting.
            rate_limit_override: Override default rate limit (0 = use default).
            rate_limit_window: Rate limit window in seconds.
            rate_limit_db: Path to rate limit SQLite database.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        # Initialize rate limiter
        self.rate_limiter: RateLimiter = create_rate_limiter(
            account_type=account_type,
            override_limit=rate_limit_override,
            window_seconds=rate_limit_window,
            db_path=rate_limit_db,
        )

        logger.info(f"Motion client initialized (base_url={self.base_url})")

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create the async HTTP client.

        Returns:
            The httpx.AsyncClient instance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0, read=self.timeout, write=10.0, pool=10.0
                ),
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        logger.debug("Motion client closed")

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        wait_for_rate_limit: bool = False,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to the Motion API.

        Automatically handles rate limiting before making requests.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            endpoint: API endpoint (without base URL).
            params: Query parameters.
            json: JSON body for POST/PATCH requests.
            wait_for_rate_limit: If True, wait when rate limited.

        Returns:
            JSON response from the API.

        Raises:
            RateLimitExceededError: If rate limit exceeded and wait=False.
            MotionApiError: For API errors.
            MotionAuthenticationError: For authentication failures.
            MotionNotFoundError: For 404 errors.
        """
        # Acquire rate limit slot
        try:
            status = await self.rate_limiter.acquire(wait=wait_for_rate_limit)
            logger.debug(
                f"Rate limit: {status.remaining_requests} requests remaining"
            )
        except RateLimitExceededError:
            logger.warning("Rate limit exceeded")
            raise

        # Make the request
        client = await self._get_client()
        url = f"{self.base_url}{endpoint}"

        logger.debug(f"Motion API {method} {endpoint}")

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
            )

            # Handle errors
            if response.status_code == 401:
                raise MotionAuthenticationError(
                    status_code=401,
                    message="Invalid API key or unauthorized access",
                )

            if response.status_code == 404:
                raise MotionNotFoundError(
                    status_code=404,
                    message=f"Resource not found: {endpoint}",
                )

            if response.status_code == 429:
                # Rate limited by Motion API
                logger.error("Rate limited by Motion API despite local limiter!")
                raise MotionApiError(
                    status_code=429,
                    message="Rate limit exceeded - please wait before retrying",
                )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get(
                    "message", f"API error: {response.status_code}"
                )
                raise MotionApiError(
                    status_code=response.status_code,
                    message=error_msg,
                    details=error_data,
                )

            # Return JSON response
            if response.content:
                return response.json()
            return {}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            raise MotionApiError(
                status_code=e.response.status_code,
                message=str(e),
            )

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise MotionApiError(
                status_code=0,
                message=f"Request failed: {e}",
            )

    # -------------------------------------------------------------------------
    # Task Endpoints
    # -------------------------------------------------------------------------
    async def list_tasks(
        self,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> TaskListResponse:
        """
        List tasks with optional filters.

        Args:
            workspace_id: Filter by workspace ID.
            project_id: Filter by project ID.
            assignee_id: Filter by assignee user ID.
            status: Filter by status name.
            cursor: Pagination cursor.

        Returns:
            TaskListResponse with list of tasks.
        """
        params: dict[str, Any] = {}
        if workspace_id:
            params["workspaceId"] = workspace_id
        if project_id:
            params["projectId"] = project_id
        if assignee_id:
            params["assigneeId"] = assignee_id
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor

        data = await self._request("GET", "/tasks", params=params)

        # Parse response
        tasks = [Task.model_validate(t) for t in data.get("tasks", [])]
        return TaskListResponse(tasks=tasks, meta=data.get("meta"))

    async def get_task(self, task_id: str) -> Task:
        """
        Get a specific task by ID.

        Args:
            task_id: The task ID.

        Returns:
            Task object.
        """
        data = await self._request("GET", f"/tasks/{task_id}")
        return Task.model_validate(data)

    async def create_task(self, task: TaskCreate) -> Task:
        """
        Create a new task.

        Args:
            task: TaskCreate model with task details.

        Returns:
            Created Task object.
        """
        # Build request body, excluding None values
        body = task.model_dump(exclude_none=True)

        data = await self._request("POST", "/tasks", json=body)
        return Task.model_validate(data)

    async def update_task(self, task_id: str, updates: TaskUpdate) -> Task:
        """
        Update an existing task.

        Args:
            task_id: The task ID to update.
            updates: TaskUpdate model with fields to update.

        Returns:
            Updated Task object.
        """
        body = updates.model_dump(exclude_none=True)
        data = await self._request("PATCH", f"/tasks/{task_id}", json=body)
        return Task.model_validate(data)

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: The task ID to delete.

        Returns:
            True if deleted successfully.
        """
        await self._request("DELETE", f"/tasks/{task_id}")
        return True

    async def move_task(
        self,
        task_id: str,
        workspace_id: str,
        project_id: Optional[str] = None,
    ) -> Task:
        """
        Move a task to a different workspace/project.

        Args:
            task_id: The task ID to move.
            workspace_id: Target workspace ID.
            project_id: Target project ID (optional).

        Returns:
            Updated Task object.
        """
        body: dict[str, Any] = {"workspaceId": workspace_id}
        if project_id:
            body["projectId"] = project_id

        data = await self._request("POST", f"/tasks/{task_id}/move", json=body)
        return Task.model_validate(data)

    async def unassign_task(self, task_id: str) -> Task:
        """
        Remove assignee from a task.

        Args:
            task_id: The task ID.

        Returns:
            Updated Task object.
        """
        data = await self._request("POST", f"/tasks/{task_id}/unassign")
        return Task.model_validate(data)

    # -------------------------------------------------------------------------
    # Project Endpoints
    # -------------------------------------------------------------------------
    async def list_projects(
        self,
        workspace_id: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> ProjectListResponse:
        """
        List projects with optional filters.

        Args:
            workspace_id: Filter by workspace ID.
            cursor: Pagination cursor.

        Returns:
            ProjectListResponse with list of projects.
        """
        params: dict[str, Any] = {}
        if workspace_id:
            params["workspaceId"] = workspace_id
        if cursor:
            params["cursor"] = cursor

        data = await self._request("GET", "/projects", params=params)

        projects = [Project.model_validate(p) for p in data.get("projects", [])]
        return ProjectListResponse(projects=projects, meta=data.get("meta"))

    async def get_project(self, project_id: str) -> Project:
        """
        Get a specific project by ID.

        Args:
            project_id: The project ID.

        Returns:
            Project object.
        """
        data = await self._request("GET", f"/projects/{project_id}")
        return Project.model_validate(data)

    async def create_project(self, project: ProjectCreate) -> Project:
        """
        Create a new project.

        Args:
            project: ProjectCreate model with project details.

        Returns:
            Created Project object.
        """
        body = project.model_dump(exclude_none=True)
        data = await self._request("POST", "/projects", json=body)
        return Project.model_validate(data)

    # -------------------------------------------------------------------------
    # Workspace Endpoints
    # -------------------------------------------------------------------------
    async def list_workspaces(self) -> WorkspaceListResponse:
        """
        List all accessible workspaces.

        Returns:
            WorkspaceListResponse with list of workspaces.
        """
        data = await self._request("GET", "/workspaces")

        workspaces = [Workspace.model_validate(w) for w in data.get("workspaces", [])]
        return WorkspaceListResponse(workspaces=workspaces, meta=data.get("meta"))

    # -------------------------------------------------------------------------
    # User Endpoints
    # -------------------------------------------------------------------------
    async def list_users(
        self,
        workspace_id: Optional[str] = None,
    ) -> UserListResponse:
        """
        List users in a workspace.

        Args:
            workspace_id: Workspace ID to list users from.

        Returns:
            UserListResponse with list of users.
        """
        params: dict[str, Any] = {}
        if workspace_id:
            params["workspaceId"] = workspace_id

        data = await self._request("GET", "/users", params=params)

        users = [User.model_validate(u) for u in data.get("users", [])]
        return UserListResponse(users=users, meta=data.get("meta"))

    async def get_current_user(self) -> User:
        """
        Get the current authenticated user.

        Returns:
            User object for the current user.
        """
        data = await self._request("GET", "/users/me")
        return User.model_validate(data)

    # -------------------------------------------------------------------------
    # Rate Limiter Access
    # -------------------------------------------------------------------------
    async def get_rate_limit_status(self) -> dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Dictionary with rate limit statistics.
        """
        return await self.rate_limiter.get_stats()
