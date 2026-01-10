# =============================================================================
# Google Calendar MCP Server - Calendar API Client
# =============================================================================
"""
Google Calendar API client wrapper.

Provides a high-level interface for calendar operations with proper
error handling and data conversion.
"""

import logging
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth import GoogleAuthManager
from .models import (
    CalendarFreeBusy,
    CalendarInfo,
    CalendarListResponse,
    EventInfo,
    EventListResponse,
    EventResponse,
    FreeBusyResponse,
    OperationResponse,
)
from .utils import (
    convert_calendar_from_api,
    convert_event_from_api,
    convert_freebusy_from_api,
    format_datetime_for_api,
    get_time_range,
    validate_calendar_id,
    validate_event_id,
)

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """
    High-level client for Google Calendar API operations.

    Handles authentication, API calls, and data conversion.

    Attributes:
        auth_manager: OAuth authentication manager.
        default_timezone: Default timezone for operations.
    """

    def __init__(
        self,
        auth_manager: GoogleAuthManager,
        default_timezone: str = "UTC",
    ) -> None:
        """
        Initialize the calendar client.

        Args:
            auth_manager: Configured GoogleAuthManager instance.
            default_timezone: Default timezone for events.
        """
        self.auth_manager = auth_manager
        self.default_timezone = default_timezone
        self._service = None

    def _get_service(self):
        """
        Get or create the Calendar API service.

        Returns:
            Calendar API service object.

        Raises:
            RuntimeError: If not authenticated.
        """
        if self._service is not None:
            return self._service

        creds = self.auth_manager.get_credentials()
        if creds is None:
            raise RuntimeError(
                "Not authenticated. Please run authentication flow first."
            )

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self.auth_manager.is_authenticated

    async def authenticate(self) -> OperationResponse:
        """
        Run the OAuth authentication flow.

        Returns:
            OperationResponse indicating success or failure.
        """
        try:
            self.auth_manager.authenticate()
            self._service = None  # Reset service to use new credentials
            return OperationResponse(
                success=True,
                message="Authentication successful",
            )
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return OperationResponse(
                success=False,
                error=str(e),
            )

    # -------------------------------------------------------------------------
    # Calendar Operations
    # -------------------------------------------------------------------------
    async def list_calendars(self) -> CalendarListResponse:
        """
        List all calendars the user has access to.

        Returns:
            CalendarListResponse with list of calendars.
        """
        try:
            service = self._get_service()
            result = service.calendarList().list().execute()

            calendars = [
                convert_calendar_from_api(cal) for cal in result.get("items", [])
            ]

            return CalendarListResponse(
                success=True,
                calendars=calendars,
            )

        except HttpError as e:
            logger.error(f"HTTP error listing calendars: {e}")
            return CalendarListResponse(
                success=False,
                error=f"Google API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error listing calendars: {e}")
            return CalendarListResponse(
                success=False,
                error=str(e),
            )

    # -------------------------------------------------------------------------
    # Event Operations
    # -------------------------------------------------------------------------
    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 10,
        single_events: bool = True,
        query: Optional[str] = None,
        page_token: Optional[str] = None,
    ) -> EventListResponse:
        """
        List events from a calendar.

        Args:
            calendar_id: Calendar ID or "primary".
            time_min: Lower bound for event start time (ISO 8601).
            time_max: Upper bound for event start time (ISO 8601).
            max_results: Maximum number of events to return.
            single_events: Whether to expand recurring events.
            query: Free text search terms.
            page_token: Token for pagination.

        Returns:
            EventListResponse with list of events.
        """
        try:
            service = self._get_service()
            calendar_id = validate_calendar_id(calendar_id)

            # Set default time range if not specified
            if time_min is None and time_max is None:
                time_min, time_max = get_time_range(
                    days_ahead=7,
                    timezone_str=self.default_timezone,
                )

            # Build request parameters
            params = {
                "calendarId": calendar_id,
                "maxResults": max_results,
                "singleEvents": single_events,
                "orderBy": "startTime" if single_events else None,
            }

            if time_min:
                params["timeMin"] = time_min
            if time_max:
                params["timeMax"] = time_max
            if query:
                params["q"] = query
            if page_token:
                params["pageToken"] = page_token

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            result = service.events().list(**params).execute()

            events = [
                convert_event_from_api(event, calendar_id)
                for event in result.get("items", [])
            ]

            return EventListResponse(
                success=True,
                events=events,
                next_page_token=result.get("nextPageToken"),
            )

        except HttpError as e:
            logger.error(f"HTTP error listing events: {e}")
            return EventListResponse(
                success=False,
                error=f"Google API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return EventListResponse(
                success=False,
                error=str(e),
            )

    async def get_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> EventResponse:
        """
        Get a specific event by ID.

        Args:
            event_id: The event identifier.
            calendar_id: The calendar identifier.

        Returns:
            EventResponse with event details.
        """
        try:
            service = self._get_service()
            calendar_id = validate_calendar_id(calendar_id)
            event_id = validate_event_id(event_id)

            result = (
                service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            event = convert_event_from_api(result, calendar_id)

            return EventResponse(
                success=True,
                event=event,
            )

        except HttpError as e:
            logger.error(f"HTTP error getting event: {e}")
            return EventResponse(
                success=False,
                error=f"Google API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return EventResponse(
                success=False,
                error=str(e),
            )

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        calendar_id: str = "primary",
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list[str]] = None,
        timezone: Optional[str] = None,
        recurrence: Optional[list[str]] = None,
        send_updates: str = "none",
    ) -> EventResponse:
        """
        Create a new calendar event.

        Args:
            summary: Event title.
            start_time: Start time (ISO 8601 or YYYY-MM-DD for all-day).
            end_time: End time (ISO 8601 or YYYY-MM-DD for all-day).
            calendar_id: Target calendar ID.
            description: Event description.
            location: Event location.
            attendees: List of attendee email addresses.
            timezone: Event timezone.
            recurrence: Recurrence rules (RRULE format).
            send_updates: Whether to send updates ('all', 'externalOnly', 'none').

        Returns:
            EventResponse with created event details.
        """
        try:
            service = self._get_service()
            calendar_id = validate_calendar_id(calendar_id)
            tz = timezone or self.default_timezone

            # Build event body
            event_body = {
                "summary": summary,
                "start": format_datetime_for_api(start_time, tz),
                "end": format_datetime_for_api(end_time, tz),
            }

            if description:
                event_body["description"] = description
            if location:
                event_body["location"] = location
            if attendees:
                event_body["attendees"] = [{"email": email} for email in attendees]
            if recurrence:
                event_body["recurrence"] = recurrence

            result = (
                service.events()
                .insert(
                    calendarId=calendar_id,
                    body=event_body,
                    sendUpdates=send_updates,
                )
                .execute()
            )

            event = convert_event_from_api(result, calendar_id)

            return EventResponse(
                success=True,
                event=event,
            )

        except HttpError as e:
            logger.error(f"HTTP error creating event: {e}")
            return EventResponse(
                success=False,
                error=f"Google API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return EventResponse(
                success=False,
                error=str(e),
            )

    async def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        summary: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        timezone: Optional[str] = None,
        send_updates: str = "none",
    ) -> EventResponse:
        """
        Update an existing calendar event.

        Args:
            event_id: Event ID to update.
            calendar_id: Calendar ID.
            summary: New event title.
            description: New description.
            location: New location.
            start_time: New start time.
            end_time: New end time.
            timezone: New timezone.
            send_updates: Whether to send updates.

        Returns:
            EventResponse with updated event details.
        """
        try:
            service = self._get_service()
            calendar_id = validate_calendar_id(calendar_id)
            event_id = validate_event_id(event_id)
            tz = timezone or self.default_timezone

            # Get current event
            current = (
                service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            # Update fields that were provided
            if summary is not None:
                current["summary"] = summary
            if description is not None:
                current["description"] = description
            if location is not None:
                current["location"] = location
            if start_time is not None:
                current["start"] = format_datetime_for_api(start_time, tz)
            if end_time is not None:
                current["end"] = format_datetime_for_api(end_time, tz)

            result = (
                service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=current,
                    sendUpdates=send_updates,
                )
                .execute()
            )

            event = convert_event_from_api(result, calendar_id)

            return EventResponse(
                success=True,
                event=event,
            )

        except HttpError as e:
            logger.error(f"HTTP error updating event: {e}")
            return EventResponse(
                success=False,
                error=f"Google API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return EventResponse(
                success=False,
                error=str(e),
            )

    async def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        send_updates: str = "none",
    ) -> OperationResponse:
        """
        Delete a calendar event.

        Args:
            event_id: Event ID to delete.
            calendar_id: Calendar ID.
            send_updates: Whether to send cancellation notices.

        Returns:
            OperationResponse indicating success or failure.
        """
        try:
            service = self._get_service()
            calendar_id = validate_calendar_id(calendar_id)
            event_id = validate_event_id(event_id)

            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates=send_updates,
            ).execute()

            return OperationResponse(
                success=True,
                message=f"Event {event_id} deleted successfully",
            )

        except HttpError as e:
            logger.error(f"HTTP error deleting event: {e}")
            return OperationResponse(
                success=False,
                error=f"Google API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return OperationResponse(
                success=False,
                error=str(e),
            )

    async def quick_add_event(
        self,
        text: str,
        calendar_id: str = "primary",
        send_updates: str = "none",
    ) -> EventResponse:
        """
        Create an event using natural language text.

        Args:
            text: Natural language description (e.g., "Meeting tomorrow at 3pm").
            calendar_id: Target calendar ID.
            send_updates: Whether to send updates.

        Returns:
            EventResponse with created event details.
        """
        try:
            service = self._get_service()
            calendar_id = validate_calendar_id(calendar_id)

            result = (
                service.events()
                .quickAdd(
                    calendarId=calendar_id,
                    text=text,
                    sendUpdates=send_updates,
                )
                .execute()
            )

            event = convert_event_from_api(result, calendar_id)

            return EventResponse(
                success=True,
                event=event,
            )

        except HttpError as e:
            logger.error(f"HTTP error quick adding event: {e}")
            return EventResponse(
                success=False,
                error=f"Google API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error quick adding event: {e}")
            return EventResponse(
                success=False,
                error=str(e),
            )

    # -------------------------------------------------------------------------
    # Free/Busy Operations
    # -------------------------------------------------------------------------
    async def get_freebusy(
        self,
        time_min: str,
        time_max: str,
        calendar_ids: Optional[list[str]] = None,
    ) -> FreeBusyResponse:
        """
        Query free/busy information for calendars.

        Args:
            time_min: Start of time range (ISO 8601).
            time_max: End of time range (ISO 8601).
            calendar_ids: List of calendar IDs to query (default: primary).

        Returns:
            FreeBusyResponse with busy time slots.
        """
        try:
            service = self._get_service()

            if calendar_ids is None:
                calendar_ids = ["primary"]

            # Validate calendar IDs
            calendar_ids = [validate_calendar_id(cid) for cid in calendar_ids]

            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": cid} for cid in calendar_ids],
            }

            result = service.freebusy().query(body=body).execute()

            calendars = []
            for cid in calendar_ids:
                cal_data = result.get("calendars", {}).get(cid, {})
                calendars.append(convert_freebusy_from_api(cid, cal_data))

            return FreeBusyResponse(
                success=True,
                time_min=time_min,
                time_max=time_max,
                calendars=calendars,
            )

        except HttpError as e:
            logger.error(f"HTTP error getting free/busy: {e}")
            return FreeBusyResponse(
                success=False,
                time_min=time_min,
                time_max=time_max,
                error=f"Google API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error getting free/busy: {e}")
            return FreeBusyResponse(
                success=False,
                time_min=time_min,
                time_max=time_max,
                error=str(e),
            )

    # -------------------------------------------------------------------------
    # Search Operations
    # -------------------------------------------------------------------------
    async def search_events(
        self,
        query: str,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 25,
    ) -> EventListResponse:
        """
        Search for events by text query.

        Args:
            query: Search terms.
            calendar_id: Calendar to search.
            time_min: Lower bound for event time.
            time_max: Upper bound for event time.
            max_results: Maximum results to return.

        Returns:
            EventListResponse with matching events.
        """
        return await self.list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            single_events=True,
            query=query,
        )
