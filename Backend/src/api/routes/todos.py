# =============================================================================
# Todo API Routes
# =============================================================================
"""
API routes for todo/task management.

Provides RESTful endpoints for:
- CRUD operations on todos
- Status updates and execution
- Filtering, pagination, and statistics

All endpoints are prefixed with /todos when registered.

Usage:
    from src.api.routes import todos
    app.include_router(todos.router, prefix="/api")
"""

import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session_dependency
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
from src.services.todo_service import TodoService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Router Configuration
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/todos", tags=["todos"])


# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------
async def get_todo_service(
    session: AsyncSession = Depends(get_session_dependency),
) -> TodoService:
    """
    Dependency to get a TodoService instance with database session.

    Args:
        session: Database session from dependency injection.

    Returns:
        TodoService instance configured with the session.
    """
    return TodoService(session)


# -----------------------------------------------------------------------------
# Create Operations
# -----------------------------------------------------------------------------
@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new todo",
    description="Create a new todo item with optional agent assignment and scheduling.",
    responses={
        201: {"description": "Todo created successfully"},
        422: {"description": "Validation error in request body"},
    },
)
async def create_todo(
    data: TodoCreate,
    chat_id: Optional[UUID] = Query(
        None,
        description="Link todo to a conversation"
    ),
    created_by: Optional[str] = Query(
        None,
        description="Creator identifier (e.g., 'telegram:123456')"
    ),
    service: TodoService = Depends(get_todo_service),
) -> TodoResponse:
    """
    Create a new todo.

    Creates a todo item that can be tracked and optionally executed by
    a specialized agent. The todo starts in 'pending' status.

    Args:
        data: Todo creation data including title and optional fields.
        chat_id: Optional UUID linking to the originating conversation.
        created_by: Optional string identifying the creator.
        service: TodoService from dependency injection.

    Returns:
        The created todo as TodoResponse.

    Example:
        POST /api/todos?created_by=telegram:123456
        {
            "title": "Review PR #123",
            "assigned_agent": "github",
            "priority": 2
        }
    """
    logger.info(f"Creating todo: {data.title}")

    todo = await service.create(data, chat_id=chat_id, created_by=created_by)

    return service._to_response(todo)


# -----------------------------------------------------------------------------
# Read Operations
# -----------------------------------------------------------------------------
@router.get(
    "",
    response_model=TodoListResponse,
    summary="List todos",
    description="List todos with optional filtering and pagination.",
    responses={
        200: {"description": "List of todos matching filters"},
    },
)
async def list_todos(
    status: Optional[TodoStatus] = Query(
        None,
        description="Filter by status"
    ),
    assigned_agent: Optional[AgentType] = Query(
        None,
        description="Filter by assigned agent"
    ),
    priority: Optional[int] = Query(
        None,
        ge=1,
        le=5,
        description="Filter by priority (1=critical, 5=lowest)"
    ),
    chat_id: Optional[UUID] = Query(
        None,
        description="Filter by conversation"
    ),
    include_completed: bool = Query(
        True,
        description="Include completed/cancelled/failed todos"
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-indexed)"
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page"
    ),
    service: TodoService = Depends(get_todo_service),
) -> TodoListResponse:
    """
    List todos with filtering and pagination.

    Returns a paginated list of todos matching the provided filters.
    By default, returns only top-level todos (no subtasks).

    Args:
        status: Filter by status (pending, in_progress, completed, failed, cancelled).
        assigned_agent: Filter by agent (github, email, calendar, obsidian, orchestrator).
        priority: Filter by exact priority level.
        chat_id: Filter by originating conversation.
        include_completed: Whether to include terminal states.
        page: Page number (starts at 1).
        page_size: Number of items per page.
        service: TodoService from dependency injection.

    Returns:
        Paginated list with metadata.

    Example:
        GET /api/todos?status=pending&assigned_agent=github&page=1&page_size=10
    """
    return await service.list_todos(
        status=status,
        assigned_agent=assigned_agent,
        priority=priority,
        chat_id=chat_id,
        include_completed=include_completed,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stats",
    response_model=TodoStats,
    summary="Get todo statistics",
    description="Get aggregated statistics about todos.",
    responses={
        200: {"description": "Todo statistics"},
    },
)
async def get_stats(
    service: TodoService = Depends(get_todo_service),
) -> TodoStats:
    """
    Get todo statistics.

    Returns aggregate counts by status, agent, and priority.
    Useful for dashboards and reporting.

    Args:
        service: TodoService from dependency injection.

    Returns:
        Aggregated statistics.

    Example:
        GET /api/todos/stats
        Response: {"total": 42, "pending": 10, "completed": 25, ...}
    """
    return await service.get_stats()


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Get a todo",
    description="Get a specific todo by ID.",
    responses={
        200: {"description": "Todo found"},
        404: {"description": "Todo not found"},
    },
)
async def get_todo(
    todo_id: UUID,
    service: TodoService = Depends(get_todo_service),
) -> TodoResponse:
    """
    Get a todo by ID.

    Retrieves a single todo with its subtask information.

    Args:
        todo_id: UUID of the todo to retrieve.
        service: TodoService from dependency injection.

    Returns:
        The todo if found.

    Raises:
        HTTPException: 404 if todo not found.

    Example:
        GET /api/todos/123e4567-e89b-12d3-a456-426614174000
    """
    todo = await service.get_by_id(todo_id, include_subtasks=True)

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    return service._to_response(todo)


