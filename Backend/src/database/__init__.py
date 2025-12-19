# =============================================================================
# Database Package
# =============================================================================
"""
Database module for the Claude Assistant Platform.

Provides async database connection management, ORM models, and a universal
DatabaseManager interface for clean dependency injection.

Usage Patterns:

1. **New Code (Recommended)** - Use DatabaseManager directly:

    from src.database import DatabaseManager, DatabaseConfig

    config = DatabaseConfig(url="postgresql+psycopg://...")
    async with DatabaseManager(config) as db:
        async with db.session() as session:
            result = await session.execute(query)

2. **Legacy Code** - Use module-level functions:

    from src.database import init_database, get_session, close_database

    await init_database()
    async with get_session() as session:
        result = await session.execute(query)
    await close_database()

3. **FastAPI Integration**:

    from src.database import get_session_dependency
    from fastapi import Depends

    @app.get("/users")
    async def get_users(session = Depends(get_session_dependency)):
        ...
"""

# DatabaseManager interface (new, recommended)
from src.database.manager import (
    DatabaseConfig,
    DatabaseManager,
    DatabaseManagerProtocol,
    create_database_manager,
)

# Connection management (backwards compatible)
from src.database.connection import (
    check_database_health,
    close_database,
    get_database_manager,
    get_session,
    get_session_dependency,
    get_session_factory,
    init_database,
)

# ORM models
from src.database.models import (
    AgentExecution,
    Base,
    Chat,
    ChatMessage,
    TelegramSession,
    Todo,
)


__all__ = [
    # DatabaseManager interface (new)
    "DatabaseConfig",
    "DatabaseManager",
    "DatabaseManagerProtocol",
    "create_database_manager",
    # Connection management (legacy)
    "init_database",
    "close_database",
    "get_session",
    "get_session_factory",
    "get_session_dependency",
    "get_database_manager",
    "check_database_health",
    # ORM models
    "Base",
    "Chat",
    "ChatMessage",
    "TelegramSession",
    "Todo",
    "AgentExecution",
]
