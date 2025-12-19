# Todo Tracking System - Implementation Plan

## Overview

This document outlines the implementation plan for a custom todo/task tracking system optimized for LLM agent execution. The system enables the orchestrator to create, track, and automatically execute tasks through specialized sub-agents.

## Design Rationale

### Why Custom vs External Platform?

We chose a custom implementation over integrating with external platforms (Todoist, Asana, etc.) because:

1. **Agent Routing**: Todos need an `assigned_agent` field to route execution to the correct sub-agent (GitHub, Email, Calendar, Obsidian)
2. **Automatic Execution**: The orchestrator must programmatically trigger task execution, not just store tasks
3. **Result Storage**: We need to capture and persist what the agent returned after execution
4. **No External Dependencies**: Eliminates API rate limits, latency, and credential management overhead
5. **Schema Flexibility**: Full control over data model for future enhancements

## Prerequisites: Database Infrastructure

Before implementing the todo system, we need to:
1. Create a universal `DatabaseManager` interface
2. Migrate from `asyncpg` to `psycopg` (psycopg3)

### Why a DatabaseManager Interface?

The current implementation uses module-level globals and functions. A proper abstraction provides:

| Benefit | Description |
|---------|-------------|
| **Testability** | Easy to mock/inject for unit tests |
| **Swappability** | Change drivers without touching business logic |
| **Lifecycle Management** | Clear init/shutdown/health check patterns |
| **Retry Logic** | Centralized connection retry and recovery |
| **Observability** | Single place for metrics and logging |
| **Type Safety** | Protocol-based interface for IDE support |

### Why psycopg over asyncpg?

| Feature | psycopg3 | asyncpg |
|---------|----------|---------|
| Native async/sync support | Yes (single package) | Async only |
| Connection pooling | Built-in `ConnectionPool` | External required |
| COPY support | Full support | Limited |
| Pipeline mode | Yes | No |
| Prepared statements | Auto-managed | Manual |
| Type adaptation | Extensible, Pythonic | Custom codecs |
| Maintained by | PostgreSQL core team | Third party |

---

### DatabaseManager Implementation

**File:** `Backend/src/database/manager.py` (new file)

```python
# =============================================================================
# Database Manager
# =============================================================================
"""
Universal database manager interface for connection lifecycle management.

Provides a clean abstraction over SQLAlchemy async engine with:
- Connection pooling configuration
- Health checks with retry logic
- Graceful shutdown
- Session context management
- Dependency injection support
"""

import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator, Protocol, Self

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """
    Immutable database configuration.

    Attributes:
        url: Database connection URL (e.g., postgresql+psycopg://user:pass@host/db)
        pool_size: Number of connections to maintain in the pool.
        max_overflow: Maximum connections beyond pool_size during peak load.
        pool_pre_ping: Whether to verify connections before use.
        pool_recycle: Seconds before recycling a connection (prevents stale connections).
        connect_timeout: Seconds to wait for a connection.
        echo: Whether to log SQL statements (debug mode).
        echo_pool: Whether to log connection pool events.
    """

    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_pre_ping: bool = True
    pool_recycle: int = 3600
    connect_timeout: int = 10
    echo: bool = False
    echo_pool: bool = False

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        if not self.url:
            raise ValueError("Database URL is required")
        if self.pool_size < 1:
            raise ValueError("pool_size must be at least 1")
        if self.max_overflow < 0:
            raise ValueError("max_overflow cannot be negative")


# -----------------------------------------------------------------------------
# Protocol Definition
# -----------------------------------------------------------------------------
class DatabaseManagerProtocol(Protocol):
    """
    Protocol defining the database manager interface.

    Implementations must provide connection lifecycle management,
    session handling, and health checking capabilities.
    """

    @property
    def is_connected(self) -> bool:
        """Whether the database connection is established."""
        ...

    async def connect(self) -> None:
        """Establish database connection and verify connectivity."""
        ...

    async def disconnect(self) -> None:
        """Close all connections and release resources."""
        ...

    async def health_check(self) -> bool:
        """
        Check database connectivity.

        Returns:
            True if database is reachable, False otherwise.
        """
        ...

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic transaction management.

        Commits on success, rolls back on exception.

        Yields:
            AsyncSession for database operations.
        """
        ...

    async def session_dependency(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency for automatic session management."""
        ...


# -----------------------------------------------------------------------------
# Implementation
# -----------------------------------------------------------------------------
class DatabaseManager:
    """
    SQLAlchemy-based database manager implementation.

    Manages the async engine lifecycle, connection pooling, and session
    creation. Designed for dependency injection and clean shutdown.

    Example:
        config = DatabaseConfig(url="postgresql+psycopg://...")
        db = DatabaseManager(config)

        async with db:
            async with db.session() as session:
                result = await session.execute(query)

        # Or manually:
        await db.connect()
        try:
            async with db.session() as session:
                ...
        finally:
            await db.disconnect()
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize the database manager.

        Args:
            config: Database configuration settings.
        """
        self._config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def is_connected(self) -> bool:
        """Whether the database connection is established."""
        return self._engine is not None

    @property
    def engine(self) -> AsyncEngine:
        """
        Get the SQLAlchemy async engine.

        Raises:
            RuntimeError: If not connected.
        """
        if self._engine is None:
            raise RuntimeError(
                "Database not connected. Call connect() first."
            )
        return self._engine

    async def connect(self) -> None:
        """
        Establish database connection and verify connectivity.

        Creates the async engine with connection pooling and tests
        the connection with a simple query.

        Raises:
            Exception: If connection fails.
        """
        if self._engine is not None:
            logger.warning("Database already connected, skipping connect()")
            return

        logger.info(f"Connecting to database (pool_size={self._config.pool_size})...")

        # Create async engine with psycopg driver
        self._engine = create_async_engine(
            self._config.url,
            echo=self._config.echo,
            echo_pool=self._config.echo_pool,
            pool_size=self._config.pool_size,
            max_overflow=self._config.max_overflow,
            pool_pre_ping=self._config.pool_pre_ping,
            pool_recycle=self._config.pool_recycle,
            connect_args={
                "connect_timeout": self._config.connect_timeout,
            },
        )

        # Create session factory
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        # Verify connection
        if not await self.health_check():
            await self.disconnect()
            raise ConnectionError("Failed to verify database connection")

        logger.info("Database connection established successfully")

    async def disconnect(self) -> None:
        """
        Close all connections and release resources.

        Safe to call multiple times.
        """
        if self._engine is None:
            return

        logger.info("Disconnecting from database...")

        await self._engine.dispose()
        self._engine = None
        self._session_factory = None

        logger.info("Database disconnected")

    async def health_check(self) -> bool:
        """
        Check database connectivity with a simple query.

        Returns:
            True if database is reachable, False otherwise.
        """
        if self._engine is None:
            return False

        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic transaction management.

        Commits on success, rolls back on exception.

        Yields:
            AsyncSession for database operations.

        Raises:
            RuntimeError: If not connected.

        Example:
            async with db.session() as session:
                user = User(name="Alice")
                session.add(user)
                # Commits automatically on exit
        """
        if self._session_factory is None:
            raise RuntimeError(
                "Database not connected. Call connect() first."
            )

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def session_dependency(self) -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency for automatic session management.

        Use with FastAPI's Depends() for request-scoped sessions.

        Yields:
            AsyncSession for the request lifecycle.

        Example:
            @app.get("/users")
            async def get_users(
                session: AsyncSession = Depends(db.session_dependency)
            ):
                ...
        """
        async with self.session() as session:
            yield session

    # -------------------------------------------------------------------------
    # Context Manager Support
    # -------------------------------------------------------------------------
    async def __aenter__(self) -> Self:
        """Async context manager entry - connects to database."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - disconnects from database."""
        await self.disconnect()


# -----------------------------------------------------------------------------
# Factory Function
# -----------------------------------------------------------------------------
def create_database_manager(
    url: str,
    *,
    pool_size: int = 5,
    max_overflow: int = 10,
    echo: bool = False,
    **kwargs,
) -> DatabaseManager:
    """
    Factory function to create a DatabaseManager with common defaults.

    Args:
        url: Database connection URL.
        pool_size: Connection pool size.
        max_overflow: Max connections beyond pool.
        echo: Whether to log SQL.
        **kwargs: Additional DatabaseConfig options.

    Returns:
        Configured DatabaseManager instance.

    Example:
        db = create_database_manager(
            "postgresql+psycopg://user:pass@localhost/mydb",
            pool_size=10,
        )
    """
    config = DatabaseConfig(
        url=url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=echo,
        **kwargs,
    )
    return DatabaseManager(config)
```

---

### Update connection.py to Use DatabaseManager

**File:** `Backend/src/database/connection.py` (refactored)

```python
# =============================================================================
# Database Connection (Backwards Compatibility Layer)
# =============================================================================
"""
Database connection module providing backwards-compatible functions.

This module wraps the DatabaseManager class to maintain compatibility
with existing code while enabling gradual migration to the new interface.

New code should import and use DatabaseManager directly:
    from src.database.manager import DatabaseManager, DatabaseConfig

Legacy code can continue using:
    from src.database import init_database, get_session
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.manager import DatabaseConfig, DatabaseManager


logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Global Instance (for backwards compatibility)
# -----------------------------------------------------------------------------
_db_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """
    Get the global DatabaseManager instance.

    Returns:
        The initialized DatabaseManager.

    Raises:
        RuntimeError: If database not initialized.
    """
    if _db_manager is None:
        raise RuntimeError(
            "Database not initialized. Call init_database() first."
        )
    return _db_manager


# -----------------------------------------------------------------------------
# Legacy Functions (backwards compatible)
# -----------------------------------------------------------------------------
async def init_database() -> None:
    """
    Initialize the database connection.

    Creates and connects the global DatabaseManager instance.
    Should be called once during application startup.

    Raises:
        Exception: If connection fails.
    """
    global _db_manager

    settings = get_settings()

    config = DatabaseConfig(
        url=settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_timeout=10,
        echo=settings.debug,
    )

    _db_manager = DatabaseManager(config)
    await _db_manager.connect()


async def close_database() -> None:
    """
    Close the database connection.

    Should be called during application shutdown.
    """
    global _db_manager

    if _db_manager is not None:
        await _db_manager.disconnect()
        _db_manager = None


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as a context manager.

    Yields:
        AsyncSession with automatic commit/rollback.

    Example:
        async with get_session() as session:
            result = await session.execute(query)
    """
    db = get_database_manager()
    async with db.session() as session:
        yield session


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        AsyncSession for the request lifecycle.
    """
    db = get_database_manager()
    async for session in db.session_dependency():
        yield session


def get_session_factory():
    """
    Get the session factory (legacy compatibility).

    Returns:
        The async session factory.
    """
    db = get_database_manager()
    return db._session_factory
```

---

### Update settings.py Database URL

**File:** `Backend/src/config/settings.py` (update property)

```python
@property
def database_url(self) -> str:
    """
    Construct the database URL for psycopg async driver.

    Returns:
        PostgreSQL connection URL using psycopg dialect.
    """
    return (
        f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
        f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    )
```

---

### Update pyproject.toml Dependencies

**File:** `Backend/pyproject.toml` (update dependencies)

```toml
# Database - replace asyncpg with psycopg
"sqlalchemy>=2.0.36",
"psycopg[binary,pool]>=3.2.0",  # Was: "asyncpg>=0.30.0"
"alembic>=1.14.0",
```

---

### Migration Commands

```powershell
# Navigate to backend directory
cd Backend

# Remove asyncpg, add psycopg
uv remove asyncpg
uv add "psycopg[binary,pool]>=3.2.0"
uv sync

# Test the new setup
uv run python -c "
from src.database.manager import DatabaseManager, DatabaseConfig
from src.config import get_settings
import asyncio

async def test():
    settings = get_settings()
    config = DatabaseConfig(url=settings.database_url)
    async with DatabaseManager(config) as db:
        print(f'Connected: {db.is_connected}')
        print(f'Health: {await db.health_check()}')

asyncio.run(test())
"
```

---

### Usage Patterns

**New Code (Recommended):**

```python
from src.database.manager import DatabaseManager, DatabaseConfig

# In application setup
config = DatabaseConfig(url=settings.database_url, pool_size=10)
db_manager = DatabaseManager(config)

# As dependency
class TodoService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create_todo(self, data: TodoCreate) -> Todo:
        async with self.db.session() as session:
            todo = Todo(**data.model_dump())
            session.add(todo)
            return todo
```

**Legacy Code (Still Works):**

```python
from src.database import init_database, get_session, close_database

# Startup
await init_database()

# Usage
async with get_session() as session:
    result = await session.execute(query)

# Shutdown
await close_database()
```

---

## Phase 1: Database Layer

### 1.1 Database Migration

**File:** `Backend/database/migrations/003_create_todos_table.sql`

