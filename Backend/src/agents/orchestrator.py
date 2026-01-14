# =============================================================================
# Orchestrator Agent
# =============================================================================
"""
Main orchestrator agent for the Claude Assistant Platform.

The orchestrator is responsible for:
- Receiving and parsing user messages
- Determining intent and required actions
- Delegating to specialized sub-agents when needed
- Managing conversation context (stored in database)
- Aggregating and formatting responses
- Logging all execution details to the database

This is the "Agent of Agents" - it coordinates work across specialized
sub-agents like TodoAgent, GitHubAgent, etc.

Architecture:
    OrchestratorAgent extends BaseAgent for consistent execution logging.
    It uses AgentRegistry to look up and delegate to sub-agents.
    The delegation flow is:
        1. User message -> Orchestrator
        2. Orchestrator determines intent (via Claude)
        3. Orchestrator either handles directly or delegates to sub-agent
        4. Sub-agent executes and returns result
        5. Orchestrator formats and returns response to user
"""

import json
import logging
from typing import Any, Optional
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import (
    AgentContext,
    AgentRegistry,
    AgentResult,
    BaseAgent,
)
from src.agents.router import AgentRouter
from src.config.settings import get_settings
from src.database import AgentExecution, get_session
from src.services.agent_execution_service import AgentExecutionService
from src.services.chat_service import ChatService, get_chat_service


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# System Prompt
# -----------------------------------------------------------------------------
ORCHESTRATOR_SYSTEM_PROMPT = """You are the Orchestrator Agent for the Claude Assistant Platform.

You coordinate user requests by either handling them directly or delegating to specialized sub-agents.

## Your Responsibilities:
1. **Parse User Intent**: Understand what the user wants to accomplish.
2. **Route Requests**: Decide whether to handle directly or delegate.
3. **Delegate Smartly**: Use specialized agents for domain-specific tasks.
4. **Provide Clear Responses**: Confirm actions and summarize results.

## Available Sub-Agents:

{agent_list}

## Available Tools:

- **delegate_to_agent**: Delegate a task to a specialized agent. Use this when the task requires specialized capabilities.
- **get_available_agents**: List all registered agents and their descriptions.

## Routing Guidelines:

1. **Todo Management** → Delegate to `todo` agent
   - Creating, listing, updating todos
   - Task tracking and management

2. **Motion Tasks** → Delegate to `motion` agent (when available)
   - AI-scheduled tasks and projects
   - Motion workspace management

3. **Calendar Operations** → Delegate to `calendar` agent (when available)
   - Scheduling meetings and events
   - Checking availability (free/busy)
   - Listing, creating, updating calendar events
   - Quick event creation from natural language

4. **Email Operations** → Delegate to `email` agent (when available)
   - Reading, searching, sending emails
   - Managing drafts and labels
   - Archiving and organizing inbox

5. **GitHub Operations** → Delegate to `github` agent (when available)
   - Repository management, issues, PRs

6. **General Queries** → Handle directly
   - Greetings, help requests, clarifications
   - Questions about capabilities

## Response Guidelines:
- Be concise but helpful
- Always confirm what action you're taking
- Summarize the result from delegated agents
- Ask clarifying questions when requests are ambiguous

Remember: You are the coordinator. Delegate domain tasks to specialists!"""


