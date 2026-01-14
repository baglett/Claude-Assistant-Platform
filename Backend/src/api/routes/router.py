# =============================================================================
# Router API Routes
# =============================================================================
"""
API endpoints for the hybrid router system.

Provides endpoints for:
- Generating agent embeddings
- Testing routing decisions
- Viewing router statistics

Usage:
    from src.api.routes.router import router
    app.include_router(router, prefix="/api/router", tags=["router"])
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.embedding_service import generate_agent_embeddings
from src.services.router_service import get_router_service


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Router Instance
# -----------------------------------------------------------------------------
router = APIRouter()


# -----------------------------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------------------------
class RouteTestRequest(BaseModel):
    """Request model for testing routing decisions."""

    message: str = Field(..., description="The message to route")


class RouteTestResponse(BaseModel):
    """Response model for routing test results."""

    agent: str | None = Field(description="Selected agent (None = orchestrator)")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    tier: int = Field(description="Routing tier that made the decision")
    latency_ms: int = Field(description="Total routing latency in milliseconds")
    scores: dict[str, float] = Field(description="Per-agent scores")
    should_bypass_orchestrator: bool = Field(
        description="Whether to bypass orchestrator"
    )


class GenerateEmbeddingsResponse(BaseModel):
    """Response model for embedding generation."""

    success: bool = Field(description="Whether generation succeeded")
    results: dict[str, bool] = Field(description="Per-agent success status")
    message: str = Field(description="Status message")


class RouterStatsResponse(BaseModel):
    """Response model for router statistics."""

    agents_loaded: int = Field(description="Number of agents loaded")
    agents_with_embeddings: int = Field(description="Number of agents with embeddings")
    bm25_initialized: bool = Field(description="Whether BM25 is initialized")
    embedding_service_available: bool = Field(
        description="Whether embedding service is available"
    )
    cache_connected: bool = Field(description="Whether cache is connected")


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.post("/test", response_model=RouteTestResponse)
async def test_routing(request: RouteTestRequest) -> RouteTestResponse:
    """
    Test routing for a given message.

    Runs the message through the routing pipeline and returns the result
    without actually executing any agent.

    Args:
        request: The route test request containing the message.

    Returns:
        RouteTestResponse with routing decision details.

    Example:
        POST /api/router/test
        {"message": "create a github issue"}

        Response:
        {
            "agent": "github",
            "confidence": 0.95,
            "tier": 1,
            "latency_ms": 2,
            "scores": {"github": 3.0, "todo": 0.0, ...},
            "should_bypass_orchestrator": true
        }
    """
    router_service = await get_router_service()
    result = await router_service.route(request.message)

    return RouteTestResponse(
        agent=result.agent,
        confidence=result.confidence,
        tier=result.tier,
        latency_ms=result.latency_ms,
        scores=result.scores,
        should_bypass_orchestrator=result.should_bypass_orchestrator,
    )


@router.post("/generate-embeddings", response_model=GenerateEmbeddingsResponse)
async def generate_embeddings() -> GenerateEmbeddingsResponse:
    """
    Generate embeddings for all agents.

    Calls OpenAI's embedding API to generate and store embeddings
    for all enabled agents. This should be called:
    - After initial setup
    - When agent descriptions change
    - When new agents are added

    Returns:
        GenerateEmbeddingsResponse with per-agent results.

    Raises:
        HTTPException: If embedding service is not configured.

    Example:
        POST /api/router/generate-embeddings

        Response:
        {
            "success": true,
            "results": {
                "github": true,
                "todo": true,
                "email": true,
                "calendar": true,
                "motion": true
            },
            "message": "Generated embeddings for 5/5 agents"
        }
    """
    try:
        results = await generate_agent_embeddings()

        if not results:
            raise HTTPException(
                status_code=503,
                detail="Embedding service not available. Check OPENAI_API_KEY.",
            )

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        # Refresh router to load new embeddings
        router_service = await get_router_service()
        await router_service.refresh_agents()

        return GenerateEmbeddingsResponse(
            success=success_count == total_count,
            results=results,
            message=f"Generated embeddings for {success_count}/{total_count} agents",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings: {str(e)}",
        )


@router.get("/stats", response_model=RouterStatsResponse)
async def get_router_stats() -> RouterStatsResponse:
    """
    Get router statistics.

    Returns information about the router's current state including
    loaded agents, embeddings, and service availability.

    Returns:
        RouterStatsResponse with router statistics.

    Example:
        GET /api/router/stats

        Response:
        {
            "agents_loaded": 5,
            "agents_with_embeddings": 5,
            "bm25_initialized": true,
            "embedding_service_available": true,
            "cache_connected": true
        }
    """
    router_service = await get_router_service()

    return RouterStatsResponse(
        agents_loaded=len(router_service.agents),
        agents_with_embeddings=len(router_service.agent_embeddings),
        bm25_initialized=router_service.bm25 is not None,
        embedding_service_available=(
            router_service.embedding_service is not None
            and router_service.embedding_service.is_available
        ),
        cache_connected=(
            router_service.cache is not None and router_service.cache.connected
        ),
    )


@router.post("/refresh")
async def refresh_router() -> dict[str, Any]:
    """
    Refresh router configuration.

    Reloads agents, patterns, BM25 index, and embeddings from the database.
    Use this after making changes to routing configuration.

    Returns:
        Dictionary with refresh status.

    Example:
        POST /api/router/refresh

        Response:
        {
            "success": true,
            "agents_loaded": 5,
            "embeddings_loaded": 5
        }
    """
    router_service = await get_router_service()
    await router_service.refresh_agents()

    return {
        "success": True,
        "agents_loaded": len(router_service.agents),
        "embeddings_loaded": len(router_service.agent_embeddings),
    }
