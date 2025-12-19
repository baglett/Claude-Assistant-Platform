# =============================================================================
# Todo Executor Service
# =============================================================================
"""
Background service for executing pending todos.

This service runs as a background task and periodically checks for pending
todos that are ready for execution. It routes each todo to the appropriate
agent based on the assigned_agent field.

Architecture:
    The TodoExecutor uses the orchestrator's agent registry to directly invoke
    specialized sub-agents for todo execution. This bypasses the orchestrator's
    "Claude decides" loop and goes directly to the known agent, which is more
    efficient for background processing.

Usage:
    from src.services.todo_executor import TodoExecutor

    # In app lifespan
    executor = TodoExecutor(orchestrator=orchestrator)
    task = asyncio.create_task(executor.start())

    # On shutdown
    executor.stop()
    await task
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from src.agents.base import AgentContext
from src.agents.orchestrator import OrchestratorAgent

if TYPE_CHECKING:
    from src.agents.base import BaseAgent

from src.database import get_session
from src.database.models import Todo
from src.models.todo import AgentType, TodoStatus
from src.services.todo_service import TodoService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Todo Executor Configuration
# -----------------------------------------------------------------------------
# Default interval between execution checks (in seconds)
DEFAULT_CHECK_INTERVAL = 30

# Maximum todos to process in a single check cycle
DEFAULT_BATCH_SIZE = 5

# Maximum retries for failed todos before marking as permanently failed
MAX_RETRIES = 3


# -----------------------------------------------------------------------------
# Todo Executor Class
# -----------------------------------------------------------------------------
class TodoExecutor:
    """
    Background service for executing pending todos.

    The executor periodically scans for pending todos that are ready for
    execution (no scheduled_at or scheduled_at in the past) and routes
    them to the appropriate agent.

    Currently, execution is a placeholder that marks todos as completed.
    Future versions will integrate with actual sub-agents (GitHub, Email,
    Calendar, Obsidian) via MCP servers.

    Attributes:
        orchestrator: The OrchestratorAgent for processing orchestrator tasks.
        check_interval: Seconds between execution checks.
        batch_size: Maximum todos to process per check.
        _running: Flag to control the execution loop.
        _task: Reference to the background task.

    Example:
        executor = TodoExecutor(
            orchestrator=orchestrator,
            check_interval=60,
            batch_size=10,
        )
        task = asyncio.create_task(executor.start())

        # Later, on shutdown
        executor.stop()
        await task
    """

    def __init__(
        self,
        orchestrator: Optional[OrchestratorAgent] = None,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        """
        Initialize the todo executor.

        Args:
            orchestrator: OrchestratorAgent for processing orchestrator-assigned tasks.
            check_interval: Seconds between checks for pending todos.
            batch_size: Maximum todos to process per check cycle.
        """
        self.orchestrator = orchestrator
        self.check_interval = check_interval
        self.batch_size = batch_size
        self._running = False
        self._task: Optional[asyncio.Task] = None

        logger.info(
            f"TodoExecutor initialized. "
            f"Check interval: {check_interval}s, Batch size: {batch_size}"
        )

    # -------------------------------------------------------------------------
    # Lifecycle Management
    # -------------------------------------------------------------------------
    async def start(self) -> None:
        """
        Start the background execution loop.

        This method runs indefinitely until stop() is called. It periodically
        checks for pending todos and executes them.
        """
        self._running = True
        logger.info("TodoExecutor started")

        while self._running:
            try:
                # Process pending todos
                processed = await self._execute_pending_todos()

                if processed > 0:
                    logger.info(f"Processed {processed} todos")

            except asyncio.CancelledError:
                logger.info("TodoExecutor received cancellation")
                break

            except Exception as e:
                logger.error(f"Error in executor loop: {e}", exc_info=True)

            # Wait before next check
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                logger.info("TodoExecutor sleep cancelled")
                break

        logger.info("TodoExecutor stopped")

    def stop(self) -> None:
        """
        Signal the executor to stop.

        This sets the running flag to False, causing the execution loop
        to exit after the current iteration.
        """
        logger.info("TodoExecutor stopping...")
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if the executor is currently running."""
        return self._running

    # -------------------------------------------------------------------------
    # Execution Logic
    # -------------------------------------------------------------------------
    async def _execute_pending_todos(self) -> int:
        """
        Find and execute pending todos.

        Queries for todos that are ready for execution and processes
        each one according to its assigned agent.

        Returns:
            Number of todos processed.
        """
        processed_count = 0

        async with get_session() as session:
            service = TodoService(session)

            # Get pending todos ready for execution
            pending_todos = await service.get_pending_for_execution(
                limit=self.batch_size
            )

            if not pending_todos:
                return 0

            logger.debug(f"Found {len(pending_todos)} pending todos")

            # Process each todo
            for todo in pending_todos:
                try:
                    success = await self._execute_single_todo(todo, service)

                    if success:
                        processed_count += 1

                except Exception as e:
                    logger.error(f"Error executing todo {todo.id}: {e}")
                    await self._mark_todo_failed(
                        service, todo.id, f"Execution error: {e}"
                    )

            # Commit all changes
            await session.commit()

        return processed_count

    async def _execute_single_todo(
        self,
        todo: Todo,
        service: TodoService,
    ) -> bool:
        """
        Execute a single todo item.

        Routes the todo to the appropriate agent based on assigned_agent
        and updates the status accordingly.

        Args:
            todo: The todo to execute.
            service: TodoService for status updates.

        Returns:
            True if execution succeeded, False otherwise.
        """
        logger.info(
            f"Executing todo {todo.id}: '{todo.title}' "
            f"(agent: {todo.assigned_agent})"
        )

        # Check retry limit
        if todo.execution_attempts >= MAX_RETRIES:
            logger.warning(
                f"Todo {todo.id} exceeded max retries ({MAX_RETRIES}). "
                "Marking as failed."
            )
            await self._mark_todo_failed(
                service,
                todo.id,
                f"Exceeded maximum retry attempts ({MAX_RETRIES})"
            )
            return False

        # Mark as in progress
        await service.update_status(todo.id, TodoStatus.IN_PROGRESS)

        # Route to appropriate handler
        agent_type = AgentType(todo.assigned_agent) if todo.assigned_agent else None
        agent_name = agent_type.value if agent_type else None

        try:
            # First, check if we have a registered agent for this type
            if agent_name and self.orchestrator:
                registered_agent = self.orchestrator.get_agent(agent_name)
                if registered_agent:
                    # Use the registered agent directly
                    result = await self._execute_via_registered_agent(
                        todo, registered_agent, service
                    )
                else:
                    # Fall back to agent-specific methods for unregistered agents
                    result = await self._execute_via_fallback(todo, agent_type)
            elif agent_type == AgentType.ORCHESTRATOR or agent_type is None:
                result = await self._execute_orchestrator_todo(todo)
            else:
                result = await self._execute_via_fallback(todo, agent_type)

            # Mark as completed with result
            await service.update_status(
                todo.id,
                TodoStatus.COMPLETED,
                result=result,
            )
            logger.info(f"Todo {todo.id} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Todo {todo.id} execution failed: {e}")
            await self._mark_todo_failed(service, todo.id, str(e))
            return False

    async def _mark_todo_failed(
        self,
        service: TodoService,
        todo_id: UUID,
        error_message: str,
    ) -> None:
        """
        Mark a todo as failed with an error message.

        Args:
            service: TodoService for status update.
            todo_id: ID of the todo to mark failed.
            error_message: Error description.
        """
        await service.update_status(
            todo_id,
            TodoStatus.FAILED,
            error_message=error_message,
        )

    # -------------------------------------------------------------------------
    # Agent Execution Methods
    # -------------------------------------------------------------------------
    async def _execute_via_registered_agent(
        self,
        todo: Todo,
        agent: "BaseAgent",
        service: TodoService,
    ) -> str:
        """
        Execute a todo via a registered sub-agent.

        This method directly invokes a registered agent from the orchestrator's
        registry, bypassing the orchestrator's delegation logic. This is more
        efficient for background processing where we already know which agent
        should handle the task.

        Args:
            todo: The todo to execute.
            agent: The registered agent instance.
            service: TodoService for any needed queries.

        Returns:
            Result string from the agent.
        """
        logger.info(f"Executing todo {todo.id} via registered agent: {agent.name}")

        # Build task description from todo
        task_parts = [f"Execute the following task: {todo.title}"]
        if todo.description:
            task_parts.append(f"\nDescription: {todo.description}")
        if todo.task_metadata:
            task_parts.append(f"\nMetadata: {todo.task_metadata}")

        task = "\n".join(task_parts)

        # Create agent context
        async with get_session() as session:
            context = AgentContext(
                chat_id=todo.chat_id,
                task=task,
                session=session,
                created_by=todo.created_by,
                metadata=todo.task_metadata or {},
            )

            # Execute the agent
            result = await agent.execute(context)

            if result.success:
                return f"[{agent.name.title()} Agent] {result.message}"
            else:
                raise Exception(result.error or result.message)

    async def _execute_via_fallback(self, todo: Todo, agent_type: AgentType) -> str:
        """
        Execute a todo via fallback methods when no agent is registered.

        This routes to the legacy agent-specific methods which are currently
        placeholders for future MCP integrations.

        Args:
            todo: The todo to execute.
            agent_type: The agent type to use.

        Returns:
            Result string from the fallback handler.
        """
        if agent_type == AgentType.GITHUB:
            return await self._execute_github_todo(todo)
        elif agent_type == AgentType.EMAIL:
            return await self._execute_email_todo(todo)
        elif agent_type == AgentType.CALENDAR:
            return await self._execute_calendar_todo(todo)
        elif agent_type == AgentType.OBSIDIAN:
            return await self._execute_obsidian_todo(todo)
        else:
            return f"Unknown agent type: {agent_type}. No fallback available."

    async def _execute_orchestrator_todo(self, todo: Todo) -> str:
        """
        Execute a todo assigned to the orchestrator.

        These are general tasks that the orchestrator handles directly.
        The orchestrator will determine the best approach for execution.

        Args:
            todo: The todo to execute.

        Returns:
            Result string describing the execution.
        """
        if not self.orchestrator:
            return (
                f"[Orchestrator] Task '{todo.title}' cannot be executed. "
                "Orchestrator not available."
            )

        # Create an execution context for the agent
        async with get_session() as session:
            context = AgentContext(
                chat_id=todo.chat_id,
                task=f"Execute task: {todo.title}\n\nDescription: {todo.description or 'No description'}",
                session=session,
                created_by=todo.created_by,
                metadata=todo.task_metadata or {},
            )

            # Execute via orchestrator's _execute_task (bypasses process_message)
            # This is for background tasks that don't need chat history
            result = await self.orchestrator.execute(context)

            if result.success:
                return f"[Orchestrator] {result.message}"
            else:
                raise Exception(result.error or result.message)

    async def _execute_github_todo(self, todo: Todo) -> str:
        """
        Execute a todo assigned to the GitHub agent.

        Routes to the GitHub MCP server for repository operations.
        Currently a placeholder implementation.

        Args:
            todo: The todo to execute.

        Returns:
            Result string describing the execution.
        """
        # TODO: Implement GitHub MCP integration
        # Extract metadata like repo, action type, etc.
        metadata = todo.task_metadata or {}
        repo = metadata.get("repo", "unknown")

        return (
            f"[GitHub Agent] Task '{todo.title}' for repo '{repo}'. "
            "GitHub integration not yet implemented."
        )

    async def _execute_email_todo(self, todo: Todo) -> str:
        """
        Execute a todo assigned to the Email agent.

        Routes to the Email MCP server for email operations.
        Currently a placeholder implementation.

        Args:
            todo: The todo to execute.

        Returns:
            Result string describing the execution.
        """
        # TODO: Implement Email MCP integration
        metadata = todo.task_metadata or {}
        recipients = metadata.get("recipients", [])

        return (
            f"[Email Agent] Task '{todo.title}' for recipients {recipients}. "
            "Email integration not yet implemented."
        )

    async def _execute_calendar_todo(self, todo: Todo) -> str:
        """
        Execute a todo assigned to the Calendar agent.

        Routes to the Calendar MCP server for scheduling operations.
        Currently a placeholder implementation.

        Args:
            todo: The todo to execute.

        Returns:
            Result string describing the execution.
        """
        # TODO: Implement Calendar MCP integration
        metadata = todo.task_metadata or {}
        event_time = metadata.get("event_time")

        return (
            f"[Calendar Agent] Task '{todo.title}' "
            f"{'at ' + event_time if event_time else ''}. "
            "Calendar integration not yet implemented."
        )

    async def _execute_obsidian_todo(self, todo: Todo) -> str:
        """
        Execute a todo assigned to the Obsidian agent.

        Routes to the Obsidian MCP server for note operations.
        Currently a placeholder implementation.

        Args:
            todo: The todo to execute.

        Returns:
            Result string describing the execution.
        """
        # TODO: Implement Obsidian MCP integration
        metadata = todo.task_metadata or {}
        vault = metadata.get("vault", "default")
        note_path = metadata.get("note_path")

        return (
            f"[Obsidian Agent] Task '{todo.title}' in vault '{vault}'"
            f"{' at ' + note_path if note_path else ''}. "
            "Obsidian integration not yet implemented."
        )

    # -------------------------------------------------------------------------
    # Manual Execution
    # -------------------------------------------------------------------------
    async def execute_todo_now(self, todo_id: UUID) -> tuple[bool, str]:
        """
        Manually execute a specific todo immediately.

        This bypasses the normal scheduling and processes the todo
        right away. Useful for on-demand execution via API.

        Args:
            todo_id: UUID of the todo to execute.

        Returns:
            Tuple of (success, result_or_error_message).
        """
        logger.info(f"Manual execution requested for todo {todo_id}")

        async with get_session() as session:
            service = TodoService(session)

            todo = await service.get_by_id(todo_id)
            if not todo:
                return False, f"Todo {todo_id} not found"

            if not todo.is_executable:
                return False, f"Todo is in '{todo.status}' state and cannot be executed"

            try:
                success = await self._execute_single_todo(todo, service)
                await session.commit()

                if success:
                    return True, f"Todo executed successfully"
                else:
                    return False, "Execution failed"

            except Exception as e:
                logger.error(f"Manual execution failed: {e}")
                return False, str(e)