```sql
-- Migration: 003_create_todos_table.sql
-- Description: Create todos table for task tracking and agent execution
-- Created: 2024-XX-XX

CREATE TABLE IF NOT EXISTS todos (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core task data
    title VARCHAR(500) NOT NULL,
    description TEXT,

    -- Status tracking
    -- pending: Created but not started
    -- in_progress: Currently being executed by an agent
    -- completed: Successfully finished
    -- failed: Execution failed
    -- cancelled: Manually cancelled by user
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),

    -- Agent assignment for execution routing
    -- NULL means orchestrator handles directly or user decides later
    assigned_agent VARCHAR(50)
        CHECK (assigned_agent IN (NULL, 'github', 'email', 'calendar', 'obsidian', 'orchestrator')),

    -- Priority for ordering (1 = highest, 5 = lowest)
    priority INTEGER DEFAULT 3 CHECK (priority >= 1 AND priority <= 5),

    -- Execution scheduling
    scheduled_at TIMESTAMP WITH TIME ZONE,  -- When to execute (NULL = manual/immediate)

    -- Execution results
    result TEXT,                            -- Agent response/output after execution
    error_message TEXT,                     -- Error details if failed
    execution_attempts INTEGER DEFAULT 0,   -- Retry tracking

    -- Context linking
    chat_id UUID REFERENCES chats(id) ON DELETE SET NULL,  -- Originating conversation
    parent_todo_id UUID REFERENCES todos(id) ON DELETE CASCADE,  -- For subtasks

    -- Metadata
    metadata JSONB DEFAULT '{}',            -- Flexible additional data

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,    -- When execution began
    completed_at TIMESTAMP WITH TIME ZONE,  -- When finished (success or fail)

    -- User tracking (for future multi-user support)
    created_by VARCHAR(100),                -- User/source identifier

    -- Indexes for common queries
    CONSTRAINT valid_completion CHECK (
        (status IN ('completed', 'failed', 'cancelled') AND completed_at IS NOT NULL)
        OR (status IN ('pending', 'in_progress') AND completed_at IS NULL)
    )
);

-- Indexes for performance
CREATE INDEX idx_todos_status ON todos(status);
CREATE INDEX idx_todos_assigned_agent ON todos(assigned_agent);
CREATE INDEX idx_todos_priority ON todos(priority);
CREATE INDEX idx_todos_scheduled_at ON todos(scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_todos_chat_id ON todos(chat_id) WHERE chat_id IS NOT NULL;
CREATE INDEX idx_todos_parent_id ON todos(parent_todo_id) WHERE parent_todo_id IS NOT NULL;
CREATE INDEX idx_todos_created_at ON todos(created_at DESC);

-- Trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_todos_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_todos_updated_at
    BEFORE UPDATE ON todos
    FOR EACH ROW
    EXECUTE FUNCTION update_todos_updated_at();

-- Comments for documentation
COMMENT ON TABLE todos IS 'Task tracking table for LLM agent execution';
COMMENT ON COLUMN todos.assigned_agent IS 'Sub-agent responsible for executing this task';
COMMENT ON COLUMN todos.result IS 'Output/response from agent after successful execution';
COMMENT ON COLUMN todos.metadata IS 'Flexible JSON storage for agent-specific parameters';
```

### 1.2 ORM Model

**File:** `Backend/src/database/models.py` (add to existing file)

```python
class Todo(Base):
    """
    Todo/Task model for tracking and executing tasks through sub-agents.

    This model supports the full lifecycle of a task:
    1. Creation (from user request or agent decision)
    2. Assignment (to a specific sub-agent)
    3. Scheduling (immediate or delayed execution)
    4. Execution (agent processes the task)
    5. Completion (success/failure with results)

    Attributes:
        id: Unique identifier (UUID)
        title: Short description of the task
        description: Detailed task information
        status: Current state (pending, in_progress, completed, failed, cancelled)
        assigned_agent: Which sub-agent should handle execution
        priority: Execution priority (1=highest, 5=lowest)
        scheduled_at: When to execute (None for manual trigger)
        result: Agent output after execution
        error_message: Error details if execution failed
        execution_attempts: Number of execution attempts
        chat_id: Link to originating conversation
        parent_todo_id: Parent task for subtask relationships
        metadata: Flexible JSON storage for additional data
    """

    __tablename__ = "todos"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the todo"
    )

    # Core fields
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Short description of the task"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed task information and context"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        doc="Current task status"
    )

    # Agent assignment
    assigned_agent: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Sub-agent responsible for execution"
    )

    # Priority
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        doc="Execution priority (1=highest, 5=lowest)"
    )

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Scheduled execution time"
    )

    # Execution results
    result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Agent output after execution"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error details if execution failed"
    )
    execution_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of execution attempts"
    )

    # Context linking
    chat_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="SET NULL"),
        nullable=True,
        doc="Originating conversation"
    )
    parent_todo_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("todos.id", ondelete="CASCADE"),
        nullable=True,
        doc="Parent task for subtasks"
    )

    # Metadata
    metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Flexible JSON storage"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Last update timestamp"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Execution start timestamp"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Completion timestamp"
    )

    # User tracking
    created_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="User or source identifier"
    )

    # Relationships
    chat: Mapped[Optional["Chat"]] = relationship(
        "Chat",
        back_populates="todos",
        doc="Associated conversation"
    )
    parent: Mapped[Optional["Todo"]] = relationship(
        "Todo",
        remote_side=[id],
        back_populates="subtasks",
        doc="Parent task"
    )
    subtasks: Mapped[list["Todo"]] = relationship(
        "Todo",
        back_populates="parent",
        cascade="all, delete-orphan",
        doc="Child subtasks"
    )
```

---

## Phase 2: Pydantic Models (API Schemas)

**File:** `Backend/src/models/todo.py` (new file)

