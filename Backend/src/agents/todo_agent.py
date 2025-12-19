# =============================================================================
# Todo Agent
# =============================================================================
"""
Specialized agent for todo/task management.

The TodoAgent handles all todo-related operations including creating,
listing, updating, and executing todos. It uses Claude's tool calling
to determine which operations to perform based on the task.

Usage:
    from src.agents.todo_agent import TodoAgent

    agent = TodoAgent(api_key=api_key)
    result = await agent.execute(context)
"""

import json
import logging
import time
from typing import Any, Optional
from uuid import UUID

import anthropic

from src.agents.base import AgentContext, AgentResult, BaseAgent
from src.database import AgentExecution
from src.models.todo import (
    AgentType,
    TodoCreate,
    TodoPriority,
    TodoStatus,
    TodoUpdate,
)
from src.services.agent_execution_service import AgentExecutionService
from src.services.todo_service import TodoService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Todo Agent System Prompt
# -----------------------------------------------------------------------------
TODO_AGENT_SYSTEM_PROMPT = """You are the Todo Agent for the Claude Assistant Platform.

Your sole responsibility is managing todos and tasks. You have access to tools for:
- Creating new todos
- Listing existing todos
- Getting todo details
- Updating todos (title, description, priority, status, assigned agent)
- Deleting todos
- Getting todo statistics

## When to Use Each Tool:

**create_todo**: When the user wants to add a new task, reminder, or todo item.
**list_todos**: When the user asks to see their tasks, pending items, or todo list.
**get_todo**: When you need full details about a specific todo (by ID).
**update_todo**: When the user wants to modify a task (change priority, mark complete, etc).
**delete_todo**: When the user wants to permanently remove a task.
**get_todo_stats**: When the user asks for an overview or summary of their tasks.

## Agent Assignment:

When creating todos, assign them to the appropriate agent:
- **github**: Code, repositories, PRs, issues
- **email**: Email drafting, sending, inbox
- **calendar**: Scheduling, events, meetings
- **obsidian**: Notes, documentation, knowledge
- **orchestrator**: General tasks, or when unsure

## Priority Levels:
- 1 = Critical (urgent, do immediately)
- 2 = High (important, do soon)
- 3 = Normal (default)
- 4 = Low (can wait)
- 5 = Lowest (backlog)

Be concise and helpful. Always confirm actions taken."""


# -----------------------------------------------------------------------------
# Todo Agent Tool Definitions
# -----------------------------------------------------------------------------
TODO_TOOLS = [
    {
        "name": "create_todo",
        "description": "Create a new todo/task item.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short, descriptive title for the todo.",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the task.",
                },
                "assigned_agent": {
                    "type": "string",
                    "enum": ["github", "email", "calendar", "obsidian", "orchestrator"],
                    "description": "Which agent should handle this task.",
                },
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Priority: 1=critical, 2=high, 3=normal, 4=low, 5=lowest.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional structured data for the task.",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_todos",
        "description": "List existing todos with optional filtering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "failed", "cancelled"],
                    "description": "Filter by status.",
                },
                "assigned_agent": {
                    "type": "string",
                    "enum": ["github", "email", "calendar", "obsidian", "orchestrator"],
                    "description": "Filter by assigned agent.",
                },
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Filter by priority level.",
                },
                "include_completed": {
                    "type": "boolean",
                    "description": "Include completed/failed/cancelled todos.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of todos to return.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_todo",
        "description": "Get details of a specific todo by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "description": "The UUID of the todo.",
                },
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "update_todo",
        "description": "Update an existing todo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "description": "The UUID of the todo to update.",
                },
                "title": {"type": "string", "description": "New title."},
                "description": {"type": "string", "description": "New description."},
                "assigned_agent": {
                    "type": "string",
                    "enum": ["github", "email", "calendar", "obsidian", "orchestrator"],
                },
                "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "failed", "cancelled"],
                },
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "delete_todo",
        "description": "Permanently delete a todo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "description": "The UUID of the todo to delete.",
                },
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "get_todo_stats",
        "description": "Get aggregated statistics about todos.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# -----------------------------------------------------------------------------
