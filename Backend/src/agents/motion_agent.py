# =============================================================================
# Motion Agent
# =============================================================================
"""
Specialized agent for Motion task and project management.

The MotionAgent handles all Motion-related operations including creating,
listing, updating, and managing tasks and projects in Motion. It communicates
with the Motion MCP server via HTTP.

IMPORTANT: Motion has strict rate limits (12 req/min for individual accounts).
The Motion MCP server handles rate limiting to prevent account suspension.

Usage:
    from src.agents.motion_agent import MotionAgent

    agent = MotionAgent(api_key=api_key, mcp_url="http://motion-mcp:8081")
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
# Motion Agent System Prompt
# -----------------------------------------------------------------------------
MOTION_AGENT_SYSTEM_PROMPT = """You are the Motion Agent for the Claude Assistant Platform.

Your responsibility is managing tasks and projects in Motion, an AI-powered calendar and task management app.

## Available Tools:

### Task Management
- **motion_list_tasks**: List tasks with optional filters (workspace, project, assignee, status)
- **motion_get_task**: Get details of a specific task by ID
- **motion_create_task**: Create a new task with name, due date, priority, etc.
- **motion_update_task**: Update an existing task
- **motion_delete_task**: Permanently delete a task
- **motion_move_task**: Move a task to a different workspace/project
- **motion_unassign_task**: Remove the assignee from a task

### Project Management
- **motion_list_projects**: List projects in Motion
- **motion_get_project**: Get details of a specific project
- **motion_create_project**: Create a new project

### Workspace & Users
- **motion_list_workspaces**: List available workspaces
- **motion_list_users**: List users in a workspace
- **motion_get_current_user**: Get info about the authenticated user

### Utilities
- **motion_get_rate_limit_status**: Check remaining API calls (important before batch ops)

## Priority Levels (for tasks):
- **ASAP** = Critical, do immediately
- **HIGH** = Important, do soon
- **MEDIUM** = Normal priority (default)
- **LOW** = Can wait

## Important Notes:
1. Motion auto-schedules tasks based on due date and duration
2. Always check rate limit status before batch operations
3. Tasks require a workspace_id - list workspaces first if needed
4. Be concise and confirm actions taken