```python
"""
Pydantic models for Todo API requests and responses.

These models handle validation, serialization, and documentation
for all todo-related API operations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class TodoStatus(str, Enum):
    """Valid status values for todos."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Valid agent types for task assignment."""
    GITHUB = "github"
    EMAIL = "email"
    CALENDAR = "calendar"
    OBSIDIAN = "obsidian"
    ORCHESTRATOR = "orchestrator"


class TodoPriority(int, Enum):
    """Priority levels for todos."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5


class TodoCreate(BaseModel):
    """
    Schema for creating a new todo.

    Attributes:
        title: Short description of the task (required)
        description: Detailed task information (optional)
        assigned_agent: Sub-agent to handle execution (optional)
        priority: Execution priority, 1-5 (default: 3)
        scheduled_at: When to execute (optional, None = manual)
        parent_todo_id: Parent task ID for subtasks (optional)
        metadata: Additional flexible data (optional)
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Short description of the task",
        examples=["Review PR #123", "Send weekly report email"]
    )
    description: Optional[str] = Field(
        None,
        description="Detailed task information and context",
        examples=["Check the authentication changes in PR #123 for security issues"]
    )
    assigned_agent: Optional[AgentType] = Field(
        None,
        description="Sub-agent responsible for execution"
    )
    priority: TodoPriority = Field(
        TodoPriority.MEDIUM,
        description="Execution priority (1=highest, 5=lowest)"
    )
    scheduled_at: Optional[datetime] = Field(
        None,
        description="Scheduled execution time (None for manual trigger)"
    )
    parent_todo_id: Optional[UUID] = Field(
        None,
        description="Parent task ID for creating subtasks"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible JSON storage for agent-specific parameters"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Create GitHub issue for bug fix",
                "description": "Create an issue in repo/name for the login timeout bug",
                "assigned_agent": "github",
                "priority": 2,
                "metadata": {
                    "repo": "owner/repo",
                    "labels": ["bug", "high-priority"]
                }
            }
        }
    )


class TodoUpdate(BaseModel):
    """
    Schema for updating an existing todo.

    All fields are optional - only provided fields will be updated.
    """

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Updated task title"
    )
    description: Optional[str] = Field(
        None,
        description="Updated task description"
    )
    assigned_agent: Optional[AgentType] = Field(
        None,
        description="Updated agent assignment"
    )
    priority: Optional[TodoPriority] = Field(
        None,
        description="Updated priority"
    )
    scheduled_at: Optional[datetime] = Field(
        None,
        description="Updated scheduled time"
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Updated metadata (replaces existing)"
    )


class TodoResponse(BaseModel):
    """
    Schema for todo responses.

    Includes all todo fields plus computed properties.
    """

    id: UUID = Field(..., description="Unique identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TodoStatus = Field(..., description="Current status")
    assigned_agent: Optional[AgentType] = Field(None, description="Assigned agent")
    priority: TodoPriority = Field(..., description="Priority level")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled time")
    result: Optional[str] = Field(None, description="Execution result")
    error_message: Optional[str] = Field(None, description="Error if failed")
    execution_attempts: int = Field(..., description="Attempt count")
    chat_id: Optional[UUID] = Field(None, description="Linked conversation")
    parent_todo_id: Optional[UUID] = Field(None, description="Parent task")
    metadata: dict[str, Any] = Field(..., description="Additional data")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    started_at: Optional[datetime] = Field(None, description="Execution start")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    created_by: Optional[str] = Field(None, description="Creator identifier")

    # Computed fields
    has_subtasks: bool = Field(False, description="Whether task has subtasks")
    subtask_count: int = Field(0, description="Number of subtasks")

    model_config = ConfigDict(from_attributes=True)


class TodoListResponse(BaseModel):
    """Schema for paginated todo list responses."""

    items: list[TodoResponse] = Field(..., description="List of todos")
    total: int = Field(..., description="Total count matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether more pages exist")


class TodoExecuteRequest(BaseModel):
    """Schema for manually triggering todo execution."""

    force: bool = Field(
        False,
        description="Force execution even if already attempted"
    )
    timeout_seconds: int = Field(
        300,
        ge=10,
        le=3600,
        description="Execution timeout in seconds"
    )


class TodoExecuteResponse(BaseModel):
    """Schema for execution response."""

    todo_id: UUID = Field(..., description="Executed todo ID")
    status: TodoStatus = Field(..., description="Status after execution")
    result: Optional[str] = Field(None, description="Execution result")
    error_message: Optional[str] = Field(None, description="Error if failed")
    execution_time_ms: int = Field(..., description="Execution duration")


class TodoStats(BaseModel):
    """Schema for todo statistics."""

    total: int = Field(..., description="Total todos")
    pending: int = Field(..., description="Pending count")
    in_progress: int = Field(..., description="In progress count")
    completed: int = Field(..., description="Completed count")
    failed: int = Field(..., description="Failed count")
    cancelled: int = Field(..., description="Cancelled count")
    by_agent: dict[str, int] = Field(..., description="Count by assigned agent")
    by_priority: dict[int, int] = Field(..., description="Count by priority")
```

---

## Phase 3: Service Layer

**File:** `Backend/src/services/todo_service.py` (new file)

