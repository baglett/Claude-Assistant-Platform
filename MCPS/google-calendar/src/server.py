# =============================================================================
# Google Calendar MCP Server
# =============================================================================
"""
FastMCP server providing Google Calendar API tools.

This server exposes MCP tools for:
- Listing calendars
- Listing, creating, updating, and deleting events
- Searching for events
- Querying free/busy information
- Quick-adding events via natural language

The server runs as a standalone HTTP service and can be called by the
orchestrator or other components to interact with Google Calendar.
"""

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .auth import GoogleAuthManager
from .client import GoogleCalendarClient
from .models import (
    CreateEventRequest,
    DeleteEventRequest,
    UpdateEventRequest,
)

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
class Settings(BaseSettings):
    """
    Server settings loaded from environment variables.

    Attributes:
        google_calendar_client_id: OAuth client ID.
        google_calendar_client_secret: OAuth client secret.
        google_calendar_token_path: Path to store OAuth tokens.
        google_calendar_oauth_port: Port for OAuth callback.
        google_calendar_default_timezone: Default timezone for events.
        host: Host address for the server.
        port: Port number for the server.
    """

    google_calendar_client_id: str = Field(
        default="",
        description="Google OAuth client ID",
    )
    google_calendar_client_secret: str = Field(
        default="",
        description="Google OAuth client secret",
    )
    google_calendar_token_path: str = Field(
        default="./data/google_calendar_token.json",
        description="Path to store OAuth tokens",
    )
    google_calendar_oauth_port: int = Field(
        default=8085,
        description="Port for OAuth callback server",
    )
    google_calendar_default_timezone: str = Field(
        default="America/New_York",
        description="Default timezone for events",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host address for the server",
    )
    port: int = Field(
        default=8084,
        description="Port number for the server",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


# -----------------------------------------------------------------------------
# Initialize Auth Manager and Client
# -----------------------------------------------------------------------------
auth_manager = GoogleAuthManager(
    client_id=settings.google_calendar_client_id,
    client_secret=settings.google_calendar_client_secret,
    token_path=settings.google_calendar_token_path,
    oauth_port=settings.google_calendar_oauth_port,
)

calendar_client = GoogleCalendarClient(
    auth_manager=auth_manager,
    default_timezone=settings.google_calendar_default_timezone,
)


# -----------------------------------------------------------------------------
# FastMCP Server
# -----------------------------------------------------------------------------
mcp = FastMCP("google-calendar-mcp")


# -----------------------------------------------------------------------------
# Authentication Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def check_auth_status() -> dict:
    """
    Check the current authentication status.

    Returns:
        Dictionary with authentication status and details.
    """
    is_auth = calendar_client.is_authenticated()
    needs_refresh = auth_manager.needs_refresh

    return {
        "authenticated": is_auth,
        "needs_refresh": needs_refresh,
        "message": (
            "Authenticated and ready"
            if is_auth
            else "Authentication required. Use authenticate tool or visit the auth URL."
        ),
    }


@mcp.tool()
async def get_auth_url() -> dict:
    """
    Get the OAuth authorization URL for manual authentication.

    Use this if automatic browser authentication is not available.

    Returns:
        Dictionary with the authorization URL.
    """
    url = auth_manager.get_auth_url()
    return {
        "auth_url": url,
        "instructions": (
            "Visit this URL in a browser to authenticate. "
            "After granting permission, you will be redirected to a local callback."
        ),
    }


# -----------------------------------------------------------------------------
# Calendar Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def list_calendars() -> dict:
    """
    List all calendars the user has access to.

    Returns:
        Dictionary containing list of calendars with id, summary,
        primary status, and access role.
    """
    result = await calendar_client.list_calendars()
    return result.model_dump()


# -----------------------------------------------------------------------------
# Event Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10,
    query: Optional[str] = None,
) -> dict:
    """
    List events from a calendar within a time range.

    Args:
        calendar_id: Calendar ID or "primary" for user's primary calendar.
        time_min: Lower bound (inclusive) for event start time (ISO 8601).
                  Defaults to now if not specified.
        time_max: Upper bound (exclusive) for event start time (ISO 8601).
                  Defaults to 7 days from now if not specified.
        max_results: Maximum number of events to return (default: 10).
        query: Optional text to search for in event titles and descriptions.

    Returns:
        Dictionary containing list of events with details.
    """
    result = await calendar_client.list_events(
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        max_results=max_results,
        query=query,
    )
    return result.model_dump()


