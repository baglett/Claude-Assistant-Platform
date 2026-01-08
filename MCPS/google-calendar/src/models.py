# =============================================================================
# Google Calendar MCP Server - Pydantic Models
# =============================================================================
"""
Pydantic models for Google Calendar API data structures.

Provides type-safe models for calendars, events, and API responses.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------
class EventStatus(str, Enum):
    """Event status values."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class ResponseStatus(str, Enum):
    """Attendee response status values."""

    NEEDS_ACTION = "needsAction"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    ACCEPTED = "accepted"


class AccessRole(str, Enum):
    """Calendar access role values."""

    FREE_BUSY_READER = "freeBusyReader"
    READER = "reader"
    WRITER = "writer"
    OWNER = "owner"


# -----------------------------------------------------------------------------
# Calendar Models
# -----------------------------------------------------------------------------
class CalendarInfo(BaseModel):
    """
    Information about a calendar.

    Attributes:
        id: Calendar identifier.
        summary: Title of the calendar.
        description: Description of the calendar.
        primary: Whether this is the primary calendar.
        access_role: The effective access role.
        background_color: Calendar background color.
        foreground_color: Calendar foreground color.
        timezone: The time zone of the calendar.
    """

    id: str = Field(..., description="Calendar identifier")
    summary: str = Field(..., description="Title of the calendar")
    description: Optional[str] = Field(None, description="Description of the calendar")
    primary: bool = Field(False, description="Whether this is the primary calendar")
    access_role: AccessRole = Field(..., description="The effective access role")
    background_color: Optional[str] = Field(None, description="Background color")
    foreground_color: Optional[str] = Field(None, description="Foreground color")
    timezone: Optional[str] = Field(None, description="Calendar time zone")


class CalendarListResponse(BaseModel):
    """Response for list calendars operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    calendars: list[CalendarInfo] = Field(
        default_factory=list, description="List of calendars"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


# -----------------------------------------------------------------------------
# Event Time Models
# -----------------------------------------------------------------------------
class EventDateTime(BaseModel):
    """
    Event date/time specification.

    For all-day events, use date. For timed events, use date_time.

    Attributes:
        date: The date (YYYY-MM-DD) for all-day events.
        date_time: The datetime (ISO 8601) for timed events.
        timezone: The time zone.
    """

    date: Optional[str] = Field(None, description="Date for all-day events")
    date_time: Optional[str] = Field(None, description="DateTime for timed events")
    timezone: Optional[str] = Field(None, description="Time zone")


# -----------------------------------------------------------------------------
# Attendee Models
# -----------------------------------------------------------------------------
class Attendee(BaseModel):
    """
    Event attendee information.

    Attributes:
        email: The attendee's email address.
        display_name: The attendee's name.
        response_status: The attendee's response status.
        organizer: Whether the attendee is the organizer.
        optional: Whether attendance is optional.
    """

    email: str = Field(..., description="Attendee email address")
    display_name: Optional[str] = Field(None, description="Attendee display name")
    response_status: ResponseStatus = Field(
        ResponseStatus.NEEDS_ACTION, description="Response status"
    )
    organizer: bool = Field(False, description="Whether this is the organizer")
    optional: bool = Field(False, description="Whether attendance is optional")


# -----------------------------------------------------------------------------
# Event Models
# -----------------------------------------------------------------------------
class EventInfo(BaseModel):
    """
    Information about a calendar event.

    Attributes:
        id: Event identifier.
        summary: Title of the event.
        description: Description of the event.
        location: Location of the event.
        start: Start time of the event.
        end: End time of the event.
        status: Status of the event.
        html_link: URL link to the event in Google Calendar.
        created: Creation time.
        updated: Last modification time.
        creator_email: Email of the event creator.
        organizer_email: Email of the event organizer.
        attendees: List of attendees.
        recurrence: Recurrence rules.
        recurring_event_id: ID of the recurring event this is part of.
        calendar_id: The calendar this event belongs to.
    """

    id: str = Field(..., description="Event identifier")
    summary: Optional[str] = Field(None, description="Title of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    location: Optional[str] = Field(None, description="Location of the event")
    start: EventDateTime = Field(..., description="Start time")
    end: EventDateTime = Field(..., description="End time")
    status: EventStatus = Field(EventStatus.CONFIRMED, description="Event status")
    html_link: Optional[str] = Field(None, description="URL to event in Calendar")
    created: Optional[str] = Field(None, description="Creation timestamp")
    updated: Optional[str] = Field(None, description="Last update timestamp")
    creator_email: Optional[str] = Field(None, description="Creator email")
    organizer_email: Optional[str] = Field(None, description="Organizer email")
    attendees: list[Attendee] = Field(default_factory=list, description="Attendees")
    recurrence: list[str] = Field(
        default_factory=list, description="Recurrence rules (RRULE)"
    )
    recurring_event_id: Optional[str] = Field(
        None, description="Parent recurring event ID"
    )
    calendar_id: Optional[str] = Field(None, description="Calendar ID")


class EventListResponse(BaseModel):
    """Response for list events operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    events: list[EventInfo] = Field(default_factory=list, description="List of events")
    next_page_token: Optional[str] = Field(None, description="Token for next page")
    error: Optional[str] = Field(None, description="Error message if failed")


