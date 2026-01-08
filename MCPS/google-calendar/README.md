# Google Calendar MCP Server

MCP server providing Google Calendar API tools for the Claude Assistant Platform.

## Features

- **Calendar Management**: List all accessible calendars
- **Event Operations**: Create, read, update, and delete events
- **Search**: Find events by text query
- **Quick Add**: Create events using natural language
- **Free/Busy**: Query availability across calendars
- **Timezone Support**: Full timezone handling

## Tools

| Tool | Description |
|------|-------------|
| `check_auth_status` | Check OAuth authentication status |
| `get_auth_url` | Get OAuth authorization URL |
| `list_calendars` | List all accessible calendars |
| `list_events` | List events with date filtering |
| `get_event` | Get specific event by ID |
| `create_event` | Create a new event |
| `update_event` | Update an existing event |
| `delete_event` | Delete an event |
| `quick_add_event` | Create event via natural language |
| `search_events` | Search events by text |
| `get_freebusy` | Query free/busy information |
| `get_current_time` | Get current time in timezone |

## Setup

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the **Google Calendar API**
4. Go to **APIs & Services** > **Credentials**
5. Create **OAuth 2.0 Client ID** (Desktop application type)
6. Download the credentials

### 2. Environment Variables

```env
# Required
GOOGLE_CALENDAR_CLIENT_ID=your-client-id
GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret

# Optional
GOOGLE_CALENDAR_TOKEN_PATH=./data/token.json
GOOGLE_CALENDAR_OAUTH_PORT=8085
GOOGLE_CALENDAR_DEFAULT_TIMEZONE=America/New_York
GOOGLE_CALENDAR_MCP_HOST=0.0.0.0
GOOGLE_CALENDAR_MCP_PORT=8084
```

### 3. First-Time Authentication

Run the server and trigger authentication:

```bash
# Local development
uv sync
uv run python -m src.server

# Then call the authenticate endpoint or use the auth URL
curl http://localhost:8084/auth/url
```

Visit the returned URL in a browser to complete OAuth flow.

## Development

```bash
# Install dependencies
make dev

# Run server
make run

# Run tests
make test

# Lint code
make lint
```

## Docker

```bash
# Build image
make docker-build

# Run container
docker run -p 8084:8084 \
  -e GOOGLE_CALENDAR_CLIENT_ID=$GOOGLE_CALENDAR_CLIENT_ID \
  -e GOOGLE_CALENDAR_CLIENT_SECRET=$GOOGLE_CALENDAR_CLIENT_SECRET \
  -v google-calendar-data:/app/data \
  google-calendar-mcp
```

## API Endpoints

### Health Check
```
GET /health
```

### Authentication
```
GET /auth/status     # Check auth status
GET /auth/url        # Get OAuth URL
POST /auth/authenticate  # Trigger OAuth flow
```

### Calendars
```
GET /calendars       # List all calendars
```

### Events
```
GET /events          # List events
GET /events/{id}     # Get specific event
POST /events         # Create event
PATCH /events/{id}   # Update event
DELETE /events/{id}  # Delete event
POST /events/quick-add  # Quick add via natural language
```

### Free/Busy
```
POST /freebusy       # Query availability
```

## License

MIT
