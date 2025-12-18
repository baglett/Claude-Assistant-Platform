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
"""

import logging
from typing import Optional
from uuid import UUID

import anthropic

from src.services.chat_service import ChatService, get_chat_service


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

    Conversation history is persisted to the database for context management
    across sessions.

    Attributes:
        client: Anthropic API client instance.
        model: Claude model identifier to use.
        chat_service: Service for database chat operations.
        max_history_length: Maximum number of messages to include in context.
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
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_history_length = max_history_length
        self.chat_service = chat_service or get_chat_service()

        logger.info(f"OrchestratorAgent initialized with model: {model}")

    async def process_message(
        self,
        message: str,
        chat_id: UUID,
    ) -> tuple[str, Optional[int]]:
        """
        Process a user message and generate a response.

        This is the main entry point for handling user interactions.
        The orchestrator will:
        1. Save the user message to the database
        2. Load conversation history from the database
        3. Send the conversation to Claude for processing
        4. Save the assistant response to the database
        5. Return the response to the user

        Args:
            message: The user's input message.
            chat_id: UUID of the chat session (from database).

        Returns:
            Tuple of (response_text, tokens_used).

        Raises:
            Exception: If the API call fails.
        """
        logger.info(f"Processing message for chat: {chat_id}")

        # Save user message to database
        await self.chat_service.add_user_message(chat_id, message)

        # Get conversation history from database
        messages = await self.chat_service.get_conversation_history(
            chat_id, limit=self.max_history_length
        )

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=ORCHESTRATOR_SYSTEM_PROMPT,
                messages=messages,
            )

            # Extract response text
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Calculate tokens used
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            tokens_used = input_tokens + output_tokens

            # Save assistant response to database with metadata
            await self.chat_service.add_assistant_message(
                chat_id=chat_id,
                content=response_text,
                llm_model=self.model,
                tokens_used=tokens_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            logger.info(f"Response generated. Tokens used: {tokens_used}")

            return response_text, tokens_used

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise Exception(f"Failed to get response from Claude: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in process_message: {e}")
            raise

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
        }
