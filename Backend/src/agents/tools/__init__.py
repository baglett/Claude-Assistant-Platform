# =============================================================================
# Agent Tools Package
# =============================================================================
"""
Tool definitions for Claude agent integration.

This package contains tool implementations that can be used by the orchestrator
and sub-agents to interact with the platform's services.

Available Tools:
    todo_tools: Tools for creating, managing, and querying todos
"""

from src.agents.tools.todo_tools import (
    TOOL_DEFINITIONS,
    TodoToolHandler,
    create_todo_tool,
    delete_todo_tool,
    execute_todo_tool,
    get_todo_tool,
    list_todos_tool,
    update_todo_tool,
)


__all__ = [
    # Tool definitions for Claude API
    "TOOL_DEFINITIONS",
    # Tool handler class
    "TodoToolHandler",
    # Individual tool functions
    "create_todo_tool",
    "list_todos_tool",
    "get_todo_tool",
    "update_todo_tool",
    "delete_todo_tool",
    "execute_todo_tool",
]
