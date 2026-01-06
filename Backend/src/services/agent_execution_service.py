# =============================================================================
# Agent Execution Service
# =============================================================================
"""
Service layer for agent execution logging and tracking.

Provides functionality to create, update, and query agent execution records.
Used by all agents to log their thinking, tool calls, and results.

Usage:
    from src.services.agent_execution_service import AgentExecutionService

    async with get_session() as session:
        service = AgentExecutionService(session)

        # Start an execution
        execution = await service.start_execution(
            agent_name="todo",
            chat_id=chat_uuid,
            task_description="Create a new todo item",
        )

        # Log thinking
        await service.log_thinking(execution.id, "Analyzing user request...")

        # Log tool call
        await service.log_tool_call(
            execution.id,
            tool_name="create_todo",
            input_data={"title": "My task"},
            output_data={"success": True, "todo_id": "..."},
        )

        # Complete execution
        await service.complete_execution(
            execution.id,
            result="Created todo successfully",
            input_tokens=100,
            output_tokens=50,
        )
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import AgentExecution


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Execution Status Constants
# -----------------------------------------------------------------------------
class ExecutionStatus:
    """Constants for execution status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# -----------------------------------------------------------------------------
# Agent Execution Service Class
# -----------------------------------------------------------------------------
class AgentExecutionService:
    """
    Service class for agent execution logging and tracking.

    Provides methods for creating, updating, and querying agent execution
    records. All agents should use this service to log their activity.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = AgentExecutionService(session)

            # Start execution
            exec_id = await service.start_execution(
                agent_name="github",
                chat_id=chat_uuid,
                task_description="Create issue for bug report",
            )

            # ... agent does work ...

            # Complete execution
            await service.complete_execution(exec_id, result="Issue #123 created")
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the agent execution service.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session

    # -------------------------------------------------------------------------
    # Execution Lifecycle Methods
    # -------------------------------------------------------------------------
    async def start_execution(
        self,
        agent_name: str,
        task_description: Optional[str] = None,
        chat_id: Optional[UUID] = None,
        todo_id: Optional[UUID] = None,
        parent_execution_id: Optional[UUID] = None,
        input_context: Optional[dict[str, Any]] = None,
    ) -> AgentExecution:
        """
        Start a new agent execution.

        Creates a new execution record and marks it as running.
        This should be called at the beginning of any agent invocation.

        Args:
            agent_name: Name of the executing agent (e.g., "orchestrator", "todo").
            task_description: Description of the task being performed.
            chat_id: Optional chat ID for context.
            todo_id: Optional todo ID if executing a todo.
            parent_execution_id: Optional parent execution for nested calls.
            input_context: Optional context data passed to the agent.

        Returns:
            The created AgentExecution record.

        Example:
            execution = await service.start_execution(
                agent_name="todo",
                chat_id=chat_uuid,
                task_description="List all pending todos",
                input_context={"recent_messages": [...]}
            )
        """
        now = datetime.now(timezone.utc)

        execution = AgentExecution(
            agent_name=agent_name,
            status=ExecutionStatus.RUNNING,
            task_description=task_description,
            chat_id=chat_id,
            todo_id=todo_id,
            parent_execution_id=parent_execution_id,
            input_context=input_context or {},
            started_at=now,
        )

        self.session.add(execution)
        await self.session.flush()
        await self.session.refresh(execution)

        logger.info(
            f"Started execution {execution.id} for agent '{agent_name}'"
            f"{f' (parent: {parent_execution_id})' if parent_execution_id else ''}"
        )

        return execution

    async def complete_execution(
        self,
        execution_id: UUID,
        result: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        llm_calls: int = 1,
    ) -> Optional[AgentExecution]:
        """
        Mark an execution as completed successfully.

        Updates the execution with the result and performance metrics.

        Args:
            execution_id: ID of the execution to complete.
            result: Final result/output of the execution.
            input_tokens: Total input tokens used.
            output_tokens: Total output tokens used.
            llm_calls: Number of LLM API calls made.

        Returns:
            Updated AgentExecution or None if not found.
        """
        execution = await self.get_by_id(execution_id)
        if not execution:
            logger.warning(f"Execution {execution_id} not found")
            return None

        now = datetime.now(timezone.utc)

        execution.status = ExecutionStatus.COMPLETED
        execution.result = result
        execution.completed_at = now
        execution.input_tokens = input_tokens
        execution.output_tokens = output_tokens
        execution.llm_calls = llm_calls

        # Calculate execution time
        if execution.started_at:
            delta = now - execution.started_at
            execution.execution_time_ms = int(delta.total_seconds() * 1000)

        await self.session.flush()
        await self.session.refresh(execution)

        logger.info(
            f"Completed execution {execution_id}: "
            f"{execution.execution_time_ms}ms, {execution.total_tokens} tokens"
        )

        return execution

    async def fail_execution(
        self,
        execution_id: UUID,
        error_message: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        llm_calls: int = 0,
    ) -> Optional[AgentExecution]:
        """
        Mark an execution as failed.

        Args:
            execution_id: ID of the execution to fail.
            error_message: Description of the error.
            input_tokens: Total input tokens used before failure.
            output_tokens: Total output tokens used before failure.
            llm_calls: Number of LLM API calls made before failure.

        Returns:
            Updated AgentExecution or None if not found.
        """
        execution = await self.get_by_id(execution_id)
        if not execution:
            logger.warning(f"Execution {execution_id} not found")
            return None

        now = datetime.now(timezone.utc)

        execution.status = ExecutionStatus.FAILED
        execution.error_message = error_message
        execution.completed_at = now
        execution.input_tokens = input_tokens
        execution.output_tokens = output_tokens
        execution.llm_calls = llm_calls

        # Calculate execution time
        if execution.started_at:
            delta = now - execution.started_at
            execution.execution_time_ms = int(delta.total_seconds() * 1000)

        await self.session.flush()
        await self.session.refresh(execution)

        logger.error(f"Execution {execution_id} failed: {error_message}")

        return execution

    async def cancel_execution(
        self,
        execution_id: UUID,
    ) -> Optional[AgentExecution]:
        """
        Cancel a running execution.

        Args:
            execution_id: ID of the execution to cancel.

        Returns:
            Updated AgentExecution or None if not found.
        """
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        if execution.is_terminal:
            logger.warning(f"Cannot cancel terminal execution {execution_id}")
            return execution

        now = datetime.now(timezone.utc)
        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = now

        if execution.started_at:
            delta = now - execution.started_at
            execution.execution_time_ms = int(delta.total_seconds() * 1000)

        await self.session.flush()
        await self.session.refresh(execution)

        logger.info(f"Cancelled execution {execution_id}")

        return execution

    # -------------------------------------------------------------------------
    # Logging Methods
    # -------------------------------------------------------------------------
    async def log_thinking(
        self,
        execution_id: UUID,
        thinking: str,
        append: bool = True,
    ) -> Optional[AgentExecution]:
        """
        Log agent thinking/reasoning to an execution.

        Args:
            execution_id: ID of the execution.
            thinking: The thinking content to log.
            append: If True, append to existing thinking. If False, replace.

        Returns:
            Updated AgentExecution or None if not found.
        """
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        if append and execution.thinking:
            execution.thinking = f"{execution.thinking}\n\n{thinking}"
        else:
            execution.thinking = thinking

        await self.session.flush()

        return execution

    async def log_tool_call(
        self,
        execution_id: UUID,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Optional[AgentExecution]:
        """
        Log a tool call to an execution.

        Args:
            execution_id: ID of the execution.
            tool_name: Name of the tool that was called.
            input_data: Input parameters to the tool.
            output_data: Output from the tool (if successful).
            duration_ms: How long the tool call took.
            error: Error message if the tool call failed.

        Returns:
            Updated AgentExecution or None if not found.
        """
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        tool_call = {
            "tool_name": tool_name,
            "input": input_data,
            "output": output_data,
            "duration_ms": duration_ms,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Append to tool_calls array
        current_calls = execution.tool_calls or []
        current_calls.append(tool_call)
        execution.tool_calls = current_calls

        await self.session.flush()

        logger.debug(f"Logged tool call '{tool_name}' for execution {execution_id}")

        return execution

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------
    async def get_by_id(
        self,
        execution_id: UUID,
        include_children: bool = False,
    ) -> Optional[AgentExecution]:
        """
        Get an execution by ID.

        Args:
            execution_id: UUID of the execution.
            include_children: Whether to eager-load child executions.

        Returns:
            AgentExecution or None if not found.
        """
        query = select(AgentExecution).where(AgentExecution.id == execution_id)

        if include_children:
            query = query.options(selectinload(AgentExecution.child_executions))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_chat(
        self,
        chat_id: UUID,
        limit: int = 50,
        include_children: bool = False,
    ) -> list[AgentExecution]:
        """
        Get all executions for a chat.

        Args:
            chat_id: UUID of the chat.
            limit: Maximum number of executions to return.
            include_children: Whether to eager-load child executions.

        Returns:
            List of AgentExecution records.
        """
        query = (
            select(AgentExecution)
            .where(AgentExecution.chat_id == chat_id)
            .order_by(AgentExecution.created_at.desc())
            .limit(limit)
        )

        if include_children:
            query = query.options(selectinload(AgentExecution.child_executions))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_todo(
        self,
        todo_id: UUID,
        limit: int = 20,
    ) -> list[AgentExecution]:
        """
        Get all executions for a todo.

        Args:
            todo_id: UUID of the todo.
            limit: Maximum number of executions to return.

        Returns:
            List of AgentExecution records.
        """
        query = (
            select(AgentExecution)
            .where(AgentExecution.todo_id == todo_id)
            .order_by(AgentExecution.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_execution_tree(
        self,
        root_execution_id: UUID,
    ) -> list[AgentExecution]:
        """
        Get an execution and all its descendants (nested calls).

        Uses recursive loading to get the full tree of executions.

        Args:
            root_execution_id: UUID of the root execution.

        Returns:
            List of AgentExecution records in the tree.
        """
        # First get the root
        root = await self.get_by_id(root_execution_id, include_children=True)
        if not root:
            return []

        # Recursively collect all descendants
        result = [root]
        await self._collect_children(root, result)

        return result

    async def _collect_children(
        self,
        parent: AgentExecution,
        result: list[AgentExecution],
    ) -> None:
        """Recursively collect child executions."""
        if not parent.child_executions:
            return

        for child in parent.child_executions:
            result.append(child)
            # Load children of this child
            child_with_children = await self.get_by_id(child.id, include_children=True)
            if child_with_children:
                await self._collect_children(child_with_children, result)

    async def get_recent_by_agent(
        self,
        agent_name: str,
        limit: int = 20,
    ) -> list[AgentExecution]:
        """
        Get recent executions for a specific agent.

        Args:
            agent_name: Name of the agent.
            limit: Maximum number of executions to return.

        Returns:
            List of AgentExecution records.
        """
        query = (
            select(AgentExecution)
            .where(AgentExecution.agent_name == agent_name)
            .order_by(AgentExecution.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_failed_executions(
        self,
        limit: int = 50,
        agent_name: Optional[str] = None,
    ) -> list[AgentExecution]:
        """
        Get recent failed executions.

        Args:
            limit: Maximum number of executions to return.
            agent_name: Optional filter by agent name.

        Returns:
            List of failed AgentExecution records.
        """
        conditions = [AgentExecution.status == ExecutionStatus.FAILED]

        if agent_name:
            conditions.append(AgentExecution.agent_name == agent_name)

        query = (
            select(AgentExecution)
            .where(and_(*conditions))
            .order_by(AgentExecution.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Statistics Methods
    # -------------------------------------------------------------------------
    async def get_token_usage_by_agent(
        self,
        since: Optional[datetime] = None,
    ) -> dict[str, dict[str, int]]:
        """
        Get token usage statistics grouped by agent.

        Args:
            since: Optional datetime to filter from.

        Returns:
            Dictionary of agent_name -> {input_tokens, output_tokens, total}.
        """
        from sqlalchemy import func

        conditions = []
        if since:
            conditions.append(AgentExecution.created_at >= since)

        query = (
            select(
                AgentExecution.agent_name,
                func.sum(AgentExecution.input_tokens).label("input_tokens"),
                func.sum(AgentExecution.output_tokens).label("output_tokens"),
                func.count(AgentExecution.id).label("execution_count"),
            )
            .group_by(AgentExecution.agent_name)
        )

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        rows = result.all()

        return {
            row.agent_name: {
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "total_tokens": (row.input_tokens or 0) + (row.output_tokens or 0),
                "execution_count": row.execution_count,
            }
            for row in rows
        }