# Todo Agent Class
# -----------------------------------------------------------------------------
class TodoAgent(BaseAgent):
    """
    Specialized agent for todo/task management.

    Handles all todo operations via Claude's tool calling. Extends BaseAgent
    to get automatic execution logging and error handling.

    Attributes:
        client: Anthropic API client.
        model: Claude model to use.

    Example:
        agent = TodoAgent(api_key="sk-...")
        context = AgentContext(
            chat_id=chat_uuid,
            task="Create a todo to review PR #123",
            session=session,
        )
        result = await agent.execute(context)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the Todo Agent.

        Args:
            api_key: Anthropic API key.
            model: Claude model to use.
        """
        super().__init__(api_key=api_key, model=model)
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

        # Token tracking for execution logging
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

    @property
    def name(self) -> str:
        """Agent identifier."""
        return "todo"

    @property
    def description(self) -> str:
        """Agent description."""
        return "Manages todo items and task tracking"

    async def _execute_task(
        self,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> AgentResult:
        """
        Execute the todo management task.

        Uses Claude's tool calling to determine and execute the appropriate
        todo operations based on the task description.

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
            f"Processing task: {context.task}\n"
            f"Chat context: {len(context.recent_messages)} recent messages",
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
            logger.error(f"TodoAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                message=f"Failed to process todo request: {str(e)}",
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
            logger.debug(f"TodoAgent tool loop iteration {iteration + 1}")

            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=TODO_AGENT_SYSTEM_PROMPT,
                tools=TODO_TOOLS,
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
                    f"Iteration {iteration + 1}: Processing tool calls",
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
        todo_service = TodoService(context.session)

        for block in content_blocks:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            logger.info(f"TodoAgent executing tool: {tool_name}")
            start_time = time.time()

            try:
                # Execute the tool
                result = await self._execute_single_tool(
                    tool_name,
                    tool_input,
                    todo_service,
                    context,
                )

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

    async def _execute_single_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        todo_service: TodoService,
        context: AgentContext,
    ) -> dict[str, Any]:
        """
        Execute a single tool and return the result.

        Args:
            tool_name: Name of the tool.
            tool_input: Input parameters.
            todo_service: TodoService instance.
            context: Agent context.

        Returns:
            Tool execution result.
        """
        if tool_name == "create_todo":
            return await self._tool_create_todo(tool_input, todo_service, context)
        elif tool_name == "list_todos":
            return await self._tool_list_todos(tool_input, todo_service)
        elif tool_name == "get_todo":
            return await self._tool_get_todo(tool_input, todo_service)
        elif tool_name == "update_todo":
            return await self._tool_update_todo(tool_input, todo_service)
        elif tool_name == "delete_todo":
            return await self._tool_delete_todo(tool_input, todo_service)
        elif tool_name == "get_todo_stats":
            return await self._tool_get_stats(todo_service)
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    # -------------------------------------------------------------------------
    # Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_create_todo(
        self,
        input_data: dict[str, Any],
        service: TodoService,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Create a new todo."""
        assigned_agent = None
        if input_data.get("assigned_agent"):
            assigned_agent = AgentType(input_data["assigned_agent"])

        priority = TodoPriority(input_data.get("priority", 3))

        todo_data = TodoCreate(
            title=input_data["title"],
            description=input_data.get("description"),
            assigned_agent=assigned_agent,
            priority=priority,
            metadata=input_data.get("metadata", {}),
        )

        todo = await service.create(
            todo_data,
            chat_id=context.chat_id,
            created_by=context.created_by,
        )

        return {
            "success": True,
            "todo_id": str(todo.id),
            "title": todo.title,
            "status": todo.status,
            "priority": todo.priority,
            "assigned_agent": todo.assigned_agent,
            "message": f"Created todo: {todo.title}",
        }

    async def _tool_list_todos(
        self,
        input_data: dict[str, Any],
        service: TodoService,
    ) -> dict[str, Any]:
        """List todos with filtering."""
        status = None
        if input_data.get("status"):
            status = TodoStatus(input_data["status"])

        assigned_agent = None
        if input_data.get("assigned_agent"):
            assigned_agent = AgentType(input_data["assigned_agent"])

        page_size = min(input_data.get("limit", 10), 50)

        result = await service.list_todos(
            status=status,
            assigned_agent=assigned_agent,
            priority=input_data.get("priority"),
            include_completed=input_data.get("include_completed", False),
            page=1,
            page_size=page_size,
        )

        todos = []
        for item in result.items:
            todos.append({
                "id": str(item.id),
                "title": item.title,
                "status": item.status.value,
                "priority": item.priority.value,
                "assigned_agent": item.assigned_agent.value if item.assigned_agent else None,
                "has_subtasks": item.has_subtasks,
            })

        return {
            "success": True,
            "total": result.total,
            "count": len(todos),
            "todos": todos,
        }

    async def _tool_get_todo(
        self,
        input_data: dict[str, Any],
        service: TodoService,
    ) -> dict[str, Any]:
        """Get a specific todo by ID."""
        todo_id = UUID(input_data["todo_id"])
        todo = await service.get_by_id(todo_id, include_subtasks=True)

        if not todo:
            return {"success": False, "error": f"Todo {todo_id} not found"}

        return {
            "success": True,
            "todo": {
                "id": str(todo.id),
                "title": todo.title,
                "description": todo.description,
                "status": todo.status,
                "priority": todo.priority,
                "assigned_agent": todo.assigned_agent,
                "result": todo.result,
                "error_message": todo.error_message,
                "created_at": todo.created_at.isoformat(),
                "metadata": todo.task_metadata,
            },
        }

    async def _tool_update_todo(
        self,
        input_data: dict[str, Any],
        service: TodoService,
    ) -> dict[str, Any]:
        """Update an existing todo."""
        todo_id = UUID(input_data["todo_id"])

        # Handle status updates specially
        if "status" in input_data:
            new_status = TodoStatus(input_data["status"])
            todo = await service.update_status(todo_id, new_status)
        else:
            update_fields = {}
            if "title" in input_data:
                update_fields["title"] = input_data["title"]
            if "description" in input_data:
                update_fields["description"] = input_data["description"]
            if "assigned_agent" in input_data:
                update_fields["assigned_agent"] = AgentType(input_data["assigned_agent"])
            if "priority" in input_data:
                update_fields["priority"] = TodoPriority(input_data["priority"])

            update_data = TodoUpdate(**update_fields)
            todo = await service.update(todo_id, update_data)

        if not todo:
            return {"success": False, "error": f"Todo {todo_id} not found"}

        return {
            "success": True,
            "todo_id": str(todo.id),
            "title": todo.title,
            "status": todo.status,
            "message": f"Updated todo: {todo.title}",
        }

    async def _tool_delete_todo(
        self,
        input_data: dict[str, Any],
        service: TodoService,
    ) -> dict[str, Any]:
        """Delete a todo."""
        todo_id = UUID(input_data["todo_id"])

        todo = await service.get_by_id(todo_id)
        if not todo:
            return {"success": False, "error": f"Todo {todo_id} not found"}

        title = todo.title
        deleted = await service.delete(todo_id)

        return {
            "success": deleted,
            "todo_id": str(todo_id),
            "message": f"Deleted todo: {title}" if deleted else "Failed to delete",
        }

    async def _tool_get_stats(self, service: TodoService) -> dict[str, Any]:
        """Get todo statistics."""
        stats = await service.get_stats()

        return {
            "success": True,
            "stats": {
                "total": stats.total,
                "pending": stats.pending,
                "in_progress": stats.in_progress,
                "completed": stats.completed,
                "failed": stats.failed,
                "cancelled": stats.cancelled,
                "by_agent": stats.by_agent,
                "by_priority": stats.by_priority,
            },
        }

    def _extract_text(self, response) -> str:
        """Extract text from Claude response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts)
