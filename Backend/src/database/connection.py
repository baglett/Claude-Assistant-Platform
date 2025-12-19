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

The global DatabaseManager instance is created on first call to init_database()
and can be accessed via get_database_manager() for advanced use cases.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import get_settings
from src.database.manager import DatabaseConfig, DatabaseManager


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Global Instance (for backwards compatibility)
# -----------------------------------------------------------------------------
_db_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """
    Get the global DatabaseManager instance.

    This function provides access to the underlying DatabaseManager for
    advanced use cases that need direct access to the engine or custom
    session configuration.

    Returns:
        The initialized DatabaseManager instance.

    Raises:
        RuntimeError: If database has not been initialized via init_database().

    Example:
        db = get_database_manager()
        print(f"Connected: {db.is_connected}")
        print(f"Pool size: {db.config.pool_size}")
    """
    if _db_manager is None:
        raise RuntimeError(
            "Database not initialized. Call init_database() first."
        )
    return _db_manager


# -----------------------------------------------------------------------------
# Database Initialization
# -----------------------------------------------------------------------------
async def init_database() -> None:
    """
    Initialize the database connection.

    Creates and connects the global DatabaseManager instance using settings
    from the application configuration. Should be called once during
    application startup.

    This function is idempotent - calling it when already initialized will
    log a warning but not raise an error.

    Raises:
        ConnectionError: If database connection fails.
        Exception: If configuration is invalid.

    Example:
        # In FastAPI lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await init_database()
            yield
            await close_database()
    """
    global _db_manager

    if _db_manager is not None:
        logger.warning("Database already initialized, skipping init_database()")
        return

    settings = get_settings()

    # Create configuration from application settings
    config = DatabaseConfig(
        url=settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_timeout=10,
        echo=settings.debug,
    )

    logger.info("Initializing database connection...")

    _db_manager = DatabaseManager(config)
    await _db_manager.connect()

    logger.info("Database connection initialized successfully")


async def close_database() -> None:
    """
    Close the database connection.

    Disconnects the global DatabaseManager and releases all pooled
    connections. Should be called during application shutdown.

    Safe to call multiple times - subsequent calls are no-ops.

    Example:
        # In FastAPI lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await init_database()
            yield
            await close_database()
    """
    global _db_manager

    if _db_manager is None:
        logger.debug("Database not initialized, nothing to close")
        return

    logger.info("Closing database connection...")

    await _db_manager.disconnect()
    _db_manager = None

    logger.info("Database connection closed")


# -----------------------------------------------------------------------------
# Session Management
# -----------------------------------------------------------------------------
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the session factory.

    Returns the underlying SQLAlchemy async_sessionmaker for advanced
    use cases that need custom session configuration.

    Returns:
        The async session factory.

    Raises:
        RuntimeError: If database has not been initialized.

    Example:
        factory = get_session_factory()
        async with factory() as session:
            # Custom session handling
            session.expire_on_commit = True
            ...
    """
    db = get_database_manager()
    return db.session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as a context manager.

    Automatically commits on success or rolls back on exception.
    This is the recommended way to interact with the database in
    application code.

    Yields:
        AsyncSession: Database session with automatic transaction management.

    Raises:
        RuntimeError: If database has not been initialized.

    Example:
        async with get_session() as session:
            # Create a record
            user = User(name="Alice")
            session.add(user)
            # Commits automatically on exit

        async with get_session() as session:
            # Query records
            result = await session.execute(select(User))
            users = result.scalars().all()
    """
    db = get_database_manager()
    async with db.session() as session:
        yield session


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Use with FastAPI's Depends() for automatic session management in
    route handlers. The session is automatically committed on success
    or rolled back on exception.

    Yields:
        AsyncSession: Database session for the request lifecycle.

    Raises:
        RuntimeError: If database has not been initialized.

    Example:
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession

        @app.get("/users")
        async def get_users(
            session: AsyncSession = Depends(get_session_dependency)
        ):
            result = await session.execute(select(User))
            return result.scalars().all()
    """
    db = get_database_manager()
    async for session in db.session_dependency():
        yield session


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------
async def check_database_health() -> bool:
    """
    Check database connectivity.

    Performs a lightweight health check query to verify the database
    is reachable and responding. Useful for health check endpoints.

    Returns:
        True if database is healthy, False otherwise.

    Example:
        @app.get("/health")
        async def health_check():
            db_healthy = await check_database_health()
            return {"database": "healthy" if db_healthy else "unhealthy"}
    """
    if _db_manager is None:
        return False
    return await _db_manager.health_check()