```python
"""
Todo service for managing task lifecycle and execution.

This service handles:
- CRUD operations for todos
- Status transitions and validation
- Execution triggering and result capture
- Query and filtering operations
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Todo
from src.models.todo import (
    TodoCreate,
    TodoUpdate,
    TodoStatus,
    AgentType,
    TodoResponse,
    TodoListResponse,
    TodoStats,
)


logger = logging.getLogger(__name__)


class TodoService:
    """
    Service class for todo management operations.

    Provides methods for creating, updating, querying, and executing todos.
    All database operations are async and support transaction management.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the todo service.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def create(
        self,
        data: TodoCreate,
        chat_id: Optional[UUID] = None,
        created_by: Optional[str] = None,
    ) -> Todo:
        """
        Create a new todo.

        Args:
            data: Todo creation data
            chat_id: Optional link to originating conversation
            created_by: Optional creator identifier

        Returns:
            Created Todo instance
        """
        todo = Todo(
            title=data.title,
            description=data.description,
            assigned_agent=data.assigned_agent.value if data.assigned_agent else None,
            priority=data.priority.value,
            scheduled_at=data.scheduled_at,
            parent_todo_id=data.parent_todo_id,
            metadata=data.metadata,
            chat_id=chat_id,
            created_by=created_by,
        )

        self.session.add(todo)
        await self.session.commit()
        await self.session.refresh(todo)

        logger.info(
            f"Created todo {todo.id}: '{todo.title}' "
            f"(agent={todo.assigned_agent}, priority={todo.priority})"
        )

        return todo

    async def get_by_id(
        self,
        todo_id: UUID,
        include_subtasks: bool = False,
    ) -> Optional[Todo]:
        """
        Get a todo by ID.

        Args:
            todo_id: Todo UUID
            include_subtasks: Whether to eager-load subtasks

        Returns:
            Todo instance or None if not found
        """
        query = select(Todo).where(Todo.id == todo_id)

        if include_subtasks:
            query = query.options(selectinload(Todo.subtasks))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(
        self,
        todo_id: UUID,
        data: TodoUpdate,
    ) -> Optional[Todo]:
        """
        Update an existing todo.

        Args:
            todo_id: Todo UUID to update
            data: Fields to update

        Returns:
            Updated Todo instance or None if not found
        """
        todo = await self.get_by_id(todo_id)
        if not todo:
            return None

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "assigned_agent" and value is not None:
                value = value.value
            elif field == "priority" and value is not None:
                value = value.value
            setattr(todo, field, value)

        await self.session.commit()
        await self.session.refresh(todo)

        logger.info(f"Updated todo {todo_id}: {list(update_data.keys())}")

        return todo

    async def delete(self, todo_id: UUID) -> bool:
        """
        Delete a todo and its subtasks.

        Args:
            todo_id: Todo UUID to delete

        Returns:
            True if deleted, False if not found
        """
        todo = await self.get_by_id(todo_id)
        if not todo:
            return False

        await self.session.delete(todo)
        await self.session.commit()

        logger.info(f"Deleted todo {todo_id}")

        return True

    async def update_status(
        self,
        todo_id: UUID,
        status: TodoStatus,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Todo]:
        """
        Update todo status with appropriate timestamp handling.

        Args:
            todo_id: Todo UUID
            status: New status
            result: Execution result (for completed status)
            error_message: Error message (for failed status)

        Returns:
            Updated Todo instance or None if not found
        """
        todo = await self.get_by_id(todo_id)
        if not todo:
            return None

        now = datetime.now(timezone.utc)
        todo.status = status.value

        # Set appropriate timestamps based on status
        if status == TodoStatus.IN_PROGRESS:
            todo.started_at = now
            todo.execution_attempts += 1
        elif status in (TodoStatus.COMPLETED, TodoStatus.FAILED, TodoStatus.CANCELLED):
            todo.completed_at = now
            if result:
                todo.result = result
            if error_message:
                todo.error_message = error_message

        await self.session.commit()
        await self.session.refresh(todo)

        logger.info(f"Updated todo {todo_id} status to {status.value}")

        return todo

    async def list_todos(
        self,
        status: Optional[TodoStatus] = None,
        assigned_agent: Optional[AgentType] = None,
        priority: Optional[int] = None,
        chat_id: Optional[UUID] = None,
        parent_todo_id: Optional[UUID] = None,
        include_subtasks: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> TodoListResponse:
        """
        List todos with filtering and pagination.

        Args:
            status: Filter by status
            assigned_agent: Filter by assigned agent
            priority: Filter by priority
            chat_id: Filter by conversation
            parent_todo_id: Filter by parent (None = top-level only)
            include_subtasks: Whether to eager-load subtasks
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Paginated list response
        """
        # Build filter conditions
        conditions = []

        if status:
            conditions.append(Todo.status == status.value)
        if assigned_agent:
            conditions.append(Todo.assigned_agent == assigned_agent.value)
        if priority:
            conditions.append(Todo.priority == priority)
        if chat_id:
            conditions.append(Todo.chat_id == chat_id)
        if parent_todo_id is not None:
            conditions.append(Todo.parent_todo_id == parent_todo_id)
        else:
            # Default to top-level todos only
            conditions.append(Todo.parent_todo_id.is_(None))

        # Count total
        count_query = select(func.count(Todo.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Fetch page
        query = select(Todo).order_by(
            Todo.priority.asc(),
            Todo.created_at.desc()
        )

        if conditions:
            query = query.where(and_(*conditions))

        if include_subtasks:
            query = query.options(selectinload(Todo.subtasks))

        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        todos = result.scalars().all()

        # Convert to response models
        items = []
        for todo in todos:
            subtask_count = 0
            if include_subtasks and todo.subtasks:
                subtask_count = len(todo.subtasks)

            response = TodoResponse(
                id=todo.id,
                title=todo.title,
                description=todo.description,
                status=TodoStatus(todo.status),
                assigned_agent=AgentType(todo.assigned_agent) if todo.assigned_agent else None,
                priority=todo.priority,
                scheduled_at=todo.scheduled_at,
                result=todo.result,
                error_message=todo.error_message,
                execution_attempts=todo.execution_attempts,
                chat_id=todo.chat_id,
                parent_todo_id=todo.parent_todo_id,
                metadata=todo.metadata,
                created_at=todo.created_at,
                updated_at=todo.updated_at,
                started_at=todo.started_at,
                completed_at=todo.completed_at,
                created_by=todo.created_by,
                has_subtasks=subtask_count > 0,
                subtask_count=subtask_count,
            )
            items.append(response)

        return TodoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def get_pending_for_execution(
        self,
        agent: Optional[AgentType] = None,
        limit: int = 10,
    ) -> list[Todo]:
        """
        Get pending todos ready for execution.

        Fetches todos that are:
        - Status is 'pending'
        - Scheduled time is None or in the past
        - Optionally filtered by agent

        Args:
            agent: Filter by assigned agent
            limit: Maximum todos to return

        Returns:
            List of todos ready for execution
        """
        now = datetime.now(timezone.utc)

        conditions = [
            Todo.status == "pending",
            or_(
                Todo.scheduled_at.is_(None),
                Todo.scheduled_at <= now,
            ),
        ]

        if agent:
            conditions.append(Todo.assigned_agent == agent.value)

        query = (
            select(Todo)
            .where(and_(*conditions))
            .order_by(Todo.priority.asc(), Todo.created_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stats(self) -> TodoStats:
        """
        Get aggregated todo statistics.

        Returns:
            TodoStats with counts by status, agent, and priority
        """
        # Count by status
        status_query = select(
            Todo.status,
            func.count(Todo.id)
        ).group_by(Todo.status)
        status_result = await self.session.execute(status_query)
        status_counts = dict(status_result.all())

        # Count by agent
        agent_query = select(
            Todo.assigned_agent,
            func.count(Todo.id)
        ).where(Todo.assigned_agent.isnot(None)).group_by(Todo.assigned_agent)
        agent_result = await self.session.execute(agent_query)
        agent_counts = dict(agent_result.all())

        # Count by priority
        priority_query = select(
            Todo.priority,
            func.count(Todo.id)
        ).group_by(Todo.priority)
        priority_result = await self.session.execute(priority_query)
        priority_counts = dict(priority_result.all())

        return TodoStats(
            total=sum(status_counts.values()),
            pending=status_counts.get("pending", 0),
            in_progress=status_counts.get("in_progress", 0),
            completed=status_counts.get("completed", 0),
            failed=status_counts.get("failed", 0),
            cancelled=status_counts.get("cancelled", 0),
            by_agent=agent_counts,
            by_priority=priority_counts,
        )
```

---

## Phase 4: API Endpoints

**File:** `Backend/src/api/routes/todos.py` (new file)

