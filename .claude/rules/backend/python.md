---
paths:
  - "Backend/**/*.py"
---

# Python Backend Standards

## Language Version

- **Python 3.14+** is required
- Use modern Python features:
  - Type hints on ALL function signatures and class attributes
  - Match statements for complex conditionals
  - Structural pattern matching where appropriate
  - f-strings for string formatting
  - Walrus operator (`:=`) when it improves readability

## Type Hints

```python
# Required: Full type hints on all functions
async def get_user(user_id: UUID) -> User | None:
    ...

# Required: Type hints on class attributes
class TodoService:
    _session: AsyncSession
    _cache: dict[str, Any]
```

## Async Patterns

- Use `async/await` for ALL I/O operations
- Use `AsyncSession` for database operations
- Use `httpx.AsyncClient` for HTTP requests
- Use `asyncio.gather()` for concurrent operations
- Use `async with` for context managers

```python
# Correct: Async database operation
async with get_session() as session:
    result = await session.execute(query)

# Correct: Concurrent HTTP requests
results = await asyncio.gather(
    client.get(url1),
    client.get(url2),
)
```

## Code Style

- Follow PEP 8 for formatting
- Follow PEP 257 for docstrings
- Maximum line length: 100 characters
- Use double quotes for strings
- Use trailing commas in multi-line collections

## Docstrings

All public functions, classes, and modules require docstrings:

```python
async def create_todo(
    title: str,
    description: str | None = None,
    priority: int = 3,
) -> Todo:
    """
    Create a new todo item in the database.

    Args:
        title: Short description of the task (max 500 chars).
        description: Optional detailed information.
        priority: Priority level from 1 (critical) to 5 (lowest).

    Returns:
        The created Todo object with generated ID.

    Raises:
        ValueError: If title exceeds 500 characters.
        DatabaseError: If the insert operation fails.
    """
```

## Dependency Management

- Use **uv** for all package operations (NOT pip)
- Commands:
  - `uv add <package>` - Add a dependency
  - `uv add --dev <package>` - Add a dev dependency
  - `uv remove <package>` - Remove a dependency
  - `uv sync` - Install from lockfile
  - `uv run <command>` - Run in virtual environment
- Always commit `uv.lock` for reproducible builds

## Error Handling

- Use specific exception types, not bare `except:`
- Log errors with context before re-raising
- Use custom exceptions for domain-specific errors
- Always clean up resources in `finally` blocks

```python
try:
    result = await risky_operation()
except SpecificError as e:
    logger.error("Operation failed", extra={"error": str(e), "context": ctx})
    raise DomainError("User-friendly message") from e
```
