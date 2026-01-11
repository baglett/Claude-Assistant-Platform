# =============================================================================
# GitHub Agent
# =============================================================================
"""
Specialized agent for GitHub repository management.

The GitHubAgent handles all GitHub-related operations including managing issues,
pull requests, branches, and repository information. It communicates with the
GitHub MCP server via HTTP.

Usage:
    from src.agents.github_agent import GitHubAgent

    agent = GitHubAgent(
        api_key=api_key,
        mcp_url="http://github-mcp:8083"
    )
    result = await agent.execute(context)
"""

import json
import logging
import time
from typing import Any

import anthropic
import httpx

from src.agents.base import AgentContext, AgentResult, BaseAgent
from src.database import AgentExecution
from src.services.agent_execution_service import AgentExecutionService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# GitHub Agent System Prompt
# -----------------------------------------------------------------------------
GITHUB_AGENT_SYSTEM_PROMPT = """You are the GitHub Agent for the Claude Assistant Platform.

Your responsibility is managing GitHub repositories - issues, pull requests, branches, and code.

## Smart Repository Resolution

**You don't always need to specify the owner!** The system can automatically resolve repositories:

1. **Just use the repo name**: `repo="Claude-Assistant-Platform"` - the system will find it
2. **Or use full path**: `repo="baglett/Claude-Assistant-Platform"` - also works
3. **Owner is optional**: Only specify `owner` when there might be ambiguity

### How Resolution Works:
- The system caches your accessible repositories (owned + member access)
- When you provide just a repo name, it searches your accessible repos
- If exactly one match is found, it uses that
- If multiple matches exist, you'll get an error asking for clarification

### Recommended First Steps:
1. Call `github_get_authenticated_user` - this caches your username
2. Call `github_list_my_repositories` - this caches your accessible repos
3. Use `github_find_repository` if you need to confirm a repo path

## Available Tools:

### Repository Discovery (NEW)
- **github_find_repository**: Find a repo by name and get its full path
- **github_list_my_repositories**: List all your accessible repos (cached)
- **github_get_authenticated_user**: Get your GitHub user info (use first!)

### Issues
- **github_list_issues**: List issues (just need repo name!)
- **github_get_issue**: Get a specific issue by number
- **github_create_issue**: Create a new issue
- **github_update_issue**: Update an existing issue
- **github_add_issue_comment**: Add a comment to an issue
- **github_list_issue_comments**: List comments on an issue

### Pull Requests
- **github_list_pull_requests**: List PRs with filters
- **github_get_pull_request**: Get a specific PR by number
- **github_create_pull_request**: Create a new pull request
- **github_update_pull_request**: Update an existing PR
- **github_merge_pull_request**: Merge a PR (merge, squash, or rebase)
- **github_list_pr_files**: List files changed in a PR
- **github_add_pr_comment**: Add a comment to a PR
- **github_create_pr_review**: Create a review (approve, request changes, comment)

### Branches
- **github_list_branches**: List all branches in a repository
- **github_get_branch**: Get details about a specific branch
- **github_create_branch**: Create a new branch from another branch
- **github_delete_branch**: Delete a branch (use with caution!)
- **github_get_default_branch**: Get the default branch name

### Repository
- **github_get_repository**: Get repository information
- **github_list_repositories**: List repositories for a specific user
- **github_get_file_content**: Get file content from a repository
- **github_list_labels**: List all labels in a repository

### Utility
- **github_check_rate_limit**: Check API rate limit status

## Important Notes:

1. **Owner is Optional**: Most tools accept just `repo` - owner will be resolved automatically
   - Example: `github_list_branches(repo="Claude-Assistant-Platform")`
   - The system finds it's at "baglett/Claude-Assistant-Platform"

2. **Repo Formats Accepted**:
   - Just name: `repo="my-repo"` (auto-resolved)
   - Full path: `repo="owner/my-repo"` (uses owner from path)
   - Explicit: `repo="my-repo", owner="someone"` (uses provided owner)

3. **Merge Methods**: `merge`, `squash`, or `rebase`

4. **Review Events**: `APPROVE`, `REQUEST_CHANGES`, or `COMMENT`

5. **Rate Limits**: GitHub has API rate limits. Use check_rate_limit to monitor.

## Common Workflows:

### Working with the User's Repos:
1. github_get_authenticated_user (establishes identity)
2. github_list_my_repositories (see all accessible repos)
3. Then use any tool with just the repo name

### Find and Work with a Repo:
1. github_find_repository(repo="Claude-Assistant-Platform")
2. Response includes full path and owner for reference
3. Continue with other tools using just the repo name

### Review a PR:
1. github_get_pull_request(repo="my-repo", pr_number=123)
2. github_list_pr_files(repo="my-repo", pr_number=123)
3. github_create_pr_review(repo="my-repo", pr_number=123, event="APPROVE")"""


# -----------------------------------------------------------------------------
# GitHub Agent Tool Definitions
# -----------------------------------------------------------------------------
GITHUB_TOOLS = [
    # Repository Discovery Tools (NEW)
    {
        "name": "github_find_repository",
        "description": "Find and resolve a repository by name. Returns the full owner/repo path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (e.g., 'my-repo' or 'owner/my-repo').",
                },
            },
            "required": ["repo"],
        },
    },
    {
        "name": "github_list_my_repositories",
        "description": "List all repositories accessible to the authenticated user (owned + member).",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["all", "owner", "member"],
                    "description": "Filter: 'all' (default), 'owner' (your repos), 'member' (org repos).",
                },
                "refresh": {
                    "type": "boolean",
                    "description": "Force refresh from GitHub API. Default: false (uses cache).",
                },
            },
            "required": [],
        },
    },
    # Issue Tools
    {
        "name": "github_list_issues",
        "description": "List issues in a GitHub repository with optional filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (e.g., 'my-repo' or 'owner/my-repo'). Owner auto-resolved.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional - auto-resolved if not provided).",
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by state. Default: open.",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated label names to filter by.",
                },
                "assignee": {
                    "type": "string",
                    "description": "Filter by assignee username.",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page (max 100). Default: 30.",
                },
            },
            "required": ["repo"],
        },
    },
    {
        "name": "github_get_issue",
        "description": "Get a specific issue by number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo", "issue_number"],
        },
    },
    {
        "name": "github_create_issue",
        "description": "Create a new issue in a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "title": {
                    "type": "string",
                    "description": "Issue title.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "body": {
                    "type": "string",
                    "description": "Issue body in Markdown.",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated label names to add.",
                },
                "assignees": {
                    "type": "string",
                    "description": "Comma-separated usernames to assign.",
                },
            },
            "required": ["repo", "title"],
        },
    },
    {
        "name": "github_update_issue",
        "description": "Update an existing issue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "title": {
                    "type": "string",
                    "description": "New title.",
                },
                "body": {
                    "type": "string",
                    "description": "New body.",
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed"],
                    "description": "New state.",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated labels (replaces existing).",
                },
                "assignees": {
                    "type": "string",
                    "description": "Comma-separated assignees (replaces existing).",
                },
            },
            "required": ["repo", "issue_number"],
        },
    },
    {
        "name": "github_add_issue_comment",
        "description": "Add a comment to an issue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number.",
                },
                "body": {
                    "type": "string",
                    "description": "Comment body in Markdown.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo", "issue_number", "body"],
        },
    },
    {
        "name": "github_list_issue_comments",
        "description": "List comments on an issue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page. Default: 30.",
                },
            },
            "required": ["repo", "issue_number"],
        },
    },
    # Pull Request Tools
    {
        "name": "github_list_pull_requests",
        "description": "List pull requests in a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by state. Default: open.",
                },
                "head": {
                    "type": "string",
                    "description": "Filter by head branch (user:branch format).",
                },
                "base": {
                    "type": "string",
                    "description": "Filter by base branch name.",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page. Default: 30.",
                },
            },
            "required": ["repo"],
        },
    },
    {
        "name": "github_get_pull_request",
        "description": "Get a specific pull request by number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "Pull request number.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo", "pr_number"],
        },
    },
    {
        "name": "github_create_pull_request",
        "description": "Create a new pull request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "title": {
                    "type": "string",
                    "description": "PR title.",
                },
                "head": {
                    "type": "string",
                    "description": "Branch with your changes.",
                },
                "base": {
                    "type": "string",
                    "description": "Branch to merge into.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "body": {
                    "type": "string",
                    "description": "PR description in Markdown.",
                },
                "draft": {
                    "type": "boolean",
                    "description": "Create as draft PR. Default: false.",
                },
            },
            "required": ["repo", "title", "head", "base"],
        },
    },
    {
        "name": "github_update_pull_request",
        "description": "Update an existing pull request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "PR number.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "title": {
                    "type": "string",
                    "description": "New title.",
                },
                "body": {
                    "type": "string",
                    "description": "New body.",
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed"],
                    "description": "New state.",
                },
                "base": {
                    "type": "string",
                    "description": "New target branch.",
                },
            },
            "required": ["repo", "pr_number"],
        },
    },
    {
        "name": "github_merge_pull_request",
        "description": "Merge a pull request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "PR number.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "merge_method": {
                    "type": "string",
                    "enum": ["merge", "squash", "rebase"],
                    "description": "Merge method. Default: merge.",
                },
                "commit_title": {
                    "type": "string",
                    "description": "Custom merge commit title.",
                },
                "commit_message": {
                    "type": "string",
                    "description": "Custom merge commit message.",
                },
            },
            "required": ["repo", "pr_number"],
        },
    },
    {
        "name": "github_list_pr_files",
        "description": "List files changed in a pull request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "PR number.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page. Default: 30.",
                },
            },
            "required": ["repo", "pr_number"],
        },
    },
    {
        "name": "github_add_pr_comment",
        "description": "Add a comment to a pull request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "PR number.",
                },
                "body": {
                    "type": "string",
                    "description": "Comment body in Markdown.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo", "pr_number", "body"],
        },
    },
    {
        "name": "github_create_pr_review",
        "description": "Create a review on a pull request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "pr_number": {
                    "type": "integer",
                    "description": "PR number.",
                },
                "event": {
                    "type": "string",
                    "enum": ["APPROVE", "REQUEST_CHANGES", "COMMENT"],
                    "description": "Review action.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "body": {
                    "type": "string",
                    "description": "Review body in Markdown.",
                },
            },
            "required": ["repo", "pr_number", "event"],
        },
    },
    # Branch Tools
    {
        "name": "github_list_branches",
        "description": "List branches in a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page. Default: 30.",
                },
            },
            "required": ["repo"],
        },
    },
    {
        "name": "github_get_branch",
        "description": "Get details about a specific branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo", "branch"],
        },
    },
    {
        "name": "github_create_branch",
        "description": "Create a new branch from another branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "branch_name": {
                    "type": "string",
                    "description": "Name for the new branch.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "source_branch": {
                    "type": "string",
                    "description": "Branch to create from. Default: default branch.",
                },
            },
            "required": ["repo", "branch_name"],
        },
    },
    {
        "name": "github_delete_branch",
        "description": "Delete a branch. WARNING: Cannot be undone!",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name to delete.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo", "branch"],
        },
    },
    {
        "name": "github_get_default_branch",
        "description": "Get the default branch name for a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo"],
        },
    },
    # Repository Tools
    {
        "name": "github_get_repository",
        "description": "Get repository information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo"],
        },
    },
    {
        "name": "github_list_repositories",
        "description": "List repositories for a user or the authenticated user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Username. If omitted, lists authenticated user's repos.",
                },
                "type": {
                    "type": "string",
                    "enum": ["all", "owner", "member"],
                    "description": "Filter type. Default: all.",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page. Default: 30.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "github_get_file_content",
        "description": "Get file content from a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "path": {
                    "type": "string",
                    "description": "File path within the repository.",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
                "ref": {
                    "type": "string",
                    "description": "Branch, tag, or SHA. Default: default branch.",
                },
            },
            "required": ["repo", "path"],
        },
    },
    {
        "name": "github_list_labels",
        "description": "List all labels in a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (owner auto-resolved).",
                },
                "owner": {
                    "type": "string",
                    "description": "Repository owner (optional).",
                },
            },
            "required": ["repo"],
        },
    },
    # Utility Tools
    {
        "name": "github_get_authenticated_user",
        "description": "Get information about the authenticated user.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "github_check_rate_limit",
        "description": "Check GitHub API rate limit status.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# -----------------------------------------------------------------------------
# GitHub Agent Class
# -----------------------------------------------------------------------------
class GitHubAgent(BaseAgent):
    """
    Specialized agent for GitHub repository management.

    Handles issues, pull requests, branches, and repository operations
    by communicating with the GitHub MCP server via HTTP.

    Attributes:
        name: Agent identifier ("github").
        description: Human-readable description.
        mcp_url: URL of the GitHub MCP server.
        client: Anthropic client for Claude API calls.
        model: Claude model to use.
    """

    def __init__(
        self,
        api_key: str,
        mcp_url: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """
        Initialize the GitHub agent.

        Args:
            api_key: Anthropic API key.
            mcp_url: URL of the GitHub MCP server.
            model: Claude model to use.
        """
        super().__init__()
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.mcp_url = mcp_url.rstrip("/")
        self._http_client: httpx.AsyncClient | None = None

        # Token tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

        logger.info(f"GitHubAgent initialized with MCP URL: {self.mcp_url}")

    @property
    def name(self) -> str:
        """Return the agent name."""
        return "github"

    @property
    def description(self) -> str:
        """Return the agent description."""
        return "Manages GitHub repositories - issues, pull requests, branches, and code"

    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create the HTTP client for MCP communication.

        Returns:
            Async HTTP client instance.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=60.0,
                headers={"Content-Type": "application/json"},
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def _execute_task(
        self,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> AgentResult:
        """
        Execute a GitHub task.

        Args:
            context: Agent context with task details.
            execution_service: Service for logging execution.
            execution: Current execution record.

        Returns:
            AgentResult with task outcome.
        """
        logger.info(f"GitHubAgent executing task: {context.task}")

        # Reset token counters
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

        # Build messages
        messages = [{"role": "user", "content": context.task}]

        # Add context from metadata if available
        if context.metadata:
            context_info = []
            if context.metadata.get("owner"):
                context_info.append(f"Repository owner: {context.metadata['owner']}")
            if context.metadata.get("repo"):
                context_info.append(f"Repository: {context.metadata['repo']}")
            if context_info:
                messages[0]["content"] = (
                    f"Context:\n" + "\n".join(context_info) + f"\n\nTask: {context.task}"
                )

        try:
            response_text = await self._process_with_tools(
                messages=messages,
                context=context,
                execution_service=execution_service,
                execution=execution,
            )

            return AgentResult(
                success=True,
                message=response_text,
                data={
                    "input_tokens": self._total_input_tokens,
                    "output_tokens": self._total_output_tokens,
                },
            )

        except Exception as e:
            logger.error(f"GitHubAgent task failed: {e}")
            return AgentResult(
                success=False,
                message=f"GitHub task failed: {str(e)}",
                error=str(e),
            )

    async def _process_with_tools(
        self,
        messages: list[dict[str, Any]],
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
        max_iterations: int = 15,
    ) -> str:
        """
        Process task with tool calling loop.

        Args:
            messages: Conversation messages.
            context: Agent context.
            execution_service: Execution logging service.
            execution: Current execution.
            max_iterations: Maximum tool call iterations.

        Returns:
            Final response text.
        """
        for iteration in range(max_iterations):
            logger.debug(f"GitHubAgent iteration {iteration + 1}/{max_iterations}")

            # Call Claude with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=GITHUB_AGENT_SYSTEM_PROMPT,
                tools=GITHUB_TOOLS,
                messages=messages,
            )

            # Track tokens and LLM calls
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._llm_calls += 1

            # Check stop reason
            if response.stop_reason == "end_turn":
                return self._extract_text(response)

            if response.stop_reason == "tool_use":
                # Add assistant message with tool calls
                messages.append({"role": "assistant", "content": response.content})

                # Execute tools and get results
                tool_results = await self._execute_tool_calls(
                    response.content,
                    context,
                    execution_service,
                    execution,
                )

                # Add tool results
                messages.append({"role": "user", "content": tool_results})

            else:
                # Unexpected stop reason
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                return self._extract_text(response)

        # Max iterations reached
        return self._extract_text(response)

    async def _execute_tool_calls(
        self,
        content: list[Any],
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> list[dict[str, Any]]:
        """
        Execute tool calls from Claude's response.

        Args:
            content: Response content blocks.
            context: Agent context.
            execution_service: Execution logging service.
            execution: Current execution.

        Returns:
            List of tool result blocks.
        """
        tool_results = []

        for block in content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            logger.info(f"GitHubAgent calling tool: {tool_name}")

            start_time = time.time()

            try:
                # Call the GitHub MCP
                result = await self._call_github_mcp(tool_name, tool_input)

                duration_ms = int((time.time() - start_time) * 1000)

                # Log the tool call
                await self.log_tool_call(
                    execution_service,
                    execution,
                    tool_name=tool_name,
                    input_data=tool_input,
                    output_data=result,
                    duration_ms=duration_ms,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")

                duration_ms = int((time.time() - start_time) * 1000)

                await self.log_tool_call(
                    execution_service,
                    execution,
                    tool_name=tool_name,
                    input_data=tool_input,
                    error=str(e),
                    duration_ms=duration_ms,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"success": False, "error": str(e)}),
                    "is_error": True,
                })

        return tool_results

    async def _call_github_mcp(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a GitHub MCP tool via HTTP.

        The GitHub MCP exposes tools via POST /tools/{tool_name} endpoints.

        Args:
            tool_name: Name of the GitHub tool to call.
            tool_input: Tool input parameters.

        Returns:
            Tool execution result from MCP server.
        """
        client = await self._get_http_client()

        try:
            # All tools use POST to /tools/{tool_name}
            response = await client.post(
                f"{self.mcp_url}/tools/{tool_name}",
                json=tool_input,
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub MCP HTTP error: {e.response.status_code}")
            error_detail = ""
            try:
                error_detail = e.response.text
            except Exception:
                pass
            return {
                "success": False,
                "error": f"GitHub MCP error: {e.response.status_code}",
                "detail": error_detail,
            }

        except httpx.RequestError as e:
            logger.error(f"GitHub MCP request error: {e}")
            return {
                "success": False,
                "error": f"Failed to connect to GitHub MCP: {e}",
            }

    def _extract_text(self, response) -> str:
        """Extract text from Claude response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts)
