# =============================================================================
# Chat Routes
# =============================================================================
"""
Chat endpoints for interacting with the orchestrator agent.
"""

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.agents import OrchestratorAgent
from src.config import Settings, get_settings
from src.models.chat import (
    ChatRequest,
    ChatResponse,
    ConversationListResponse,
    ConversationSummary,
    ErrorResponse,
)
from src.services.chat_service import get_chat_service


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Router Setup
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/chat", tags=["Chat"])


# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------
def get_orchestrator(
    settings: Annotated[Settings, Depends(get_settings)]
) -> OrchestratorAgent:
    """
    Dependency to get the orchestrator agent instance.

    Args:
        settings: Application settings.

    Returns:
        OrchestratorAgent instance configured with current settings.

    Raises:
        HTTPException: If Anthropic API key is not configured.
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key not configured. Please set ANTHROPIC_API_KEY."
        )

    return OrchestratorAgent(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model
    )


async def verify_localhost(request: Request) -> None:
    """
    Verify that the request is coming from localhost.

    This is a security measure to restrict access during development.

    Args:
        request: The incoming request.

    Raises:
        HTTPException: If request is not from localhost.
    """
    client_host = request.client.host if request.client else None
    allowed_hosts = ["127.0.0.1", "localhost", "::1"]

    # Also allow Docker internal networking
    if client_host and not (
        client_host in allowed_hosts or
        client_host.startswith("172.") or  # Docker bridge network
        client_host.startswith("192.168.")  # Local network
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Only localhost connections allowed. Got: {client_host}"
        )


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.post(
    "",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    },
    summary="Send Message to Orchestrator",
    description="Send a message to the orchestrator agent and receive a response.",
    dependencies=[Depends(verify_localhost)]
)
async def chat(
    request: ChatRequest,
    orchestrator: Annotated[OrchestratorAgent, Depends(get_orchestrator)]
) -> ChatResponse:
    """
    Process a chat message through the orchestrator agent.

    This endpoint accepts a user message, processes it through the
    Claude-powered orchestrator agent, and returns the response.

    Args:
        request: The chat request containing the user's message.
        orchestrator: The orchestrator agent instance.

    Returns:
        ChatResponse with the orchestrator's response.

    Raises:
        HTTPException: If processing fails.
    """
    start_time = time.time()

    # Get or create a chat session using the chat service
    chat_service = get_chat_service()

    try:
        # Get existing chat or create a new one
        chat = await chat_service.get_or_create_chat(chat_id=request.chat_id)
        chat_id = chat.id

        logger.info(f"Processing chat request for chat_id: {chat_id}")

        # Process the message through the orchestrator
        response_text, tokens_used = await orchestrator.process_message(
            message=request.message,
            chat_id=chat_id
        )

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        return ChatResponse(
            response=response_text,
            chat_id=chat_id,
            tokens_used=tokens_used,
            processing_time_ms=round(processing_time_ms, 2)
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List Conversations",
    description="Get a paginated list of all chat sessions.",
    dependencies=[Depends(verify_localhost)]
)
async def list_conversations(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=50, description="Items per page"),
) -> ConversationListResponse:
    """
    List all conversations with pagination.

    Returns conversations ordered by most recently modified first.
    Each conversation includes an auto-generated title from the first message.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page (max 50).

    Returns:
        Paginated list of conversation summaries.
    """
    chat_service = get_chat_service()

    try:
        summaries, total = await chat_service.list_conversations(
            page=page,
            page_size=page_size,
        )

        items = [ConversationSummary(**s) for s in summaries]
        has_next = (page * page_size) < total

        return ConversationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
        )

    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )


@router.get(
    "/conversations/{chat_id}",
    summary="Get Conversation History",
    description="Retrieve the history of a specific chat session.",
    dependencies=[Depends(verify_localhost)]
)
async def get_conversation(chat_id: str) -> dict:
    """
    Get the history of a chat session.

    Args:
        chat_id: The UUID of the chat session to retrieve.

    Returns:
        Dictionary containing conversation history.
    """
    from uuid import UUID

    chat_service = get_chat_service()

    try:
        # Parse the UUID
        chat_uuid = UUID(chat_id)

        # Get conversation history
        messages = await chat_service.get_conversation_history(chat_uuid)

        return {
            "chat_id": chat_id,
            "messages": messages,
            "message_count": len(messages)
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat_id format. Must be a valid UUID."
        )
    except Exception as e:
        logger.error(f"Error retrieving conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation: {str(e)}"
        )


@router.delete(
    "/conversations/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Conversation",
    description="Delete a chat session and all its messages.",
    dependencies=[Depends(verify_localhost)]
)
async def delete_conversation(chat_id: str) -> None:
    """
    Delete a conversation and all its messages.

    Args:
        chat_id: The UUID of the chat session to delete.

    Raises:
        HTTPException: If the conversation is not found or deletion fails.
    """
    from uuid import UUID

    chat_service = get_chat_service()

    try:
        # Parse the UUID
        chat_uuid = UUID(chat_id)

        # Delete the conversation
        deleted = await chat_service.delete_chat(chat_uuid)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {chat_id} not found."
            )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat_id format. Must be a valid UUID."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )
