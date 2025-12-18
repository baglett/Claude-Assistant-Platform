# =============================================================================
# Telegram MCP Server
# =============================================================================
"""
FastMCP server providing Telegram Bot API tools.

This server exposes MCP tools for:
- Sending messages to Telegram chats
- Getting chat information
- Sending typing indicators

The server runs as a standalone HTTP service and can be called by the
orchestrator or other components to interact with Telegram.
"""

import logging
import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
class Settings(BaseSettings):
    """
    Server settings loaded from environment variables.

    Attributes:
        telegram_bot_token: Telegram bot token from @BotFather.
        host: Host address for the server.
        port: Port number for the server.
    """

    telegram_bot_token: str = Field(
        default="",
        description="Telegram bot token from @BotFather",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host address for the server",
    )
    port: int = Field(
        default=8080,
        description="Port number for the server",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
TELEGRAM_API_BASE_URL = "https://api.telegram.org/bot{token}"


# -----------------------------------------------------------------------------
# Pydantic Models for API
# -----------------------------------------------------------------------------
class SendMessageRequest(BaseModel):
    """
    Request model for sending a Telegram message.

    Attributes:
        chat_id: The chat ID to send the message to.
        text: The message text.
        parse_mode: Optional parse mode (HTML, Markdown, MarkdownV2).
        reply_to_message_id: Optional message ID to reply to.
        disable_notification: Send message silently.
    """

    chat_id: int = Field(..., description="Target chat ID")
    text: str = Field(..., description="Message text to send")
    parse_mode: Optional[str] = Field(
        default=None,
        description="Parse mode: HTML, Markdown, or MarkdownV2",
    )
    reply_to_message_id: Optional[int] = Field(
        default=None,
        description="ID of the message to reply to",
    )
    disable_notification: bool = Field(
        default=False,
        description="Send message silently",
    )


class SendMessageResponse(BaseModel):
    """
    Response model for send message operation.

    Attributes:
        success: Whether the message was sent successfully.
        message_id: The ID of the sent message.
        error: Error message if the operation failed.
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    message_id: Optional[int] = Field(
        default=None,
        description="ID of the sent message",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed",
    )


class ChatInfoResponse(BaseModel):
    """
    Response model for chat info operation.

    Attributes:
        success: Whether the operation succeeded.
        chat_id: The chat ID.
        chat_type: Type of chat (private, group, supergroup, channel).
        title: Chat title (for groups and channels).
        username: Chat username.
        first_name: First name (for private chats).
        last_name: Last name (for private chats).
        error: Error message if the operation failed.
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    chat_id: Optional[int] = Field(default=None, description="Chat ID")
    chat_type: Optional[str] = Field(default=None, description="Type of chat")
    title: Optional[str] = Field(default=None, description="Chat title")
    username: Optional[str] = Field(default=None, description="Chat username")
    first_name: Optional[str] = Field(default=None, description="First name")
    last_name: Optional[str] = Field(default=None, description="Last name")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class TypingActionRequest(BaseModel):
    """
    Request model for sending typing action.

    Attributes:
        chat_id: The chat ID to send the typing action to.
    """

    chat_id: int = Field(..., description="Target chat ID")


class TypingActionResponse(BaseModel):
    """
    Response model for typing action operation.

    Attributes:
        success: Whether the operation succeeded.
        error: Error message if the operation failed.
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# -----------------------------------------------------------------------------
# Telegram API Client
# -----------------------------------------------------------------------------
class TelegramClient:
    """
    HTTP client for Telegram Bot API.

    Provides methods for interacting with the Telegram Bot API.

    Attributes:
        bot_token: The Telegram bot token.
        _api_base_url: Base URL for API requests.
        _client: Async HTTP client.
    """

    def __init__(self, bot_token: str) -> None:
        """
        Initialize the Telegram client.

        Args:
            bot_token: Telegram bot token from @BotFather.
        """
        self.bot_token = bot_token
        self._api_base_url = TELEGRAM_API_BASE_URL.format(token=bot_token)
        self._client: Optional[httpx.AsyncClient] = None

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
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        disable_notification: bool = False,
    ) -> SendMessageResponse:
        """
        Send a message to a Telegram chat.

        Args:
            chat_id: The chat ID to send to.
            text: The message text.
            parse_mode: Optional parse mode.
            reply_to_message_id: Optional message ID to reply to.
            disable_notification: Send silently.

        Returns:
            SendMessageResponse with result.
        """
        client = await self._get_client()
        url = f"{self._api_base_url}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_notification": disable_notification,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            if data.get("ok"):
                return SendMessageResponse(
                    success=True,
                    message_id=data.get("result", {}).get("message_id"),
                )
            else:
                return SendMessageResponse(
                    success=False,
                    error=data.get("description", "Unknown error"),
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending message: {e.response.status_code}")
            return SendMessageResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
            )

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return SendMessageResponse(
                success=False,
                error=str(e),
            )

    async def get_chat(self, chat_id: int) -> ChatInfoResponse:
        """
        Get information about a chat.

        Args:
            chat_id: The chat ID to get info for.

        Returns:
            ChatInfoResponse with chat details.
        """
        client = await self._get_client()
        url = f"{self._api_base_url}/getChat"

        try:
            response = await client.post(url, json={"chat_id": chat_id})
            response.raise_for_status()

            data = response.json()
            if data.get("ok"):
                result = data.get("result", {})
                return ChatInfoResponse(
                    success=True,
                    chat_id=result.get("id"),
                    chat_type=result.get("type"),
                    title=result.get("title"),
                    username=result.get("username"),
                    first_name=result.get("first_name"),
                    last_name=result.get("last_name"),
                )
            else:
                return ChatInfoResponse(
                    success=False,
                    error=data.get("description", "Unknown error"),
                )

        except Exception as e:
            logger.error(f"Error getting chat info: {e}")
            return ChatInfoResponse(
                success=False,
                error=str(e),
            )

    async def send_chat_action(
        self, chat_id: int, action: str = "typing"
    ) -> TypingActionResponse:
        """
        Send a chat action (e.g., typing indicator).

        Args:
            chat_id: The chat ID.
            action: The action type (default: "typing").

        Returns:
            TypingActionResponse with result.
        """
        client = await self._get_client()
        url = f"{self._api_base_url}/sendChatAction"

        try:
            response = await client.post(
                url, json={"chat_id": chat_id, "action": action}
            )
            response.raise_for_status()

            data = response.json()
            if data.get("ok"):
                return TypingActionResponse(success=True)
            else:
                return TypingActionResponse(
                    success=False,
                    error=data.get("description", "Unknown error"),
                )

        except Exception as e:
            logger.error(f"Error sending chat action: {e}")
            return TypingActionResponse(
                success=False,
                error=str(e),
            )


# -----------------------------------------------------------------------------
# Initialize Telegram Client
# -----------------------------------------------------------------------------
telegram_client = TelegramClient(settings.telegram_bot_token)


# -----------------------------------------------------------------------------
# FastMCP Server
# -----------------------------------------------------------------------------
mcp = FastMCP("telegram-mcp")


@mcp.tool()
async def send_message(
    chat_id: int,
    text: str,
    parse_mode: Optional[str] = None,
    reply_to_message_id: Optional[int] = None,
    disable_notification: bool = False,
) -> dict:
    """
    Send a text message to a Telegram chat.

    Args:
        chat_id: The Telegram chat ID to send the message to.
        text: The text content of the message.
        parse_mode: Optional formatting mode (HTML, Markdown, MarkdownV2).
        reply_to_message_id: Optional message ID to reply to.
        disable_notification: If True, send message silently.

    Returns:
        Dictionary with success status and message_id or error.
    """
    result = await telegram_client.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_to_message_id=reply_to_message_id,
        disable_notification=disable_notification,
    )
    return result.model_dump()


@mcp.tool()
async def get_chat_info(chat_id: int) -> dict:
    """
    Get information about a Telegram chat.

    Args:
        chat_id: The Telegram chat ID to get information for.

    Returns:
        Dictionary with chat details (id, type, title, username, etc.).
    """
    result = await telegram_client.get_chat(chat_id)
    return result.model_dump()


@mcp.tool()
async def send_typing_action(chat_id: int) -> dict:
    """
    Send a typing indicator to a Telegram chat.

    Shows a "typing..." indicator to the user for a few seconds.

    Args:
        chat_id: The Telegram chat ID to send the typing indicator to.

    Returns:
        Dictionary with success status.
    """
    result = await telegram_client.send_chat_action(chat_id, "typing")
    return result.model_dump()


# -----------------------------------------------------------------------------
# FastAPI Application (for HTTP access)
# -----------------------------------------------------------------------------
fastapi_app = FastAPI(
    title="Telegram MCP Server",
    description="MCP server providing Telegram Bot API tools",
    version="0.1.0",
)


@fastapi_app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Dictionary with service status.
    """
    return {"status": "healthy", "service": "telegram-mcp"}


@fastapi_app.post("/tools/send_message", response_model=SendMessageResponse)
async def http_send_message(request: SendMessageRequest) -> SendMessageResponse:
    """
    HTTP endpoint for sending a Telegram message.

    Args:
        request: The send message request.

    Returns:
        SendMessageResponse with result.
    """
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=500, detail="Bot token not configured")

    return await telegram_client.send_message(
        chat_id=request.chat_id,
        text=request.text,
        parse_mode=request.parse_mode,
        reply_to_message_id=request.reply_to_message_id,
        disable_notification=request.disable_notification,
    )


@fastapi_app.post("/tools/get_chat_info", response_model=ChatInfoResponse)
async def http_get_chat_info(chat_id: int) -> ChatInfoResponse:
    """
    HTTP endpoint for getting chat information.

    Args:
        chat_id: The chat ID to get info for.

    Returns:
        ChatInfoResponse with chat details.
    """
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=500, detail="Bot token not configured")

    return await telegram_client.get_chat(chat_id)


@fastapi_app.post("/tools/send_typing_action", response_model=TypingActionResponse)
async def http_send_typing_action(request: TypingActionRequest) -> TypingActionResponse:
    """
    HTTP endpoint for sending typing indicator.

    Args:
        request: The typing action request.

    Returns:
        TypingActionResponse with result.
    """
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=500, detail="Bot token not configured")

    return await telegram_client.send_chat_action(request.chat_id, "typing")


@fastapi_app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    await telegram_client.close()
    logger.info("Telegram client closed")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Run the server."""
    import uvicorn

    logger.info(f"Starting Telegram MCP Server on {settings.host}:{settings.port}")

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set - server will not function properly")

    uvicorn.run(
        fastapi_app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