```python
"""
API routes for todo management.

Provides RESTful endpoints for:
- CRUD operations on todos
- Status updates and execution
- Filtering and statistics
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_session
from src.models.todo import (
    TodoCreate,
    TodoUpdate,
    TodoResponse,
    TodoListResponse,
    TodoExecuteRequest,
    TodoExecuteResponse,
    TodoStats,
    TodoStatus,
    AgentType,
)
from src.services.todo_service import TodoService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/todos", tags=["todos"])


async def get_todo_service(
    session: AsyncSession = Depends(get_session),
) -> TodoService:
    """Dependency to get TodoService instance."""
    return TodoService(session)


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new todo",
    description="Create a new todo item with optional agent assignment and scheduling.",
)
async def create_todo(
    data: TodoCreate,
    chat_id: Optional[UUID] = Query(None, description="Link to conversation"),
    created_by: Optional[str] = Query(None, description="Creator identifier"),
    service: TodoService = Depends(get_todo_service),
) -> TodoResponse:
    """
    Create a new todo.

    Args:
        data: Todo creation data
        chat_id: Optional conversation link
        created_by: Optional creator identifier

    Returns:
        Created todo response
    """
    todo = await service.create(data, chat_id=chat_id, created_by=created_by)

    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        status=TodoStatus(todo.status),
        assigned_agent=AgentType(todo.assigned_agent) if todo.assigned_agent else None,
        priority=todo.priority,
        scheduled_at=todo.scheduled_at,
        result=todo.result,
        error_message=todo.error_message,
        execution_attempts=todo.execution_attempts,
        chat_id=todo.chat_id,
        parent_todo_id=todo.parent_todo_id,
        metadata=todo.metadata,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        started_at=todo.started_at,
        completed_at=todo.completed_at,
        created_by=todo.created_by,
        has_subtasks=False,
        subtask_count=0,
    )


@router.get(
    "",
    response_model=TodoListResponse,
    summary="List todos",
    description="List todos with optional filtering and pagination.",
)
async def list_todos(
    status: Optional[TodoStatus] = Query(None, description="Filter by status"),
    assigned_agent: Optional[AgentType] = Query(None, description="Filter by agent"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by priority"),
    chat_id: Optional[UUID] = Query(None, description="Filter by conversation"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: TodoService = Depends(get_todo_service),
) -> TodoListResponse:
    """
    List todos with filtering.

    Returns paginated list of todos matching the provided filters.
    """
    return await service.list_todos(
        status=status,
        assigned_agent=assigned_agent,
        priority=priority,
        chat_id=chat_id,
        page=page,
        page_size=page_size,
        include_subtasks=True,
    )


@router.get(
    "/stats",
    response_model=TodoStats,
    summary="Get todo statistics",
    description="Get aggregated statistics about todos.",
)
async def get_stats(
    service: TodoService = Depends(get_todo_service),
) -> TodoStats:
    """Get todo statistics."""
    return await service.get_stats()


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Get a todo",
    description="Get a specific todo by ID.",
)
async def get_todo(
    todo_id: UUID,
    service: TodoService = Depends(get_todo_service),
) -> TodoResponse:
    """
    Get a todo by ID.

    Args:
        todo_id: Todo UUID

    Returns:
        Todo response

    Raises:
        404: Todo not found
    """
    todo = await service.get_by_id(todo_id, include_subtasks=True)

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    subtask_count = len(todo.subtasks) if todo.subtasks else 0

    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        status=TodoStatus(todo.status),
        assigned_agent=AgentType(todo.assigned_agent) if todo.assigned_agent else None,
        priority=todo.priority,
        scheduled_at=todo.scheduled_at,
        result=todo.result,
        error_message=todo.error_message,
        execution_attempts=todo.execution_attempts,
        chat_id=todo.chat_id,
        parent_todo_id=todo.parent_todo_id,
        metadata=todo.metadata,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        started_at=todo.started_at,
        completed_at=todo.completed_at,
        created_by=todo.created_by,
        has_subtasks=subtask_count > 0,
        subtask_count=subtask_count,
    )


@router.patch(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Update a todo",
    description="Update a todo's fields. Only provided fields are updated.",
)
async def update_todo(
    todo_id: UUID,
    data: TodoUpdate,
    service: TodoService = Depends(get_todo_service),
) -> TodoResponse:
    """
    Update a todo.

    Args:
        todo_id: Todo UUID
        data: Fields to update

    Returns:
        Updated todo response

    Raises:
        404: Todo not found
    """
    todo = await service.update(todo_id, data)

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        status=TodoStatus(todo.status),
        assigned_agent=AgentType(todo.assigned_agent) if todo.assigned_agent else None,
        priority=todo.priority,
        scheduled_at=todo.scheduled_at,
        result=todo.result,
        error_message=todo.error_message,
        execution_attempts=todo.execution_attempts,
        chat_id=todo.chat_id,
        parent_todo_id=todo.parent_todo_id,
        metadata=todo.metadata,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        started_at=todo.started_at,
        completed_at=todo.completed_at,
        created_by=todo.created_by,
        has_subtasks=False,
        subtask_count=0,
    )


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a todo",
    description="Delete a todo and all its subtasks.",
)
async def delete_todo(
    todo_id: UUID,
    service: TodoService = Depends(get_todo_service),
) -> None:
    """
    Delete a todo.

    Args:
        todo_id: Todo UUID

    Raises:
        404: Todo not found
    """
    deleted = await service.delete(todo_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )


@router.post(
    "/{todo_id}/execute",
    response_model=TodoExecuteResponse,
    summary="Execute a todo",
    description="Manually trigger execution of a pending todo.",
)
async def execute_todo(
    todo_id: UUID,
    request: TodoExecuteRequest = TodoExecuteRequest(),
    service: TodoService = Depends(get_todo_service),
) -> TodoExecuteResponse:
    """
    Execute a todo.

    Triggers the assigned agent to process the todo.

    Args:
        todo_id: Todo UUID
        request: Execution options

    Returns:
        Execution result

    Raises:
        404: Todo not found
        400: Todo not in executable state
    """
    todo = await service.get_by_id(todo_id)

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    if todo.status not in ("pending", "failed") and not request.force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Todo is in '{todo.status}' state. Use force=true to override.",
        )

    # TODO: Implement actual execution via orchestrator/sub-agents
    # This is a placeholder that will be implemented in Phase 5

    import time
    start_time = time.time()

    # Mark as in progress
    await service.update_status(todo_id, TodoStatus.IN_PROGRESS)

    # Placeholder: actual execution would happen here
    # result = await orchestrator.execute_todo(todo)

    # For now, mark as completed with placeholder result
    await service.update_status(
        todo_id,
        TodoStatus.COMPLETED,
        result="Execution placeholder - implement in Phase 5",
    )

    execution_time_ms = int((time.time() - start_time) * 1000)

    updated_todo = await service.get_by_id(todo_id)

    return TodoExecuteResponse(
        todo_id=todo_id,
        status=TodoStatus(updated_todo.status),
        result=updated_todo.result,
        error_message=updated_todo.error_message,
        execution_time_ms=execution_time_ms,
    )


@router.post(
    "/{todo_id}/cancel",
    response_model=TodoResponse,
    summary="Cancel a todo",
    description="Cancel a pending or in-progress todo.",
)
async def cancel_todo(
    todo_id: UUID,
    service: TodoService = Depends(get_todo_service),
) -> TodoResponse:
    """
    Cancel a todo.

    Args:
        todo_id: Todo UUID

    Returns:
        Cancelled todo response

    Raises:
        404: Todo not found
        400: Todo already completed
    """
    todo = await service.get_by_id(todo_id)

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )

    if todo.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel todo in '{todo.status}' state",
        )

    updated = await service.update_status(todo_id, TodoStatus.CANCELLED)

    return TodoResponse(
        id=updated.id,
        title=updated.title,
        description=updated.description,
        status=TodoStatus(updated.status),
        assigned_agent=AgentType(updated.assigned_agent) if updated.assigned_agent else None,
        priority=updated.priority,
        scheduled_at=updated.scheduled_at,
        result=updated.result,
        error_message=updated.error_message,
        execution_attempts=updated.execution_attempts,
        chat_id=updated.chat_id,
        parent_todo_id=updated.parent_todo_id,
        metadata=updated.metadata,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        started_at=updated.started_at,
        completed_at=updated.completed_at,
        created_by=updated.created_by,
        has_subtasks=False,
        subtask_count=0,
    )
```

**Update:** `Backend/src/api/main.py` - Register the router

```python
# Add to imports
from src.api.routes.todos import router as todos_router

# Add in create_app() or where routers are registered
app.include_router(todos_router, prefix="/api")
```

---

## Phase 5: Orchestrator Integration

### 5.1 Todo Tools for Orchestrator

