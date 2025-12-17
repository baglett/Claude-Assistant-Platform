# =============================================================================
# Orchestrator Agent
# =============================================================================
"""
Main orchestrator agent for the Claude Assistant Platform.

The orchestrator is responsible for:
- Receiving and parsing user messages
- Determining intent and required actions
- Delegating to specialized sub-agents when needed
- Managing conversation context
- Aggregating and formatting responses
"""

import logging
from typing import Optional

import anthropic


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# System Prompt
# -----------------------------------------------------------------------------
ORCHESTRATOR_SYSTEM_PROMPT = """You are an intelligent personal assistant orchestrator for the Claude Assistant Platform.

Your primary responsibilities are:
1. **Understanding User Intent**: Parse natural language requests to determine what the user wants to accomplish.
2. **Task Management**: Help users create, track, and manage todo items and tasks.
3. **Intelligent Routing**: When specialized capabilities are needed (GitHub, Email, Calendar, Obsidian), acknowledge and prepare for delegation to sub-agents.
4. **Context Awareness**: Maintain conversation context and reference previous interactions when relevant.
5. **Clear Communication**: Provide concise, helpful responses that confirm understanding and next steps.

## Response Guidelines:
- Be concise but thorough
- Confirm your understanding of requests before taking action
- When you would need to use external tools (GitHub, email, etc.), explain what you would do
- For todo/task requests, acknowledge the task and its status
- If a request is ambiguous, ask clarifying questions

## Available Capabilities (Future Integration):
- **GitHub**: Create issues, PRs, check CI status, manage repositories
- **Email**: Read, draft, and send emails
- **Calendar**: Schedule events, check availability
- **Obsidian**: Create and search notes in knowledge vault
- **Todo Management**: Create, update, and track tasks

## Current Mode:
You are running in LOCAL DEVELOPMENT mode. External integrations are not yet connected.
When a user requests an action that would require external tools, acknowledge the request
and explain what you would do once the integration is available.

Remember: You are helpful, efficient, and focused on getting things done."""


# -----------------------------------------------------------------------------
# Orchestrator Agent Class
# -----------------------------------------------------------------------------
class OrchestratorAgent:
    """
    Main orchestrator agent using the Anthropic Claude API.

    This agent serves as the central coordinator for the Claude Assistant
    Platform, handling user interactions and delegating to sub-agents.

    Attributes:
        client: Anthropic API client instance.
        model: Claude model identifier to use.
        conversation_history: Dictionary mapping conversation IDs to message lists.
        max_history_length: Maximum number of messages to retain per conversation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_history_length: int = 50
    ) -> None:
        """
        Initialize the orchestrator agent.

        Args:
            api_key: Anthropic API key for authentication.
            model: Claude model identifier to use for completions.
            max_history_length: Maximum messages to retain per conversation.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_history_length = max_history_length

        # In-memory conversation storage (replace with database in production)
        self.conversation_history: dict[str, list[dict]] = {}

        logger.info(f"OrchestratorAgent initialized with model: {model}")

    def _get_conversation(self, conversation_id: str) -> list[dict]:
        """
        Get or create conversation history for a given ID.

        Args:
            conversation_id: Unique identifier for the conversation.

        Returns:
            List of message dictionaries for the conversation.
        """
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []

        return self.conversation_history[conversation_id]

    def _add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> None:
        """
        Add a message to conversation history.

        Args:
            conversation_id: Unique identifier for the conversation.
            role: Message role ('user' or 'assistant').
            content: Message content text.
        """
        conversation = self._get_conversation(conversation_id)
        conversation.append({"role": role, "content": content})

        # Trim history if it exceeds max length
        if len(conversation) > self.max_history_length:
            # Keep the most recent messages
            self.conversation_history[conversation_id] = conversation[
                -self.max_history_length:
            ]

    async def process_message(
        self,
        message: str,
        conversation_id: str
    ) -> tuple[str, Optional[int]]:
        """
        Process a user message and generate a response.

        This is the main entry point for handling user interactions.
        The orchestrator will:
        1. Add the user message to conversation history
        2. Send the conversation to Claude for processing
        3. Parse the response and determine any required actions
        4. Return the response to the user

        Args:
            message: The user's input message.
            conversation_id: Unique identifier for the conversation.

        Returns:
            Tuple of (response_text, tokens_used).

        Raises:
            Exception: If the API call fails.
        """
        logger.info(f"Processing message for conversation: {conversation_id}")

        # Add user message to history
        self._add_message(conversation_id, "user", message)

        # Get full conversation history
        messages = self._get_conversation(conversation_id)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=ORCHESTRATOR_SYSTEM_PROMPT,
                messages=messages
            )

            # Extract response text
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Add assistant response to history
            self._add_message(conversation_id, "assistant", response_text)

            # Calculate tokens used
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            logger.info(
                f"Response generated. Tokens used: {tokens_used}"
            )

            return response_text, tokens_used

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise Exception(f"Failed to get response from Claude: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in process_message: {e}")
            raise

    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear the conversation history for a given ID.

        Args:
            conversation_id: Unique identifier for the conversation.

        Returns:
            True if conversation was cleared, False if it didn't exist.
        """
        if conversation_id in self.conversation_history:
            del self.conversation_history[conversation_id]
            logger.info(f"Cleared conversation: {conversation_id}")
            return True

        return False

    def get_conversation_summary(self, conversation_id: str) -> dict:
        """
        Get a summary of a conversation.

        Args:
            conversation_id: Unique identifier for the conversation.

        Returns:
            Dictionary with conversation metadata.
        """
        conversation = self._get_conversation(conversation_id)

        return {
            "conversation_id": conversation_id,
            "message_count": len(conversation),
            "exists": conversation_id in self.conversation_history
        }
