# =============================================================================
# Database Package
# =============================================================================
"""
Database module for the Claude Assistant Platform.

Provides async database connection management and ORM models.
"""

from src.database.connection import (
    close_database,
    get_session,
    get_session_dependency,
    get_session_factory,
    init_database,
)
from src.database.models import Base, Chat, ChatMessage, TelegramSession


__all__ = [
    # Connection management
    "init_database",
    "close_database",
    "get_session",
    "get_session_factory",
    "get_session_dependency",
    # ORM models
    "Base",
    "Chat",
    "ChatMessage",
    "TelegramSession",
]
