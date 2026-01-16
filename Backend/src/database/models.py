# =============================================================================
# Database ORM Models
# =============================================================================
"""
SQLAlchemy ORM models for the Claude Assistant Platform.

These models map to the PostgreSQL tables defined in the migrations.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
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


# =============================================================================
# Enums for Resume Schema
# =============================================================================

class SkillProficiency(StrEnum):
    """Skill proficiency levels matching PostgreSQL enum."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillCategory(StrEnum):
    """Skill categories for organization matching PostgreSQL enum."""

    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    DEVOPS = "devops"
    SOFT_SKILL = "soft_skill"
    TOOL = "tool"
    METHODOLOGY = "methodology"
    OTHER = "other"


class EmploymentType(StrEnum):
    """Employment types matching PostgreSQL enum."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"


class DegreeType(StrEnum):
    """Education degree types matching PostgreSQL enum."""

    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"
    CERTIFICATE = "certificate"
    BOOTCAMP = "bootcamp"
    OTHER = "other"


class ResumeFormat(StrEnum):
    """Resume output formats matching PostgreSQL enum."""

    PDF = "pdf"
    DOCX = "docx"


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


# =============================================================================
# Resume Schema Models
# =============================================================================


# -----------------------------------------------------------------------------
# UserProfile Model
# -----------------------------------------------------------------------------
class UserProfile(Base):
    """
    ORM model for resume.user_profiles table.

    Contains personal information, contact details, professional links,
    and default summary for resume generation. This is the central table
    that all other resume data relates to.

    Attributes:
        id: Unique identifier (UUID).
        first_name: User's first name.
        last_name: User's last name.
        email: Primary email address.
        phone: Phone number.
        city: City of residence.
        state: State/province.
        country: Country of residence.
        linkedin_url: LinkedIn profile URL.
        github_url: GitHub profile URL.
        portfolio_url: Portfolio website URL.
        personal_website: Personal website URL.
        professional_summary: Default professional summary for resumes.
        telegram_user_id: Optional link to Telegram identity.
        metadata: Flexible JSONB storage.
        created_at: When the profile was created.
        updated_at: When the profile was last modified.
    """

    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "resume"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Personal information
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="User's first name",
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="User's last name",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Primary email address",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Phone number",
    )

    # Location
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="City of residence",
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="State or province",
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="United States",
        server_default="United States",
        doc="Country of residence",
    )

    # Professional links
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="LinkedIn profile URL",
    )
    github_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="GitHub profile URL",
    )
    portfolio_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Portfolio website URL",
    )
    personal_website: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Personal website URL",
    )

    # Professional summary
    professional_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Default professional summary for resumes",
    )

    # Telegram identity link
    telegram_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        doc="Links profile to Telegram identity",
    )

    # Metadata
    profile_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Flexible JSON storage for additional profile data",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    skills: Mapped[list["Skill"]] = relationship(
        "Skill",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Skill.display_order",
        lazy="selectin",
    )
    work_experiences: Mapped[list["WorkExperience"]] = relationship(
        "WorkExperience",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(WorkExperience.start_date)",
        lazy="selectin",
    )
    education_entries: Mapped[list["Education"]] = relationship(
        "Education",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(Education.end_date)",
        lazy="selectin",
    )
    certifications: Mapped[list["Certification"]] = relationship(
        "Certification",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(Certification.issue_date)",
        lazy="selectin",
    )
    generated_resumes: Mapped[list["GeneratedResume"]] = relationship(
        "GeneratedResume",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(GeneratedResume.generated_at)",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of the profile."""
        return f"<UserProfile(id={self.id}, name={self.first_name} {self.last_name})>"

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}"


# -----------------------------------------------------------------------------
# Skill Model
# -----------------------------------------------------------------------------
class Skill(Base):
    """
    ORM model for resume.skills table.

    Represents a skill with category, proficiency level, and experience.
    Used for matching against job requirements.

    Attributes:
        id: Unique identifier (UUID).
        profile_id: Foreign key to user profile.
        name: Skill name.
        category: Skill category (programming_language, framework, etc.).
        proficiency: Proficiency level (beginner to expert).
        years_experience: Years of experience with this skill.
        keywords: Alternative names for job matching.
        display_order: Order for resume display.
        is_featured: Whether to prioritize in resume generation.
        created_at: When the skill was added.
        updated_at: When the skill was last modified.
    """

    __tablename__ = "skills"
    __table_args__ = {"schema": "resume"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign key
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resume.user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Skill details
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Skill name",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SkillCategory.OTHER,
        server_default=SkillCategory.OTHER,
        doc="Skill category",
    )
    proficiency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SkillProficiency.INTERMEDIATE,
        server_default=SkillProficiency.INTERMEDIATE,
        doc="Proficiency level",
    )
    years_experience: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 1),
        nullable=True,
        doc="Years of experience with this skill",
    )

    # Matching keywords
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Alternative names for job matching",
    )

    # Display settings
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Order for resume display",
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether to prioritize in resume generation",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="skills",
    )

    def __repr__(self) -> str:
        """String representation of the skill."""
        return f"<Skill(id={self.id}, name={self.name}, proficiency={self.proficiency})>"


