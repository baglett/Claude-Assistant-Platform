# =============================================================================
# FastAPI Application Entry Point
# =============================================================================
"""
Main FastAPI application for the Claude Assistant Platform.

This module creates and configures the FastAPI application instance,
including middleware, routes, and exception handlers.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import chat, health
from src.config import get_settings


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Lifespan Management
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan events.

    Handles startup and shutdown procedures including:
    - Database connection initialization
    - Resource cleanup on shutdown

    Args:
        app: The FastAPI application instance.

    Yields:
        None during application runtime.
    """
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
    logger.info(f"Debug mode: {settings.debug}")

    if not settings.anthropic_api_key:
        logger.warning(
            "ANTHROPIC_API_KEY not set. Chat functionality will be unavailable."
        )

    # TODO: Initialize database connection pool here
    # TODO: Initialize any background tasks

    yield

    # Shutdown
    logger.info("Shutting down application...")
    # TODO: Close database connections
    # TODO: Cancel background tasks


# -----------------------------------------------------------------------------
# Application Factory
# -----------------------------------------------------------------------------
def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Claude Assistant Platform API",
        description=(
            "A self-hosted AI assistant platform powered by the Claude Agents SDK. "
            "Provides an orchestrator agent for intelligent task management and "
            "delegation to specialized sub-agents."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )

    # -------------------------------------------------------------------------
    # Middleware Configuration
    # -------------------------------------------------------------------------

    # CORS middleware - restrict to localhost for now
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",      # Next.js frontend
            "http://127.0.0.1:3000",
            "http://localhost:8000",      # API itself (for Swagger UI)
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        Global exception handler for unhandled exceptions.

        Args:
            request: The incoming request.
            exc: The unhandled exception.

        Returns:
            JSON response with error details.
        """
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "details": str(exc) if settings.debug else None
            }
        )

    # -------------------------------------------------------------------------
    # Route Registration
    # -------------------------------------------------------------------------

    # Health check routes
    app.include_router(health.router)

    # Chat routes
    app.include_router(chat.router, prefix="/api")

    # -------------------------------------------------------------------------
    # Root Endpoint
    # -------------------------------------------------------------------------

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """
        Root endpoint providing API information.

        Returns:
            Dictionary with API information and links.
        """
        return {
            "name": "Claude Assistant Platform API",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs" if settings.debug else "disabled",
            "health": "/health"
        }

    return app


# -----------------------------------------------------------------------------
# Application Instance
# -----------------------------------------------------------------------------
app = create_app()


# -----------------------------------------------------------------------------
# Development Server Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
