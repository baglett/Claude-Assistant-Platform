# =============================================================================
# Database ORM Models
# =============================================================================
"""
SQLAlchemy ORM models for the Claude Assistant Platform.

These models map to the PostgreSQL tables defined in the migrations.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# -----------------------------------------------------------------------------
# Base Model
# -----------------------------------------------------------------------------
class Base(DeclarativeBase):
    """
    Base class for all ORM models.

    Provides common functionality and type annotations.
    """

    pass


# -----------------------------------------------------------------------------
# Chat Model
# -----------------------------------------------------------------------------
class Chat(Base):
    """
    ORM model for messaging.chats table.

    Represents a chat/conversation session that can contain multiple messages.

    Attributes:
        id: Unique identifier (UUID).
        created_on: Timestamp when the chat was created.
        modified_on: Timestamp when the chat was last modified.
        messages: Relationship to chat messages.
    """

    __tablename__ = "chats"
    __table_args__ = {"schema": "messaging"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Timestamps
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    modified_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_on",
        lazy="selectin",  # Eager load messages by default
    )

    def __repr__(self) -> str:
        """String representation of the chat."""
        return f"<Chat(id={self.id}, created_on={self.created_on})>"


# -----------------------------------------------------------------------------
# ChatMessage Model
# -----------------------------------------------------------------------------
class ChatMessage(Base):
    """
    ORM model for messaging.chat_messages table.

    Represents an individual message within a chat conversation.

    Attributes:
        id: Unique identifier (UUID).
        chat_id: Foreign key to parent chat.
        previous_message_id: Reference to previous message (linked list).
        role: Message sender role (user, assistant, system, tool).
        content: Message text content.
        llm_model: Model used for assistant responses.
        message_metadata: JSONB metadata (token usage, etc.).
        created_on: Timestamp when message was created.
    """

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system', 'tool')",
            name="chat_messages_role_check",
        ),
        {"schema": "messaging"},
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign keys
    chat_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messaging.chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_message_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messaging.chat_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Message content
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # LLM metadata
    llm_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    message_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Timestamps
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    chat: Mapped["Chat"] = relationship(
        "Chat",
        back_populates="messages",
    )
    previous_message: Mapped[Optional["ChatMessage"]] = relationship(
        "ChatMessage",
        remote_side=[id],
        foreign_keys=[previous_message_id],
    )

    def __repr__(self) -> str:
        """String representation of the message."""
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        return f"<ChatMessage(id={self.id}, role={self.role}, content='{content_preview}')>"

    def to_api_format(self) -> dict[str, str]:
        """
        Convert to Claude API message format.

        Returns:
            Dictionary with 'role' and 'content' keys.
        """
        return {"role": self.role, "content": self.content}


# -----------------------------------------------------------------------------
# TelegramSession Model
# -----------------------------------------------------------------------------
class TelegramSession(Base):
    """
    ORM model for messaging.telegram_sessions table.

    Maps Telegram chat IDs to internal chat sessions, allowing users to
    manage conversation context from Telegram.

    Attributes:
        telegram_chat_id: Telegram chat ID (primary key).
        telegram_user_id: Telegram user ID.
        active_chat_id: Currently active internal chat UUID.
        created_on: When the session mapping was created.
        modified_on: When the session was last modified.
    """

    __tablename__ = "telegram_sessions"
    __table_args__ = {"schema": "messaging"}

    # Primary key: Telegram chat ID
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    # Telegram user ID
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    # Foreign key to active chat
    active_chat_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messaging.chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Timestamps
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    modified_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    active_chat: Mapped["Chat"] = relationship(
        "Chat",
        foreign_keys=[active_chat_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of the session."""
        return (
            f"<TelegramSession(telegram_chat_id={self.telegram_chat_id}, "
            f"active_chat_id={self.active_chat_id})>"
        )
