# Google Calendar MCP Server - Implementation Plan

## Research Summary

### Official Google MCP Support
Google has announced official MCP support for several services, but **Google Calendar is NOT included**:
- **Available Now**: BigQuery, GCE, GKE, Maps Grounding Lite
- **Coming Soon**: Cloud Run, Cloud Storage, Spanner, Looker, etc.
- **Not Listed**: Google Calendar

Reference: [Google Cloud MCP Announcement](https://cloud.google.com/blog/products/ai-machine-learning/announcing-official-mcp-support-for-google-services)

### Community MCP Servers Evaluated

| Repository | Language | Stars | License | Tools | Key Features |
|------------|----------|-------|---------|-------|--------------|
| [nspady/google-calendar-mcp](https://github.com/nspady/google-calendar-mcp) | TypeScript | 865 | MIT | 12 | Multi-account, conflict detection, image-to-event, smart scheduling |
| [deciduus/calendar-mcp](https://github.com/deciduus/calendar-mcp) | Python | - | AGPL/Commercial | 13+ | FastAPI + MCP SDK, busyness analysis, mutual scheduling |
| [rsc1102/Google_Calendar_MCP](https://github.com/rsc1102/Google_Calendar_MCP) | Python | - | - | 4 | Simple CRUD, good starting point |
| [aaronsb/google-workspace-mcp](https://github.com/aaronsb/google-workspace-mcp) | TypeScript | - | - | 5 | Full Workspace (Gmail + Calendar + Drive) |
| [guinacio/mcp-google-calendar](https://github.com/guinacio/mcp-google-calendar) | Python | - | - | - | Conflict checking, timezone detection |

---

## Recommendation

**Build our own MCP server** based on:
1. **Primary reference**: `nspady/google-calendar-mcp` for feature completeness
2. **Implementation style**: Match our existing `Telegram MCP` pattern (Python, FastMCP, FastAPI, Pydantic)
3. **Inspiration**: `deciduus/calendar-mcp` for Python architecture patterns

### Rationale
- Our platform is Python-based with FastMCP pattern already established
- TypeScript implementations would require additional tooling/expertise
- AGPL license of `deciduus/calendar-mcp` is restrictive; we'll implement our own
- We can cherry-pick the best features from multiple implementations

---

## Architecture

### Directory Structure
```
MCPS/google-calendar/
├── src/
│   ├── __init__.py
│   ├── server.py           # FastMCP server + FastAPI HTTP endpoints
│   ├── client.py           # Google Calendar API client wrapper
│   ├── auth.py             # OAuth 2.0 flow handler
│   ├── models.py           # Pydantic models for events, calendars, etc.
│   └── utils.py            # Timezone handling, date parsing
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   └── test_tools.py
├── Dockerfile
├── Makefile
├── pyproject.toml
├── README.md
└── google-calendar.md      # This file
```

### Technology Stack
| Component | Technology | Notes |
|-----------|------------|-------|
| MCP Protocol | `mcp>=1.9.0` (FastMCP) | Matches Telegram MCP |
| HTTP Server | `fastapi>=0.115.0` + `uvicorn` | For direct HTTP access |
| Google API | `google-api-python-client` | Calendar API v3 |
| OAuth | `google-auth-oauthlib` | Desktop app flow |
| HTTP Client | `httpx>=0.28.0` | Async HTTP requests |
| Validation | `pydantic>=2.10.0` | Request/response models |
| Settings | `pydantic-settings>=2.6.0` | Environment config |

---

## MCP Tools Definition

### Phase 1: Core Tools (MVP)

| Tool | Description | Priority |
|------|-------------|----------|
| `list_calendars` | List all accessible calendars | P0 |
| `list_events` | Get events with date range filtering | P0 |
| `get_event` | Get specific event by ID | P0 |
| `create_event` | Create a new calendar event | P0 |
| `update_event` | Modify an existing event | P0 |
| `delete_event` | Remove an event | P0 |

### Phase 2: Enhanced Features

| Tool | Description | Priority |
|------|-------------|----------|
| `search_events` | Text-based event searching | P1 |
| `get_freebusy` | Check availability windows | P1 |
| `quick_add_event` | Natural language event creation | P1 |
| `respond_to_event` | RSVP (accept/decline/maybe) | P1 |
| `get_current_time` | Get timezone-aware current datetime | P1 |

### Phase 3: Advanced Features

| Tool | Description | Priority |
|------|-------------|----------|
| `add_attendee` | Add attendee to existing event | P2 |
| `remove_attendee` | Remove attendee from event | P2 |
| `check_conflicts` | Detect overlapping events | P2 |
| `find_available_slots` | Find open meeting times | P2 |
| `list_colors` | Get available event colors | P2 |

---

## Tool Specifications

### `list_calendars`
```python
@mcp.tool()
async def list_calendars() -> dict:
    """
    List all calendars the user has access to.

    Returns:
        Dictionary containing list of calendars with id, summary,
        primary status, and access role.
    """
```

### `list_events`
```python
@mcp.tool()
async def list_events(
    calendar_id: str = "primary",
    time_min: str | None = None,  # ISO 8601
    time_max: str | None = None,  # ISO 8601
    max_results: int = 10,
    single_events: bool = True,   # Expand recurring events
) -> dict:
    """
    List events from a calendar within a time range.

    Args:
        calendar_id: Calendar ID or "primary" for user's primary calendar.
        time_min: Lower bound (inclusive) for event start time.
        time_max: Upper bound (exclusive) for event start time.
        max_results: Maximum number of events to return.
        single_events: Whether to expand recurring events.

    Returns:
        Dictionary containing list of events with details.
    """
```

### `create_event`
```python
@mcp.tool()
async def create_event(
    summary: str,
    start_time: str,              # ISO 8601 or date
    end_time: str,                # ISO 8601 or date
    calendar_id: str = "primary",
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,  # Email addresses
    timezone: str | None = None,
    reminders: dict | None = None,
    recurrence: list[str] | None = None,  # RRULE strings
) -> dict:
    """
    Create a new calendar event.

    Args:
        summary: Event title.
        start_time: Start time in ISO 8601 format or YYYY-MM-DD for all-day.
        end_time: End time in ISO 8601 format or YYYY-MM-DD for all-day.
        calendar_id: Target calendar ID.
        description: Event description/notes.
        location: Event location.
        attendees: List of attendee email addresses.
        timezone: Timezone for the event (e.g., "America/New_York").
        reminders: Custom reminder settings.
        recurrence: Recurrence rules (RRULE format).

    Returns:
        Dictionary containing created event details.
    """
```

### `get_freebusy`
```python
@mcp.tool()
async def get_freebusy(
    time_min: str,
    time_max: str,
    calendar_ids: list[str] | None = None,
) -> dict:
    """
    Query free/busy information for calendars.

    Args:
        time_min: Start of time range (ISO 8601).
        time_max: End of time range (ISO 8601).
        calendar_ids: List of calendar IDs to query (default: primary).

    Returns:
        Dictionary with busy time slots for each calendar.
    """
```

---

## Authentication Strategy

### OAuth 2.0 Desktop App Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OAuth 2.0 Flow                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   1. User triggers auth → Server generates auth URL                 │
│                                                                     │
│   2. User visits URL → Grants permission → Google redirects         │
│      to localhost callback                                          │
│                                                                     │
│   3. Server exchanges code for tokens → Stores in secure location   │
│                                                                     │
│   4. Tokens auto-refresh on expiry                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Token Storage Options

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| Local file | Simple, portable | Security if not encrypted | Dev only |
| Environment variable | CI/CD friendly | Can't refresh | Short-lived tokens |
| Docker secret | Secure, managed | Complexity | Production |
| Database | Centralized, multi-user | Overhead | Future multi-user |

**Initial Implementation**: File-based storage with encryption at rest, path configurable via `GOOGLE_CALENDAR_TOKEN_PATH`.

### Required Scopes
```python
SCOPES = [
    "https://www.googleapis.com/auth/calendar",           # Full access
    # OR more restrictive:
    # "https://www.googleapis.com/auth/calendar.readonly",  # Read-only
    # "https://www.googleapis.com/auth/calendar.events",    # Events only
]
```

---

## Environment Variables

```env
# Google Calendar MCP Configuration
GOOGLE_CALENDAR_CLIENT_ID=<oauth-client-id>
GOOGLE_CALENDAR_CLIENT_SECRET=<oauth-client-secret>
GOOGLE_CALENDAR_TOKEN_PATH=/app/data/google_calendar_token.json
GOOGLE_CALENDAR_OAUTH_PORT=8085
GOOGLE_CALENDAR_DEFAULT_TIMEZONE=America/New_York

# Server Configuration
GOOGLE_CALENDAR_MCP_HOST=0.0.0.0
GOOGLE_CALENDAR_MCP_PORT=8084
```

---

## Docker Integration

### Dockerfile
```dockerfile
FROM python:3.14-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/

# Token storage volume
VOLUME ["/app/data"]

EXPOSE 8084

CMD ["uv", "run", "python", "-m", "src.server"]
```

### docker-compose.yml Addition
```yaml
services:
  google-calendar-mcp:
    build:
      context: ./MCPS/google-calendar
      dockerfile: Dockerfile
    container_name: google-calendar-mcp
    environment:
      - GOOGLE_CALENDAR_CLIENT_ID=${GOOGLE_CALENDAR_CLIENT_ID}
      - GOOGLE_CALENDAR_CLIENT_SECRET=${GOOGLE_CALENDAR_CLIENT_SECRET}
      - GOOGLE_CALENDAR_TOKEN_PATH=/app/data/token.json
      - GOOGLE_CALENDAR_MCP_PORT=8084
    volumes:
      - google-calendar-data:/app/data
    ports:
      - "8084:8084"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8084/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - internal

volumes:
  google-calendar-data:
```

---

## Integration with Orchestrator

### Calendar Sub-Agent
```python
# Backend/src/agents/calendar_agent.py

class CalendarAgent(BaseAgent):
    """Sub-agent for Google Calendar operations."""

    name = "calendar"
    description = "Manages Google Calendar events, scheduling, and availability"

    tools = [
        "list_calendars",
        "list_events",
        "get_event",
        "create_event",
        "update_event",
        "delete_event",
        "get_freebusy",
        "quick_add_event",
    ]
```

### Agent Registration
```python
# In Backend/src/api/main.py startup

from src.agents.calendar_agent import CalendarAgent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing code ...

    # Register Calendar Agent
    calendar_agent = CalendarAgent(
        mcp_client=GoogleCalendarMCPClient(settings.google_calendar_mcp_url)
    )
    orchestrator.register_agent(calendar_agent)

    yield
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up project structure matching Telegram MCP pattern
- [ ] Implement OAuth 2.0 flow with token storage
- [ ] Create GoogleCalendarClient wrapper class
- [ ] Implement core tools: `list_calendars`, `list_events`, `get_event`
- [ ] Add FastAPI HTTP endpoints
- [ ] Dockerfile and docker-compose integration
- [ ] Basic health check endpoint

### Phase 2: CRUD Operations (Week 2)
- [ ] Implement `create_event` with full options
- [ ] Implement `update_event` with partial updates
- [ ] Implement `delete_event` with confirmation
- [ ] Add `search_events` for text-based search
- [ ] Add `quick_add_event` for natural language input
- [ ] Unit tests for all tools

### Phase 3: Scheduling Features (Week 3)
- [ ] Implement `get_freebusy` for availability
- [ ] Add `respond_to_event` for RSVPs
- [ ] Implement `check_conflicts` for overlap detection
- [ ] Add timezone utilities
- [ ] Create CalendarAgent for orchestrator
- [ ] Integration tests

### Phase 4: Polish & Production (Week 4)
- [ ] Add attendee management tools
- [ ] Implement `find_available_slots`
- [ ] Add recurrence pattern support
- [ ] Error handling improvements
- [ ] Rate limiting and retry logic
- [ ] Documentation and README
- [ ] Production deployment configuration

---

## Security Considerations

1. **OAuth Token Security**
   - Store tokens encrypted at rest
   - Never log token values
   - Use short-lived access tokens with refresh

2. **Scope Limitation**
   - Start with minimal required scopes
   - Document why each scope is needed

3. **Input Validation**
   - Validate all calendar IDs
   - Sanitize event content
   - Validate date/time formats

4. **Rate Limiting**
   - Respect Google API quotas (1,000,000 requests/day default)
   - Implement exponential backoff
   - Cache calendar list responses

---

## Testing Strategy

### Unit Tests
```python
# tests/test_client.py
async def test_list_events_with_date_range():
    """Test event listing with date filters."""

async def test_create_event_with_attendees():
    """Test event creation with attendee list."""
```

### Integration Tests
```python
# tests/test_integration.py
async def test_full_event_lifecycle():
    """Test create → update → delete flow."""
```

### Mock Strategy
- Use `pytest-vcr` or `responses` for API mocking
- Create fixtures for common calendar/event data
- Test both success and error paths

---

## Open Questions

1. **Multi-Account Support**: Do we need multiple Google accounts? (Future consideration)
2. **Recurring Events**: Full RRULE support or simplified patterns?
3. **Webhooks**: Should we support push notifications for calendar changes?
4. **Shared Calendars**: How to handle calendars shared with the user?

---

## References

- [Google Calendar API v3 Documentation](https://developers.google.com/calendar/api/v3/reference)
- [Google OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [MCP Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [nspady/google-calendar-mcp](https://github.com/nspady/google-calendar-mcp) - Primary reference
- [deciduus/calendar-mcp](https://github.com/deciduus/calendar-mcp) - Python architecture reference
