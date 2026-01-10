# =============================================================================
# Google Calendar MCP Server - Utilities
# =============================================================================
"""
Utility functions for the Google Calendar MCP server.

Provides helpers for timezone handling, date parsing, and data conversion.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from .models import (
    AccessRole,
    Attendee,
    CalendarFreeBusy,
    CalendarInfo,
    EventDateTime,
    EventInfo,
    EventStatus,
    ResponseStatus,
    TimePeriod,
)


# -----------------------------------------------------------------------------
# Date/Time Utilities
# -----------------------------------------------------------------------------
def parse_datetime(dt_string: str, default_tz: str = "UTC") -> datetime:
    """
    Parse a datetime string to a datetime object.

    Handles ISO 8601 format with or without timezone.

    Args:
        dt_string: DateTime string to parse.
        default_tz: Default timezone if none specified.

    Returns:
        Parsed datetime object.
    """
    # Try parsing with timezone
    try:
        return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
    except ValueError:
        pass

    # Try parsing without timezone and add default
    try:
        dt = datetime.fromisoformat(dt_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(default_tz))
        return dt
    except ValueError:
        pass

    # Try parsing as date only
    try:
        return datetime.strptime(dt_string, "%Y-%m-%d").replace(
            tzinfo=ZoneInfo(default_tz)
        )
    except ValueError:
        raise ValueError(f"Unable to parse datetime: {dt_string}")


def format_datetime_for_api(
    dt_string: str,
    timezone_str: Optional[str] = None,
) -> dict[str, str]:
    """
    Format a datetime string for the Google Calendar API.

    Args:
        dt_string: DateTime string (ISO 8601 or YYYY-MM-DD).
        timezone_str: Optional timezone identifier.

    Returns:
        Dictionary with either 'date' or 'dateTime' and 'timeZone'.
    """
    # Check if this is a date-only string (all-day event)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", dt_string):
        return {"date": dt_string}

    # It's a datetime string
    result = {"dateTime": dt_string}
    if timezone_str:
        result["timeZone"] = timezone_str

    return result


def get_current_time(timezone_str: str = "UTC") -> datetime:
    """
    Get current time in the specified timezone.

    Args:
        timezone_str: Timezone identifier (e.g., "America/New_York").

    Returns:
        Current datetime in the specified timezone.
    """
    return datetime.now(ZoneInfo(timezone_str))


def get_time_range(
    days_ahead: int = 7,
    timezone_str: str = "UTC",
) -> tuple[str, str]:
    """
    Get a time range from now to a number of days ahead.

    Args:
        days_ahead: Number of days to look ahead.
        timezone_str: Timezone for the range.

    Returns:
        Tuple of (time_min, time_max) in ISO 8601 format.
    """
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    future = now + timedelta(days=days_ahead)

    return (now.isoformat(), future.isoformat())


# -----------------------------------------------------------------------------
# Data Conversion Utilities
# -----------------------------------------------------------------------------
def convert_calendar_from_api(api_calendar: dict[str, Any]) -> CalendarInfo:
    """
    Convert Google Calendar API calendar data to CalendarInfo model.

    Args:
        api_calendar: Calendar data from Google API.

    Returns:
        CalendarInfo model instance.
    """
    return CalendarInfo(
        id=api_calendar["id"],
        summary=api_calendar.get("summary", ""),
        description=api_calendar.get("description"),
        primary=api_calendar.get("primary", False),
        access_role=AccessRole(api_calendar.get("accessRole", "reader")),
        background_color=api_calendar.get("backgroundColor"),
        foreground_color=api_calendar.get("foregroundColor"),
        timezone=api_calendar.get("timeZone"),
    )


def convert_event_datetime_from_api(
    api_datetime: dict[str, Any],
) -> EventDateTime:
    """
    Convert Google Calendar API datetime to EventDateTime model.

    Args:
        api_datetime: DateTime data from Google API.

    Returns:
        EventDateTime model instance.
    """
    return EventDateTime(
        date=api_datetime.get("date"),
        date_time=api_datetime.get("dateTime"),
        timezone=api_datetime.get("timeZone"),
    )


def convert_attendee_from_api(api_attendee: dict[str, Any]) -> Attendee:
    """
    Convert Google Calendar API attendee to Attendee model.

    Args:
        api_attendee: Attendee data from Google API.

    Returns:
        Attendee model instance.
    """
    return Attendee(
        email=api_attendee["email"],
        display_name=api_attendee.get("displayName"),
        response_status=ResponseStatus(
            api_attendee.get("responseStatus", "needsAction")
        ),
        organizer=api_attendee.get("organizer", False),
        optional=api_attendee.get("optional", False),
    )


def convert_event_from_api(
    api_event: dict[str, Any],
    calendar_id: Optional[str] = None,
) -> EventInfo:
    """
    Convert Google Calendar API event to EventInfo model.

    Args:
        api_event: Event data from Google API.
        calendar_id: Optional calendar ID to include.

    Returns:
        EventInfo model instance.
    """
    # Convert attendees
    attendees = [
        convert_attendee_from_api(a) for a in api_event.get("attendees", [])
    ]

    # Get creator and organizer emails
    creator_email = api_event.get("creator", {}).get("email")
    organizer_email = api_event.get("organizer", {}).get("email")

    return EventInfo(
        id=api_event["id"],
        summary=api_event.get("summary"),
        description=api_event.get("description"),
        location=api_event.get("location"),
        start=convert_event_datetime_from_api(api_event.get("start", {})),
        end=convert_event_datetime_from_api(api_event.get("end", {})),
        status=EventStatus(api_event.get("status", "confirmed")),
        html_link=api_event.get("htmlLink"),
        created=api_event.get("created"),
        updated=api_event.get("updated"),
        creator_email=creator_email,
        organizer_email=organizer_email,
        attendees=attendees,
        recurrence=api_event.get("recurrence", []),
        recurring_event_id=api_event.get("recurringEventId"),
        calendar_id=calendar_id,
    )


def convert_freebusy_from_api(
    calendar_id: str,
    api_freebusy: dict[str, Any],
) -> CalendarFreeBusy:
    """
    Convert Google Calendar API free/busy data to model.

    Args:
        calendar_id: The calendar identifier.
        api_freebusy: Free/busy data from Google API.

    Returns:
        CalendarFreeBusy model instance.
    """
    busy_periods = [
        TimePeriod(start=period["start"], end=period["end"])
        for period in api_freebusy.get("busy", [])
    ]

    errors = [str(e) for e in api_freebusy.get("errors", [])]

    return CalendarFreeBusy(
        calendar_id=calendar_id,
        busy=busy_periods,
        errors=errors,
    )


# -----------------------------------------------------------------------------
# Validation Utilities
# -----------------------------------------------------------------------------
def validate_calendar_id(calendar_id: str) -> str:
    """
    Validate and normalize a calendar ID.

    Args:
        calendar_id: Calendar ID to validate.

    Returns:
        Normalized calendar ID.

    Raises:
        ValueError: If calendar ID is invalid.
    """
    if not calendar_id:
        raise ValueError("Calendar ID cannot be empty")

    # Normalize common shortcuts
    if calendar_id.lower() in ("primary", "me", "default"):
        return "primary"

    return calendar_id.strip()


def validate_event_id(event_id: str) -> str:
    """
    Validate and normalize an event ID.

    Args:
        event_id: Event ID to validate.

    Returns:
        Normalized event ID.

    Raises:
        ValueError: If event ID is invalid.
    """
    if not event_id:
        raise ValueError("Event ID cannot be empty")

    return event_id.strip()
