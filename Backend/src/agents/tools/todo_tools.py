# =============================================================================
# Todo Tools for Orchestrator Agent
# =============================================================================
"""
Tool definitions and handlers for todo management operations.

These tools allow the orchestrator agent to create, manage, and execute
todos via the Anthropic Claude API tool calling feature.

Usage:
    from src.agents.tools import TOOL_DEFINITIONS, TodoToolHandler

    # Pass TOOL_DEFINITIONS to Claude API
    response = client.messages.create(
        model=model,
        tools=TOOL_DEFINITIONS,
        messages=messages,
    )

    # Handle tool calls with TodoToolHandler
    handler = TodoToolHandler(session)
    result = await handler.handle_tool_call(tool_name, tool_input)
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.todo import (
    AgentType,
    TodoCreate,
    TodoPriority,
    TodoStatus,
    TodoUpdate,
)
from src.services.todo_service import TodoService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Tool Definitions for Claude API
# -----------------------------------------------------------------------------
# These definitions follow Anthropic's tool schema format for Claude API

TOOL_DEFINITIONS = [
    {
        "name": "create_todo",
        "description": (
            "Create a new todo/task item. Use this when the user asks to "
            "create a task, reminder, or todo item. The todo will be stored "
            "in the database and can be executed by specialized agents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": (
                        "Short, descriptive title for the todo (max 500 chars). "
                        "Should clearly describe what needs to be done."
                    ),
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Detailed description of the task. Include any relevant "
                        "context, requirements, or acceptance criteria."
                    ),
                },
                "assigned_agent": {
                    "type": "string",
                    "enum": ["github", "email", "calendar", "obsidian", "orchestrator"],
                    "description": (
                        "Which agent should handle this task. Use 'github' for "
                        "repo/code tasks, 'email' for email tasks, 'calendar' for "
                        "scheduling, 'obsidian' for notes, or 'orchestrator' for "
                        "general tasks you can handle directly."
                    ),
                },
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": (
                        "Priority level: 1=critical, 2=high, 3=normal (default), "
                        "4=low, 5=lowest. Use lower numbers for urgent tasks."
                    ),
                },
                "metadata": {
                    "type": "object",
                    "description": (
                        "Additional structured data for the task. Examples: "
                        '{"repo": "owner/repo"} for GitHub, '
                        '{"recipients": ["email@example.com"]} for email.'
                    ),
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_todos",
        "description": (
            "List existing todos with optional filtering. Use this when the "
            "user asks to see their tasks, check pending items, or review "
            "what's on their todo list."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "failed", "cancelled"],
                    "description": (
                        "Filter by status. Omit to show all active todos."
                    ),
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
                    "description": "Filter by exact priority level.",
                },
                "include_completed": {
                    "type": "boolean",
                    "description": (
                        "Whether to include completed/failed/cancelled todos. "
                        "Default is false to show only active items."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of todos to return (default: 10).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_todo",
        "description": (
            "Get details of a specific todo by its ID. Use this when you need "
            "full information about a particular task."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The UUID of the todo to retrieve.",
                },
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "update_todo",
        "description": (
            "Update an existing todo. Use this when the user wants to modify "
            "a task's title, description, priority, or assigned agent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The UUID of the todo to update.",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the todo.",
                },
                "description": {
                    "type": "string",
                    "description": "New description for the todo.",
                },
                "assigned_agent": {
                    "type": "string",
                    "enum": ["github", "email", "calendar", "obsidian", "orchestrator"],
                    "description": "Change the assigned agent.",
                },
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Change the priority level.",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "failed", "cancelled"],
                    "description": (
                        "Change the status. Use 'completed' to mark done, "
                        "'cancelled' to cancel a task."
                    ),
                },
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "delete_todo",
        "description": (
            "Permanently delete a todo. Use this when the user wants to remove "
            "a task entirely. This cannot be undone."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The UUID of the todo to delete.",
                },
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "execute_todo",
        "description": (
            "Trigger execution of a pending todo. Use this when the user wants "
            "to immediately run a task. The appropriate agent will process it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The UUID of the todo to execute.",
                },
                "force": {
                    "type": "boolean",
                    "description": (
                        "Force execution even if the todo is not in 'pending' state. "
                        "Default is false."
                    ),
                },
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "get_todo_stats",
        "description": (
            "Get statistics about todos. Use this when the user asks for an "
            "overview, summary, or statistics about their tasks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# -----------------------------------------------------------------------------
# Tool Handler Class
# -----------------------------------------------------------------------------
class TodoToolHandler:
    """
    Handler for executing todo tool calls from the orchestrator agent.

    This class processes tool calls from Claude's response and executes
    the corresponding operations via the TodoService.

    Attributes:
        service: TodoService instance for database operations.
        chat_id: Optional chat ID to associate with created todos.
        created_by: Optional creator identifier (e.g., "telegram:123").

    Example:
        handler = TodoToolHandler(session, chat_id=chat_uuid, created_by="telegram:123")
        result = await handler.handle_tool_call("create_todo", {"title": "My task"})
    """

    def __init__(
        self,
        session: AsyncSession,
        chat_id: Optional[UUID] = None,
        created_by: Optional[str] = None,
    ) -> None:
        """
        Initialize the tool handler.

        Args:
            session: SQLAlchemy async session for database operations.
            chat_id: Optional chat ID to link todos to conversation.
            created_by: Optional string identifying the creator.
        """
        self.service = TodoService(session)
        self.chat_id = chat_id
        self.created_by = created_by

    async def handle_tool_call(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Route and execute a tool call.

        This is the main entry point for processing tool calls from Claude.
        It routes to the appropriate handler function based on the tool name.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Input parameters for the tool.

        Returns:
            Dictionary with the tool execution result.

        Raises:
            ValueError: If the tool name is not recognized.
        """
        logger.info(f"Handling tool call: {tool_name}")
        logger.debug(f"Tool input: {tool_input}")

        # Route to appropriate handler
        handlers = {
            "create_todo": self._handle_create_todo,
            "list_todos": self._handle_list_todos,
            "get_todo": self._handle_get_todo,
            "update_todo": self._handle_update_todo,
            "delete_todo": self._handle_delete_todo,
            "execute_todo": self._handle_execute_todo,
            "get_todo_stats": self._handle_get_stats,
        }

        handler = handlers.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")

        try:
            result = await handler(tool_input)
            logger.info(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # Individual Tool Handlers
    # -------------------------------------------------------------------------
    async def _handle_create_todo(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle create_todo tool call.

        Creates a new todo with the provided parameters and links it
        to the current chat/conversation if available.

        Args:
            input_data: Tool input containing title and optional fields.

        Returns:
            Dictionary with created todo details.
        """
        # Parse agent type if provided
        assigned_agent = None
        if input_data.get("assigned_agent"):
            assigned_agent = AgentType(input_data["assigned_agent"])

        # Parse priority (default to NORMAL if not provided)
        priority = TodoPriority(input_data.get("priority", 3))

        # Create the todo
        todo_data = TodoCreate(
            title=input_data["title"],
            description=input_data.get("description"),
            assigned_agent=assigned_agent,
            priority=priority,
            metadata=input_data.get("metadata", {}),
        )

        todo = await self.service.create(
            todo_data,
            chat_id=self.chat_id,
            created_by=self.created_by,
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

    async def _handle_list_todos(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle list_todos tool call.

        Retrieves todos matching the provided filters.

        Args:
            input_data: Tool input containing optional filters.

        Returns:
            Dictionary with list of todos.
        """
        # Parse optional filters
        status = None
        if input_data.get("status"):
            status = TodoStatus(input_data["status"])

        assigned_agent = None
        if input_data.get("assigned_agent"):
            assigned_agent = AgentType(input_data["assigned_agent"])

        # Get todos with pagination
        page_size = min(input_data.get("limit", 10), 50)

        result = await self.service.list_todos(
            status=status,
            assigned_agent=assigned_agent,
            priority=input_data.get("priority"),
            include_completed=input_data.get("include_completed", False),
            page=1,
            page_size=page_size,
        )

        # Format todos for response
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

    async def _handle_get_todo(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle get_todo tool call.

        Retrieves full details of a specific todo.

        Args:
            input_data: Tool input containing todo_id.

        Returns:
            Dictionary with todo details.
        """
        todo_id = UUID(input_data["todo_id"])
        todo = await self.service.get_by_id(todo_id, include_subtasks=True)

        if not todo:
            return {
                "success": False,
                "error": f"Todo {todo_id} not found",
            }

        return {
            "success": True,
            "todo": {
                "id": str(todo.id),
                "title": todo.title,
                "description": todo.description,
                "status": todo.status,
                "priority": todo.priority,
                "assigned_agent": todo.assigned_agent,
                "scheduled_at": todo.scheduled_at.isoformat() if todo.scheduled_at else None,
                "result": todo.result,
                "error_message": todo.error_message,
                "execution_attempts": todo.execution_attempts,
                "created_at": todo.created_at.isoformat(),
                "updated_at": todo.updated_at.isoformat(),
                "started_at": todo.started_at.isoformat() if todo.started_at else None,
                "completed_at": todo.completed_at.isoformat() if todo.completed_at else None,
                "metadata": todo.task_metadata,
                "subtask_count": len(todo.subtasks) if todo.subtasks else 0,
            },
        }

    async def _handle_update_todo(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle update_todo tool call.

        Updates an existing todo with the provided fields.

        Args:
            input_data: Tool input containing todo_id and fields to update.

        Returns:
            Dictionary with updated todo details.
        """
        todo_id = UUID(input_data["todo_id"])

        # Build update data (only include provided fields)
        update_fields = {}

        if "title" in input_data:
            update_fields["title"] = input_data["title"]

        if "description" in input_data:
            update_fields["description"] = input_data["description"]

        if "assigned_agent" in input_data:
            update_fields["assigned_agent"] = AgentType(input_data["assigned_agent"])

        if "priority" in input_data:
            update_fields["priority"] = TodoPriority(input_data["priority"])

        # Handle status updates specially
        if "status" in input_data:
            new_status = TodoStatus(input_data["status"])
            todo = await self.service.update_status(todo_id, new_status)
        else:
            update_data = TodoUpdate(**update_fields)
            todo = await self.service.update(todo_id, update_data)

        if not todo:
            return {
                "success": False,
                "error": f"Todo {todo_id} not found",
            }

        return {
            "success": True,
            "todo_id": str(todo.id),
            "title": todo.title,
            "status": todo.status,
            "message": f"Updated todo: {todo.title}",
        }

    async def _handle_delete_todo(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle delete_todo tool call.

        Permanently deletes a todo and its subtasks.

        Args:
            input_data: Tool input containing todo_id.

        Returns:
            Dictionary with deletion result.
        """
        todo_id = UUID(input_data["todo_id"])

        # Get todo first for the response message
        todo = await self.service.get_by_id(todo_id)
        if not todo:
            return {
                "success": False,
                "error": f"Todo {todo_id} not found",
            }

        title = todo.title
        deleted = await self.service.delete(todo_id)

        return {
            "success": deleted,
            "todo_id": str(todo_id),
            "message": f"Deleted todo: {title}" if deleted else "Failed to delete",
        }

    async def _handle_execute_todo(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle execute_todo tool call.

        Triggers execution of a pending todo. Currently a placeholder
        that marks the todo as completed.

        Args:
            input_data: Tool input containing todo_id and optional force flag.

        Returns:
            Dictionary with execution result.
        """
        todo_id = UUID(input_data["todo_id"])
        force = input_data.get("force", False)

        todo = await self.service.get_by_id(todo_id)
        if not todo:
            return {
                "success": False,
                "error": f"Todo {todo_id} not found",
            }

        if not todo.is_executable and not force:
            return {
                "success": False,
                "error": f"Todo is in '{todo.status}' state. Use force=true to override.",
            }

        # Mark as in progress
        await self.service.update_status(todo_id, TodoStatus.IN_PROGRESS)

        # TODO: Implement actual execution via sub-agents
        # For now, mark as completed with placeholder result
        result_message = (
            f"Execution placeholder for '{todo.title}'. "
            f"Agent: {todo.assigned_agent or 'orchestrator'}"
        )

        await self.service.update_status(
            todo_id,
            TodoStatus.COMPLETED,
            result=result_message,
        )

        return {
            "success": True,
            "todo_id": str(todo_id),
            "status": "completed",
            "result": result_message,
            "message": f"Executed todo: {todo.title}",
        }

    async def _handle_get_stats(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle get_todo_stats tool call.

        Returns aggregated statistics about todos.

        Args:
            input_data: Tool input (no parameters required).

        Returns:
            Dictionary with todo statistics.
        """
        stats = await self.service.get_stats()

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
                "by_priority": {
                    "critical": stats.by_priority.get(1, 0),
                    "high": stats.by_priority.get(2, 0),
                    "normal": stats.by_priority.get(3, 0),
                    "low": stats.by_priority.get(4, 0),
                    "lowest": stats.by_priority.get(5, 0),
                },
            },
        }


# -----------------------------------------------------------------------------
# Standalone Tool Functions (for direct use without handler)
# -----------------------------------------------------------------------------
async def create_todo_tool(
    session: AsyncSession,
    title: str,
    description: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    priority: int = 3,
    metadata: Optional[dict] = None,
    chat_id: Optional[UUID] = None,
    created_by: Optional[str] = None,
) -> dict[str, Any]:
    """
    Standalone function to create a todo.

    This is a convenience wrapper for direct programmatic use.

    Args:
        session: SQLAlchemy async session.
        title: Todo title.
        description: Optional description.
        assigned_agent: Agent to assign (github, email, calendar, obsidian, orchestrator).
        priority: Priority level (1-5).
        metadata: Additional metadata dict.
        chat_id: Optional chat ID to link todo.
        created_by: Optional creator identifier.

    Returns:
        Dictionary with created todo details.
    """
    handler = TodoToolHandler(session, chat_id, created_by)
    return await handler._handle_create_todo({
        "title": title,
        "description": description,
        "assigned_agent": assigned_agent,
        "priority": priority,
        "metadata": metadata or {},
    })


async def list_todos_tool(
    session: AsyncSession,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    priority: Optional[int] = None,
    include_completed: bool = False,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Standalone function to list todos.

    Args:
        session: SQLAlchemy async session.
        status: Optional status filter.
        assigned_agent: Optional agent filter.
        priority: Optional priority filter.
        include_completed: Whether to include completed todos.
        limit: Maximum number of results.

    Returns:
        Dictionary with list of todos.
    """
    handler = TodoToolHandler(session)
    return await handler._handle_list_todos({
        "status": status,
        "assigned_agent": assigned_agent,
        "priority": priority,
        "include_completed": include_completed,
        "limit": limit,
    })


async def get_todo_tool(
    session: AsyncSession,
    todo_id: str,
) -> dict[str, Any]:
    """
    Standalone function to get a todo by ID.

    Args:
        session: SQLAlchemy async session.
        todo_id: UUID string of the todo.

    Returns:
        Dictionary with todo details.
    """
    handler = TodoToolHandler(session)
    return await handler._handle_get_todo({"todo_id": todo_id})


async def update_todo_tool(
    session: AsyncSession,
    todo_id: str,
    **kwargs,
) -> dict[str, Any]:
    """
    Standalone function to update a todo.

    Args:
        session: SQLAlchemy async session.
        todo_id: UUID string of the todo.
        **kwargs: Fields to update (title, description, priority, status, assigned_agent).

    Returns:
        Dictionary with updated todo details.
    """
    handler = TodoToolHandler(session)
    return await handler._handle_update_todo({"todo_id": todo_id, **kwargs})


async def delete_todo_tool(
    session: AsyncSession,
    todo_id: str,
) -> dict[str, Any]:
    """
    Standalone function to delete a todo.

    Args:
        session: SQLAlchemy async session.
        todo_id: UUID string of the todo.

    Returns:
        Dictionary with deletion result.
    """
    handler = TodoToolHandler(session)
    return await handler._handle_delete_todo({"todo_id": todo_id})


async def execute_todo_tool(
    session: AsyncSession,
    todo_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """
    Standalone function to execute a todo.

    Args:
        session: SQLAlchemy async session.
        todo_id: UUID string of the todo.
        force: Force execution even if not pending.

    Returns:
        Dictionary with execution result.
    """
    handler = TodoToolHandler(session)
    return await handler._handle_execute_todo({"todo_id": todo_id, "force": force})
