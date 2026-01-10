# =============================================================================
# Google Calendar Agent
# =============================================================================
"""
Specialized agent for Google Calendar management.

The GoogleCalendarAgent handles all Google Calendar-related operations including
listing calendars, creating/updating/deleting events, searching, and querying
free/busy information. It communicates with the Google Calendar MCP server via HTTP.

Usage:
    from src.agents.google_calendar_agent import GoogleCalendarAgent

    agent = GoogleCalendarAgent(
        api_key=api_key,
        mcp_url="http://google-calendar-mcp:8084"
    )
    result = await agent.execute(context)
"""

import json
import logging
import time
from typing import Any

import anthropic
import httpx

from src.agents.base import AgentContext, AgentResult, BaseAgent
from src.database import AgentExecution
from src.services.agent_execution_service import AgentExecutionService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Google Calendar Agent System Prompt
# -----------------------------------------------------------------------------
GOOGLE_CALENDAR_AGENT_SYSTEM_PROMPT = """You are the Google Calendar Agent for the Claude Assistant Platform.

Your responsibility is managing calendars and events in Google Calendar.

## Available Tools:

### Authentication
- **calendar_check_auth_status**: Check if authenticated with Google Calendar
- **calendar_get_auth_url**: Get OAuth URL for authentication (if needed)

### Calendars
- **calendar_list_calendars**: List all accessible calendars

### Events
- **calendar_list_events**: List events with optional date range and search
- **calendar_get_event**: Get a specific event by ID
- **calendar_create_event**: Create a new calendar event
- **calendar_update_event**: Update an existing event
- **calendar_delete_event**: Delete an event
- **calendar_quick_add**: Create event using natural language (e.g., "Meeting tomorrow at 3pm")
- **calendar_search_events**: Search for events by text query

### Scheduling
- **calendar_get_freebusy**: Query free/busy information for scheduling
- **calendar_get_current_time**: Get current time in a timezone

## Date/Time Format:
- Use ISO 8601 format: "2024-01-15T10:00:00" or "2024-01-15" for all-day events
- Always include timezone when relevant (e.g., "America/New_York")

## Important Notes:
1. Always check auth status first if operations fail with 401
2. Use "primary" as calendar_id for the user's main calendar
3. For recurring events, use RRULE format (e.g., "RRULE:FREQ=WEEKLY;COUNT=10")
4. Be concise and confirm actions taken

## Workflow Tips:
- To schedule a meeting: Use create_event with start_time, end_time, and attendees
- To find a free slot: Use get_freebusy to check availability
- For quick scheduling: Use quick_add with natural language
- To reschedule: Use update_event with new times"""


