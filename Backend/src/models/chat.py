# =============================================================================
# Chat Models
# =============================================================================
"""
Pydantic models for chat request and response handling.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


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
        conversation_id: Optional ID to continue an existing conversation.
    """

    message: str = Field(
        min_length=1,
        max_length=10000,
        description="The user's message to send to the orchestrator"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation ID to continue an existing conversation"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Create a todo item to review the project architecture",
                    "conversation_id": None
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """
    Response payload from the chat endpoint.

    Attributes:
        response: The orchestrator's response message.
        conversation_id: ID of the conversation for future reference.
        tokens_used: Number of tokens consumed by this request.
        processing_time_ms: Time taken to process the request in milliseconds.
    """

    response: str = Field(
        description="The orchestrator's response message"
    )
    conversation_id: str = Field(
        description="Conversation ID for continuing the conversation"
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
                    "conversation_id": "conv_abc123",
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