# -----------------------------------------------------------------------------
# Orchestrator Tool Definitions
# -----------------------------------------------------------------------------
ORCHESTRATOR_TOOLS = [
    {
        "name": "delegate_to_agent",
        "description": (
            "Delegate a task to a specialized sub-agent. Use this when the task "
            "requires domain-specific capabilities. The agent will execute the task "
            "and return a result."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": (
                        "Name of the agent to delegate to (e.g., 'todo', 'github', 'email'). "
                        "Use get_available_agents to see what agents are available."
                    ),
                },
                "task": {
                    "type": "string",
                    "description": (
                        "Clear description of what the agent should do. Be specific "
                        "about the action required."
                    ),
                },
                "context": {
                    "type": "object",
                    "description": (
                        "Additional context for the agent (optional). Include any "
                        "relevant metadata or parameters."
                    ),
                },
            },
            "required": ["agent_name", "task"],
        },
    },
    {
        "name": "get_available_agents",
        "description": (
            "Get a list of all available sub-agents and their descriptions. "
            "Use this to understand what capabilities are available for delegation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# -----------------------------------------------------------------------------
# Orchestrator Agent Class
# -----------------------------------------------------------------------------
class OrchestratorAgent(BaseAgent):
    """
    Main orchestrator agent using the Anthropic Claude API.

    This agent serves as the central coordinator for the Claude Assistant
    Platform, handling user interactions and delegating to sub-agents.

    The orchestrator extends BaseAgent to get automatic execution logging,
    and uses AgentRegistry to manage and invoke sub-agents.

    Attributes:
        client: Anthropic API client instance.
        model: Claude model identifier to use.
        registry: Registry of available sub-agents.
        chat_service: Service for database chat operations.
        max_history_length: Maximum number of messages to include in context.
        router: AgentRouter for fast routing bypassing LLM classification.
        router_enabled: Whether the hybrid router is enabled.

    Example:
        orchestrator = OrchestratorAgent(api_key="sk-...")
        orchestrator.register_agent(TodoAgent(api_key="sk-..."))

        response, tokens = await orchestrator.process_message(
            message="Create a todo to review PR #123",
            chat_id=chat_uuid,
            created_by="telegram:123",
        )
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_history_length: int = 50,
        chat_service: Optional[ChatService] = None,
    ) -> None:
        """
        Initialize the orchestrator agent.

        Args:
            api_key: Anthropic API key for authentication.
            model: Claude model identifier to use for completions.
            max_history_length: Maximum messages to include in context.
            chat_service: Optional ChatService instance for database operations.
        """
        super().__init__(api_key=api_key, model=model)

        self.client = anthropic.Anthropic(api_key=api_key)
        self.max_history_length = max_history_length
        self.chat_service = chat_service or get_chat_service()

        # Initialize agent registry
        self.registry = AgentRegistry()

        # Initialize router for fast bypassing of LLM classification
        # Router uses the registry to look up agents, so it's created after registry
        settings = get_settings()
        self.router_enabled = settings.router_enabled
        self.router: AgentRouter | None = None
        if self.router_enabled:
            self.router = AgentRouter(self.registry)
            logger.info("Hybrid router enabled for fast agent routing")

        # Token tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

        logger.info(f"OrchestratorAgent initialized with model: {model}")

    @property
    def name(self) -> str:
        """Agent identifier."""
        return "orchestrator"

    @property
    def description(self) -> str:
        """Agent description."""
        return "Main coordinator that delegates tasks to specialized sub-agents"

    # -------------------------------------------------------------------------
    # Agent Registry Management
    # -------------------------------------------------------------------------
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register a sub-agent with the orchestrator.

        Args:
            agent: BaseAgent instance to register.

        Example:
            orchestrator.register_agent(TodoAgent(api_key=api_key))
            orchestrator.register_agent(GitHubAgent(api_key=api_key))
        """
        self.registry.register(agent)
        logger.info(f"Registered sub-agent: {agent.name}")

    async def initialize_router(self, session: Optional[AsyncSession] = None) -> None:
        """
        Initialize the hybrid router for fast agent routing.

        This must be called after all agents are registered and before
        processing messages. It loads agent patterns from the database
        and sets up caching.

        Args:
            session: Optional database session for loading agent data.
        """
        if self.router and self.router_enabled:
            await self.router.initialize(session)
            logger.info("Hybrid router initialized with registered agents")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get a registered agent by name.

        Args:
            name: Agent name.

        Returns:
            BaseAgent instance or None if not found.
        """
        return self.registry.get(name)

    def list_agents(self) -> list[dict[str, str]]:
        """
        List all registered agents.

        Returns:
            List of dicts with agent name and description.
        """
        return self.registry.list_agents()

    def _get_agent_list_text(self) -> str:
        """
        Generate formatted text listing available agents for the system prompt.

        Returns:
            Formatted string of agent names and descriptions.
        """
        agents = self.list_agents()
        if not agents:
            return "No specialized agents currently registered."

        lines = []
        for agent in agents:
            lines.append(f"- **{agent['name']}**: {agent['description']}")
        return "\n".join(lines)

    def _get_system_prompt(self) -> str:
        """
        Get the system prompt with dynamically populated agent list.

        Returns:
            Complete system prompt string.
        """
        return ORCHESTRATOR_SYSTEM_PROMPT.format(
            agent_list=self._get_agent_list_text()
        )

    # -------------------------------------------------------------------------
    # Main Entry Point
    # -------------------------------------------------------------------------
    async def process_message(
        self,
        message: str,
        chat_id: UUID,
        created_by: Optional[str] = None,
    ) -> tuple[str, Optional[int]]:
        """
        Process a user message and generate a response.

        This is the main entry point for handling user interactions.
        The orchestrator will:
        1. Save the user message to the database
        2. Load conversation history from the database
        3. Create an AgentContext and execute
        4. Save the assistant response to the database
        5. Return the response to the user

        Args:
            message: The user's input message.
            chat_id: UUID of the chat session (from database).
            created_by: Optional creator identifier for todos (e.g., "telegram:123").

        Returns:
            Tuple of (response_text, tokens_used).

        Raises:
            Exception: If the API call fails.
        """
        logger.info(f"Processing message for chat: {chat_id}")

        # Save user message to database
        await self.chat_service.add_user_message(chat_id, message)

        # Get conversation history from database
        recent_messages = await self.chat_service.get_conversation_history(
            chat_id, limit=self.max_history_length
        )

        # Get a database session for execution
        async with get_session() as session:
            # Build context for execution
            context = AgentContext(
                chat_id=chat_id,
                task=message,  # The task is the user's message
                session=session,
                created_by=created_by,
                recent_messages=recent_messages,
            )

            # Execute the orchestrator logic (via BaseAgent.execute)
            result = await self.execute(context)

            # Commit any changes made during execution
            await session.commit()

        # Calculate tokens
        tokens_used = self._total_input_tokens + self._total_output_tokens

        # Save assistant response to database with metadata
        await self.chat_service.add_assistant_message(
            chat_id=chat_id,
            content=result.message,
            llm_model=self.model,
            tokens_used=tokens_used,
            input_tokens=self._total_input_tokens,
            output_tokens=self._total_output_tokens,
        )

        logger.info(f"Response generated. Tokens used: {tokens_used}")

        return result.message, tokens_used

    # -------------------------------------------------------------------------
    # BaseAgent Implementation
    # -------------------------------------------------------------------------
    async def _execute_task(
        self,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> AgentResult:
        """
        Execute the orchestrator's task.

        This method first tries the hybrid router for fast routing to agents,
        bypassing the LLM classification when confident. If routing is not
        confident, falls back to the full tool calling loop.

        Args:
            context: Execution context with task and chat info.
            execution_service: Service for logging execution details.
            execution: Current execution record.

        Returns:
            AgentResult with the response.
        """
        # Reset token counters for this execution
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

        # Log initial thinking
        await self.log_thinking(
            execution_service,
            execution,
            f"Received task: {context.task}\n"
            f"Available agents: {[a['name'] for a in self.list_agents()]}",
        )

        try:
            # ----------------------------------------------------------------
            # Try fast routing first (bypasses LLM classification)
            # ----------------------------------------------------------------
            if self.router and self.router_enabled:
                await self.log_thinking(
                    execution_service,
                    execution,
                    "Attempting fast routing via hybrid router...",
                )

                routed_result = await self.router.try_route(context.task, context)

                if routed_result:
                    # Router successfully handled the request
                    router_stats = self.router.get_stats()
                    await self.log_thinking(
                        execution_service,
                        execution,
                        f"Fast routing successful! Bypassed LLM classification.\n"
                        f"Router stats: {router_stats}",
                    )

                    return AgentResult(
                        success=routed_result.success,
                        message=routed_result.message,
                        data={
                            **(routed_result.data or {}),
                            "routed_directly": True,
                            "router_stats": router_stats,
                            "tokens_used": 0,  # No orchestrator LLM tokens used
                            "llm_calls": 0,
                        },
                        error=routed_result.error,
                    )
                else:
                    # Router not confident, fall back to LLM
                    await self.log_thinking(
                        execution_service,
                        execution,
                        "Router not confident, falling back to LLM classification...",
                    )

            # ----------------------------------------------------------------
            # Fall back to LLM-based tool calling loop
            # ----------------------------------------------------------------
            response_text = await self._process_with_tools(
                context=context,
                execution_service=execution_service,
                execution=execution,
            )

            return AgentResult(
                success=True,
                message=response_text,
                data={
                    "tokens_used": self._total_input_tokens + self._total_output_tokens,
                    "llm_calls": self._llm_calls,
                    "routed_directly": False,
                },
            )

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return AgentResult(
                success=False,
                message=f"Failed to get response from Claude: {e}",
                error=str(e),
            )

        except Exception as e:
            logger.error(f"Unexpected error in orchestrator: {e}", exc_info=True)
            return AgentResult(
                success=False,
                message=f"An error occurred: {e}",
                error=str(e),
            )

    async def _process_with_tools(
        self,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
        max_iterations: int = 10,
    ) -> str:
        """
        Process with tool calling support.

        Implements the tool use loop - calls Claude, handles any tool calls,
        sends results back to Claude, and continues until Claude produces
        a final text response.

        Args:
            context: Agent context.
            execution_service: For logging.
            execution: Current execution.
            max_iterations: Maximum number of tool call iterations.

        Returns:
            Final response text.
        """
        # Build messages from context
        working_messages = list(context.recent_messages)

        for iteration in range(max_iterations):
            logger.debug(f"Orchestrator tool loop iteration {iteration + 1}")

            # Call Claude API with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self._get_system_prompt(),
                tools=ORCHESTRATOR_TOOLS,
                messages=working_messages,
            )

            # Track tokens
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._llm_calls += 1

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Claude is done - extract final text response
                return self._extract_text_response(response)

            elif response.stop_reason == "tool_use":
                # Claude wants to use tools - process them
                logger.info(f"Processing tool calls (iteration {iteration + 1})")

                await self.log_thinking(
                    execution_service,
                    execution,
                    f"Iteration {iteration + 1}: Claude requested tool calls",
                )

                # Add assistant's response (with tool_use blocks) to messages
                working_messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Process tool calls and collect results
                tool_results = await self._execute_tool_calls(
                    content_blocks=response.content,
                    context=context,
                    execution_service=execution_service,
                    execution=execution,
                )

                # Add tool results to messages
                working_messages.append({
                    "role": "user",
                    "content": tool_results,
                })

            else:
                # Unexpected stop reason
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                return self._extract_text_response(response)

        # Max iterations reached
        logger.warning(f"Max tool iterations ({max_iterations}) reached")
        return (
            "I apologize, but I encountered an issue processing your request. "
            "Please try again or rephrase your message."
        )

    async def _execute_tool_calls(
        self,
        content_blocks: list,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> list[dict[str, Any]]:
        """
        Execute tool calls from Claude's response.

        Args:
            content_blocks: Content blocks from Claude's response.
            context: Agent context.
            execution_service: For logging.
            execution: Current execution.

        Returns:
            List of tool_result content blocks.
        """
        tool_results = []

        for block in content_blocks:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            logger.info(f"Orchestrator executing tool: {tool_name}")

            try:
                # Execute the tool
                if tool_name == "delegate_to_agent":
                    result = await self._tool_delegate_to_agent(
                        tool_input,
                        context,
                        execution_service,
                        execution,
                    )
                elif tool_name == "get_available_agents":
                    result = self._tool_get_available_agents()
                else:
                    result = {"success": False, "error": f"Unknown tool: {tool_name}"}

                # Log the tool call
                await self.log_tool_call(
                    execution_service,
                    execution,
                    tool_name=tool_name,
                    input_data=tool_input,
                    output_data=result,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")

                await self.log_tool_call(
                    execution_service,
                    execution,
                    tool_name=tool_name,
                    input_data=tool_input,
                    error=str(e),
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"success": False, "error": str(e)}),
                    "is_error": True,
                })

        return tool_results

    # -------------------------------------------------------------------------
    # Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_delegate_to_agent(
        self,
        input_data: dict[str, Any],
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> dict[str, Any]:
        """
        Delegate a task to a sub-agent.

        This is the core delegation mechanism. It:
        1. Looks up the agent in the registry
        2. Creates a new context for the sub-agent (with parent execution ID)
        3. Executes the sub-agent
        4. Returns the result

        Args:
            input_data: Tool input with agent_name, task, and optional context.
            context: Parent agent context.
            execution_service: For logging.
            execution: Current execution.

        Returns:
            Result from the sub-agent.
        """
        agent_name = input_data.get("agent_name")
        task = input_data.get("task")
        extra_context = input_data.get("context", {})

        # Validate inputs
        if not agent_name:
            return {"success": False, "error": "agent_name is required"}
        if not task:
            return {"success": False, "error": "task is required"}

        # Look up agent
        agent = self.get_agent(agent_name)
        if not agent:
            available = [a["name"] for a in self.list_agents()]
            return {
                "success": False,
                "error": f"Agent '{agent_name}' not found. Available: {available}",
            }

        logger.info(f"Delegating to agent '{agent_name}': {task}")

        await self.log_thinking(
            execution_service,
            execution,
            f"Delegating task to '{agent_name}' agent:\n{task}",
        )

        # Create context for sub-agent
        # Pass the parent execution ID so we can trace the call chain
        sub_context = AgentContext(
            chat_id=context.chat_id,
            task=task,
            session=context.session,
            created_by=context.created_by,
            recent_messages=context.recent_messages,  # Share conversation context
            relevant_todos=context.relevant_todos,
            parent_execution_id=execution.id,  # Link to parent
            metadata={**context.metadata, **extra_context},
        )

        # Execute the sub-agent
        result = await agent.execute(sub_context)

        # Accumulate tokens from sub-agent (if tracked)
        if hasattr(agent, "_total_input_tokens"):
            self._total_input_tokens += agent._total_input_tokens
            self._total_output_tokens += agent._total_output_tokens
            self._llm_calls += agent._llm_calls

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "error": result.error,
            "agent": agent_name,
        }

    def _tool_get_available_agents(self) -> dict[str, Any]:
        """
        Get list of available agents.

        Returns:
            Dict with list of agent info.
        """
        agents = self.list_agents()
        return {
            "success": True,
            "count": len(agents),
            "agents": agents,
        }

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _extract_text_response(self, response) -> str:
        """
        Extract text content from Claude's response.

        Concatenates all text blocks in the response content.

        Args:
            response: Claude API response object.

        Returns:
            Combined text from all text blocks.
        """
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts)

    # -------------------------------------------------------------------------
    # Conversation Management
    # -------------------------------------------------------------------------
    async def clear_conversation(self, chat_id: UUID) -> bool:
        """
        Clear the conversation history for a chat.

        Args:
            chat_id: UUID of the chat to clear.

        Returns:
            True if messages were cleared, False otherwise.
        """
        try:
            count = await self.chat_service.clear_chat_messages(chat_id)
            logger.info(f"Cleared {count} messages from chat: {chat_id}")
            return count > 0
        except Exception as e:
            logger.error(f"Error clearing chat {chat_id}: {e}")
            return False

    async def get_conversation_summary(self, chat_id: UUID) -> dict:
        """
        Get a summary of a conversation.

        Args:
            chat_id: UUID of the chat.

        Returns:
            Dictionary with conversation metadata.
        """
        messages = await self.chat_service.get_messages(chat_id)

        return {
            "chat_id": str(chat_id),
            "message_count": len(messages),
            "registered_agents": [a["name"] for a in self.list_agents()],
        }

    # -------------------------------------------------------------------------
    # Router Management
    # -------------------------------------------------------------------------
    def get_router_stats(self) -> dict[str, Any]:
        """
        Get router performance statistics.

        Returns statistics about routing decisions including:
        - Total requests processed
        - Tier hit counts (regex, hybrid, LLM)
        - Cache hit rate
        - Orchestrator fallback rate
        - Average latency

        Returns:
            Dictionary with router performance metrics, or empty dict if
            router is disabled.
        """
        if self.router and self.router_enabled:
            return self.router.get_stats()
        return {}

    def reset_router_stats(self) -> None:
        """Reset router performance statistics."""
        if self.router:
            self.router.reset_stats()

    async def refresh_router(self, session: Optional[AsyncSession] = None) -> None:
        """
        Refresh router configuration.

        Call this when agent configuration changes in the database
        to reload patterns, keywords, and embeddings.

        Args:
            session: Optional database session for reloading agent data.
        """
        if self.router and self.router_enabled:
            await self.router.refresh(session)
            logger.info("Router configuration refreshed")
