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

Example:
    from src.database.manager import DatabaseManager, DatabaseConfig

    config = DatabaseConfig(url="postgresql+psycopg://user:pass@localhost/db")

    async with DatabaseManager(config) as db:
        async with db.session() as session:
            result = await session.execute(query)
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
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

    This dataclass holds all configuration needed to establish and manage
    database connections. It is frozen (immutable) to prevent accidental
    modification after creation.

    Attributes:
        url: Database connection URL (e.g., postgresql+psycopg://user:pass@host/db).
            Must include the SQLAlchemy dialect prefix.
        pool_size: Number of connections to maintain in the pool. These connections
            are kept open and reused for better performance.
        max_overflow: Maximum additional connections beyond pool_size during peak load.
            These extra connections are closed when no longer needed.
        pool_pre_ping: Whether to verify connections before use by issuing a test query.
            Helps detect and recover from stale connections.
        pool_recycle: Seconds before recycling a connection. Prevents issues with
            connections that have been open too long (e.g., server-side timeouts).
        connect_timeout: Seconds to wait when establishing a new connection.
        echo: Whether to log all SQL statements. Useful for debugging.
        echo_pool: Whether to log connection pool events (checkout, checkin, etc.).

    Example:
        config = DatabaseConfig(
            url="postgresql+psycopg://user:pass@localhost:5432/mydb",
            pool_size=10,
            max_overflow=20,
            echo=True,  # Enable SQL logging for debugging
        )
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
        """
        Validate configuration on creation.

        Raises:
            ValueError: If any configuration value is invalid.
        """
        if not self.url:
            raise ValueError("Database URL is required")
        if self.pool_size < 1:
            raise ValueError("pool_size must be at least 1")
        if self.max_overflow < 0:
            raise ValueError("max_overflow cannot be negative")
        if self.pool_recycle < 0:
            raise ValueError("pool_recycle cannot be negative")
        if self.connect_timeout < 1:
            raise ValueError("connect_timeout must be at least 1 second")


# -----------------------------------------------------------------------------
# Protocol Definition
# -----------------------------------------------------------------------------
class DatabaseManagerProtocol(Protocol):
    """
    Protocol defining the database manager interface.

    This protocol enables type-safe dependency injection and makes it easy
    to create mock implementations for testing. Any class implementing these
    methods can be used as a database manager.

    Implementations must provide:
    - Connection lifecycle management (connect, disconnect)
    - Health checking capabilities
    - Session creation with automatic transaction management
    - FastAPI dependency integration
    """

    @property
    def is_connected(self) -> bool:
        """
        Whether the database connection is established.

        Returns:
            True if connected and ready to handle queries, False otherwise.
        """
        ...

    async def connect(self) -> None:
        """
        Establish database connection and verify connectivity.

        Should create the connection pool and verify at least one
        connection can be established successfully.

        Raises:
            ConnectionError: If connection cannot be established.
        """
        ...

    async def disconnect(self) -> None:
        """
        Close all connections and release resources.

        Should be safe to call multiple times. After disconnecting,
        is_connected should return False.
        """
        ...

    async def health_check(self) -> bool:
        """
        Check database connectivity.

        Performs a lightweight query to verify the database is reachable
        and responding to queries.

        Returns:
            True if database is reachable and healthy, False otherwise.
        """
        ...

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic transaction management.

        The session automatically commits on successful exit and rolls
        back on exception. This is the primary way to interact with
        the database.

        Yields:
            AsyncSession for database operations.

        Raises:
            RuntimeError: If not connected.
        """
        ...

    async def session_dependency(self) -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency for automatic session management.

        Use with FastAPI's Depends() for request-scoped sessions that
        are automatically cleaned up after the request completes.

        Yields:
            AsyncSession for the request lifecycle.
        """
        ...


# -----------------------------------------------------------------------------
# Implementation
# -----------------------------------------------------------------------------
class DatabaseManager:
    """
    SQLAlchemy-based database manager implementation.

    Manages the async engine lifecycle, connection pooling, and session
    creation. Designed for dependency injection and clean shutdown.

    This class implements the DatabaseManagerProtocol and can be used
    as an async context manager for automatic connect/disconnect.

    Attributes:
        _config: The database configuration.
        _engine: SQLAlchemy async engine (None if not connected).
        _session_factory: Session factory for creating new sessions.

    Example:
        # Using as context manager (recommended)
        config = DatabaseConfig(url="postgresql+psycopg://...")
        async with DatabaseManager(config) as db:
            async with db.session() as session:
                result = await session.execute(query)

        # Manual lifecycle management
        db = DatabaseManager(config)
        await db.connect()
        try:
            async with db.session() as session:
                ...
        finally:
            await db.disconnect()

        # Dependency injection
        class MyService:
            def __init__(self, db: DatabaseManager):
                self.db = db

            async def do_something(self):
                async with self.db.session() as session:
                    ...
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize the database manager.

        Does not establish a connection - call connect() or use as
        async context manager to connect.

        Args:
            config: Database configuration settings.
        """
        self._config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def config(self) -> DatabaseConfig:
        """
        Get the database configuration.

        Returns:
            The immutable DatabaseConfig used by this manager.
        """
        return self._config

    @property
    def is_connected(self) -> bool:
        """
        Whether the database connection is established.

        Returns:
            True if the engine has been created and connect() succeeded.
        """
        return self._engine is not None

    @property
    def engine(self) -> AsyncEngine:
        """
        Get the SQLAlchemy async engine.

        Use this for advanced operations that require direct engine access,
        such as running DDL statements or managing transactions manually.

        Returns:
            The async engine instance.

        Raises:
            RuntimeError: If not connected.
        """
        if self._engine is None:
            raise RuntimeError(
                "Database not connected. Call connect() first."
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Get the session factory.

        Use this for advanced scenarios where you need to create sessions
        with custom options or manage the session lifecycle manually.

        Returns:
            The async session factory.

        Raises:
            RuntimeError: If not connected.
        """
        if self._session_factory is None:
            raise RuntimeError(
                "Database not connected. Call connect() first."
            )
        return self._session_factory

    async def connect(self) -> None:
        """
        Establish database connection and verify connectivity.

        Creates the async engine with connection pooling configured according
        to the DatabaseConfig. Verifies connectivity by performing a health
        check query.

        This method is idempotent - calling it when already connected will
        log a warning but not raise an error.

        Raises:
            ConnectionError: If connection cannot be established or health
                check fails.
        """
        if self._engine is not None:
            logger.warning("Database already connected, skipping connect()")
            return

        logger.info(
            f"Connecting to database (pool_size={self._config.pool_size}, "
            f"max_overflow={self._config.max_overflow})..."
        )

        # Create async engine with psycopg driver
        # The connection URL dialect determines which driver is used
        self._engine = create_async_engine(
            self._config.url,
            echo=self._config.echo,
            echo_pool=self._config.echo_pool,
            pool_size=self._config.pool_size,
            max_overflow=self._config.max_overflow,
            pool_pre_ping=self._config.pool_pre_ping,
            pool_recycle=self._config.pool_recycle,
            # psycopg-specific connection arguments
            connect_args={
                "connect_timeout": self._config.connect_timeout,
            },
        )

        # Create session factory with sensible defaults
        # - expire_on_commit=False: Objects remain usable after commit
        # - autocommit=False: Explicit transaction control
        # - autoflush=False: Manual flush control for better performance
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        # Verify connection with health check
        if not await self.health_check():
            await self.disconnect()
            raise ConnectionError("Failed to verify database connection")

        logger.info("Database connection established successfully")

    async def disconnect(self) -> None:
        """
        Close all connections and release resources.

        Disposes of the engine, closing all pooled connections. Safe to
        call multiple times - subsequent calls are no-ops.

        After disconnecting, is_connected returns False and any attempt
        to get sessions will raise RuntimeError.
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

        Executes "SELECT 1" to verify the database is reachable and
        responding to queries. This is a lightweight check suitable
        for frequent health monitoring.

        Returns:
            True if database is reachable and responded successfully,
            False if any error occurred.
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

        Creates a new session that automatically commits on successful
        exit from the context manager, or rolls back if an exception
        is raised. This is the recommended way to interact with the
        database.

        Yields:
            AsyncSession for database operations.

        Raises:
            RuntimeError: If not connected.

        Example:
            async with db.session() as session:
                # Create a new record
                user = User(name="Alice")
                session.add(user)
                # Commits automatically on exit

            async with db.session() as session:
                # Query records
                result = await session.execute(
                    select(User).where(User.name == "Alice")
                )
                user = result.scalar_one()

            async with db.session() as session:
                # If exception is raised, transaction is rolled back
                session.add(User(name="Bob"))
                raise ValueError("Oops!")  # Rollback happens here
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

        Use with FastAPI's Depends() for request-scoped sessions. The
        session is automatically committed on success or rolled back
        on exception, and cleaned up after the request completes.

        Yields:
            AsyncSession for the request lifecycle.

        Example:
            from fastapi import Depends

            @app.get("/users/{user_id}")
            async def get_user(
                user_id: int,
                session: AsyncSession = Depends(db.session_dependency)
            ):
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                return result.scalar_one_or_none()
        """
        async with self.session() as session:
            yield session

    # -------------------------------------------------------------------------
    # Context Manager Support
    # -------------------------------------------------------------------------
    async def __aenter__(self) -> Self:
        """
        Async context manager entry - connects to database.

        Returns:
            Self for use in the context block.

        Example:
            async with DatabaseManager(config) as db:
                # db is now connected
                ...
            # db is automatically disconnected here
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit - disconnects from database.

        Always disconnects, regardless of whether an exception occurred.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Exception traceback if an exception was raised.
        """
        await self.disconnect()

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        """
        Return a string representation of the manager.

        Returns:
            String showing connection status and pool configuration.
        """
        status = "connected" if self.is_connected else "disconnected"
        return (
            f"DatabaseManager(status={status}, "
            f"pool_size={self._config.pool_size}, "
            f"max_overflow={self._config.max_overflow})"
        )


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

    This is a convenience function for creating a DatabaseManager with
    the most commonly customized settings exposed as keyword arguments.

    Args:
        url: Database connection URL (e.g., postgresql+psycopg://...).
        pool_size: Number of connections to keep in the pool.
        max_overflow: Maximum additional connections during peak load.
        echo: Whether to log SQL statements.
        **kwargs: Additional DatabaseConfig options (pool_pre_ping,
            pool_recycle, connect_timeout, echo_pool).

    Returns:
        Configured DatabaseManager instance (not yet connected).

    Example:
        # Simple usage
        db = create_database_manager(
            "postgresql+psycopg://user:pass@localhost/mydb"
        )

        # With custom pool settings
        db = create_database_manager(
            "postgresql+psycopg://user:pass@localhost/mydb",
            pool_size=10,
            max_overflow=20,
            echo=True,
        )

        # Use as context manager
        async with create_database_manager(url) as db:
            async with db.session() as session:
                ...
    """
    config = DatabaseConfig(
        url=url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=echo,
        **kwargs,
    )
    return DatabaseManager(config)
