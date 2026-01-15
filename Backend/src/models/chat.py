# =============================================================================
# Chat Models
# =============================================================================
"""
Pydantic models for chat request and response handling.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """
    A single message in a conversation.

    Attributes:
        role: The role of the message sender (user or assistant).
        content: The text content of the message.
        timestamp: When the message was created.
    """

    role: Literal["user", "assistant"] = Field(
        description="Role of the message sender"
    )
    content: str = Field(
        description="Text content of the message"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message creation timestamp"
    )


class ChatRequest(BaseModel):
    """
    Request payload for the chat endpoint.

    Attributes:
        message: The user's message to the orchestrator.
        chat_id: Optional UUID to continue an existing chat session.
    """

    message: str = Field(
        min_length=1,
        max_length=10000,
        description="The user's message to send to the orchestrator"
    )
    chat_id: Optional[UUID] = Field(
        default=None,
        description="Optional chat ID (UUID) to continue an existing conversation"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Create a todo item to review the project architecture",
                    "chat_id": None
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """
    Response payload from the chat endpoint.

    Attributes:
        response: The orchestrator's response message.
        chat_id: UUID of the chat session for future reference.
        tokens_used: Number of tokens consumed by this request.
        processing_time_ms: Time taken to process the request in milliseconds.
    """

    response: str = Field(
        description="The orchestrator's response message"
    )
    chat_id: UUID = Field(
        description="Chat ID (UUID) for continuing the conversation"
    )
    tokens_used: Optional[int] = Field(
        default=None,
        description="Number of tokens consumed"
    )
    processing_time_ms: Optional[float] = Field(
        default=None,
        description="Processing time in milliseconds"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "I've created a todo item to review the project architecture. Is there anything specific you'd like me to focus on?",
                    "chat_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tokens_used": 150,
                    "processing_time_ms": 1234.56
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    Attributes:
        error: Error type or code.
        message: Human-readable error message.
        details: Optional additional error details.
    """

    error: str = Field(
        description="Error type or code"
    )
    message: str = Field(
        description="Human-readable error message"
    )
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details"
    )


class ConversationSummary(BaseModel):
    """
    Summary of a conversation for list display.

    Attributes:
        id: Unique conversation identifier (UUID).
        title: Auto-generated title from first user message.
        created_on: When the conversation was created.
        modified_on: When the conversation was last updated.
        message_count: Total number of messages in the conversation.
    """

    id: UUID = Field(
        description="Unique conversation identifier"
    )
    title: str = Field(
        description="Auto-generated title from first user message"
    )
    created_on: datetime = Field(
        description="When the conversation was created"
    )
    modified_on: datetime = Field(
        description="When the conversation was last updated"
    )
    message_count: int = Field(
        description="Total number of messages in the conversation"
    )

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    """
    Paginated list of conversation summaries.

    Attributes:
        items: List of conversation summaries.
        total: Total number of conversations.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        has_next: Whether more pages exist.
    """

    items: list[ConversationSummary] = Field(
        description="List of conversation summaries"
    )
    total: int = Field(
        description="Total number of conversations"
    )
    page: int = Field(
        description="Current page number (1-indexed)"
    )
    page_size: int = Field(
        description="Number of items per page"
    )
    has_next: bool = Field(
        description="Whether more pages exist"
    )
