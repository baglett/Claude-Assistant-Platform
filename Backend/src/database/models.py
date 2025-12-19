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
    Integer,
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


# -----------------------------------------------------------------------------
# Todo Model
# -----------------------------------------------------------------------------
class Todo(Base):
    """
    ORM model for tasks.todos table.

    Represents a todo/task that can be tracked and executed by agents.
    Supports agent assignment, scheduling, priority, and result storage.

    Attributes:
        id: Unique identifier (UUID).
        title: Short description of the task.
        description: Detailed task information.
        status: Current state (pending, in_progress, completed, failed, cancelled).
        assigned_agent: Sub-agent responsible for execution.
        priority: Execution priority (1=critical, 5=lowest).
        scheduled_at: When to execute (None for manual trigger).
        result: Agent output after execution.
        error_message: Error details if execution failed.
        execution_attempts: Number of execution attempts.
        chat_id: Link to originating conversation.
        parent_todo_id: Parent task for subtask relationships.
        task_metadata: Flexible JSONB storage for agent-specific parameters.
        created_at: When the todo was created.
        updated_at: When the todo was last modified.
        started_at: When execution began.
        completed_at: When execution finished.
        created_by: User or source that created this todo.
    """

    __tablename__ = "todos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')",
            name="todos_status_check",
        ),
        CheckConstraint(
            "assigned_agent IS NULL OR assigned_agent IN ('github', 'email', 'calendar', 'obsidian', 'orchestrator')",
            name="todos_assigned_agent_check",
        ),
        CheckConstraint(
            "priority >= 1 AND priority <= 5",
            name="todos_priority_check",
        ),
        CheckConstraint(
            "execution_attempts >= 0",
            name="todos_execution_attempts_check",
        ),
        {"schema": "tasks"},
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Core fields
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Short description of the task",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed task information and context",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        doc="Current task status",
    )

    # Agent assignment
    assigned_agent: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Sub-agent responsible for execution",
    )

    # Priority (1 = highest, 5 = lowest)
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
        doc="Execution priority (1=critical, 5=lowest)",
    )

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Scheduled execution time (None for manual trigger)",
    )

    # Execution results
    result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Agent output after successful execution",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error details if execution failed",
    )
    execution_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Number of execution attempts",
    )

    # Context linking
    chat_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messaging.chats.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Reference to originating conversation",
    )
    parent_todo_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.todos.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Parent task for subtask hierarchies",
    )

    # Task metadata (named task_metadata to avoid conflict with SQLAlchemy's metadata)
    task_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Flexible JSON storage for agent-specific parameters",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When the todo was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the todo was last modified",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution began",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution finished (success or failure)",
    )

    # User tracking
    created_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="User or source that created this todo",
    )

    # Relationships
    chat: Mapped[Optional["Chat"]] = relationship(
        "Chat",
        foreign_keys=[chat_id],
        doc="Associated conversation",
    )
    parent: Mapped[Optional["Todo"]] = relationship(
        "Todo",
        remote_side=[id],
        foreign_keys=[parent_todo_id],
        back_populates="subtasks",
        doc="Parent task",
    )
    subtasks: Mapped[list["Todo"]] = relationship(
        "Todo",
        back_populates="parent",
        cascade="all, delete-orphan",
        doc="Child subtasks",
    )

    def __repr__(self) -> str:
        """String representation of the todo."""
        title_preview = self.title[:30] + "..." if len(self.title) > 30 else self.title
        return (
            f"<Todo(id={self.id}, status={self.status}, "
            f"title='{title_preview}')>"
        )

    @property
    def is_terminal(self) -> bool:
        """
        Check if the todo is in a terminal state.

        Returns:
            True if completed, failed, or cancelled.
        """
        return self.status in ("completed", "failed", "cancelled")

    @property
    def is_executable(self) -> bool:
        """
        Check if the todo can be executed.

        Returns:
            True if pending or failed (for retry).
        """
        return self.status in ("pending", "failed")


# -----------------------------------------------------------------------------
# AgentExecution Model
# -----------------------------------------------------------------------------
class AgentExecution(Base):
    """
    ORM model for agents.executions table.

    Stores detailed execution logs for all agent invocations, including
    thinking process, tool calls, results, and performance metrics.
    Supports tracking nested agent calls via parent_execution_id.

    Attributes:
        id: Unique identifier (UUID).
        chat_id: Reference to conversation context.
        todo_id: Reference to todo being executed (if applicable).
        parent_execution_id: Parent execution for nested agent calls.
        agent_name: Name of the executing agent.
        status: Current execution status.
        task_description: The task or instruction given to the agent.
        input_context: Context passed to the agent (JSONB).
        thinking: Agent's reasoning and thought process.
        tool_calls: Array of tool invocations (JSONB).
        result: Final execution result/output.
        error_message: Error details if execution failed.
        input_tokens: Total input tokens used.
        output_tokens: Total output tokens used.
        execution_time_ms: Total execution duration in milliseconds.
        llm_calls: Number of LLM API calls made.
        started_at: When execution began.
        completed_at: When execution finished.
        created_at: When this record was created.
    """

    __tablename__ = "executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="executions_status_check",
        ),
        {"schema": "agents"},
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # -------------------------------------------------------------------------
    # Context Linking
    # -------------------------------------------------------------------------
    chat_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messaging.chats.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Reference to conversation context",
    )
    todo_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.todos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Reference to todo being executed",
    )
    parent_execution_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Parent execution for nested agent calls",
    )

    # -------------------------------------------------------------------------
    # Agent Information
    # -------------------------------------------------------------------------
    agent_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Name of the executing agent",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        doc="Current execution status",
    )

    # -------------------------------------------------------------------------
    # Execution Details
    # -------------------------------------------------------------------------
    task_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="The task or instruction given to the agent",
    )
    input_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Context passed to the agent",
    )
    thinking: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Agent reasoning and thought process",
    )
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        doc="Array of tool invocations",
    )
    result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Final execution result/output",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error details if execution failed",
    )

    # -------------------------------------------------------------------------
    # Performance Metrics
    # -------------------------------------------------------------------------
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Total input tokens used",
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Total output tokens used",
    )
    execution_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Total execution duration in milliseconds",
    )
    llm_calls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Number of LLM API calls made",
    )

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution began",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution finished",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When this record was created",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    chat: Mapped[Optional["Chat"]] = relationship(
        "Chat",
        foreign_keys=[chat_id],
        doc="Associated conversation",
    )
    todo: Mapped[Optional["Todo"]] = relationship(
        "Todo",
        foreign_keys=[todo_id],
        doc="Associated todo",
    )
    parent_execution: Mapped[Optional["AgentExecution"]] = relationship(
        "AgentExecution",
        remote_side=[id],
        foreign_keys=[parent_execution_id],
        back_populates="child_executions",
        doc="Parent execution (for nested calls)",
    )
    child_executions: Mapped[list["AgentExecution"]] = relationship(
        "AgentExecution",
        back_populates="parent_execution",
        doc="Child executions (nested agent calls)",
    )

    def __repr__(self) -> str:
        """String representation of the execution."""
        return (
            f"<AgentExecution(id={self.id}, agent={self.agent_name}, "
            f"status={self.status})>"
        )

    @property
    def is_terminal(self) -> bool:
        """Check if the execution is in a terminal state."""
        return self.status in ("completed", "failed", "cancelled")

    @property
    def total_tokens(self) -> int:
        """Get total token usage."""
        return self.input_tokens + self.output_tokens