@mcp.tool()
async def get_event(
    event_id: str,
    calendar_id: str = "primary",
) -> dict:
    """
    Get a specific calendar event by its ID.

    Args:
        event_id: The event identifier.
        calendar_id: The calendar identifier (default: "primary").

    Returns:
        Dictionary containing the event details.
    """
    result = await calendar_client.get_event(
        event_id=event_id,
        calendar_id=calendar_id,
    )
    return result.model_dump()


@mcp.tool()
async def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str = "primary",
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[list[str]] = None,
    timezone: Optional[str] = None,
    recurrence: Optional[list[str]] = None,
) -> dict:
    """
    Create a new calendar event.

    Args:
        summary: Event title.
        start_time: Start time in ISO 8601 format (e.g., "2024-01-15T10:00:00")
                   or YYYY-MM-DD for all-day events.
        end_time: End time in ISO 8601 format or YYYY-MM-DD for all-day events.
        calendar_id: Target calendar ID (default: "primary").
        description: Event description/notes.
        location: Event location.
        attendees: List of attendee email addresses.
        timezone: Timezone for the event (e.g., "America/New_York").
                  Defaults to server's configured timezone.
        recurrence: Recurrence rules in RRULE format
                   (e.g., ["RRULE:FREQ=WEEKLY;COUNT=10"]).

    Returns:
        Dictionary containing the created event details.
    """
    result = await calendar_client.create_event(
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        calendar_id=calendar_id,
        description=description,
        location=location,
        attendees=attendees,
        timezone=timezone,
        recurrence=recurrence,
    )
    return result.model_dump()


@mcp.tool()
async def update_event(
    event_id: str,
    calendar_id: str = "primary",
    summary: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    timezone: Optional[str] = None,
) -> dict:
    """
    Update an existing calendar event.

    Only provide the fields you want to change. Unchanged fields will
    keep their current values.

    Args:
        event_id: The event ID to update.
        calendar_id: The calendar ID (default: "primary").
        summary: New event title.
        description: New event description.
        location: New event location.
        start_time: New start time (ISO 8601 or YYYY-MM-DD).
        end_time: New end time (ISO 8601 or YYYY-MM-DD).
        timezone: New timezone for the event.

    Returns:
        Dictionary containing the updated event details.
    """
    result = await calendar_client.update_event(
        event_id=event_id,
        calendar_id=calendar_id,
        summary=summary,
        description=description,
        location=location,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
    )
    return result.model_dump()


@mcp.tool()
async def delete_event(
    event_id: str,
    calendar_id: str = "primary",
    send_updates: str = "none",
) -> dict:
    """
    Delete a calendar event.

    Args:
        event_id: The event ID to delete.
        calendar_id: The calendar ID (default: "primary").
        send_updates: Whether to send cancellation notices.
                     Options: "all", "externalOnly", "none" (default).

    Returns:
        Dictionary indicating success or failure.
    """
    result = await calendar_client.delete_event(
        event_id=event_id,
        calendar_id=calendar_id,
        send_updates=send_updates,
    )
    return result.model_dump()


@mcp.tool()
async def quick_add_event(
    text: str,
    calendar_id: str = "primary",
) -> dict:
    """
    Create an event using natural language text.

    Google Calendar will parse the text to extract event details
    like title, date, time, and location.

    Args:
        text: Natural language description of the event.
              Examples:
              - "Meeting with John tomorrow at 3pm"
              - "Dentist appointment on Friday 2-3pm"
              - "Team lunch at noon next Monday at Italian Restaurant"
        calendar_id: Target calendar ID (default: "primary").

    Returns:
        Dictionary containing the created event details.
    """
    result = await calendar_client.quick_add_event(
        text=text,
        calendar_id=calendar_id,
    )
    return result.model_dump()


@mcp.tool()
async def search_events(
    query: str,
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 25,
) -> dict:
    """
    Search for events by text query.

    Searches event titles and descriptions for matching text.

    Args:
        query: Search terms to match.
        calendar_id: Calendar to search (default: "primary").
        time_min: Lower bound for event time (ISO 8601).
        time_max: Upper bound for event time (ISO 8601).
        max_results: Maximum number of results (default: 25).

    Returns:
        Dictionary containing matching events.
    """
    result = await calendar_client.search_events(
        query=query,
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        max_results=max_results,
    )
    return result.model_dump()