**File:** `Backend/src/agents/tools/todo_tools.py` (new file)

```python
"""
Todo management tools for the orchestrator agent.

These tools allow the orchestrator to create, manage, and execute
todos as part of conversation handling.
"""

from typing import Optional
from uuid import UUID

from agents import function_tool, RunContext

from src.models.todo import TodoCreate, TodoStatus, AgentType, TodoPriority
from src.services.todo_service import TodoService


@function_tool
async def create_todo(
    ctx: RunContext,
    title: str,
    description: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    priority: int = 3,
) -> dict:
    """
    Create a new todo item for tracking and later execution.

    Use this when the user asks to remember, track, or schedule a task.

    Args:
        title: Short description of the task (required)
        description: Detailed information about what needs to be done
        assigned_agent: Which agent should handle this (github, email, calendar, obsidian)
        priority: 1 (critical) to 5 (lowest), default 3

    Returns:
        Created todo information including ID
    """
    # Get service from context (injected during agent setup)
    service: TodoService = ctx.deps.get("todo_service")
    chat_id: Optional[UUID] = ctx.deps.get("chat_id")

    agent_type = None
    if assigned_agent:
        try:
            agent_type = AgentType(assigned_agent.lower())
        except ValueError:
            return {"error": f"Invalid agent: {assigned_agent}. Use: github, email, calendar, obsidian"}

    data = TodoCreate(
        title=title,
        description=description,
        assigned_agent=agent_type,
        priority=TodoPriority(priority),
    )

    todo = await service.create(data, chat_id=chat_id, created_by="orchestrator")

    return {
        "id": str(todo.id),
        "title": todo.title,
        "status": todo.status,
        "assigned_agent": todo.assigned_agent,
        "message": f"Created todo: {todo.title}",
    }


@function_tool
async def list_todos(
    ctx: RunContext,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    List current todos with optional filtering.

    Use this when the user asks about their tasks, todos, or what's pending.

    Args:
        status: Filter by status (pending, in_progress, completed, failed)
        assigned_agent: Filter by agent (github, email, calendar, obsidian)
        limit: Maximum number to return (default 10)

    Returns:
        List of todos matching filters
    """
    service: TodoService = ctx.deps.get("todo_service")

    status_filter = None
    if status:
        try:
            status_filter = TodoStatus(status.lower())
        except ValueError:
            return {"error": f"Invalid status: {status}"}

    agent_filter = None
    if assigned_agent:
        try:
            agent_filter = AgentType(assigned_agent.lower())
        except ValueError:
            return {"error": f"Invalid agent: {assigned_agent}"}

    result = await service.list_todos(
        status=status_filter,
        assigned_agent=agent_filter,
        page_size=limit,
    )

    todos = [
        {
            "id": str(t.id),
            "title": t.title,
            "status": t.status.value,
            "priority": t.priority.value,
            "assigned_agent": t.assigned_agent.value if t.assigned_agent else None,
        }
        for t in result.items
    ]

    return {
        "todos": todos,
        "total": result.total,
        "showing": len(todos),
    }


@function_tool
async def complete_todo(
    ctx: RunContext,
    todo_id: str,
    result: Optional[str] = None,
) -> dict:
    """
    Mark a todo as completed.

    Use this after successfully completing a task.

    Args:
        todo_id: The todo's UUID
        result: Optional result/outcome description

    Returns:
        Updated todo information
    """
    service: TodoService = ctx.deps.get("todo_service")

    try:
        uuid = UUID(todo_id)
    except ValueError:
        return {"error": "Invalid todo_id format"}

    todo = await service.update_status(uuid, TodoStatus.COMPLETED, result=result)

    if not todo:
        return {"error": f"Todo {todo_id} not found"}

    return {
        "id": str(todo.id),
        "title": todo.title,
        "status": todo.status,
        "result": todo.result,
        "message": f"Completed: {todo.title}",
    }


@function_tool
async def get_todo_stats(ctx: RunContext) -> dict:
    """
    Get statistics about todos.

    Use this when the user asks for an overview of their tasks.

    Returns:
        Counts by status, agent, and priority
    """
    service: TodoService = ctx.deps.get("todo_service")
    stats = await service.get_stats()

    return {
        "total": stats.total,
        "pending": stats.pending,
        "in_progress": stats.in_progress,
        "completed": stats.completed,
        "failed": stats.failed,
        "by_agent": stats.by_agent,
    }
```

### 5.2 Update Orchestrator Agent

**File:** `Backend/src/agents/orchestrator.py` - Update to include todo tools

```python
# Add imports
from src.agents.tools.todo_tools import (
    create_todo,
    list_todos,
    complete_todo,
    get_todo_stats,
)

# Update agent configuration
orchestrator = Agent(
    name="orchestrator",
    model="claude-sonnet-4-20250514",
    instructions=ORCHESTRATOR_INSTRUCTIONS,
    tools=[
        create_todo,
        list_todos,
        complete_todo,
        get_todo_stats,
        # ... existing tools
    ],
    handoffs=[
        # ... existing handoffs
    ],
)
```

### 5.3 Update Orchestrator Instructions

Add to the system prompt:

```
## Todo Management

You can help users track and manage tasks using todo tools:

- **create_todo**: Create a new task to track. Assign to an agent if it requires specific capabilities.
- **list_todos**: Show current tasks, optionally filtered by status or agent.
- **complete_todo**: Mark a task as done after completion.
- **get_todo_stats**: Show overview of task counts.

When a user mentions wanting to remember something, track a task, or schedule work:
1. Create a todo with an appropriate title and description
2. Assign to the relevant agent if the task requires specific capabilities
3. Set appropriate priority (1=critical, 5=lowest)

Examples of when to create todos:
- "Remind me to review that PR tomorrow" → create_todo with github agent
- "I need to send the weekly report" → create_todo with email agent
- "Schedule a meeting with the team" → create_todo with calendar agent
- "Add this to my notes" → create_todo with obsidian agent
```

---

## Phase 6: Background Execution (Optional)

**File:** `Backend/src/services/todo_executor.py` (new file)

This handles automatic execution of scheduled todos in the background.