# -----------------------------------------------------------------------------
# Google Calendar Agent Tool Definitions
# -----------------------------------------------------------------------------
GOOGLE_CALENDAR_TOOLS = [
    # Authentication Tools
    {
        "name": "calendar_check_auth_status",
        "description": "Check if authenticated with Google Calendar. Use this first if operations fail.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "calendar_get_auth_url",
        "description": "Get the OAuth authorization URL if authentication is needed.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # Calendar Tools
    {
        "name": "calendar_list_calendars",
        "description": "List all calendars the user has access to.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # Event Tools
    {
        "name": "calendar_list_events",
        "description": "List events from a calendar within a time range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID or 'primary' for main calendar. Default: 'primary'.",
                },
                "time_min": {
                    "type": "string",
                    "description": "Start of time range (ISO 8601). Defaults to now.",
                },
                "time_max": {
                    "type": "string",
                    "description": "End of time range (ISO 8601). Defaults to 7 days from now.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum events to return. Default: 10.",
                },
                "query": {
                    "type": "string",
                    "description": "Optional text to search in event titles/descriptions.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "calendar_get_event",
        "description": "Get a specific calendar event by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "The event identifier.",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Default: 'primary'.",
                },
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "calendar_create_event",
        "description": "Create a new calendar event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Event title.",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time (ISO 8601) or YYYY-MM-DD for all-day.",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time (ISO 8601) or YYYY-MM-DD for all-day.",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Target calendar ID. Default: 'primary'.",
                },
                "description": {
                    "type": "string",
                    "description": "Event description/notes.",
                },
                "location": {
                    "type": "string",
                    "description": "Event location.",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses.",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone (e.g., 'America/New_York').",
                },
                "recurrence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Recurrence rules in RRULE format.",
                },
            },
            "required": ["summary", "start_time", "end_time"],
        },
    },
    {
        "name": "calendar_update_event",
        "description": "Update an existing calendar event. Only provided fields are changed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "The event ID to update.",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Default: 'primary'.",
                },
                "summary": {
                    "type": "string",
                    "description": "New event title.",
                },
                "description": {
                    "type": "string",
                    "description": "New description.",
                },
                "location": {
                    "type": "string",
                    "description": "New location.",
                },
                "start_time": {
                    "type": "string",
                    "description": "New start time (ISO 8601).",
                },
                "end_time": {
                    "type": "string",
                    "description": "New end time (ISO 8601).",
                },
                "timezone": {
                    "type": "string",
                    "description": "New timezone.",
                },
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "calendar_delete_event",
        "description": "Delete a calendar event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "The event ID to delete.",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID. Default: 'primary'.",
                },
                "send_updates": {
                    "type": "string",
                    "enum": ["all", "externalOnly", "none"],
                    "description": "Whether to send cancellation notices. Default: 'none'.",
                },
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "calendar_quick_add",
        "description": "Create an event using natural language text. Google parses the text automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Natural language event description (e.g., 'Meeting with John tomorrow at 3pm').",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Target calendar ID. Default: 'primary'.",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "calendar_search_events",
        "description": "Search for events by text query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms to match in event titles/descriptions.",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar to search. Default: 'primary'.",
                },
                "time_min": {
                    "type": "string",
                    "description": "Start of time range (ISO 8601).",
                },
                "time_max": {
                    "type": "string",
                    "description": "End of time range (ISO 8601).",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results. Default: 25.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "calendar_get_freebusy",
        "description": "Query free/busy information to find available time slots.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {
                    "type": "string",
                    "description": "Start of time range (ISO 8601).",
                },
                "time_max": {
                    "type": "string",
                    "description": "End of time range (ISO 8601).",
                },
                "calendar_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Calendar IDs to query. Default: ['primary'].",
                },
            },
            "required": ["time_min", "time_max"],
        },
    },
    {
        "name": "calendar_get_current_time",
        "description": "Get the current date and time in a specified timezone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Timezone (e.g., 'America/New_York'). Uses server default if not specified.",
                },
            },
            "required": [],
        },
    },
]


# -----------------------------------------------------------------------------
# Tool Name to MCP Endpoint Mapping
# -----------------------------------------------------------------------------
CALENDAR_TOOL_TO_MCP = {
    "calendar_check_auth_status": ("GET", "/auth/status"),
    "calendar_get_auth_url": ("GET", "/auth/url"),
    "calendar_list_calendars": ("GET", "/calendars"),
    "calendar_list_events": ("GET", "/events"),
    "calendar_get_event": ("GET", "/events/{event_id}"),
    "calendar_create_event": ("POST", "/events"),
    "calendar_update_event": ("PATCH", "/events/{event_id}"),
    "calendar_delete_event": ("DELETE", "/events/{event_id}"),
    "calendar_quick_add": ("POST", "/events/quick-add"),
    "calendar_search_events": ("GET", "/events"),  # Uses query param
    "calendar_get_freebusy": ("POST", "/freebusy"),
    "calendar_get_current_time": ("GET", "/time"),  # Custom endpoint
}


