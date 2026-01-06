# =============================================================================
# Todo Service
# =============================================================================
"""
Service layer for todo/task management operations.

Provides business logic for creating, updating, querying, and managing
todos. Handles status transitions, filtering, pagination, and statistics.

Usage:
    from src.services.todo_service import TodoService

    async with get_session() as session:
        service = TodoService(session)
        todo = await service.create(TodoCreate(title="My task"))
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import Todo
from src.models.todo import (
    AgentType,
    TodoCreate,
    TodoListResponse,
    TodoPriority,
    TodoResponse,
    TodoStats,
    TodoStatus,
    TodoUpdate,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Todo Service Class
# -----------------------------------------------------------------------------
class TodoService:
    """
    Service class for todo management operations.

    Provides methods for creating, updating, querying, and executing todos.
    All database operations use the provided async session.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = TodoService(session)

            # Create a todo
            todo = await service.create(
                TodoCreate(title="Review PR", assigned_agent=AgentType.GITHUB)
            )

            # Update status
            await service.update_status(todo.id, TodoStatus.COMPLETED)

            # Get statistics
            stats = await service.get_stats()
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the todo service.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session

    # -------------------------------------------------------------------------
    # Create Operations
    # -------------------------------------------------------------------------
    async def create(
        self,
        data: TodoCreate,
        chat_id: Optional[UUID] = None,
        created_by: Optional[str] = None,
    ) -> Todo:
        """
        Create a new todo.

        Args:
            data: Todo creation data from API request.
            chat_id: Optional link to originating conversation.
            created_by: Optional identifier of creator (e.g., "telegram:123").

        Returns:
            Created Todo ORM instance.

        Example:
            todo = await service.create(
                TodoCreate(
                    title="Create GitHub issue",
                    assigned_agent=AgentType.GITHUB,
                    priority=TodoPriority.HIGH,
                ),
                chat_id=conversation_uuid,
                created_by="telegram:123456",
            )
        """
        todo = Todo(
            title=data.title,
            description=data.description,
            assigned_agent=data.assigned_agent.value if data.assigned_agent else None,
            priority=data.priority.value,
            scheduled_at=data.scheduled_at,
            parent_todo_id=data.parent_todo_id,
            task_metadata=data.metadata,
            chat_id=chat_id,
            created_by=created_by,
        )

        self.session.add(todo)
        await self.session.flush()
        await self.session.refresh(todo)

        logger.info(
            f"Created todo {todo.id}: '{todo.title}' "
            f"(agent={todo.assigned_agent}, priority={todo.priority})"
        )

        return todo

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    async def get_by_id(
        self,
        todo_id: UUID,
        include_subtasks: bool = False,
    ) -> Optional[Todo]:
        """
        Get a todo by ID.

        Args:
            todo_id: Todo UUID to retrieve.
            include_subtasks: Whether to eager-load subtasks relationship.

        Returns:
            Todo instance or None if not found.

        Example:
            todo = await service.get_by_id(todo_uuid, include_subtasks=True)
            if todo:
                print(f"Found: {todo.title}")
                print(f"Subtasks: {len(todo.subtasks)}")
        """
        query = select(Todo).where(Todo.id == todo_id)

        if include_subtasks:
            query = query.options(selectinload(Todo.subtasks))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_todos(
        self,
        status: Optional[TodoStatus] = None,
        assigned_agent: Optional[AgentType] = None,
        priority: Optional[int] = None,
        chat_id: Optional[UUID] = None,
        parent_todo_id: Optional[UUID] = None,
        include_completed: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> TodoListResponse:
        """
        List todos with filtering and pagination.

        Args:
            status: Filter by status (e.g., TodoStatus.PENDING).
            assigned_agent: Filter by assigned agent (e.g., AgentType.GITHUB).
            priority: Filter by exact priority level (1-5).
            chat_id: Filter by originating conversation.
            parent_todo_id: Filter by parent (use None for top-level only).
            include_completed: Whether to include completed/cancelled todos.
            page: Page number (1-indexed).
            page_size: Number of items per page (max 100).

        Returns:
            TodoListResponse with paginated results and metadata.

        Example:
            # Get all pending GitHub tasks
            result = await service.list_todos(
                status=TodoStatus.PENDING,
                assigned_agent=AgentType.GITHUB,
            )
            for todo in result.items:
                print(f"- {todo.title}")
        """
        # Build filter conditions
        conditions = []

        if status:
            conditions.append(Todo.status == status.value)
        elif not include_completed:
            conditions.append(
                Todo.status.notin_(["completed", "failed", "cancelled"])
            )

        if assigned_agent:
            conditions.append(Todo.assigned_agent == assigned_agent.value)

        if priority:
            conditions.append(Todo.priority == priority)

        if chat_id:
            conditions.append(Todo.chat_id == chat_id)

        # Handle parent filtering - None means top-level only
        if parent_todo_id is not None:
            conditions.append(Todo.parent_todo_id == parent_todo_id)
        else:
            conditions.append(Todo.parent_todo_id.is_(None))

        # Count total matching todos
        count_query = select(func.count(Todo.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Fetch page of todos with subtasks
        query = (
            select(Todo)
            .options(selectinload(Todo.subtasks))
            .order_by(Todo.priority.asc(), Todo.created_at.desc())
        )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        todos = result.scalars().all()

        # Convert to response models
        items = [self._to_response(todo) for todo in todos]

        return TodoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------
    async def update(
        self,
        todo_id: UUID,
        data: TodoUpdate,
    ) -> Optional[Todo]:
        """
        Update an existing todo.

        Only fields provided in the update data are modified.

        Args:
            todo_id: Todo UUID to update.
            data: Fields to update (only non-None fields are applied).

        Returns:
            Updated Todo instance or None if not found.

        Example:
            todo = await service.update(
                todo_uuid,
                TodoUpdate(priority=TodoPriority.CRITICAL)
            )
        """
        todo = await self.get_by_id(todo_id)
        if not todo:
            return None

        # Only update provided fields (exclude_unset=True)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            # Convert enums to their values for database storage
            if field == "assigned_agent" and value is not None:
                value = value.value
            elif field == "priority" and value is not None:
                value = value.value
            elif field == "metadata":
                field = "task_metadata"  # Map to ORM field name

            setattr(todo, field, value)

        await self.session.flush()
        await self.session.refresh(todo)

        logger.info(f"Updated todo {todo_id}: {list(update_data.keys())}")

        return todo

    async def update_status(
        self,
        todo_id: UUID,
        status: TodoStatus,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Todo]:
        """
        Update todo status with appropriate timestamp handling.

        Automatically sets started_at when moving to in_progress,
        and completed_at when moving to a terminal state.

        Args:
            todo_id: Todo UUID to update.
            status: New status to set.
            result: Execution result (typically for completed status).
            error_message: Error details (typically for failed status).

        Returns:
            Updated Todo instance or None if not found.

        Example:
            # Start execution
            await service.update_status(todo_id, TodoStatus.IN_PROGRESS)

            # Mark complete with result
            await service.update_status(
                todo_id,
                TodoStatus.COMPLETED,
                result="Created issue #123 successfully"
            )
        """
        todo = await self.get_by_id(todo_id)
        if not todo:
            return None

        now = datetime.now(timezone.utc)
        todo.status = status.value

        # Set appropriate timestamps based on status transition
        if status == TodoStatus.IN_PROGRESS:
            todo.started_at = now
            todo.execution_attempts += 1
        elif status in (TodoStatus.COMPLETED, TodoStatus.FAILED, TodoStatus.CANCELLED):
            todo.completed_at = now
            if result:
                todo.result = result
            if error_message:
                todo.error_message = error_message

        await self.session.flush()
        await self.session.refresh(todo)

        logger.info(f"Updated todo {todo_id} status to {status.value}")

        return todo

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------
    async def delete(self, todo_id: UUID) -> bool:
        """
        Delete a todo and its subtasks.

        Uses CASCADE delete defined in the database schema.

        Args:
            todo_id: Todo UUID to delete.

        Returns:
            True if deleted, False if not found.

        Example:
            deleted = await service.delete(todo_uuid)
            if deleted:
                print("Todo deleted successfully")
        """
        todo = await self.get_by_id(todo_id)
        if not todo:
            return False

        await self.session.delete(todo)
        await self.session.flush()

        logger.info(f"Deleted todo {todo_id}")

        return True

    # -------------------------------------------------------------------------
    # Execution Operations
    # -------------------------------------------------------------------------
    async def get_pending_for_execution(
        self,
        agent: Optional[AgentType] = None,
        limit: int = 10,
    ) -> list[Todo]:
        """
        Get pending todos ready for execution.

        Fetches todos that are:
        - Status is 'pending'
        - Scheduled time is None (immediate) or in the past
        - Optionally filtered by assigned agent

        Results are ordered by priority (ascending) and creation time.

        Args:
            agent: Filter by assigned agent (None for all agents).
            limit: Maximum todos to return.

        Returns:
            List of todos ready for execution.

        Example:
            # Get pending GitHub tasks ready to execute
            todos = await service.get_pending_for_execution(
                agent=AgentType.GITHUB,
                limit=5
            )
        """
        now = datetime.now(timezone.utc)

        conditions = [
            Todo.status == "pending",
            or_(
                Todo.scheduled_at.is_(None),
                Todo.scheduled_at <= now,
            ),
        ]

        if agent:
            conditions.append(Todo.assigned_agent == agent.value)

        query = (
            select(Todo)
            .where(and_(*conditions))
            .order_by(Todo.priority.asc(), Todo.created_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Statistics Operations
    # -------------------------------------------------------------------------
    async def get_stats(self) -> TodoStats:
        """
        Get aggregated todo statistics.

        Returns counts by status, agent, and priority for dashboard
        and reporting purposes.

        Returns:
            TodoStats with aggregate counts.

        Example:
            stats = await service.get_stats()
            print(f"Total: {stats.total}")
            print(f"Pending: {stats.pending}")
            print(f"By agent: {stats.by_agent}")
        """
        # Count by status
        status_query = select(
            Todo.status,
            func.count(Todo.id)
        ).group_by(Todo.status)
        status_result = await self.session.execute(status_query)
        status_counts = dict(status_result.all())

        # Count by agent (only non-null agents)
        agent_query = select(
            Todo.assigned_agent,
            func.count(Todo.id)
        ).where(Todo.assigned_agent.isnot(None)).group_by(Todo.assigned_agent)
        agent_result = await self.session.execute(agent_query)
        agent_counts = dict(agent_result.all())

        # Count by priority
        priority_query = select(
            Todo.priority,
            func.count(Todo.id)
        ).group_by(Todo.priority)
        priority_result = await self.session.execute(priority_query)
        priority_counts = dict(priority_result.all())

        return TodoStats(
            total=sum(status_counts.values()),
            pending=status_counts.get("pending", 0),
            in_progress=status_counts.get("in_progress", 0),
            completed=status_counts.get("completed", 0),
            failed=status_counts.get("failed", 0),
            cancelled=status_counts.get("cancelled", 0),
            by_agent=agent_counts,
            by_priority=priority_counts,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _to_response(self, todo: Todo) -> TodoResponse:
        """
        Convert a Todo ORM instance to a TodoResponse.

        Handles enum conversion and computed fields like subtask counts.

        Args:
            todo: Todo ORM instance to convert.

        Returns:
            TodoResponse Pydantic model.
        """
        subtask_count = len(todo.subtasks) if todo.subtasks else 0

        return TodoResponse(
            id=todo.id,
            title=todo.title,
            description=todo.description,
            status=TodoStatus(todo.status),
            assigned_agent=AgentType(todo.assigned_agent) if todo.assigned_agent else None,
            priority=TodoPriority(todo.priority),
            scheduled_at=todo.scheduled_at,
            result=todo.result,
            error_message=todo.error_message,
            execution_attempts=todo.execution_attempts,
            chat_id=todo.chat_id,
            parent_todo_id=todo.parent_todo_id,
            metadata=todo.task_metadata,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
            started_at=todo.started_at,
            completed_at=todo.completed_at,
            created_by=todo.created_by,
            has_subtasks=subtask_count > 0,
            subtask_count=subtask_count,
        )
