# =============================================================================
# Telegram Service Package
# =============================================================================
"""
Telegram integration for the Claude Assistant Platform.

This package provides components for receiving messages from Telegram via
long-polling and sending responses back via the Telegram Bot API or MCP server.

Components:
    - TelegramPoller: Long-polling client for receiving updates
    - TelegramMessageHandler: Routes messages to orchestrator and sends responses
    - Models: Pydantic models for Telegram data structures

Example:
    ```python
    from src.services.telegram import TelegramPoller, TelegramMessageHandler

    # Initialize components
    handler = TelegramMessageHandler(orchestrator, bot_token, mcp_url)
    poller = TelegramPoller(
        bot_token=bot_token,
        allowed_user_ids=[123456789],
        message_handler=handler.handle_message,
    )

    # Start polling
    await poller.start()
    ```
"""

from src.services.telegram.message_handler import TelegramMessageHandler
from src.services.telegram.models import (
    IncomingTelegramMessage,
    SendMessageRequest,
    SendMessageResponse,
    TelegramChat,
    TelegramGetUpdatesResponse,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
)
from src.services.telegram.poller import TelegramPoller


__all__ = [
    # Main Classes
    "TelegramPoller",
    "TelegramMessageHandler",
    # Models
    "TelegramUser",
    "TelegramChat",
    "TelegramMessage",
    "TelegramUpdate",
    "TelegramGetUpdatesResponse",
    "SendMessageRequest",
    "SendMessageResponse",
    "IncomingTelegramMessage",
]