@router.get(
    "/{todo_id}/subtasks",
    response_model=TodoListResponse,
    summary="Get subtasks",
    description="Get all subtasks of a todo.",
    responses={
        200: {"description": "List of subtasks"},
        404: {"description": "Parent todo not found"},
    },
)
async def get_subtasks(
    todo_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TodoService = Depends(get_todo_service),
) -> TodoListResponse:
    """
    Get subtasks of a todo.

    Retrieves all child todos of the specified parent.

    Args:
        todo_id: UUID of the parent todo.
        page: Page number.
        page_size: Items per page.
        service: TodoService from dependency injection.

    Returns:
        Paginated list of subtasks.

    Raises:
        HTTPException: 404 if parent todo not found.
    """
    # Verify parent exists
    parent = await service.get_by_id(todo_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    return await service.list_todos(
        parent_todo_id=todo_id,
        page=page,
        page_size=page_size,
    )


# -----------------------------------------------------------------------------
# Update Operations
# -----------------------------------------------------------------------------
@router.patch(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Update a todo",
    description="Update a todo's fields. Only provided fields are updated.",
    responses={
        200: {"description": "Todo updated successfully"},
        404: {"description": "Todo not found"},
        422: {"description": "Validation error"},
    },
)
async def update_todo(
    todo_id: UUID,
    data: TodoUpdate,
    service: TodoService = Depends(get_todo_service),
) -> TodoResponse:
    """
    Update a todo.

    Partially updates a todo - only fields present in the request
    body are modified.

    Args:
        todo_id: UUID of the todo to update.
        data: Fields to update.
        service: TodoService from dependency injection.

    Returns:
        The updated todo.

    Raises:
        HTTPException: 404 if todo not found.

    Example:
        PATCH /api/todos/123e4567-e89b-12d3-a456-426614174000
        {"priority": 1}
    """
    todo = await service.update(todo_id, data)

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    return service._to_response(todo)


# -----------------------------------------------------------------------------
# Delete Operations
# -----------------------------------------------------------------------------
@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a todo",
    description="Delete a todo and all its subtasks.",
    responses={
        204: {"description": "Todo deleted successfully"},
        404: {"description": "Todo not found"},
    },
)
async def delete_todo(
    todo_id: UUID,
    service: TodoService = Depends(get_todo_service),
) -> None:
    """
    Delete a todo.

    Permanently removes a todo and all its subtasks (cascade delete).

    Args:
        todo_id: UUID of the todo to delete.
        service: TodoService from dependency injection.

    Raises:
        HTTPException: 404 if todo not found.

    Example:
        DELETE /api/todos/123e4567-e89b-12d3-a456-426614174000
    """
    deleted = await service.delete(todo_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )


# -----------------------------------------------------------------------------
# Status Operations
# -----------------------------------------------------------------------------
@router.post(
    "/{todo_id}/execute",
    response_model=TodoExecuteResponse,
    summary="Execute a todo",
    description="Manually trigger execution of a pending todo.",
    responses={
        200: {"description": "Execution completed"},
        400: {"description": "Todo not in executable state"},
        404: {"description": "Todo not found"},
    },
)
async def execute_todo(
    todo_id: UUID,
    request: TodoExecuteRequest = TodoExecuteRequest(),
    service: TodoService = Depends(get_todo_service),
) -> TodoExecuteResponse:
    """
    Execute a todo.

    Triggers the assigned agent to process the todo. Currently a
    placeholder that marks the todo as completed.

    Args:
        todo_id: UUID of the todo to execute.
        request: Execution options (force, timeout).
        service: TodoService from dependency injection.

    Returns:
        Execution result with status and timing.

    Raises:
        HTTPException: 404 if not found, 400 if not executable.

    Example:
        POST /api/todos/123e4567-e89b-12d3-a456-426614174000/execute
        {"force": true}
    """
    todo = await service.get_by_id(todo_id)

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    if not todo.is_executable and not request.force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Todo is in '{todo.status}' state. Use force=true to override.",
        )

    # Track execution time
    start_time = time.time()

    # Mark as in progress
    await service.update_status(todo_id, TodoStatus.IN_PROGRESS)

    # TODO: Implement actual execution via orchestrator/sub-agents
    # For now, mark as completed with placeholder result
    result_message = (
        f"Execution placeholder for '{todo.title}'. "
        f"Agent: {todo.assigned_agent or 'orchestrator'}"
    )

    await service.update_status(
        todo_id,
        TodoStatus.COMPLETED,
        result=result_message,
    )

    execution_time_ms = int((time.time() - start_time) * 1000)

    # Get updated todo for response
    updated_todo = await service.get_by_id(todo_id)

    return TodoExecuteResponse(
        todo_id=todo_id,
        status=TodoStatus(updated_todo.status),
        result=updated_todo.result,
        error_message=updated_todo.error_message,
        execution_time_ms=execution_time_ms,
    )


@router.post(
    "/{todo_id}/cancel",
    response_model=TodoResponse,
    summary="Cancel a todo",
    description="Cancel a pending or in-progress todo.",
    responses={
        200: {"description": "Todo cancelled"},
        400: {"description": "Todo already in terminal state"},
        404: {"description": "Todo not found"},
    },
)
async def cancel_todo(
    todo_id: UUID,
    service: TodoService = Depends(get_todo_service),
) -> TodoResponse:
    """
    Cancel a todo.

    Moves the todo to 'cancelled' status. Cannot cancel already
    completed or failed todos.

    Args:
        todo_id: UUID of the todo to cancel.
        service: TodoService from dependency injection.

    Returns:
        The cancelled todo.

    Raises:
        HTTPException: 404 if not found, 400 if already terminal.

    Example:
        POST /api/todos/123e4567-e89b-12d3-a456-426614174000/cancel
    """
    todo = await service.get_by_id(todo_id)

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    if todo.is_terminal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel todo in '{todo.status}' state",
        )

    updated = await service.update_status(todo_id, TodoStatus.CANCELLED)

    return service._to_response(updated)