```python
"""
Background todo executor service.

Periodically checks for pending todos that are ready for execution
and triggers their assigned agents.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import async_session_factory
from src.models.todo import TodoStatus, AgentType
from src.services.todo_service import TodoService


logger = logging.getLogger(__name__)


class TodoExecutor:
    """
    Background service for executing scheduled todos.

    Runs a loop that:
    1. Fetches pending todos ready for execution
    2. Delegates to appropriate sub-agents
    3. Updates status based on results
    """

    def __init__(
        self,
        check_interval_seconds: int = 60,
        max_concurrent: int = 5,
    ):
        """
        Initialize the executor.

        Args:
            check_interval_seconds: How often to check for pending todos
            max_concurrent: Maximum concurrent executions
        """
        self.check_interval = check_interval_seconds
        self.max_concurrent = max_concurrent
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def start(self) -> None:
        """Start the background executor loop."""
        if self._running:
            logger.warning("TodoExecutor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"TodoExecutor started (interval={self.check_interval}s, "
            f"max_concurrent={self.max_concurrent})"
        )

    async def stop(self) -> None:
        """Stop the background executor."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("TodoExecutor stopped")

    async def _run_loop(self) -> None:
        """Main executor loop."""
        while self._running:
            try:
                await self._process_pending_todos()
            except Exception as e:
                logger.error(f"Error in executor loop: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

    async def _process_pending_todos(self) -> None:
        """Fetch and process pending todos."""
        async with async_session_factory() as session:
            service = TodoService(session)

            # Get todos ready for execution
            todos = await service.get_pending_for_execution(limit=self.max_concurrent)

            if not todos:
                return

            logger.info(f"Found {len(todos)} todos ready for execution")

            # Execute concurrently with semaphore limiting
            tasks = [
                self._execute_todo(session, service, todo)
                for todo in todos
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_todo(
        self,
        session: AsyncSession,
        service: TodoService,
        todo,
    ) -> None:
        """
        Execute a single todo.

        Args:
            session: Database session
            service: Todo service instance
            todo: Todo to execute
        """
        async with self._semaphore:
            logger.info(f"Executing todo {todo.id}: {todo.title}")

            try:
                # Mark as in progress
                await service.update_status(todo.id, TodoStatus.IN_PROGRESS)

                # Route to appropriate agent
                result = await self._route_to_agent(todo)

                # Mark as completed
                await service.update_status(
                    todo.id,
                    TodoStatus.COMPLETED,
                    result=result,
                )

                logger.info(f"Todo {todo.id} completed successfully")

            except Exception as e:
                logger.error(f"Todo {todo.id} failed: {e}", exc_info=True)

                await service.update_status(
                    todo.id,
                    TodoStatus.FAILED,
                    error_message=str(e),
                )

    async def _route_to_agent(self, todo) -> str:
        """
        Route todo execution to the appropriate agent.

        Args:
            todo: Todo to execute

        Returns:
            Execution result string
        """
        agent = todo.assigned_agent

        # TODO: Implement actual agent routing
        # This will integrate with the sub-agent system

        if agent == "github":
            # return await github_agent.execute(todo)
            return "GitHub agent execution placeholder"
        elif agent == "email":
            # return await email_agent.execute(todo)
            return "Email agent execution placeholder"
        elif agent == "calendar":
            # return await calendar_agent.execute(todo)
            return "Calendar agent execution placeholder"
        elif agent == "obsidian":
            # return await obsidian_agent.execute(todo)
            return "Obsidian agent execution placeholder"
        else:
            # Orchestrator handles directly
            # return await orchestrator.execute(todo)
            return "Orchestrator execution placeholder"
```

---

## Implementation Checklist

### Phase 0: Prerequisites (Database Infrastructure)

**0.1 - DatabaseManager Interface:**
- [ ] Create `Backend/src/database/manager.py` with `DatabaseConfig` dataclass
- [ ] Implement `DatabaseManagerProtocol` for type safety
- [ ] Implement `DatabaseManager` class with lifecycle methods
- [ ] Add async context manager support (`__aenter__`/`__aexit__`)
- [ ] Add `create_database_manager()` factory function
- [ ] Write unit tests for DatabaseManager

**0.2 - psycopg Migration:**
- [ ] Update `pyproject.toml` to replace asyncpg with `psycopg[binary,pool]>=3.2.0`
- [ ] Update `settings.py` database URL to use `postgresql+psycopg://`
- [ ] Refactor `connection.py` to wrap DatabaseManager (backwards compatibility)
- [ ] Run `uv sync` to install new dependencies
- [ ] Test database connectivity with new driver
- [ ] Verify existing functionality works with psycopg

**0.3 - Update Exports:**
- [ ] Update `Backend/src/database/__init__.py` to export new classes
- [ ] Update any direct imports in services to use new interface

### Phase 1: Database Layer
- [ ] Create migration file `003_create_todos_table.sql`
- [ ] Add `Todo` model to `Backend/src/database/models.py`
- [ ] Add relationship to `Chat` model (optional)
- [ ] Run migration against development database
- [ ] Verify table creation and indexes

### Phase 2: Pydantic Models
- [ ] Create `Backend/src/models/todo.py`
- [ ] Define all request/response schemas
- [ ] Add validation rules
- [ ] Write model tests

### Phase 3: Service Layer
- [ ] Create `Backend/src/services/todo_service.py`
- [ ] Implement CRUD operations
- [ ] Implement status transitions
- [ ] Implement filtering and pagination
- [ ] Implement statistics aggregation
- [ ] Write service tests

### Phase 4: API Endpoints
- [ ] Create `Backend/src/api/routes/todos.py`
- [ ] Implement all REST endpoints
- [ ] Register router in `main.py`
- [ ] Add OpenAPI documentation
- [ ] Write API integration tests

### Phase 5: Orchestrator Integration
- [ ] Create `Backend/src/agents/tools/todo_tools.py`
- [ ] Update orchestrator configuration
- [ ] Update orchestrator instructions
- [ ] Test tool invocation
- [ ] Test conversation flows

### Phase 6: Background Execution (Optional)
- [ ] Create `Backend/src/services/todo_executor.py`
- [ ] Integrate with application lifecycle
- [ ] Implement agent routing
- [ ] Add configuration options
- [ ] Write executor tests

### Documentation Updates
- [ ] Update `ARCHITECTURE.md` with implementation details
- [ ] Update `CLAUDE.md` changelog
- [ ] Update `README.md` with API documentation
- [ ] Update `.env.example` if new config needed

---

## API Reference (After Implementation)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/todos` | Create a new todo |
| `GET` | `/api/todos` | List todos with filtering |
| `GET` | `/api/todos/stats` | Get todo statistics |
| `GET` | `/api/todos/{id}` | Get a specific todo |
| `PATCH` | `/api/todos/{id}` | Update a todo |
| `DELETE` | `/api/todos/{id}` | Delete a todo |
| `POST` | `/api/todos/{id}/execute` | Trigger execution |
| `POST` | `/api/todos/{id}/cancel` | Cancel a todo |

---

## Testing Strategy

### Unit Tests
- Model validation (Pydantic)
- Service methods (mocked database)
- Tool functions (mocked context)

### Integration Tests
- API endpoint responses
- Database operations
- Status transitions

### End-to-End Tests
- Create todo via chat
- List todos via chat
- Execute todo and verify result
- Background execution flow

---

## Future Enhancements

1. **Recurring Todos**: Support for daily/weekly/monthly repetition
2. **Due Dates**: Separate from scheduled execution time
3. **Tags/Labels**: Flexible categorization
4. **Dependencies**: Todo A must complete before Todo B
5. **Notifications**: Telegram alerts for status changes
6. **Web Dashboard**: Visual todo management interface
