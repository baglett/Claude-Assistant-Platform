# =============================================================================
# Database Connection
# =============================================================================
"""
Async database connection management using SQLAlchemy.

Provides connection pooling and session management for PostgreSQL.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Global Database Engine and Session Factory
# -----------------------------------------------------------------------------
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


# -----------------------------------------------------------------------------
# Database Initialization
# -----------------------------------------------------------------------------
async def init_database() -> None:
    """
    Initialize the database connection pool.

    Creates the async engine and session factory. Should be called once
    during application startup.

    Raises:
        Exception: If database connection fails.
    """
    global _engine, _session_factory

    settings = get_settings()

    logger.info("Initializing database connection...")

    # Create async engine with connection pooling
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,  # Log SQL statements in debug mode
        pool_size=5,  # Number of connections to keep open
        max_overflow=10,  # Additional connections when pool is exhausted
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Create session factory
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire objects after commit
        autocommit=False,
        autoflush=False,
    )

    # Test the connection
    try:
        async with _engine.begin() as conn:
            await conn.execute(
                # Simple query to test connection
                # Using text() for raw SQL
                __import__("sqlalchemy").text("SELECT 1")
            )
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_database() -> None:
    """
    Close the database connection pool.

    Should be called during application shutdown.
    """
    global _engine, _session_factory

    if _engine:
        logger.info("Closing database connection pool...")
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connection pool closed")


# -----------------------------------------------------------------------------
# Session Management
# -----------------------------------------------------------------------------
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the session factory.

    Returns:
        The async session factory.

    Raises:
        RuntimeError: If database has not been initialized.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call init_database() first."
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as a context manager.

    Automatically commits on success or rolls back on exception.

    Yields:
        AsyncSession: Database session.

    Raises:
        RuntimeError: If database has not been initialized.

    Example:
        async with get_session() as session:
            result = await session.execute(query)
    """
    factory = get_session_factory()

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Use this with FastAPI's Depends() for automatic session management.

    Yields:
        AsyncSession: Database session.

    Example:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session_dependency)):
            ...
    """
    async with get_session() as session:
        yield session