class EventResponse(BaseModel):
    """Response for single event operations."""

    success: bool = Field(..., description="Whether the operation succeeded")
    event: Optional[EventInfo] = Field(None, description="Event details")
    error: Optional[str] = Field(None, description="Error message if failed")


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------
class CreateEventRequest(BaseModel):
    """Request model for creating an event."""

    summary: str = Field(..., description="Event title")
    start_time: str = Field(..., description="Start time (ISO 8601 or YYYY-MM-DD)")
    end_time: str = Field(..., description="End time (ISO 8601 or YYYY-MM-DD)")
    calendar_id: str = Field("primary", description="Target calendar ID")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    attendees: Optional[list[str]] = Field(None, description="Attendee emails")
    timezone: Optional[str] = Field(None, description="Event timezone")
    recurrence: Optional[list[str]] = Field(None, description="Recurrence rules")


class UpdateEventRequest(BaseModel):
    """Request model for updating an event."""

    event_id: str = Field(..., description="Event ID to update")
    calendar_id: str = Field("primary", description="Calendar ID")
    summary: Optional[str] = Field(None, description="New event title")
    description: Optional[str] = Field(None, description="New description")
    location: Optional[str] = Field(None, description="New location")
    start_time: Optional[str] = Field(None, description="New start time")
    end_time: Optional[str] = Field(None, description="New end time")
    timezone: Optional[str] = Field(None, description="New timezone")


class DeleteEventRequest(BaseModel):
    """Request model for deleting an event."""

    event_id: str = Field(..., description="Event ID to delete")
    calendar_id: str = Field("primary", description="Calendar ID")
    send_updates: str = Field(
        "none", description="Whether to send updates: 'all', 'externalOnly', 'none'"
    )


# -----------------------------------------------------------------------------
# Free/Busy Models
# -----------------------------------------------------------------------------
class TimePeriod(BaseModel):
    """A time period with start and end."""

    start: str = Field(..., description="Start time (ISO 8601)")
    end: str = Field(..., description="End time (ISO 8601)")


class CalendarFreeBusy(BaseModel):
    """Free/busy information for a calendar."""

    calendar_id: str = Field(..., description="Calendar identifier")
    busy: list[TimePeriod] = Field(default_factory=list, description="Busy periods")
    errors: list[str] = Field(default_factory=list, description="Any errors")


class FreeBusyResponse(BaseModel):
    """Response for free/busy query."""

    success: bool = Field(..., description="Whether the operation succeeded")
    time_min: str = Field(..., description="Start of query range")
    time_max: str = Field(..., description="End of query range")
    calendars: list[CalendarFreeBusy] = Field(
        default_factory=list, description="Free/busy info per calendar"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


# -----------------------------------------------------------------------------
# Generic Response Models
# -----------------------------------------------------------------------------
class OperationResponse(BaseModel):
    """Generic response for operations without specific return data."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: Optional[str] = Field(None, description="Success or status message")
    error: Optional[str] = Field(None, description="Error message if failed")
