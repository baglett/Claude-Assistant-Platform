# =============================================================================
# Chat Service
# =============================================================================
"""
Service layer for chat and message operations.

Provides business logic for creating, retrieving, and managing chat
conversations and their messages.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Chat, ChatMessage, get_session


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Chat Service Class
# -----------------------------------------------------------------------------
class ChatService:
    """
    Service for managing chat conversations and messages.

    Provides methods for creating chats, adding messages, and retrieving
    conversation history for use with the Claude API.

    Attributes:
        max_history_messages: Maximum messages to include in context.
    """

    def __init__(self, max_history_messages: int = 50) -> None:
        """
        Initialize the chat service.

        Args:
            max_history_messages: Maximum messages to retrieve for context.
        """
        self.max_history_messages = max_history_messages

    # -------------------------------------------------------------------------
    # Chat Operations
    # -------------------------------------------------------------------------
    async def create_chat(self, session: Optional[AsyncSession] = None) -> Chat:
        """
        Create a new chat conversation.

        Args:
            session: Optional database session (creates one if not provided).

        Returns:
            The newly created Chat object.
        """
        if session:
            chat = Chat()
            session.add(chat)
            await session.flush()  # Get the ID without committing
            logger.info(f"Created new chat: {chat.id}")
            return chat
        else:
            async with get_session() as session:
                chat = Chat()
                session.add(chat)
                await session.flush()
                logger.info(f"Created new chat: {chat.id}")
                return chat

    async def get_chat(
        self, chat_id: UUID, session: Optional[AsyncSession] = None
    ) -> Optional[Chat]:
        """
        Get a chat by ID.

        Args:
            chat_id: The chat's UUID.
            session: Optional database session.

        Returns:
            The Chat object or None if not found.
        """
        if session:
            return await session.get(Chat, chat_id)
        else:
            async with get_session() as session:
                return await session.get(Chat, chat_id)

    async def get_or_create_chat(
        self, chat_id: Optional[UUID] = None, session: Optional[AsyncSession] = None
    ) -> Chat:
        """
        Get an existing chat or create a new one.

        Args:
            chat_id: Optional chat ID to look up.
            session: Optional database session.

        Returns:
            The existing or newly created Chat object.
        """
        if chat_id:
            chat = await self.get_chat(chat_id, session)
            if chat:
                return chat
            logger.warning(f"Chat {chat_id} not found, creating new chat")

        return await self.create_chat(session)

    # -------------------------------------------------------------------------
    # Message Operations
    # -------------------------------------------------------------------------
    async def add_message(
        self,
        chat_id: UUID,
        role: str,
        content: str,
        llm_model: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> ChatMessage:
        """
        Add a message to a chat.

        Args:
            chat_id: The chat's UUID.
            role: Message role ('user', 'assistant', 'system', 'tool').
            content: Message text content.
            llm_model: Model identifier (for assistant messages).
            metadata: Additional metadata (token usage, etc.).
            session: Optional database session.

        Returns:
            The created ChatMessage object.
        """
        async def _add_message(sess: AsyncSession) -> ChatMessage:
            # Get the last message in the chat for linking
            last_message_query = (
                select(ChatMessage)
                .where(ChatMessage.chat_id == chat_id)
                .order_by(ChatMessage.created_on.desc())
                .limit(1)
            )
            result = await sess.execute(last_message_query)
            last_message = result.scalar_one_or_none()

            # Create new message
            message = ChatMessage(
                chat_id=chat_id,
                previous_message_id=last_message.id if last_message else None,
                role=role,
                content=content,
                llm_model=llm_model,
                message_metadata=metadata,
            )
            sess.add(message)
            await sess.flush()

            logger.debug(
                f"Added {role} message to chat {chat_id}: "
                f"{content[:50]}{'...' if len(content) > 50 else ''}"
            )
            return message

        if session:
            return await _add_message(session)
        else:
            async with get_session() as session:
                return await _add_message(session)

    async def get_messages(
        self,
        chat_id: UUID,
        limit: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> list[ChatMessage]:
        """
        Get messages for a chat, ordered by creation time.

        Args:
            chat_id: The chat's UUID.
            limit: Maximum number of messages to retrieve.
            session: Optional database session.

        Returns:
            List of ChatMessage objects.
        """
        limit = limit or self.max_history_messages

        async def _get_messages(sess: AsyncSession) -> list[ChatMessage]:
            query = (
                select(ChatMessage)
                .where(ChatMessage.chat_id == chat_id)
                .order_by(ChatMessage.created_on.asc())
                .limit(limit)
            )
            result = await sess.execute(query)
            return list(result.scalars().all())

        if session:
            return await _get_messages(session)
        else:
            async with get_session() as session:
                return await _get_messages(session)

    async def get_conversation_history(
        self,
        chat_id: UUID,
        limit: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> list[dict[str, str]]:
        """
        Get conversation history in Claude API format.

        Args:
            chat_id: The chat's UUID.
            limit: Maximum number of messages to retrieve.
            session: Optional database session.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        messages = await self.get_messages(chat_id, limit, session)
        return [msg.to_api_format() for msg in messages]

    async def clear_chat_messages(
        self, chat_id: UUID, session: Optional[AsyncSession] = None
    ) -> int:
        """
        Delete all messages in a chat (but keep the chat itself).

        Args:
            chat_id: The chat's UUID.
            session: Optional database session.

        Returns:
            Number of messages deleted.
        """
        from sqlalchemy import delete

        async def _clear_messages(sess: AsyncSession) -> int:
            # First, clear all previous_message_id references to avoid FK issues
            update_query = (
                ChatMessage.__table__.update()
                .where(ChatMessage.chat_id == chat_id)
                .values(previous_message_id=None)
            )
            await sess.execute(update_query)

            # Now delete all messages
            delete_query = delete(ChatMessage).where(ChatMessage.chat_id == chat_id)
            result = await sess.execute(delete_query)
            logger.info(f"Cleared {result.rowcount} messages from chat {chat_id}")
            return result.rowcount

        if session:
            return await _clear_messages(session)
        else:
            async with get_session() as session:
                return await _clear_messages(session)

    # -------------------------------------------------------------------------
    # Combined Operations
    # -------------------------------------------------------------------------
    async def add_user_message(
        self,
        chat_id: UUID,
        content: str,
        session: Optional[AsyncSession] = None,
    ) -> ChatMessage:
        """
        Convenience method to add a user message.

        Args:
            chat_id: The chat's UUID.
            content: Message content.
            session: Optional database session.

        Returns:
            The created ChatMessage.
        """
        return await self.add_message(
            chat_id=chat_id,
            role="user",
            content=content,
            session=session,
        )

    async def add_assistant_message(
        self,
        chat_id: UUID,
        content: str,
        llm_model: str,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> ChatMessage:
        """
        Convenience method to add an assistant message with metadata.

        Args:
            chat_id: The chat's UUID.
            content: Message content.
            llm_model: Model identifier used.
            tokens_used: Total tokens used.
            input_tokens: Input tokens used.
            output_tokens: Output tokens used.
            session: Optional database session.

        Returns:
            The created ChatMessage.
        """
        metadata = {}
        if tokens_used is not None:
            metadata["tokens_used"] = tokens_used
        if input_tokens is not None:
            metadata["input_tokens"] = input_tokens
        if output_tokens is not None:
            metadata["output_tokens"] = output_tokens

        return await self.add_message(
            chat_id=chat_id,
            role="assistant",
            content=content,
            llm_model=llm_model,
            metadata=metadata if metadata else None,
            session=session,
        )


# -----------------------------------------------------------------------------
# Default Service Instance
# -----------------------------------------------------------------------------
# Singleton instance for use throughout the application
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """
    Get the singleton ChatService instance.

    Returns:
        The ChatService instance.
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