# -----------------------------------------------------------------------------
# Google Calendar Agent Class
# -----------------------------------------------------------------------------
class GoogleCalendarAgent(BaseAgent):
    """
    Specialized agent for Google Calendar management.

    Communicates with the Google Calendar MCP server via HTTP to manage
    calendars, events, and scheduling.

    Attributes:
        client: Anthropic API client.
        model: Claude model to use.
        mcp_url: URL of the Google Calendar MCP server.
        http_client: Async HTTP client for MCP calls.

    Example:
        agent = GoogleCalendarAgent(
            api_key="sk-...",
            mcp_url="http://google-calendar-mcp:8084"
        )
        context = AgentContext(
            chat_id=chat_uuid,
            task="Schedule a meeting with John tomorrow at 2pm",
            session=session,
        )
        result = await agent.execute(context)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        mcp_url: str = "http://google-calendar-mcp:8084",
    ):
        """
        Initialize the Google Calendar Agent.

        Args:
            api_key: Anthropic API key.
            model: Claude model to use.
            mcp_url: URL of the Google Calendar MCP server.
        """
        super().__init__(api_key=api_key, model=model)
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.mcp_url = mcp_url.rstrip("/")
        self._http_client: httpx.AsyncClient | None = None

        # Token tracking for execution logging
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

    @property
    def name(self) -> str:
        """Agent identifier."""
        return "calendar"

    @property
    def description(self) -> str:
        """Agent description."""
        return "Manages Google Calendar events, scheduling, and availability"

    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create the async HTTP client for MCP calls.

        Returns:
            The httpx.AsyncClient instance.
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def _execute_task(
        self,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> AgentResult:
        """
        Execute the Google Calendar management task.

        Uses Claude's tool calling to determine and execute the appropriate
        Calendar operations based on the task description.

        Args:
            context: Execution context with task and chat info.
            execution_service: Service for logging execution details.
            execution: Current execution record.

        Returns:
            AgentResult with the outcome.
        """
        if not self.client:
            return AgentResult(
                success=False,
                message="API client not initialized",
                error="No API key provided",
            )

        # Reset token counters
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

        # Build messages for Claude
        messages = self._build_messages(context)

        # Log initial thinking
        await self.log_thinking(
            execution_service,
            execution,
            f"Processing Google Calendar task: {context.task}\n"
            f"MCP URL: {self.mcp_url}",
        )

        # Process with tool calling loop
        try:
            result_text = await self._process_with_tools(
                messages=messages,
                context=context,
                execution_service=execution_service,
                execution=execution,
            )

            return AgentResult(
                success=True,
                message=result_text,
            )

        except Exception as e:
            logger.error(f"GoogleCalendarAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                message=f"Failed to process Calendar request: {str(e)}",
                error=str(e),
            )

    def _build_messages(self, context: AgentContext) -> list[dict[str, Any]]:
        """
        Build the message list for Claude.

        Args:
            context: The agent context.

        Returns:
            List of messages in Claude format.
        """
        messages = []

        # Add recent conversation context (limit to avoid token overflow)
        for msg in context.recent_messages[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add the current task as the final user message
        messages.append({
            "role": "user",
            "content": context.task,
        })

        return messages

    async def _process_with_tools(
        self,
        messages: list[dict[str, Any]],
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
        max_iterations: int = 10,
    ) -> str:
        """
        Process the task with tool calling loop.

        Args:
            messages: Conversation messages.
            context: Agent context.
            execution_service: For logging.
            execution: Current execution.
            max_iterations: Max tool call iterations.

        Returns:
            Final response text.
        """
        working_messages = list(messages)

        for iteration in range(max_iterations):
            logger.debug(f"GoogleCalendarAgent tool loop iteration {iteration + 1}")

            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=GOOGLE_CALENDAR_AGENT_SYSTEM_PROMPT,
                tools=GOOGLE_CALENDAR_TOOLS,
                messages=working_messages,
            )

            # Track tokens
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._llm_calls += 1

            # Check stop reason
            if response.stop_reason == "end_turn":
                return self._extract_text(response)

            elif response.stop_reason == "tool_use":
                # Process tool calls
                await self.log_thinking(
                    execution_service,
                    execution,
                    f"Iteration {iteration + 1}: Processing Calendar tool calls",
                )

                # Add assistant response to messages
                working_messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Execute tools and get results
                tool_results = await self._execute_tools(
                    response.content,
                    context,
                    execution_service,
                    execution,
                )

                # Add tool results to messages
                working_messages.append({
                    "role": "user",
                    "content": tool_results,
                })

            else:
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                return self._extract_text(response)

        return "Max iterations reached. Please try a simpler request."

    async def _execute_tools(
        self,
        content_blocks: list,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> list[dict[str, Any]]:
        """
        Execute tool calls from Claude's response.

        Args:
            content_blocks: Response content blocks.
            context: Agent context.
            execution_service: For logging.
            execution: Current execution.

        Returns:
            List of tool result blocks.
        """
        tool_results = []

        for block in content_blocks:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            logger.info(f"GoogleCalendarAgent executing tool: {tool_name}")
            start_time = time.time()

            try:
                # Execute the tool via Calendar MCP
                result = await self._call_calendar_mcp(tool_name, tool_input)

                duration_ms = int((time.time() - start_time) * 1000)

                # Log the tool call
                await self.log_tool_call(
                    execution_service,
                    execution,
                    tool_name=tool_name,
                    input_data=tool_input,
                    output_data=result,
                    duration_ms=duration_ms,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")

                duration_ms = int((time.time() - start_time) * 1000)

                await self.log_tool_call(
                    execution_service,
                    execution,
                    tool_name=tool_name,
                    input_data=tool_input,
                    error=str(e),
                    duration_ms=duration_ms,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"success": False, "error": str(e)}),
                    "is_error": True,
                })

        return tool_results

    async def _call_calendar_mcp(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a Google Calendar MCP tool via HTTP.

        Maps agent tool names to MCP HTTP endpoints.

        Args:
            tool_name: Name of the Calendar tool to call.
            tool_input: Tool input parameters.

        Returns:
            Tool execution result from MCP server.
        """
        client = await self._get_http_client()

        try:
            # Map tool to HTTP method and endpoint
            if tool_name == "calendar_check_auth_status":
                response = await client.get(f"{self.mcp_url}/auth/status")

            elif tool_name == "calendar_get_auth_url":
                response = await client.get(f"{self.mcp_url}/auth/url")

            elif tool_name == "calendar_list_calendars":
                response = await client.get(f"{self.mcp_url}/calendars")

            elif tool_name == "calendar_list_events":
                params = {k: v for k, v in tool_input.items() if v is not None}
                response = await client.get(f"{self.mcp_url}/events", params=params)

            elif tool_name == "calendar_get_event":
                event_id = tool_input.get("event_id")
                calendar_id = tool_input.get("calendar_id", "primary")
                response = await client.get(
                    f"{self.mcp_url}/events/{event_id}",
                    params={"calendar_id": calendar_id},
                )

            elif tool_name == "calendar_create_event":
                response = await client.post(
                    f"{self.mcp_url}/events",
                    json=tool_input,
                )

            elif tool_name == "calendar_update_event":
                event_id = tool_input.pop("event_id")
                response = await client.patch(
                    f"{self.mcp_url}/events/{event_id}",
                    json=tool_input,
                )

            elif tool_name == "calendar_delete_event":
                event_id = tool_input.get("event_id")
                calendar_id = tool_input.get("calendar_id", "primary")
                send_updates = tool_input.get("send_updates", "none")
                response = await client.delete(
                    f"{self.mcp_url}/events/{event_id}",
                    params={"calendar_id": calendar_id, "send_updates": send_updates},
                )

            elif tool_name == "calendar_quick_add":
                text = tool_input.get("text")
                calendar_id = tool_input.get("calendar_id", "primary")
                response = await client.post(
                    f"{self.mcp_url}/events/quick-add",
                    params={"text": text, "calendar_id": calendar_id},
                )

            elif tool_name == "calendar_search_events":
                params = {k: v for k, v in tool_input.items() if v is not None}
                response = await client.get(f"{self.mcp_url}/events", params=params)

            elif tool_name == "calendar_get_freebusy":
                response = await client.post(
                    f"{self.mcp_url}/freebusy",
                    params=tool_input,
                )

            elif tool_name == "calendar_get_current_time":
                # This tool returns current time - MCP may not have this endpoint
                # We'll call the health endpoint and include time info
                timezone = tool_input.get("timezone")
                if timezone:
                    response = await client.get(
                        f"{self.mcp_url}/health",
                        params={"timezone": timezone},
                    )
                else:
                    response = await client.get(f"{self.mcp_url}/health")

                # Return time info from health or construct it
                data = response.json()
                if "datetime" not in data:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo

                    tz = ZoneInfo(timezone or "UTC")
                    now = datetime.now(tz)
                    return {
                        "success": True,
                        "datetime": now.isoformat(),
                        "timezone": str(tz),
                    }
                return data

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Calendar MCP HTTP error: {e.response.status_code}")
            error_detail = ""
            try:
                error_detail = e.response.text
            except Exception:
                pass
            return {
                "success": False,
                "error": f"Calendar MCP error: {e.response.status_code}",
                "detail": error_detail,
            }

        except httpx.RequestError as e:
            logger.error(f"Calendar MCP request error: {e}")
            return {
                "success": False,
                "error": f"Failed to connect to Calendar MCP: {e}",
            }

    def _extract_text(self, response) -> str:
        """Extract text from Claude response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts)
