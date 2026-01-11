---
paths:
  - "Backend/src/models/**/*.py"
---

# Pydantic Model Patterns

## Model Organization

Models are organized by domain in `Backend/src/models/`:

```
models/
├── __init__.py
├── chat.py          # Chat and message models
├── todo.py          # Todo request/response models
└── agent.py         # Agent execution models
```

## Naming Conventions

| Purpose | Suffix | Example |
|---------|--------|---------|
| Create request | `Create` | `TodoCreate` |
| Update request | `Update` | `TodoUpdate` |
| Response | `Response` | `TodoResponse` |
| List response | `ListResponse` | `TodoListResponse` |
| Base/shared | `Base` | `TodoBase` |

## Request Models

```python
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

class TodoCreate(BaseModel):
    """Request model for creating a new todo."""

    title: str = Field(
        ...,  # Required
        min_length=1,
        max_length=500,
        description="Short description of the task",
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional detailed information",
    )
    priority: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Priority level (1=critical, 5=lowest)",
    )
    assigned_agent: AgentType | None = Field(
        default=None,
        description="Agent to handle this todo",
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()
```

## Update Models

Use `None` defaults to indicate "no change":

```python
class TodoUpdate(BaseModel):
    """Request model for updating a todo. All fields optional."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: TodoStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)

    model_config = ConfigDict(
        # Only include fields that were explicitly set
        extra="forbid",
    )
```

## Response Models

```python
from datetime import datetime
from pydantic import ConfigDict

class TodoResponse(BaseModel):
    """Response model for a single todo."""

    id: UUID
    title: str
    description: str | None
    status: TodoStatus
    priority: int
    assigned_agent: AgentType | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode
    )
```

## List Response Models

Include pagination metadata:

```python
class TodoListResponse(BaseModel):
    """Response model for a list of todos with pagination."""

    items: list[TodoResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
```

## Enums

Use `StrEnum` for string-based enums:

```python
from enum import StrEnum

class TodoStatus(StrEnum):
    """Possible states for a todo item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentType(StrEnum):
    """Available agent types for task assignment."""

    GITHUB = "github"
    EMAIL = "email"
    CALENDAR = "calendar"
    OBSIDIAN = "obsidian"
    ORCHESTRATOR = "orchestrator"
```

## Model Config

Common configuration options:

```python
from pydantic import ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,      # Allow ORM objects
        extra="forbid",            # Reject unknown fields
        str_strip_whitespace=True, # Auto-strip strings
        validate_assignment=True,  # Validate on attribute set
        use_enum_values=True,      # Serialize enums as values
    )
```

## Validation Patterns

```python
from pydantic import field_validator, model_validator

class TodoCreate(BaseModel):
    scheduled_at: datetime | None = None
    deadline: datetime | None = None

    @field_validator("scheduled_at", "deadline")
    @classmethod
    def must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is not None and v < datetime.now(timezone.utc):
            raise ValueError("Date must be in the future")
        return v

    @model_validator(mode="after")
    def deadline_after_scheduled(self) -> "TodoCreate":
        if self.scheduled_at and self.deadline:
            if self.deadline < self.scheduled_at:
                raise ValueError("Deadline must be after scheduled time")
        return self
```

## Key Rules

1. **Always use Field()** for documentation and validation
2. **Separate Create/Update/Response** - Different validation needs
3. **Use ConfigDict** - Not class Config (Pydantic v2)
4. **from_attributes=True** - For ORM compatibility
5. **StrEnum for string enums** - Better serialization

## Anti-Patterns

- **DON'T** use class Config (use model_config = ConfigDict())
- **DON'T** skip Field() descriptions (they become API docs)
- **DON'T** use one model for create/update/response (separate concerns)
- **DON'T** use regular Enum for string values (use StrEnum)
- **DON'T** skip from_attributes when working with ORM models
- **DON'T** use Optional without default value (use `| None = None`)
- **DON'T** validate in __init__ (use @field_validator or @model_validator)
- **DON'T** use mutable defaults (use Field(default_factory=...))