# -----------------------------------------------------------------------------
# WorkExperience Model
# -----------------------------------------------------------------------------
class WorkExperience(Base):
    """
    ORM model for resume.work_experiences table.

    Represents a job position in the user's work history.

    Attributes:
        id: Unique identifier (UUID).
        profile_id: Foreign key to user profile.
        company_name: Name of the employer.
        company_url: Company website URL.
        company_location: Company location.
        job_title: Position title.
        employment_type: Type of employment (full_time, etc.).
        start_date: Employment start date.
        end_date: Employment end date (None if current).
        is_current: Whether this is the current position.
        description: Job description.
        achievements: Array of achievement bullet points.
        skills_used: Skills utilized in this role.
        display_order: Order for resume display.
        created_at: When the entry was added.
        updated_at: When the entry was last modified.
    """

    __tablename__ = "work_experiences"
    __table_args__ = {"schema": "resume"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign key
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resume.user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Company information
    company_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        doc="Employer name",
    )
    company_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Company website URL",
    )
    company_location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Company location",
    )

    # Role information
    job_title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        doc="Position title",
    )
    employment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EmploymentType.FULL_TIME,
        server_default=EmploymentType.FULL_TIME,
        doc="Type of employment",
    )

    # Dates
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Employment start date",
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Employment end date (None if current)",
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether this is the current position",
    )

    # Description and achievements
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Job description",
    )
    achievements: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Achievement bullet points",
    )

    # Skills used
    skills_used: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Skills utilized in this role",
    )

    # Display order
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Order for resume display",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="work_experiences",
    )

    def __repr__(self) -> str:
        """String representation of the work experience."""
        return f"<WorkExperience(id={self.id}, title={self.job_title}, company={self.company_name})>"


# -----------------------------------------------------------------------------
# Education Model
# -----------------------------------------------------------------------------
class Education(Base):
    """
    ORM model for resume.education table.

    Represents an educational entry in the user's background.

    Attributes:
        id: Unique identifier (UUID).
        profile_id: Foreign key to user profile.
        institution_name: Name of the institution.
        institution_location: Institution location.
        institution_url: Institution website URL.
        degree_type: Type of degree (bachelor, master, etc.).
        degree_name: Full degree name.
        field_of_study: Major or field of study.
        start_date: Start date.
        end_date: Graduation or expected date.
        is_in_progress: Whether currently enrolled.
        gpa: Grade point average.
        gpa_scale: GPA scale (usually 4.0).
        honors: Academic honors.
        relevant_coursework: Relevant courses.
        activities: Extracurricular activities.
        display_order: Order for resume display.
        created_at: When the entry was added.
        updated_at: When the entry was last modified.
    """

    __tablename__ = "education"
    __table_args__ = {"schema": "resume"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign key
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resume.user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Institution information
    institution_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        doc="Name of the institution",
    )
    institution_location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Institution location",
    )
    institution_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Institution website URL",
    )

    # Degree information
    degree_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Type of degree",
    )
    degree_name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        doc="Full degree name (e.g., Bachelor of Science)",
    )
    field_of_study: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        doc="Major or field of study",
    )

    # Dates
    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Start date",
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Graduation or expected date",
    )
    is_in_progress: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether currently enrolled",
    )

    # Academic details
    gpa: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        doc="Grade point average",
    )
    gpa_scale: Mapped[Decimal] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=Decimal("4.0"),
        server_default="4.0",
        doc="GPA scale",
    )

    # Additional details
    honors: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Academic honors",
    )
    relevant_coursework: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Relevant courses",
    )
    activities: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Extracurricular activities",
    )

    # Display order
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Order for resume display",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="education_entries",
    )

    def __repr__(self) -> str:
        """String representation of the education entry."""
        return f"<Education(id={self.id}, degree={self.degree_type}, field={self.field_of_study})>"


# -----------------------------------------------------------------------------
# Certification Model
# -----------------------------------------------------------------------------
class Certification(Base):
    """
    ORM model for resume.certifications table.

    Represents a professional certification or credential.

    Attributes:
        id: Unique identifier (UUID).
        profile_id: Foreign key to user profile.
        name: Certification name.
        issuing_organization: Organization that issued the certification.
        credential_id: Credential ID or number.
        credential_url: URL to verify the credential.
        issue_date: When the certification was issued.
        expiration_date: When the certification expires (None if no expiration).
        is_active: Whether the certification is currently active.
        related_skills: Skills this certification validates.
        display_order: Order for resume display.
        created_at: When the entry was added.
        updated_at: When the entry was last modified.
    """

    __tablename__ = "certifications"
    __table_args__ = {"schema": "resume"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign key
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resume.user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Certification details
    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        doc="Certification name",
    )
    issuing_organization: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        doc="Organization that issued the certification",
    )
    credential_id: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Credential ID or number",
    )
    credential_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="URL to verify the credential",
    )

    # Dates
    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="When the certification was issued",
    )
    expiration_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="When the certification expires",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="Whether the certification is currently active",
    )

    # Related skills
    related_skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Skills this certification validates",
    )

    # Display order
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Order for resume display",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="certifications",
    )

    def __repr__(self) -> str:
        """String representation of the certification."""
        return f"<Certification(id={self.id}, name={self.name})>"


