# =============================================================================
# Telegram Poller
# =============================================================================
"""
Long-polling client for receiving Telegram Bot API updates.

This module implements a TelegramPoller class that continuously polls the
Telegram API for new messages and routes them to the message handler.
"""

import asyncio
import logging
from typing import Callable, Coroutine, Optional, Any

import httpx

from src.services.telegram.models import (
    IncomingTelegramMessage,
    TelegramGetUpdatesResponse,
    TelegramUpdate,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
TELEGRAM_API_BASE_URL = "https://api.telegram.org/bot{token}"


# -----------------------------------------------------------------------------
# Type Aliases
# -----------------------------------------------------------------------------
# Type for the message handler callback function
MessageHandlerCallback = Callable[
    [IncomingTelegramMessage],
    Coroutine[Any, Any, None]
]


# -----------------------------------------------------------------------------
# Telegram Poller Class
# -----------------------------------------------------------------------------
class TelegramPoller:
    """
    Long-polling client for Telegram Bot API.

    Continuously polls the Telegram API for new updates and routes them
    to a message handler callback. Implements automatic reconnection and
    error handling.

    Attributes:
        bot_token: The Telegram bot token for authentication.
        allowed_user_ids: Set of user IDs allowed to interact with the bot.
        polling_timeout: Timeout in seconds for long-polling requests.
        message_handler: Callback function to handle incoming messages.
        _running: Flag indicating whether the poller is running.
        _last_update_id: The last processed update ID (for offset).
        _client: Async HTTP client for API requests.
    """

    def __init__(
        self,
        bot_token: str,
        allowed_user_ids: list[int],
        polling_timeout: int = 30,
        message_handler: Optional[MessageHandlerCallback] = None,
    ) -> None:
        """
        Initialize the Telegram poller.

        Args:
            bot_token: Telegram bot token from @BotFather.
            allowed_user_ids: List of Telegram user IDs allowed to use the bot.
            polling_timeout: Timeout in seconds for long-polling (default: 30).
            message_handler: Async callback function to handle incoming messages.
        """
        self.bot_token = bot_token
        self.allowed_user_ids = set(allowed_user_ids)
        self.polling_timeout = polling_timeout
        self.message_handler = message_handler

        # Internal state
        self._running = False
        self._last_update_id: Optional[int] = None
        self._client: Optional[httpx.AsyncClient] = None

        # Build the base API URL
        self._api_base_url = TELEGRAM_API_BASE_URL.format(token=bot_token)

        logger.info(
            f"TelegramPoller initialized. Allowed users: {len(allowed_user_ids)}"
        )

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        """
        Check if the poller is currently running.

        Returns:
            True if the polling loop is active.
        """
        return self._running

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
            # Use a longer timeout for long-polling
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=self.polling_timeout + 10,  # Extra buffer for polling
                    write=10.0,
                    pool=10.0,
                )
            )
        return self._client

    async def _close_client(self) -> None:
        """Close the HTTP client if it exists."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # -------------------------------------------------------------------------
    # API Methods
    # -------------------------------------------------------------------------
    async def _get_updates(self) -> list[TelegramUpdate]:
        """
        Fetch updates from the Telegram API using long-polling.

        Returns:
            List of TelegramUpdate objects.

        Raises:
            Exception: If the API request fails.
        """
        client = await self._get_client()

        # Build request parameters
        params: dict[str, Any] = {
            "timeout": self.polling_timeout,
            "allowed_updates": ["message", "edited_message"],
        }

        # Add offset if we have processed updates before
        if self._last_update_id is not None:
            params["offset"] = self._last_update_id + 1

        url = f"{self._api_base_url}/getUpdates"

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            updates_response = TelegramGetUpdatesResponse.model_validate(data)

            if not updates_response.ok:
                logger.error(
                    f"Telegram API error: {updates_response.description}"
                )
                return []

            return updates_response.result

        except httpx.TimeoutException:
            # Timeout is expected for long-polling when no updates
            logger.debug("Long-polling timeout (no new updates)")
            return []

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching updates: {e.response.status_code}")
            raise

        except Exception as e:
            logger.error(f"Error fetching updates: {e}")
            raise

    # -------------------------------------------------------------------------
    # Message Processing
    # -------------------------------------------------------------------------
    def _is_user_allowed(self, user_id: int) -> bool:
        """
        Check if a user is allowed to interact with the bot.

        Args:
            user_id: The Telegram user ID to check.

        Returns:
            True if the user is in the allowed list, or if no whitelist is set.
        """
        # If no allowed users are configured, allow everyone (dev mode)
        if not self.allowed_user_ids:
            logger.warning(
                "No allowed user IDs configured - allowing all users (insecure!)"
            )
            return True

        return user_id in self.allowed_user_ids

    async def _process_update(self, update: TelegramUpdate) -> None:
        """
        Process a single Telegram update.

        Validates the user, extracts the message, and routes to the handler.

        Args:
            update: The TelegramUpdate to process.
        """
        # Convert to internal message format
        incoming_message = IncomingTelegramMessage.from_telegram_update(update)

        if incoming_message is None:
            logger.debug(f"Skipping update {update.update_id} (no text message)")
            return

        # Check user authorization
        if not self._is_user_allowed(incoming_message.user_id):
            logger.warning(
                f"Unauthorized user {incoming_message.user_id} "
                f"({incoming_message.user_display_name}) attempted to use bot"
            )
            return

        logger.info(
            f"Received message from {incoming_message.user_display_name} "
            f"(ID: {incoming_message.user_id}): {incoming_message.text[:50]}..."
        )

        # Route to message handler
        if self.message_handler:
            try:
                await self.message_handler(incoming_message)
            except Exception as e:
                logger.error(
                    f"Error in message handler for update {update.update_id}: {e}",
                    exc_info=True,
                )
        else:
            logger.warning("No message handler configured - message not processed")

    # -------------------------------------------------------------------------
    # Polling Loop
    # -------------------------------------------------------------------------
    async def start(self) -> None:
        """
        Start the long-polling loop.

        This method runs indefinitely until stop() is called or an
        unrecoverable error occurs. It automatically handles temporary
        errors with exponential backoff.
        """
        if self._running:
            logger.warning("Poller is already running")
            return

        self._running = True
        logger.info("Starting Telegram poller...")

        # Exponential backoff parameters
        retry_delay = 1.0
        max_retry_delay = 60.0

        while self._running:
            try:
                # Fetch updates from Telegram
                updates = await self._get_updates()

                # Reset retry delay on successful request
                retry_delay = 1.0

                # Process each update
                for update in updates:
                    # Update the offset to acknowledge processed updates
                    self._last_update_id = update.update_id

                    # Process the update (don't let one failure stop others)
                    try:
                        await self._process_update(update)
                    except Exception as e:
                        logger.error(
                            f"Error processing update {update.update_id}: {e}",
                            exc_info=True,
                        )

            except asyncio.CancelledError:
                # Graceful shutdown requested
                logger.info("Poller received cancellation signal")
                break

            except Exception as e:
                # Log error and retry with backoff
                logger.error(
                    f"Error in polling loop (retry in {retry_delay}s): {e}",
                    exc_info=True,
                )
                await asyncio.sleep(retry_delay)

                # Increase delay with exponential backoff
                retry_delay = min(retry_delay * 2, max_retry_delay)

        # Cleanup
        await self._close_client()
        self._running = False
        logger.info("Telegram poller stopped")

    async def stop(self) -> None:
        """
        Stop the long-polling loop.

        Signals the polling loop to exit gracefully.
        """
        if not self._running:
            logger.warning("Poller is not running")
            return

        logger.info("Stopping Telegram poller...")
        self._running = False

    # -------------------------------------------------------------------------
    # Handler Registration
    # -------------------------------------------------------------------------
    def set_message_handler(self, handler: MessageHandlerCallback) -> None:
        """
        Set the message handler callback.

        Args:
            handler: Async function that takes an IncomingTelegramMessage.
        """
        self.message_handler = handler
        logger.debug("Message handler registered")

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    async def get_me(self) -> dict:
        """
        Get information about the bot.

        Returns:
            Dictionary with bot information.

        Raises:
            Exception: If the API request fails.
        """
        client = await self._get_client()
        url = f"{self._api_base_url}/getMe"

        response = await client.get(url)
        response.raise_for_status()

        data = response.json()
        if not data.get("ok"):
            raise Exception(f"Failed to get bot info: {data.get('description')}")

        return data.get("result", {})

    async def verify_token(self) -> bool:
        """
        Verify that the bot token is valid.

        Returns:
            True if the token is valid, False otherwise.
        """
        try:
            bot_info = await self.get_me()
            logger.info(
                f"Bot token verified. Bot: @{bot_info.get('username', 'unknown')}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to verify bot token: {e}")
            return False
