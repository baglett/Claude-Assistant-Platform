# =============================================================================
# FastAPI Application Entry Point
# =============================================================================
"""
Main FastAPI application for the Claude Assistant Platform.

This module creates and configures the FastAPI application instance,
including middleware, routes, and exception handlers.

Note: On Windows, use run.py to start the application. It configures the
correct event loop (SelectorEventLoop) required by psycopg's async support.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.agents.motion_agent import MotionAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.todo_agent import TodoAgent
from src.api.routes import chat, health, todos
from src.config import get_settings
from src.database import close_database, init_database
from src.services.telegram import TelegramMessageHandler, TelegramPoller
from src.services.todo_executor import TodoExecutor

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Silence noisy third-party loggers
# httpx logs every HTTP request at INFO level (including polling every 30s)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# -----------------------------------------------------------------------------
# Lifespan Management
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan events.

    Handles startup and shutdown procedures including:
    - Database connection initialization
    - Telegram poller initialization and startup
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

    # -------------------------------------------------------------------------
    # Initialize Database Connection
    # -------------------------------------------------------------------------
    await init_database()
    logger.info("Database connection initialized")

    # Track background tasks and handlers for cleanup
    telegram_poller_task: asyncio.Task | None = None
    telegram_handler: TelegramMessageHandler | None = None
    todo_executor: TodoExecutor | None = None
    todo_executor_task: asyncio.Task | None = None

    # -------------------------------------------------------------------------
    # Initialize Orchestrator Agent
    # -------------------------------------------------------------------------
    orchestrator: OrchestratorAgent | None = None

    if settings.anthropic_api_key:
        orchestrator = OrchestratorAgent(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
        )

        # Register sub-agents with the orchestrator
        todo_agent = TodoAgent(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
        )
        orchestrator.register_agent(todo_agent)
        logger.info("Registered TodoAgent with orchestrator")

        # Register Motion Agent if configured
        if settings.motion_is_configured:
            motion_agent = MotionAgent(
                api_key=settings.anthropic_api_key,
                model=settings.claude_model,
                mcp_url=settings.motion_mcp_url,
            )
            orchestrator.register_agent(motion_agent)
            logger.info(
                f"Registered MotionAgent with orchestrator "
                f"(MCP: {settings.motion_mcp_url})"
            )
        else:
            logger.info(
                "Motion integration not configured - MotionAgent not registered"
            )

        # Store orchestrator in app state for route access
        app.state.orchestrator = orchestrator
        logger.info("Orchestrator agent initialized with registered sub-agents")
    else:
        logger.warning(
            "ANTHROPIC_API_KEY not set. Chat functionality will be unavailable."
        )

    # -------------------------------------------------------------------------
    # Initialize Telegram Poller
    # -------------------------------------------------------------------------
    if settings.telegram_is_configured and orchestrator:
        # Log which bot is being used (dev vs prod)
        bot_mode = "DEVELOPMENT" if settings.telegram_is_dev_bot else "PRODUCTION"
        logger.info(f"Initializing Telegram integration ({bot_mode} bot)...")

        # Get the active bot token (dev or prod based on APP_ENV)
        active_bot_token = settings.telegram_active_bot_token

        # Create the message handler (uses direct Telegram API for replies)
        # Note: Agent-initiated messages use MCP tools separately
        telegram_handler = TelegramMessageHandler(
            orchestrator=orchestrator,
            bot_token=active_bot_token,
        )

        # Create the poller
        telegram_poller = TelegramPoller(
            bot_token=active_bot_token,
            allowed_user_ids=settings.telegram_allowed_user_ids_list,
            polling_timeout=settings.telegram_polling_timeout,
            message_handler=telegram_handler.handle_message,
        )

        # Verify bot token before starting
        if await telegram_poller.verify_token():
            # Start the poller as a background task
            telegram_poller_task = asyncio.create_task(
                telegram_poller.start(),
                name="telegram_poller",
            )
            app.state.telegram_poller = telegram_poller
            app.state.telegram_handler = telegram_handler
            logger.info(f"Telegram poller started ({bot_mode} bot)")
        else:
            logger.error(
                "Failed to verify Telegram bot token. "
                "Telegram integration disabled."
            )
    elif settings.telegram_enabled and not settings.telegram_active_bot_token:
        logger.warning(
            "No Telegram bot token configured. "
            "Set TELEGRAM_BOT_TOKEN (prod) or TELEGRAM_DEV_BOT_TOKEN (dev). "
            "Telegram integration disabled."
        )
    elif settings.telegram_enabled and not orchestrator:
        logger.warning(
            "Orchestrator not available. Telegram integration disabled."
        )

    # -------------------------------------------------------------------------
    # Initialize Todo Executor (Background Task Processing)
    # -------------------------------------------------------------------------
    if orchestrator and settings.todo_executor_enabled:
        logger.info("Initializing Todo Executor...")

        todo_executor = TodoExecutor(
            orchestrator=orchestrator,
            check_interval=settings.todo_executor_interval,
            batch_size=settings.todo_executor_batch_size,
        )

        # Start the executor as a background task
        todo_executor_task = asyncio.create_task(
            todo_executor.start(),
            name="todo_executor",
        )
        app.state.todo_executor = todo_executor
        logger.info("Todo Executor started as background task")
    elif not settings.todo_executor_enabled:
        logger.info("Todo Executor disabled by configuration")

    yield

    # -------------------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------------------
    logger.info("Shutting down application...")

    # Stop Todo Executor
    if todo_executor:
        logger.info("Stopping Todo Executor...")
        todo_executor.stop()

    if todo_executor_task and not todo_executor_task.done():
        todo_executor_task.cancel()
        try:
            await todo_executor_task
        except asyncio.CancelledError:
            logger.info("Todo Executor stopped")

    # Stop Telegram poller
    if telegram_poller_task and not telegram_poller_task.done():
        logger.info("Stopping Telegram poller...")
        telegram_poller_task.cancel()
        try:
            await telegram_poller_task
        except asyncio.CancelledError:
            logger.info("Telegram poller stopped")

    # Close Telegram handler HTTP client
    if telegram_handler:
        await telegram_handler.close()
        logger.info("Telegram handler closed")

    # Close database connection
    await close_database()
    logger.info("Database connection closed")


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

    # Todo routes
    app.include_router(todos.router, prefix="/api")

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
