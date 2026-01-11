---
paths:
  - "Backend/src/api/**/*.py"
---

# FastAPI Patterns

## Route Organization

- Group related routes in separate files under `Backend/src/api/routes/`
- Use `APIRouter` with appropriate prefix and tags
- Register routers in `main.py`

```python
# Backend/src/api/routes/todos.py
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/api/todos", tags=["todos"])

@router.get("/", response_model=TodoListResponse)
async def list_todos(
    status: TodoStatus | None = None,
    limit: int = Query(default=50, le=100),
    session: AsyncSession = Depends(get_session),
) -> TodoListResponse:
    """List todos with optional filtering."""
    ...
```

## Dependency Injection

- Use `Depends()` for database sessions, services, and auth
- Create reusable dependencies in `Backend/src/api/dependencies.py`
- Avoid global state; inject everything

```python
# Dependency for database session
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# Dependency for authenticated user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    ...
```

## Request/Response Models

- Use Pydantic models for all request bodies and responses
- Define models in `Backend/src/models/`
- Use `response_model` parameter for automatic serialization

```python
@router.post("/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(
    request: TodoCreate,
    session: AsyncSession = Depends(get_session),
) -> TodoResponse:
    ...
```

## Error Handling

- Use `HTTPException` for API errors
- Use appropriate status codes
- Return consistent error response format

```python
@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TodoResponse:
    todo = await service.get_by_id(session, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} not found",
        )
    return TodoResponse.model_validate(todo)
```

## Lifespan Management

- Use the lifespan context manager for startup/shutdown
- Initialize services, start background tasks on startup
- Clean up resources, stop tasks on shutdown

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    await initialize_database()
    background_task = asyncio.create_task(run_executor())

    yield

    # Shutdown
    background_task.cancel()
    await cleanup_resources()

app = FastAPI(lifespan=lifespan)
```

## Health Checks

- Always include a `/health` endpoint
- Return service status and dependencies
- Use for Docker health checks and monitoring

```python
@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "backend"}
```