@mcp.tool()
async def get_freebusy(
    time_min: str,
    time_max: str,
    calendar_ids: Optional[list[str]] = None,
) -> dict:
    """
    Query free/busy information for calendars.

    Returns busy time slots within the specified range. Useful for
    finding available meeting times.

    Args:
        time_min: Start of time range (ISO 8601).
        time_max: End of time range (ISO 8601).
        calendar_ids: List of calendar IDs to query.
                     Defaults to ["primary"] if not specified.

    Returns:
        Dictionary with busy time slots for each calendar.
    """
    result = await calendar_client.get_freebusy(
        time_min=time_min,
        time_max=time_max,
        calendar_ids=calendar_ids,
    )
    return result.model_dump()


@mcp.tool()
async def get_current_time(
    timezone: Optional[str] = None,
) -> dict:
    """
    Get the current date and time in a specified timezone.

    Useful for relative event scheduling.

    Args:
        timezone: Timezone identifier (e.g., "America/New_York").
                  Defaults to server's configured timezone.

    Returns:
        Dictionary with current datetime information.
    """
    tz_str = timezone or settings.google_calendar_default_timezone
    try:
        tz = ZoneInfo(tz_str)
        now = datetime.now(tz)
        return {
            "success": True,
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": tz_str,
            "day_of_week": now.strftime("%A"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# -----------------------------------------------------------------------------
# FastAPI Application (for HTTP access)
# -----------------------------------------------------------------------------
fastapi_app = FastAPI(
    title="Google Calendar MCP Server",
    description="MCP server providing Google Calendar API tools",
    version="0.1.0",
)


@fastapi_app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Dictionary with service status.
    """
    is_auth = calendar_client.is_authenticated()
    return {
        "status": "healthy",
        "service": "google-calendar-mcp",
        "authenticated": is_auth,
    }


@fastapi_app.get("/auth/status")
async def http_auth_status() -> dict:
    """Get authentication status via HTTP."""
    return await check_auth_status()


@fastapi_app.get("/auth/url")
async def http_auth_url() -> dict:
    """Get OAuth authorization URL via HTTP."""
    return await get_auth_url()


@fastapi_app.post("/auth/authenticate")
async def http_authenticate() -> dict:
    """
    Trigger OAuth authentication flow.

    Note: This will open a browser window for authentication.
    Use /auth/url for headless environments.
    """
    result = await calendar_client.authenticate()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/calendars")
async def http_list_calendars() -> dict:
    """List all calendars via HTTP."""
    if not calendar_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await calendar_client.list_calendars()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/events")
async def http_list_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10,
    query: Optional[str] = None,
) -> dict:
    """List events via HTTP."""
    if not calendar_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await calendar_client.list_events(
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        max_results=max_results,
        query=query,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/events/{event_id}")
async def http_get_event(
    event_id: str,
    calendar_id: str = "primary",
) -> dict:
    """Get a specific event via HTTP."""
    if not calendar_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await calendar_client.get_event(
        event_id=event_id,
        calendar_id=calendar_id,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.post("/events")
async def http_create_event(request: CreateEventRequest) -> dict:
    """Create an event via HTTP."""
    if not calendar_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await calendar_client.create_event(
        summary=request.summary,
        start_time=request.start_time,
        end_time=request.end_time,
        calendar_id=request.calendar_id,
        description=request.description,
        location=request.location,
        attendees=request.attendees,
        timezone=request.timezone,
        recurrence=request.recurrence,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.patch("/events/{event_id}")
async def http_update_event(
    event_id: str,
    request: UpdateEventRequest,
) -> dict:
    """Update an event via HTTP."""
    if not calendar_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await calendar_client.update_event(
        event_id=event_id,
        calendar_id=request.calendar_id,
        summary=request.summary,
        description=request.description,
        location=request.location,
        start_time=request.start_time,
        end_time=request.end_time,
        timezone=request.timezone,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.delete("/events/{event_id}")
async def http_delete_event(
    event_id: str,
    calendar_id: str = "primary",
    send_updates: str = "none",
) -> dict:
    """Delete an event via HTTP."""
    if not calendar_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await calendar_client.delete_event(
        event_id=event_id,
        calendar_id=calendar_id,
        send_updates=send_updates,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.post("/events/quick-add")
async def http_quick_add_event(
    text: str,
    calendar_id: str = "primary",
) -> dict:
    """Quick add an event via HTTP."""
    if not calendar_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await calendar_client.quick_add_event(
        text=text,
        calendar_id=calendar_id,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.post("/freebusy")
async def http_get_freebusy(
    time_min: str,
    time_max: str,
    calendar_ids: Optional[list[str]] = None,
) -> dict:
    """Query free/busy via HTTP."""
    if not calendar_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await calendar_client.get_freebusy(
        time_min=time_min,
        time_max=time_max,
        calendar_ids=calendar_ids,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def is_interactive_environment() -> bool:
    """
    Check if we're running in an interactive environment where OAuth browser flow works.

    Returns False if running in Docker, headless server, or no display available.
    """
    import os
    import sys

    # Check for Docker
    if os.path.exists("/.dockerenv"):
        return False

    # Check for common container indicators
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return False

    # Check for display (Linux)
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        return False

    # Check for SSH session without X forwarding
    if os.environ.get("SSH_CLIENT") and not os.environ.get("DISPLAY"):
        return False

    return True


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Run the server."""
    import os
    import uvicorn

    logger.info(f"Starting Google Calendar MCP Server on {settings.host}:{settings.port}")

    if not settings.google_calendar_client_id:
        logger.warning(
            "GOOGLE_CALENDAR_CLIENT_ID not set - authentication will not work"
        )

    if calendar_client.is_authenticated():
        logger.info("Already authenticated with Google Calendar")
    else:
        # Check if we have credentials configured
        if settings.google_calendar_client_id and settings.google_calendar_client_secret:
            # Check if refresh token is available via env var
            refresh_token = os.environ.get("GOOGLE_CALENDAR_REFRESH_TOKEN")

            if refresh_token:
                # Token should have been loaded by auth_manager already
                # If we got here, it means the refresh failed
                logger.error("GOOGLE_CALENDAR_REFRESH_TOKEN is set but authentication failed")
                logger.error("The refresh token may be invalid or revoked")
                logger.info("Please generate a new refresh token")
            elif is_interactive_environment():
                # Interactive environment - can run browser OAuth flow
                logger.info("=" * 60)
                logger.info("Google Calendar authentication required - starting OAuth flow...")
                logger.info("=" * 60)
                logger.info("")
                logger.info("A browser window will open for you to sign in to Google.")
                logger.info("After signing in, grant the requested permissions.")
                logger.info("")
                logger.info(f"OAuth callback will be received on port {settings.google_calendar_oauth_port}")
                logger.info("")

                try:
                    auth_manager.authenticate()
                    logger.info("Authentication successful!")
                    logger.info("")
                    logger.info("To use this in production, set GOOGLE_CALENDAR_REFRESH_TOKEN to:")
                    # Read the saved token to show the refresh token
                    import json
                    with open(settings.google_calendar_token_path, "r") as f:
                        token_data = json.load(f)
                    logger.info(f"  {token_data.get('refresh_token')}")
                    logger.info("")
                except Exception as e:
                    logger.error(f"Authentication failed: {e}")
            else:
                # Headless/container environment - need refresh token
                logger.warning("=" * 60)
                logger.warning("Google Calendar authentication required but running in headless mode")
                logger.warning("=" * 60)
                logger.warning("")
                logger.warning("To authenticate, set the GOOGLE_CALENDAR_REFRESH_TOKEN environment variable.")
                logger.warning("")
                logger.warning("To get a refresh token:")
                logger.warning("  1. Run this MCP server locally (not in Docker)")
                logger.warning("  2. Complete the OAuth flow in your browser")
                logger.warning("  3. Copy the refresh_token from data/google_calendar_token.json")
                logger.warning("  4. Set GOOGLE_CALENDAR_REFRESH_TOKEN=<token> in your environment")
                logger.warning("")
        else:
            logger.info("Not authenticated - set GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET")

    uvicorn.run(
        fastapi_app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
