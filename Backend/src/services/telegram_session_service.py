# =============================================================================
# Telegram Session Service
# =============================================================================
"""
Service for managing Telegram to internal chat session mappings.

Handles the relationship between Telegram chat IDs and internal chat
sessions, allowing users to create new sessions via commands.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Chat, TelegramSession, get_session
from src.services.chat_service import ChatService, get_chat_service


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Telegram Session Service Class
# -----------------------------------------------------------------------------
class TelegramSessionService:
    """
    Service for managing Telegram session mappings.

    Maps Telegram chat IDs to internal chat sessions and provides methods
    for creating new sessions (fresh context) from Telegram.

    Attributes:
        chat_service: ChatService instance for chat operations.
    """

    def __init__(self, chat_service: Optional[ChatService] = None) -> None:
        """
        Initialize the Telegram session service.

        Args:
            chat_service: Optional ChatService instance. Uses singleton if not provided.
        """
        self.chat_service = chat_service or get_chat_service()

    # -------------------------------------------------------------------------
    # Session Operations
    # -------------------------------------------------------------------------
    async def get_session(
        self, telegram_chat_id: int, db_session: Optional[AsyncSession] = None
    ) -> Optional[TelegramSession]:
        """
        Get the Telegram session for a chat ID.

        Args:
            telegram_chat_id: The Telegram chat ID.
            db_session: Optional database session.

        Returns:
            TelegramSession if found, None otherwise.
        """
        async def _get_session(sess: AsyncSession) -> Optional[TelegramSession]:
            return await sess.get(TelegramSession, telegram_chat_id)

        if db_session:
            return await _get_session(db_session)
        else:
            async with get_session() as sess:
                return await _get_session(sess)

    async def get_or_create_session(
        self,
        telegram_chat_id: int,
        telegram_user_id: int,
        db_session: Optional[AsyncSession] = None,
    ) -> tuple[TelegramSession, bool]:
        """
        Get existing session or create a new one.

        Args:
            telegram_chat_id: The Telegram chat ID.
            telegram_user_id: The Telegram user ID.
            db_session: Optional database session.

        Returns:
            Tuple of (TelegramSession, created) where created is True if new.
        """
        async def _get_or_create(sess: AsyncSession) -> tuple[TelegramSession, bool]:
            # Try to get existing session
            session = await sess.get(TelegramSession, telegram_chat_id)
            if session:
                return session, False

            # Create new chat and session
            chat = Chat()
            sess.add(chat)
            await sess.flush()  # Get the chat ID

            session = TelegramSession(
                telegram_chat_id=telegram_chat_id,
                telegram_user_id=telegram_user_id,
                active_chat_id=chat.id,
            )
            sess.add(session)
            await sess.flush()

            logger.info(
                f"Created new session for Telegram chat {telegram_chat_id} "
                f"-> internal chat {chat.id}"
            )
            return session, True

        if db_session:
            return await _get_or_create(db_session)
        else:
            async with get_session() as sess:
                return await _get_or_create(sess)

    async def get_active_chat_id(
        self,
        telegram_chat_id: int,
        telegram_user_id: int,
        db_session: Optional[AsyncSession] = None,
    ) -> UUID:
        """
        Get the active chat ID for a Telegram chat, creating if needed.

        This is the main method to call when processing a Telegram message.

        Args:
            telegram_chat_id: The Telegram chat ID.
            telegram_user_id: The Telegram user ID.
            db_session: Optional database session.

        Returns:
            UUID of the active internal chat.
        """
        session, _ = await self.get_or_create_session(
            telegram_chat_id, telegram_user_id, db_session
        )
        return session.active_chat_id

    async def create_new_chat(
        self,
        telegram_chat_id: int,
        telegram_user_id: int,
        db_session: Optional[AsyncSession] = None,
    ) -> UUID:
        """
        Create a new chat session for a Telegram chat.

        This is called when the user wants to start a fresh conversation
        (e.g., via /new command). Creates a new internal chat and updates
        the session to point to it.

        Args:
            telegram_chat_id: The Telegram chat ID.
            telegram_user_id: The Telegram user ID.
            db_session: Optional database session.

        Returns:
            UUID of the newly created internal chat.
        """
        async def _create_new_chat(sess: AsyncSession) -> UUID:
            # Create new internal chat
            new_chat = Chat()
            sess.add(new_chat)
            await sess.flush()

            # Get or create the Telegram session
            session = await sess.get(TelegramSession, telegram_chat_id)

            if session:
                # Update existing session to point to new chat
                old_chat_id = session.active_chat_id
                session.active_chat_id = new_chat.id
                logger.info(
                    f"Switched Telegram chat {telegram_chat_id} from "
                    f"chat {old_chat_id} to new chat {new_chat.id}"
                )
            else:
                # Create new session
                session = TelegramSession(
                    telegram_chat_id=telegram_chat_id,
                    telegram_user_id=telegram_user_id,
                    active_chat_id=new_chat.id,
                )
                sess.add(session)
                logger.info(
                    f"Created new session for Telegram chat {telegram_chat_id} "
                    f"-> internal chat {new_chat.id}"
                )

            await sess.flush()
            return new_chat.id

        if db_session:
            return await _create_new_chat(db_session)
        else:
            async with get_session() as sess:
                return await _create_new_chat(sess)

    async def clear_current_chat(
        self,
        telegram_chat_id: int,
        db_session: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Clear all messages in the current chat but keep the chat session.

        Args:
            telegram_chat_id: The Telegram chat ID.
            db_session: Optional database session.

        Returns:
            True if messages were cleared, False if session not found.
        """
        async def _clear_chat(sess: AsyncSession) -> bool:
            session = await sess.get(TelegramSession, telegram_chat_id)
            if not session:
                return False

            await self.chat_service.clear_chat_messages(
                session.active_chat_id, sess
            )
            return True

        if db_session:
            return await _clear_chat(db_session)
        else:
            async with get_session() as sess:
                return await _clear_chat(sess)

    async def get_chat_history_count(
        self,
        telegram_chat_id: int,
        db_session: Optional[AsyncSession] = None,
    ) -> int:
        """
        Get the number of messages in the current chat.

        Args:
            telegram_chat_id: The Telegram chat ID.
            db_session: Optional database session.

        Returns:
            Number of messages, or 0 if session not found.
        """
        from sqlalchemy import func as sql_func
        from src.database.models import ChatMessage

        async def _get_count(sess: AsyncSession) -> int:
            session = await sess.get(TelegramSession, telegram_chat_id)
            if not session:
                return 0

            query = (
                select(sql_func.count())
                .select_from(ChatMessage)
                .where(ChatMessage.chat_id == session.active_chat_id)
            )
            result = await sess.execute(query)
            return result.scalar() or 0

        if db_session:
            return await _get_count(db_session)
        else:
            async with get_session() as sess:
                return await _get_count(sess)


# -----------------------------------------------------------------------------
# Default Service Instance
# -----------------------------------------------------------------------------
_telegram_session_service: Optional[TelegramSessionService] = None


def get_telegram_session_service() -> TelegramSessionService:
    """
    Get the singleton TelegramSessionService instance.

    Returns:
        The TelegramSessionService instance.
    """
    global _telegram_session_service
    if _telegram_session_service is None:
        _telegram_session_service = TelegramSessionService()
    return _telegram_session_service
