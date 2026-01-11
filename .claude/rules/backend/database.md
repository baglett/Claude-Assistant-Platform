---
paths:
  - "Backend/src/database/**/*.py"
  - "Backend/database/**/*.sql"
---

# Database Patterns

## Schema Organization

The database is organized into schemas by domain:

| Schema | Purpose | Tables |
|--------|---------|--------|
| `messaging` | Chat and messages | `chats`, `messages` |
| `tasks` | Todo management | `todos` |
| `agents` | Execution tracking | `executions` |
| `telegram` | Telegram integration | `sessions` |

## SQLAlchemy ORM

Use async SQLAlchemy with the following patterns:

```python
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Query with filtering
async def get_todos_by_status(
    session: AsyncSession,
    status: TodoStatus,
) -> list[Todo]:
    query = select(Todo).where(Todo.status == status).order_by(Todo.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())

# Insert
async def create_todo(session: AsyncSession, todo: Todo) -> Todo:
    session.add(todo)
    await session.commit()
    await session.refresh(todo)
    return todo

# Update
async def update_todo(
    session: AsyncSession,
    todo_id: UUID,
    updates: dict[str, Any],
) -> Todo | None:
    query = update(Todo).where(Todo.id == todo_id).values(**updates).returning(Todo)
    result = await session.execute(query)
    await session.commit()
    return result.scalar_one_or_none()
```

## DatabaseManager

Use `DatabaseManager` for connection management:

```python
from src.database.manager import DatabaseManager, DatabaseConfig

config = DatabaseConfig(
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    username=settings.db_user,
    password=settings.db_password,
)

manager = DatabaseManager(config)

# Get session
async with manager.session() as session:
    todos = await get_todos(session)

# Health check
is_healthy = await manager.health_check()
```

## Session Context Manager

Always use `async with` for database sessions:

```python
# Correct: Session is properly closed
async with get_session() as session:
    result = await session.execute(query)
    await session.commit()

# Wrong: Session may leak
session = await get_session()
result = await session.execute(query)
```

## Migration Conventions

Migrations are stored in `Backend/database/migrations/`:

```sql
-- 005_create_new_table.sql

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS domain_name;

-- Create table with IF NOT EXISTS for idempotency
CREATE TABLE IF NOT EXISTS domain_name.table_name (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_table_name_name
    ON domain_name.table_name(name);

-- Add comments
COMMENT ON TABLE domain_name.table_name IS 'Description of the table';
```

## Migration Naming

- Sequential numbering: `001_`, `002_`, etc.
- Descriptive names: `003_create_todos_table.sql`
- One logical change per migration
- Always include `IF NOT EXISTS` / `IF EXISTS` for idempotency

## ORM Model Definition

```python
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Todo(Base):
    __tablename__ = "todos"
    __table_args__ = {"schema": "tasks"}

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=3)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    # Relationships
    chat: Mapped["Chat"] = relationship(back_populates="todos")
```

## Key Rules

1. **Always use async sessions** - Never block on database I/O
2. **Use context managers** - Ensures proper cleanup
3. **Parameterized queries only** - SQLAlchemy handles this
4. **Index query patterns** - Add indexes for common filters
5. **Use JSONB for flexibility** - For agent-specific metadata
