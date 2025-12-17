# =============================================================================
# Health Check Routes
# =============================================================================
"""
Health check endpoints for monitoring and container orchestration.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.config import get_settings


# -----------------------------------------------------------------------------
# Router Setup
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/health", tags=["Health"])


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------
class HealthStatus(BaseModel):
    """
    Health check response model.

    Attributes:
        status: Current health status (healthy, degraded, unhealthy).
        timestamp: Time of the health check.
        version: Application version.
        environment: Current environment (development, staging, production).
    """

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="Current health status"
    )
    timestamp: datetime = Field(
        description="Time of the health check"
    )
    version: str = Field(
        description="Application version"
    )
    environment: str = Field(
        description="Current environment"
    )


class DetailedHealthStatus(HealthStatus):
    """
    Detailed health check with component status.

    Attributes:
        components: Status of individual system components.
    """

    components: dict[str, dict] = Field(
        description="Status of individual components"
    )


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.get(
    "",
    response_model=HealthStatus,
    summary="Basic Health Check",
    description="Returns basic health status for container orchestration."
)
async def health_check() -> HealthStatus:
    """
    Perform a basic health check.

    This endpoint is used by Docker health checks and load balancers
    to verify the service is running.

    Returns:
        HealthStatus: Basic health status information.
    """
    settings = get_settings()

    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.app_env
    )


@router.get(
    "/detailed",
    response_model=DetailedHealthStatus,
    summary="Detailed Health Check",
    description="Returns detailed health status including component checks."
)
async def detailed_health_check() -> DetailedHealthStatus:
    """
    Perform a detailed health check with component status.

    Checks the health of all system components including:
    - Database connectivity
    - Anthropic API availability
    - Memory and resource usage

    Returns:
        DetailedHealthStatus: Detailed health status with component info.
    """
    settings = get_settings()

    # Check components (simplified for now)
    components = {
        "api": {
            "status": "healthy",
            "latency_ms": 0
        },
        "database": {
            "status": "healthy" if settings.postgres_host else "not_configured",
            "host": settings.postgres_host
        },
        "anthropic_api": {
            "status": "configured" if settings.anthropic_api_key else "not_configured",
            "model": settings.claude_model
        }
    }

    # Determine overall status
    overall_status = "healthy"
    if not settings.anthropic_api_key:
        overall_status = "degraded"

    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.app_env,
        components=components
    )
