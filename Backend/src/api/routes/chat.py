# =============================================================================
# Chat Routes
# =============================================================================
"""
Chat endpoints for interacting with the orchestrator agent.
"""

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.agents import OrchestratorAgent
from src.config import Settings, get_settings
from src.models.chat import ChatRequest, ChatResponse, ErrorResponse


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

    # Generate or use existing conversation ID
    conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"

    try:
        # Process the message through the orchestrator
        response_text, tokens_used = await orchestrator.process_message(
            message=request.message,
            conversation_id=conversation_id
        )

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            tokens_used=tokens_used,
            processing_time_ms=round(processing_time_ms, 2)
        )

    except Exception as e:
        # Log the error (in production, use proper logging)
        print(f"Error processing chat request: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get(
    "/conversations/{conversation_id}",
    summary="Get Conversation History",
    description="Retrieve the history of a specific conversation.",
    dependencies=[Depends(verify_localhost)]
)
async def get_conversation(conversation_id: str) -> dict:
    """
    Get the history of a conversation.

    Args:
        conversation_id: The ID of the conversation to retrieve.

    Returns:
        Dictionary containing conversation history.

    Note:
        This is a placeholder implementation. Full implementation
        requires database integration.
    """
    # TODO: Implement conversation history retrieval from database
    return {
        "conversation_id": conversation_id,
        "messages": [],
        "message": "Conversation history not yet implemented"
    }