## Workflow Tips:
- To create a task: First list workspaces to get workspace_id
- To assign a task: First list users to get assignee_id
- For batch operations: Check rate_limit_status first"""


# -----------------------------------------------------------------------------
# Motion Agent Tool Definitions
# -----------------------------------------------------------------------------
MOTION_TOOLS = [
    # Task Management Tools
    {
        "name": "motion_list_tasks",
        "description": "List tasks from Motion with optional filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "description": "Filter by workspace ID.",
                },
                "project_id": {
                    "type": "string",
                    "description": "Filter by project ID.",
                },
                "assignee_id": {
                    "type": "string",
                    "description": "Filter by assignee user ID.",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (e.g., 'To Do', 'In Progress', 'Done').",
                },
            },
            "required": [],
        },
    },
    {
        "name": "motion_get_task",
        "description": "Get a specific task by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The unique task identifier.",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "motion_create_task",
        "description": "Create a new task in Motion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Task name/title.",
                },
                "workspace_id": {
                    "type": "string",
                    "description": "Workspace ID to create task in.",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in ISO 8601 format (e.g., 2024-12-31T17:00:00Z).",
                },
                "duration": {
                    "type": "integer",
                    "description": "Duration in minutes.",
                },
                "project_id": {
                    "type": "string",
                    "description": "Project ID to add task to.",
                },
                "description": {
                    "type": "string",
                    "description": "Task description (Markdown supported).",
                },
                "priority": {
                    "type": "string",
                    "enum": ["ASAP", "HIGH", "MEDIUM", "LOW"],
                    "description": "Priority level.",
                },
                "assignee_id": {
                    "type": "string",
                    "description": "User ID to assign task to.",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of label names.",
                },
            },
            "required": ["name", "workspace_id"],
        },
    },
    {
        "name": "motion_update_task",
        "description": "Update an existing task. Only provided fields are updated.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to update.",
                },
                "name": {"type": "string", "description": "New task name."},
                "due_date": {"type": "string", "description": "New due date (ISO 8601)."},
                "duration": {"type": "integer", "description": "New duration in minutes."},
                "project_id": {"type": "string", "description": "New project ID."},
                "description": {"type": "string", "description": "New description."},
                "priority": {
                    "type": "string",
                    "enum": ["ASAP", "HIGH", "MEDIUM", "LOW"],
                    "description": "New priority.",
                },
                "status": {"type": "string", "description": "New status name."},
                "assignee_id": {"type": "string", "description": "New assignee user ID."},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New labels (replaces existing).",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "motion_delete_task",
        "description": "Permanently delete a task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to delete.",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "motion_move_task",
        "description": "Move a task to a different workspace or project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to move.",
                },
                "workspace_id": {
                    "type": "string",
                    "description": "Target workspace ID.",
                },
                "project_id": {
                    "type": "string",
                    "description": "Target project ID (optional).",
                },
            },
            "required": ["task_id", "workspace_id"],
        },
    },
    {
        "name": "motion_unassign_task",
        "description": "Remove the assignee from a task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to unassign.",
                },
            },
            "required": ["task_id"],
        },
    },
    # Project Management Tools
    {
        "name": "motion_list_projects",
        "description": "List projects from Motion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "description": "Filter by workspace ID.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "motion_get_project",
        "description": "Get a specific project by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID.",
                },
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "motion_create_project",
        "description": "Create a new project in Motion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name.",
                },
                "workspace_id": {
                    "type": "string",
                    "description": "Workspace ID to create project in.",
                },
                "description": {
                    "type": "string",
                    "description": "Project description.",
                },
                "status": {
                    "type": "string",
                    "description": "Initial status name.",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label names.",
                },
            },
            "required": ["name", "workspace_id"],
        },
    },
    # Workspace & User Tools
    {
        "name": "motion_list_workspaces",
        "description": "List all accessible workspaces.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "motion_list_users",
        "description": "List users in a workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "description": "Workspace ID to list users from.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "motion_get_current_user",
        "description": "Get the current authenticated user.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # Utility Tools
    {
        "name": "motion_get_rate_limit_status",
        "description": "Check rate limit status. Use before batch operations.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# -----------------------------------------------------------------------------
# Motion Agent Class
# -----------------------------------------------------------------------------
class MotionAgent(BaseAgent):
    """
    Specialized agent for Motion task and project management.

    Communicates with the Motion MCP server via HTTP to manage tasks,
    projects, workspaces, and users in Motion.

    Attributes:
        client: Anthropic API client.
        model: Claude model to use.
        mcp_url: URL of the Motion MCP server.
        http_client: Async HTTP client for MCP calls.

    Example:
        agent = MotionAgent(
            api_key="sk-...",
            mcp_url="http://motion-mcp:8081"
        )
        context = AgentContext(
            chat_id=chat_uuid,
            task="Create a task to review the quarterly report",
            session=session,
        )
        result = await agent.execute(context)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        mcp_url: str = "http://motion-mcp:8081",
    ):
        """
        Initialize the Motion Agent.

        Args:
            api_key: Anthropic API key.
            model: Claude model to use.
            mcp_url: URL of the Motion MCP server.
        """
        super().__init__(api_key=api_key, model=model)
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.mcp_url = mcp_url.rstrip("/")
        self._http_client: httpx.AsyncClient | None = None

        # Token tracking for execution logging
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

    @property
    def name(self) -> str:
        """Agent identifier."""
        return "motion"

    @property
    def description(self) -> str:
        """Agent description."""
        return "Manages tasks and projects in Motion (AI calendar/task manager)"

    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create the async HTTP client for MCP calls.

        Returns:
            The httpx.AsyncClient instance.
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def _execute_task(
        self,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> AgentResult:
        """
        Execute the Motion management task.

        Uses Claude's tool calling to determine and execute the appropriate
        Motion operations based on the task description.

        Args:
            context: Execution context with task and chat info.
            execution_service: Service for logging execution details.
            execution: Current execution record.

        Returns:
            AgentResult with the outcome.
        """
        if not self.client:
            return AgentResult(
                success=False,
                message="API client not initialized",
                error="No API key provided",
            )

        # Reset token counters
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

        # Build messages for Claude
        messages = self._build_messages(context)

        # Log initial thinking
        await self.log_thinking(
            execution_service,
            execution,
            f"Processing Motion task: {context.task}\n"
            f"MCP URL: {self.mcp_url}",
        )

        # Process with tool calling loop
        try:
            result_text = await self._process_with_tools(
                messages=messages,
                context=context,
                execution_service=execution_service,
                execution=execution,
            )

            return AgentResult(
                success=True,
                message=result_text,
            )

        except Exception as e:
            logger.error(f"MotionAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                message=f"Failed to process Motion request: {str(e)}",
                error=str(e),
            )

    def _build_messages(self, context: AgentContext) -> list[dict[str, Any]]:
        """
        Build the message list for Claude.

        Includes recent conversation context and the current task.

        Args:
            context: The agent context.

        Returns:
            List of messages in Claude format.
        """
        messages = []

        # Add recent conversation context
        for msg in context.recent_messages:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add the current task as the final user message
        messages.append({
            "role": "user",
            "content": context.task,
        })

        return messages

    async def _process_with_tools(
        self,
        messages: list[dict[str, Any]],
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
        max_iterations: int = 10,
    ) -> str:
        """
        Process the task with tool calling loop.

        Args:
            messages: Conversation messages.
            context: Agent context.
            execution_service: For logging.
            execution: Current execution.
            max_iterations: Max tool call iterations.

        Returns:
            Final response text.
        """
        working_messages = list(messages)

        for iteration in range(max_iterations):
            logger.debug(f"MotionAgent tool loop iteration {iteration + 1}")

            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=MOTION_AGENT_SYSTEM_PROMPT,
                tools=MOTION_TOOLS,
                messages=working_messages,
            )

            # Track tokens
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._llm_calls += 1

            # Check stop reason
            if response.stop_reason == "end_turn":
                return self._extract_text(response)

            elif response.stop_reason == "tool_use":
                # Process tool calls
                await self.log_thinking(
                    execution_service,
                    execution,
                    f"Iteration {iteration + 1}: Processing Motion tool calls",
                )

                # Add assistant response to messages
                working_messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Execute tools and get results
                tool_results = await self._execute_tools(
                    response.content,
                    context,
                    execution_service,
                    execution,
                )

                # Add tool results to messages
                working_messages.append({
                    "role": "user",
                    "content": tool_results,
                })

            else:
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                return self._extract_text(response)

        return "Max iterations reached. Please try a simpler request."

    async def _execute_tools(
        self,
        content_blocks: list,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> list[dict[str, Any]]:
        """
        Execute tool calls from Claude's response.

        Args:
            content_blocks: Response content blocks.
            context: Agent context.
            execution_service: For logging.
            execution: Current execution.

        Returns:
            List of tool result blocks.
        """
        tool_results = []

        for block in content_blocks:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            logger.info(f"MotionAgent executing tool: {tool_name}")
            start_time = time.time()

            try:
                # Execute the tool via Motion MCP
                result = await self._call_motion_mcp(tool_name, tool_input)

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

    async def _call_motion_mcp(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a Motion MCP tool via HTTP.

        The Motion MCP server handles rate limiting and API communication.

        Args:
            tool_name: Name of the Motion tool to call.
            tool_input: Tool input parameters.

        Returns:
            Tool execution result from MCP server.
        """
        client = await self._get_http_client()

        # The MCP server exposes tools at specific endpoints
        # For simplicity, we'll call the FastMCP tool endpoint
        # In practice, MCP tools are typically called via the MCP protocol
        # For HTTP-based access, we'll use a simple POST endpoint pattern

        # Build the request URL - call the tool via a generic endpoint
        # The Motion MCP server is a FastMCP server with HTTP endpoints
        url = f"{self.mcp_url}/tools/{tool_name}"

        try:
            response = await client.post(
                url,
                json=tool_input,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 404:
                # Try alternate endpoint pattern
                # Some MCP servers use a single /call endpoint
                alt_url = f"{self.mcp_url}/call"
                response = await client.post(
                    alt_url,
                    json={"tool": tool_name, "arguments": tool_input},
                    headers={"Content-Type": "application/json"},
                )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"MCP HTTP error: {e.response.status_code}")
            return {
                "success": False,
                "error": f"MCP server error: {e.response.status_code}",
            }

        except httpx.RequestError as e:
            logger.error(f"MCP request error: {e}")
            return {
                "success": False,
                "error": f"Failed to connect to Motion MCP: {e}",
            }

    def _extract_text(self, response) -> str:
        """Extract text from Claude response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts)
