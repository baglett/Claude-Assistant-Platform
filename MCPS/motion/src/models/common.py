# =============================================================================
# Motion MCP Server - Common Models
# =============================================================================
"""
Common Pydantic models shared across all Motion API interactions.

These models provide base classes and shared structures used throughout
the Motion MCP server.
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

# Type variable for generic responses
T = TypeVar("T")


# -----------------------------------------------------------------------------
# Error Models
# -----------------------------------------------------------------------------
class MotionApiError(BaseModel):
    """
    Motion API error response.

    Attributes:
        error: Error type or code.
        message: Human-readable error message.
        details: Additional error details.
    """

    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )


# -----------------------------------------------------------------------------
# Response Wrapper Models
# -----------------------------------------------------------------------------
class MotionResponse(BaseModel, Generic[T]):
    """
    Generic response wrapper for Motion API responses.

    Attributes:
        success: Whether the request was successful.
        data: The response data (if successful).
        error: Error information (if failed).
    """

    success: bool = Field(..., description="Whether the request succeeded")
    data: Optional[T] = Field(default=None, description="Response data if successful")
    error: Optional[MotionApiError] = Field(
        default=None, description="Error details if failed"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response for list endpoints.

    Attributes:
        items: List of items in this page.
        next_cursor: Cursor for the next page (None if last page).
        has_more: Whether there are more items.
    """

    items: list[T] = Field(default_factory=list, description="Items in this page")
    next_cursor: Optional[str] = Field(
        default=None, description="Cursor for the next page"
    )
    has_more: bool = Field(default=False, description="Whether there are more items")


# -----------------------------------------------------------------------------
# Shared Nested Models
# -----------------------------------------------------------------------------
class Label(BaseModel):
    """
    Task label.

    Attributes:
        name: The label name.
    """

    name: str = Field(..., description="Label name")


class CustomFieldValue(BaseModel):
    """
    Custom field value.

    Supports various types: text, number, url, date, select, multiSelect,
    person, multiPerson, email, phone, checkbox, relatedTo.

    Attributes:
        type: The field type.
        value: The field value (type varies based on field type).
    """

    type: str = Field(..., description="Custom field type")
    value: Any = Field(..., description="Field value")
