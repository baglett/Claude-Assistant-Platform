# =============================================================================
# Telegram Message Handler
# =============================================================================
"""
Message handler for routing Telegram messages to the orchestrator.

This module bridges incoming Telegram messages with the orchestrator agent
and sends responses back via the Telegram API or MCP server.

Session management allows users to create fresh conversation contexts
via the /new command.
"""

import logging
from typing import Optional

import httpx

from src.agents.orchestrator import OrchestratorAgent
from src.services.telegram.models import IncomingTelegramMessage, SendMessageRequest
from src.services.telegram_session_service import (
    TelegramSessionService,
    get_telegram_session_service,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
# Maximum message length for Telegram (4096 characters)
MAX_TELEGRAM_MESSAGE_LENGTH = 4096


# -----------------------------------------------------------------------------
# Telegram Message Handler Class
# -----------------------------------------------------------------------------
class TelegramMessageHandler:
    """
    Handles incoming Telegram messages and routes them to the orchestrator.

    This class is responsible for:
    - Receiving processed messages from the poller
    - Managing Telegram-to-database session mapping
    - Sending typing indicators to show the bot is working
    - Routing messages to the orchestrator for processing
    - Sending responses back via the Telegram API (or MCP server)
    - Handling bot commands (/new, /clear, /help, /start)

    Attributes:
        orchestrator: The OrchestratorAgent instance for processing messages.
        session_service: Service for managing Telegram session mappings.
        bot_token: Telegram bot token for sending messages.
        mcp_url: URL of the Telegram MCP server (optional).
        use_mcp: Whether to use MCP server for sending messages.
        _client: Async HTTP client for API requests.
    """

    def __init__(
        self,
        orchestrator: OrchestratorAgent,
        bot_token: str,
        mcp_url: Optional[str] = None,
        session_service: Optional[TelegramSessionService] = None,
    ) -> None:
        """
        Initialize the message handler.

        Args:
            orchestrator: The OrchestratorAgent to route messages to.
            bot_token: Telegram bot token for sending messages directly.
            mcp_url: URL of the Telegram MCP server (optional).
            session_service: Optional TelegramSessionService instance.
        """
        self.orchestrator = orchestrator
        self.bot_token = bot_token
        self.mcp_url = mcp_url
        self.use_mcp = mcp_url is not None
        self.session_service = session_service or get_telegram_session_service()

        self._client: Optional[httpx.AsyncClient] = None
        self._api_base_url = f"https://api.telegram.org/bot{bot_token}"

        logger.info(
            f"TelegramMessageHandler initialized. "
            f"Using MCP: {self.use_mcp}"
        )

    # -------------------------------------------------------------------------
    # HTTP Client Management
    # -------------------------------------------------------------------------
    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create the async HTTP client.

        Returns:
            The httpx.AsyncClient instance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client if it exists."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # -------------------------------------------------------------------------
    # Telegram API Methods (Direct)
    # -------------------------------------------------------------------------
    async def _send_typing_action(self, chat_id: int) -> None:
        """
        Send typing indicator to show the bot is processing.

        Args:
            chat_id: The chat to send the typing indicator to.
        """
        client = await self._get_client()
        url = f"{self._api_base_url}/sendChatAction"

        try:
            await client.post(url, json={"chat_id": chat_id, "action": "typing"})
        except Exception as e:
            # Typing indicator is non-critical, just log and continue
            logger.debug(f"Failed to send typing action: {e}")

    async def _send_message_direct(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None,
        parse_mode: Optional[str] = None,
    ) -> bool:
        """
        Send a message directly via Telegram Bot API.

        Args:
            chat_id: The chat to send the message to.
            text: The message text.
            reply_to_message_id: Message ID to reply to (optional).
            parse_mode: Parse mode for formatting (optional).

        Returns:
            True if the message was sent successfully.
        """
        client = await self._get_client()
        url = f"{self._api_base_url}/sendMessage"

        request = SendMessageRequest(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=reply_to_message_id,
            parse_mode=parse_mode,
        )

        try:
            response = await client.post(
                url, json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("ok"):
                logger.error(f"Failed to send message: {data.get('description')}")
                return False

            logger.debug(f"Message sent to chat {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending message to chat {chat_id}: {e}")
            return False

    # -------------------------------------------------------------------------
    # Telegram API Methods (via MCP)
    # -------------------------------------------------------------------------
    async def _send_message_via_mcp(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None,
        parse_mode: Optional[str] = None,
    ) -> bool:
        """
        Send a message via the Telegram MCP server.

        Args:
            chat_id: The chat to send the message to.
            text: The message text.
            reply_to_message_id: Message ID to reply to (optional).
            parse_mode: Parse mode for formatting (optional).

        Returns:
            True if the message was sent successfully.
        """
        if not self.mcp_url:
            logger.error("MCP URL not configured")
            return False

        client = await self._get_client()
        url = f"{self.mcp_url}/tools/send_message"

        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            if not data.get("success"):
                logger.error(f"MCP send_message failed: {data.get('error')}")
                return False

            logger.debug(f"Message sent via MCP to chat {chat_id}")
            return True

        except httpx.ConnectError:
            logger.warning(
                "Could not connect to MCP server, falling back to direct API"
            )
            return await self._send_message_direct(
                chat_id, text, reply_to_message_id, parse_mode
            )

        except Exception as e:
            logger.error(f"Error sending message via MCP: {e}")
            return False

    # -------------------------------------------------------------------------
    # Message Sending (Unified)
    # -------------------------------------------------------------------------
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None,
        parse_mode: Optional[str] = None,
    ) -> bool:
        """
        Send a message to a Telegram chat.

        Automatically splits long messages and chooses between direct API
        and MCP server based on configuration.

        Args:
            chat_id: The chat to send the message to.
            text: The message text.
            reply_to_message_id: Message ID to reply to (optional).
            parse_mode: Parse mode for formatting (optional).

        Returns:
            True if all message parts were sent successfully.
        """
        # Split long messages
        message_parts = self._split_message(text)

        success = True
        for i, part in enumerate(message_parts):
            # Only reply to original message for first part
            reply_id = reply_to_message_id if i == 0 else None

            if self.use_mcp:
                part_success = await self._send_message_via_mcp(
                    chat_id, part, reply_id, parse_mode
                )
            else:
                part_success = await self._send_message_direct(
                    chat_id, part, reply_id, parse_mode
                )

            if not part_success:
                success = False

        return success

    def _split_message(self, text: str) -> list[str]:
        """
        Split a long message into chunks that fit Telegram's limit.

        Attempts to split at paragraph or sentence boundaries when possible.

        Args:
            text: The message text to split.

        Returns:
            List of message parts.
        """
        if len(text) <= MAX_TELEGRAM_MESSAGE_LENGTH:
            return [text]

        parts = []
        remaining = text

        while remaining:
            if len(remaining) <= MAX_TELEGRAM_MESSAGE_LENGTH:
                parts.append(remaining)
                break

            # Find a good split point (paragraph, newline, or period)
            chunk = remaining[:MAX_TELEGRAM_MESSAGE_LENGTH]

            # Try to split at paragraph boundary
            split_point = chunk.rfind("\n\n")
            if split_point < MAX_TELEGRAM_MESSAGE_LENGTH // 2:
                # Try newline
                split_point = chunk.rfind("\n")
            if split_point < MAX_TELEGRAM_MESSAGE_LENGTH // 2:
                # Try period
                split_point = chunk.rfind(". ")
                if split_point > 0:
                    split_point += 1  # Include the period
            if split_point < MAX_TELEGRAM_MESSAGE_LENGTH // 2:
                # Force split at max length
                split_point = MAX_TELEGRAM_MESSAGE_LENGTH

            parts.append(remaining[:split_point].strip())
            remaining = remaining[split_point:].strip()

        return parts

    # -------------------------------------------------------------------------
    # Command Detection
    # -------------------------------------------------------------------------
    def _is_command(self, text: str) -> tuple[bool, str, str]:
        """
        Check if a message is a bot command.

        Args:
            text: The message text.

        Returns:
            Tuple of (is_command, command_name, arguments).
        """
        if not text.startswith("/"):
            return False, "", ""

        parts = text.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove leading '/' and lowercase

        # Handle commands with @botname suffix
        if "@" in command:
            command = command.split("@")[0]

        args = parts[1] if len(parts) > 1 else ""

        return True, command, args

    # -------------------------------------------------------------------------
    # Main Message Handler
    # -------------------------------------------------------------------------
    async def handle_message(self, message: IncomingTelegramMessage) -> None:
        """
        Handle an incoming Telegram message.

        This is the main entry point called by the poller for each message.
        It checks for commands, manages sessions, routes messages to the
        orchestrator, and sends responses.

        Args:
            message: The incoming Telegram message to process.
        """
        logger.info(
            f"Handling message from {message.user_display_name} "
            f"in chat {message.chat_id}"
        )

        # Check if this is a command
        is_command, command, args = self._is_command(message.text)
        if is_command:
            await self.handle_command(message, command, args)
            return

        # Send typing indicator to show we're working
        await self._send_typing_action(message.chat_id)

        try:
            # Get or create the database chat session for this Telegram chat
            chat_id = await self.session_service.get_active_chat_id(
                telegram_chat_id=message.chat_id,
                telegram_user_id=message.user_id,
            )

            # Process the message through the orchestrator with database chat_id
            response_text, tokens_used = await self.orchestrator.process_message(
                message=message.text,
                chat_id=chat_id,
            )

            logger.info(
                f"Orchestrator response generated. "
                f"Tokens: {tokens_used}, Length: {len(response_text)}"
            )

            # Send the response back to Telegram
            success = await self.send_message(
                chat_id=message.chat_id,
                text=response_text,
                reply_to_message_id=message.message_id,
            )

            if success:
                logger.info(f"Response sent to chat {message.chat_id}")
            else:
                logger.error(f"Failed to send response to chat {message.chat_id}")

        except Exception as e:
            logger.error(
                f"Error processing message from {message.user_display_name}: {e}",
                exc_info=True,
            )

            # Send error message to user
            error_message = (
                "I'm sorry, I encountered an error processing your message. "
                "Please try again later."
            )
            await self.send_message(
                chat_id=message.chat_id,
                text=error_message,
                reply_to_message_id=message.message_id,
            )

    # -------------------------------------------------------------------------
    # Command Handlers
    # -------------------------------------------------------------------------
    async def handle_command(
        self, message: IncomingTelegramMessage, command: str, args: str
    ) -> None:
        """
        Handle a Telegram bot command.

        Supported commands:
        - /start - Welcome message
        - /help - Show available commands
        - /new - Start a new conversation (fresh context)
        - /clear - Clear messages in current conversation
        - /status - Show current session info

        Args:
            message: The incoming message containing the command.
            command: The command without the leading slash.
            args: Any arguments after the command.
        """
        logger.debug(f"Command received: /{command} {args}")

        if command == "start":
            await self._handle_start_command(message)
        elif command == "help":
            await self._handle_help_command(message)
        elif command == "new":
            await self._handle_new_command(message)
        elif command == "clear":
            await self._handle_clear_command(message)
        elif command == "status":
            await self._handle_status_command(message)
        else:
            await self.send_message(
                chat_id=message.chat_id,
                text=f"Unknown command: /{command}\nType /help for available commands.",
            )

    async def _handle_start_command(self, message: IncomingTelegramMessage) -> None:
        """Handle the /start command."""
        # Create a session if it doesn't exist
        _, created = await self.session_service.get_or_create_session(
            telegram_chat_id=message.chat_id,
            telegram_user_id=message.user_id,
        )

        welcome_message = (
            "Welcome to the Claude Assistant Platform!\n\n"
            "I'm your AI assistant powered by Claude. "
            "You can ask me questions, request help with tasks, "
            "or have a conversation.\n\n"
            "Available commands:\n"
            "/new - Start a fresh conversation\n"
            "/clear - Clear current conversation history\n"
            "/status - Show session info\n"
            "/help - Show this help message\n\n"
            "Just send me a message to get started!"
        )
        await self.send_message(chat_id=message.chat_id, text=welcome_message)

    async def _handle_help_command(self, message: IncomingTelegramMessage) -> None:
        """Handle the /help command."""
        help_message = (
            "Claude Assistant Platform - Help\n\n"
            "Just send me any message and I'll do my best to help!\n\n"
            "Available commands:\n"
            "/start - Welcome message and setup\n"
            "/new - Start a new conversation with fresh context\n"
            "/clear - Clear messages but keep the same conversation\n"
            "/status - Show current session information\n"
            "/help - Show this help message\n\n"
            "Tip: Use /new when you want to change topics completely!"
        )
        await self.send_message(chat_id=message.chat_id, text=help_message)

    async def _handle_new_command(self, message: IncomingTelegramMessage) -> None:
        """Handle the /new command - creates a fresh conversation."""
        try:
            # Create a new database chat and update the session
            new_chat_id = await self.session_service.create_new_chat(
                telegram_chat_id=message.chat_id,
                telegram_user_id=message.user_id,
            )

            await self.send_message(
                chat_id=message.chat_id,
                text=(
                    "Started a new conversation!\n\n"
                    "I've cleared my memory of our previous discussion. "
                    "What would you like to talk about?"
                ),
            )
            logger.info(
                f"Created new chat {new_chat_id} for Telegram chat {message.chat_id}"
            )

        except Exception as e:
            logger.error(f"Error creating new chat: {e}", exc_info=True)
            await self.send_message(
                chat_id=message.chat_id,
                text="Sorry, I couldn't start a new conversation. Please try again.",
            )

    async def _handle_clear_command(self, message: IncomingTelegramMessage) -> None:
        """Handle the /clear command - clears messages in current chat."""
        try:
            cleared = await self.session_service.clear_current_chat(
                telegram_chat_id=message.chat_id,
            )

            if cleared:
                await self.send_message(
                    chat_id=message.chat_id,
                    text=(
                        "Conversation history cleared!\n\n"
                        "I've forgotten our previous messages but kept this "
                        "conversation session. Send me a new message to continue."
                    ),
                )
            else:
                await self.send_message(
                    chat_id=message.chat_id,
                    text="No conversation history to clear.",
                )

        except Exception as e:
            logger.error(f"Error clearing chat: {e}", exc_info=True)
            await self.send_message(
                chat_id=message.chat_id,
                text="Sorry, I couldn't clear the conversation. Please try again.",
            )

    async def _handle_status_command(self, message: IncomingTelegramMessage) -> None:
        """Handle the /status command - shows session info."""
        try:
            session = await self.session_service.get_session(message.chat_id)

            if session:
                message_count = await self.session_service.get_chat_history_count(
                    message.chat_id
                )
                status_text = (
                    "Session Status\n\n"
                    f"Telegram Chat ID: {message.chat_id}\n"
                    f"Active Chat ID: {session.active_chat_id}\n"
                    f"Messages in context: {message_count}\n"
                    f"Session created: {session.created_on.strftime('%Y-%m-%d %H:%M')}\n\n"
                    "Use /new to start a fresh conversation."
                )
            else:
                status_text = (
                    "No active session found.\n\n"
                    "Send a message or use /start to begin!"
                )

            await self.send_message(chat_id=message.chat_id, text=status_text)

        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            await self.send_message(
                chat_id=message.chat_id,
                text="Sorry, I couldn't retrieve the session status.",
            )
