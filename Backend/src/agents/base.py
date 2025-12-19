# =============================================================================
# Base Agent Classes
# =============================================================================
"""
Base classes and protocols for the agent system.

Provides the foundational abstractions for all agents in the platform:
- AgentContext: Context passed to agents for execution
- AgentResult: Result returned by agent execution
- BaseAgent: Abstract base class for all agents

Usage:
    from src.agents.base import BaseAgent, AgentContext, AgentResult

    class MyAgent(BaseAgent):
        @property
        def name(self) -> str:
            return "my_agent"

        @property
        def description(self) -> str:
            return "Does something useful"

        async def execute(self, context: AgentContext) -> AgentResult:
            # Agent implementation
            return AgentResult(success=True, message="Done!")
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AgentExecution
from src.services.agent_execution_service import AgentExecutionService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Agent Context
# -----------------------------------------------------------------------------
@dataclass
class AgentContext:
    """
    Context passed to agents for execution.

    Contains all the information an agent needs to perform its task,
    including conversation context, user identity, and execution tracking.

    Attributes:
        chat_id: UUID of the conversation (for DB queries).
        task: The specific instruction or task to perform.
        session: Database session for queries.
        created_by: User identifier (e.g., "telegram:123456").
        recent_messages: Last N messages from conversation for context.
        relevant_todos: Todos related to this chat/task.
        parent_execution_id: ID of parent execution (for nested agent calls).
        metadata: Additional context data.

    Example:
        context = AgentContext(
            chat_id=chat_uuid,
            task="Create a todo for reviewing PR #123",
            session=session,
            created_by="telegram:123456",
            recent_messages=[
                {"role": "user", "content": "Can you create a todo..."},
            ],
        )
    """

    # Required fields
    chat_id: UUID
    task: str
    session: AsyncSession

    # User context
    created_by: Optional[str] = None

    # Conversation context (last 10 messages by default)
    recent_messages: list[dict[str, Any]] = field(default_factory=list)

    # Related todos for context
    relevant_todos: list[dict[str, Any]] = field(default_factory=list)

    # Execution tracking (for nested agent calls)
    parent_execution_id: Optional[UUID] = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_input_context(self) -> dict[str, Any]:
        """
        Convert to a dictionary for storing in execution logs.

        Returns:
            Dictionary representation of the context.
        """
        return {
            "chat_id": str(self.chat_id),
            "task": self.task,
            "created_by": self.created_by,
            "recent_messages_count": len(self.recent_messages),
            "relevant_todos_count": len(self.relevant_todos),
            "parent_execution_id": str(self.parent_execution_id) if self.parent_execution_id else None,
            "metadata": self.metadata,
        }


# -----------------------------------------------------------------------------
# Agent Result
# -----------------------------------------------------------------------------
@dataclass
class AgentResult:
    """
    Result returned by agent execution.

    Contains the outcome of an agent's work, including success status,
    output message, and any data produced.

    Attributes:
        success: Whether the execution succeeded.
        message: Human-readable result message.
        data: Structured data output (optional).
        error: Error message if failed (optional).
        delegate_to: Agent to delegate to next (optional).
        delegate_task: Task for the delegated agent (optional).

    Example:
        # Successful result
        result = AgentResult(
            success=True,
            message="Created todo: Review PR #123",
            data={"todo_id": "abc-123", "title": "Review PR #123"},
        )

        # Failed result
        result = AgentResult(
            success=False,
            message="Failed to create todo",
            error="Database connection failed",
        )

        # Delegation result
        result = AgentResult(
            success=True,
            message="Delegating to GitHub agent",
            delegate_to="github",
            delegate_task="Create issue for bug report",
        )
    """

    success: bool
    message: str

    # Structured output data
    data: Optional[dict[str, Any]] = None

    # Error information
    error: Optional[str] = None

    # Delegation (for agent-to-agent calls via orchestrator)
    delegate_to: Optional[str] = None
    delegate_task: Optional[str] = None
    delegate_metadata: Optional[dict[str, Any]] = None

    @property
    def requires_delegation(self) -> bool:
        """Check if this result requires delegation to another agent."""
        return self.delegate_to is not None


# -----------------------------------------------------------------------------
# Agent Protocol
# -----------------------------------------------------------------------------
class AgentProtocol(Protocol):
    """
    Protocol defining the interface for all agents.

    This protocol ensures type safety when working with agents
    without requiring inheritance.
    """

    @property
    def name(self) -> str:
        """Unique identifier for the agent."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what the agent does."""
        ...

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's task."""
        ...


# -----------------------------------------------------------------------------
# Base Agent Class
# -----------------------------------------------------------------------------
class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Provides common functionality for agent execution, including:
    - Execution logging via AgentExecutionService
    - Error handling and result formatting
    - Thinking and tool call logging

    Subclasses must implement:
    - name: Unique agent identifier
    - description: What the agent does
    - _execute_task: The actual task logic

    Example:
        class TodoAgent(BaseAgent):
            @property
            def name(self) -> str:
                return "todo"

            @property
            def description(self) -> str:
                return "Manages todo items and task tracking"

            async def _execute_task(
                self,
                context: AgentContext,
                execution_service: AgentExecutionService,
                execution: AgentExecution,
            ) -> AgentResult:
                # Implementation here
                return AgentResult(success=True, message="Done!")
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the base agent.

        Args:
            api_key: Anthropic API key (optional, may use environment).
            model: Claude model to use for this agent.
        """
        self.api_key = api_key
        self.model = model

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for the agent.

        Returns:
            Agent name (e.g., "todo", "github", "email").
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of what the agent does.

        Returns:
            Description string.
        """
        pass

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's task with full logging.

        This method handles:
        1. Creating an execution record
        2. Calling the subclass implementation
        3. Logging the result
        4. Error handling

        Args:
            context: The execution context.

        Returns:
            AgentResult with the execution outcome.
        """
        execution_service = AgentExecutionService(context.session)

        # Start execution record
        execution = await execution_service.start_execution(
            agent_name=self.name,
            task_description=context.task,
            chat_id=context.chat_id,
            parent_execution_id=context.parent_execution_id,
            input_context=context.to_input_context(),
        )

        try:
            # Call subclass implementation
            result = await self._execute_task(context, execution_service, execution)

            # Complete or fail based on result
            if result.success:
                await execution_service.complete_execution(
                    execution.id,
                    result=result.message,
                    input_tokens=getattr(self, '_total_input_tokens', 0),
                    output_tokens=getattr(self, '_total_output_tokens', 0),
                    llm_calls=getattr(self, '_llm_calls', 0),
                )
            else:
                await execution_service.fail_execution(
                    execution.id,
                    error_message=result.error or result.message,
                    input_tokens=getattr(self, '_total_input_tokens', 0),
                    output_tokens=getattr(self, '_total_output_tokens', 0),
                    llm_calls=getattr(self, '_llm_calls', 0),
                )

            return result

        except Exception as e:
            logger.error(f"Agent {self.name} execution failed: {e}", exc_info=True)

            # Record the failure
            await execution_service.fail_execution(
                execution.id,
                error_message=str(e),
            )

            return AgentResult(
                success=False,
                message=f"Agent execution failed: {str(e)}",
                error=str(e),
            )

    @abstractmethod
    async def _execute_task(
        self,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> AgentResult:
        """
        Execute the agent's task (subclass implementation).

        This method contains the actual agent logic. Subclasses should:
        1. Log thinking via execution_service.log_thinking()
        2. Log tool calls via execution_service.log_tool_call()
        3. Return an AgentResult

        Args:
            context: The execution context.
            execution_service: Service for logging execution details.
            execution: The current execution record.

        Returns:
            AgentResult with the execution outcome.
        """
        pass

    async def log_thinking(
        self,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
        thinking: str,
    ) -> None:
        """
        Helper to log agent thinking.

        Args:
            execution_service: The execution service.
            execution: The current execution.
            thinking: The thinking content.
        """
        await execution_service.log_thinking(execution.id, thinking)

    async def log_tool_call(
        self,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Helper to log a tool call.

        Args:
            execution_service: The execution service.
            execution: The current execution.
            tool_name: Name of the tool.
            input_data: Input to the tool.
            output_data: Output from the tool.
            duration_ms: Execution time.
            error: Error message if failed.
        """
        await execution_service.log_tool_call(
            execution.id,
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            error=error,
        )


# -----------------------------------------------------------------------------
# Agent Registry
# -----------------------------------------------------------------------------
class AgentRegistry:
    """
    Registry for looking up agents by name.

    Provides a central place to register and retrieve agents.

    Example:
        registry = AgentRegistry()
        registry.register(TodoAgent())
        registry.register(GitHubAgent())

        agent = registry.get("todo")
        result = await agent.execute(context)
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """
        Register an agent.

        Args:
            agent: The agent instance to register.
        """
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")

    def get(self, name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.

        Args:
            name: The agent name.

        Returns:
            The agent instance or None if not found.
        """
        return self._agents.get(name)

    def list_agents(self) -> list[dict[str, str]]:
        """
        List all registered agents.

        Returns:
            List of dicts with name and description.
        """
        return [
            {"name": agent.name, "description": agent.description}
            for agent in self._agents.values()
        ]

    @property
    def agent_names(self) -> list[str]:
        """Get list of registered agent names."""
        return list(self._agents.keys())
