# =============================================================================
# Models Package
# =============================================================================
"""
Pydantic models and API schemas for the Claude Assistant Platform.

This package contains Pydantic models used for:
- API request/response validation
- Data serialization
- OpenAPI documentation generation

Note: SQLAlchemy ORM models are in src/database/models.py

Usage:
    from src.models import TodoCreate, TodoResponse, TodoStatus
    from src.models.chat import ChatRequest, ChatResponse
"""

# Todo models
from src.models.todo import (
    AgentType,
    TodoCreate,
    TodoExecuteRequest,
    TodoExecuteResponse,
    TodoListResponse,
    TodoPriority,
    TodoResponse,
    TodoStats,
    TodoStatus,
    TodoUpdate,
)


__all__ = [
    # Todo models
    "TodoStatus",
    "AgentType",
    "TodoPriority",
    "TodoCreate",
    "TodoUpdate",
    "TodoExecuteRequest",
    "TodoResponse",
    "TodoListResponse",
    "TodoExecuteResponse",
    "TodoStats",
]