# -----------------------------------------------------------------------------
# JobListing Model
# -----------------------------------------------------------------------------
class JobListing(Base):
    """
    ORM model for resume.job_listings table.

    Stores scraped job descriptions for resume tailoring.

    Attributes:
        id: Unique identifier (UUID).
        url: Source URL of the job listing.
        source_site: Website source (linkedin, indeed, etc.).
        job_title: Position title.
        company_name: Company name.
        company_url: Company website URL.
        location: Job location.
        is_remote: Whether the position is remote.
        salary_min: Minimum salary (if available).
        salary_max: Maximum salary (if available).
        salary_currency: Salary currency.
        description: Full job description.
        required_skills: Skills explicitly required.
        preferred_skills: Skills listed as preferred.
        requirements: Other requirements.
        raw_html: Original HTML for re-parsing.
        scraped_at: When the listing was scraped.
        notes: User notes.
        is_favorite: Whether marked as favorite.
        application_status: Current application status.
        applied_at: When user applied.
        created_at: When the entry was added.
        updated_at: When the entry was last modified.
    """

    __tablename__ = "job_listings"
    __table_args__ = {"schema": "resume"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Source information
    url: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        unique=True,
        doc="Source URL of the job listing",
    )
    source_site: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Website source",
    )

    # Job details
    job_title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Position title",
    )
    company_name: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        doc="Company name",
    )
    company_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Company website URL",
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        doc="Job location",
    )
    is_remote: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        doc="Whether the position is remote",
    )

    # Salary information
    salary_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Minimum salary",
    )
    salary_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Maximum salary",
    )
    salary_currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
        server_default="USD",
        doc="Salary currency",
    )

    # Job description
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full job description",
    )

    # Extracted requirements
    required_skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Skills explicitly required",
    )
    preferred_skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Skills listed as preferred",
    )
    requirements: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Other requirements",
    )

    # Raw HTML
    raw_html: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Original HTML for re-parsing",
    )

    # Scraping metadata
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When the listing was scraped",
    )

    # User notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User notes",
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether marked as favorite",
    )

    # Application status
    application_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="not_applied",
        server_default="not_applied",
        doc="Current application status",
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When user applied",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    generated_resumes: Mapped[list["GeneratedResume"]] = relationship(
        "GeneratedResume",
        back_populates="job_listing",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of the job listing."""
        return f"<JobListing(id={self.id}, title={self.job_title}, company={self.company_name})>"


# -----------------------------------------------------------------------------
# GeneratedResume Model
# -----------------------------------------------------------------------------
class GeneratedResume(Base):
    """
    ORM model for resume.generated_resumes table.

    Records of generated resumes with Google Drive file references.

    Attributes:
        id: Unique identifier (UUID).
        profile_id: Foreign key to user profile.
        job_listing_id: Foreign key to job listing (optional).
        name: Resume name/identifier.
        format: Output format (pdf, docx).
        drive_file_id: Google Drive file ID.
        drive_file_url: Google Drive file URL.
        drive_folder_id: Google Drive folder ID.
        content_snapshot: JSON snapshot of data used.
        included_skills: UUIDs of skills included.
        skill_match_score: Percentage of required skills matched.
        overall_match_score: Overall suitability score.
        match_analysis: Detailed matching breakdown.
        template_used: Template name used.
        generation_params: Generation parameters.
        generated_at: When the resume was generated.
        created_at: When the record was created.
        updated_at: When the record was last modified.
    """

    __tablename__ = "generated_resumes"
    __table_args__ = {"schema": "resume"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign keys
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resume.user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_listing_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resume.job_listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Resume metadata
    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        doc="Resume name/identifier",
    )
    format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Output format",
    )

    # Google Drive storage
    drive_file_id: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Google Drive file ID",
    )
    drive_file_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Google Drive file URL",
    )
    drive_folder_id: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Google Drive folder ID",
    )

    # Content snapshot
    content_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="JSON snapshot of data used for this resume",
    )

    # Included skills (stored as UUID array)
    included_skills: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        default=list,
        server_default="{}",
        doc="UUIDs of skills included in this resume",
    )

    # Match analysis
    skill_match_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        doc="Percentage of required skills matched",
    )
    overall_match_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        doc="Overall suitability score",
    )
    match_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Detailed matching breakdown",
    )

    # Generation metadata
    template_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="default",
        server_default="default",
        doc="Template name used",
    )
    generation_params: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Generation parameters",
    )

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When the resume was generated",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="generated_resumes",
    )
    job_listing: Mapped[Optional["JobListing"]] = relationship(
        "JobListing",
        back_populates="generated_resumes",
    )

    def __repr__(self) -> str:
        """String representation of the generated resume."""
        return f"<GeneratedResume(id={self.id}, name={self.name}, format={self.format})>"
