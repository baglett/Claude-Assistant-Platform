# Motion MCP Server

MCP (Model Context Protocol) server providing Motion API tools for the Claude Assistant Platform.

## Overview

This service exposes Motion's AI-powered task and project management API as MCP tools that can be called by AI assistants. It enables natural language interaction with Motion for:

- **Task Management**: Create, update, delete, move, and list tasks
- **Project Management**: Create and list projects
- **Workspace Management**: List accessible workspaces
- **User Management**: List users and get current user info
- **Rate Limit Monitoring**: Check API usage to prevent overuse

## Features

### MCP Tools (14 Total)

| Tool | Description |
|------|-------------|
| `motion_list_tasks` | List tasks with optional filters (workspace, project, assignee, status) |
| `motion_get_task` | Get a specific task by ID |
| `motion_create_task` | Create a new task with name, due date, priority, etc. |
| `motion_update_task` | Update an existing task |
| `motion_delete_task` | Delete a task permanently |
| `motion_move_task` | Move a task to a different workspace/project |
| `motion_unassign_task` | Remove the assignee from a task |
| `motion_list_projects` | List projects with optional workspace filter |
| `motion_get_project` | Get a specific project by ID |
| `motion_create_project` | Create a new project |
| `motion_list_workspaces` | List all accessible workspaces |
| `motion_list_users` | List users in a workspace |
| `motion_get_current_user` | Get the current authenticated user |
| `motion_get_rate_limit_status` | Check rate limit status |

### Rate Limiting (CRITICAL)

Motion enforces strict API rate limits. **Exceeding these limits can result in account suspension.**

| Account Type | Limit |
|--------------|-------|
| Individual | 12 requests per minute |
| Team | 120 requests per minute |
| Enterprise | Custom (contact Motion) |

This server implements robust rate limiting with:

- **Token bucket algorithm** with sliding window
- **SQLite persistence** - rate limit state survives restarts
- **Automatic enforcement** - requests are blocked before exceeding limits
- **Clear error messages** with wait time information
- **Configurable limits** via environment variables

## Requirements

- Python 3.12+
- Motion API key (get from [Motion Settings](https://app.usemotion.com/web/settings/api))

## Installation

```powershell
# Navigate to the motion MCP directory
cd MCPS/motion

# Install dependencies using uv
make install
# OR
uv sync
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
# Required
MOTION_API_KEY=your-api-key-here

# Rate limiting (adjust based on your account type)
MOTION_ACCOUNT_TYPE=individual  # individual | team | enterprise

# Optional overrides
MOTION_RATE_LIMIT_OVERRIDE=0    # 0 = use default
MOTION_RATE_LIMIT_WINDOW=60     # Window in seconds
MOTION_RATE_LIMIT_DB=motion_rate_limit.db

# Server settings
HOST=0.0.0.0
PORT=8081
LOG_LEVEL=INFO
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MOTION_API_KEY` | Your Motion API key | Required |
| `MOTION_ACCOUNT_TYPE` | Account type for rate limits | `individual` |
| `MOTION_RATE_LIMIT_OVERRIDE` | Custom rate limit (0=default) | `0` |
| `MOTION_RATE_LIMIT_WINDOW` | Rate limit window (seconds) | `60` |
| `MOTION_RATE_LIMIT_DB` | SQLite DB path for persistence | `motion_rate_limit.db` |
| `MOTION_API_BASE_URL` | Motion API base URL | `https://api.usemotion.com/v1` |
| `MOTION_REQUEST_TIMEOUT` | Request timeout (seconds) | `30` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8081` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Usage

### Running the Server

```powershell
# Development mode (with hot-reload)
make dev

# Production mode
make run

# Or directly with uv
uv run motion-mcp
```

The server runs on port 8081 by default.

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and configuration status |
| `/rate-limit` | GET | Current rate limit status |

### Example: Check Health

```bash
curl http://localhost:8081/health
```

Response:
```json
{
  "status": "healthy",
  "service": "motion-mcp",
  "api_configured": true,
  "rate_limit_type": "individual"
}
```

### Example: Check Rate Limit

```bash
curl http://localhost:8081/rate-limit
```

Response:
```json
{
  "success": true,
  "max_requests": 12,
  "window_seconds": 60,
  "remaining_requests": 10,
  "can_proceed": true,
  "wait_seconds": 0
}
```

## Tool Reference

### Task Tools

#### `motion_list_tasks`

List tasks with optional filters.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace_id` | string | No | Filter by workspace ID |
| `project_id` | string | No | Filter by project ID |
| `assignee_id` | string | No | Filter by assignee user ID |
| `status` | string | No | Filter by status (e.g., "To Do", "In Progress", "Done") |

**Response:** `{ success, tasks[], count }`

---

#### `motion_get_task`

Get a specific task by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | The unique task identifier |

**Response:** `{ success, task }`

---

#### `motion_create_task`

Create a new task in Motion.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Task name/title |
| `workspace_id` | string | Yes | Workspace ID to create task in |
| `due_date` | string | No | Due date (ISO 8601 format) |
| `duration` | integer | No | Duration in minutes |
| `project_id` | string | No | Project ID to add task to |
| `description` | string | No | Task description (Markdown supported) |
| `priority` | string | No | Priority: `ASAP`, `HIGH`, `MEDIUM`, `LOW` |
| `assignee_id` | string | No | User ID to assign task to |
| `labels` | string[] | No | List of label names |

**Response:** `{ success, task, message }`

---

#### `motion_update_task`

Update an existing task. Only provided fields are updated.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | The task ID to update |
| `name` | string | No | New task name |
| `due_date` | string | No | New due date (ISO 8601) |
| `duration` | integer | No | New duration in minutes |
| `project_id` | string | No | New project ID |
| `description` | string | No | New description |
| `priority` | string | No | New priority level |
| `status` | string | No | New status name |
| `assignee_id` | string | No | New assignee user ID |
| `labels` | string[] | No | New labels (replaces existing) |

**Response:** `{ success, task, message }`

---

#### `motion_delete_task`

Permanently delete a task.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | The task ID to delete |

**Response:** `{ success, message }`

---

#### `motion_move_task`

Move a task to a different workspace or project.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | The task ID to move |
| `workspace_id` | string | Yes | Target workspace ID |
| `project_id` | string | No | Target project ID |

**Response:** `{ success, task, message }`

---

#### `motion_unassign_task`

Remove the assignee from a task.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | The task ID to unassign |

**Response:** `{ success, task, message }`

---

### Project Tools

#### `motion_list_projects`

List projects with optional workspace filter.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace_id` | string | No | Filter by workspace ID |

**Response:** `{ success, projects[], count }`

---

#### `motion_get_project`

Get a specific project by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | The project ID |

**Response:** `{ success, project }`

---

#### `motion_create_project`

Create a new project.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Project name |
| `workspace_id` | string | Yes | Workspace ID |
| `description` | string | No | Project description |
| `status` | string | No | Initial status name |
| `labels` | string[] | No | Label names to add |

**Response:** `{ success, project, message }`

---

### Workspace Tools

#### `motion_list_workspaces`

List all accessible workspaces.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (none) | - | - | No parameters required |

**Response:** `{ success, workspaces[], count }`

---

### User Tools

#### `motion_list_users`

List users in a workspace.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace_id` | string | No | Workspace ID to list users from |

**Response:** `{ success, users[], count }`

---

#### `motion_get_current_user`

Get the current authenticated user.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (none) | - | - | No parameters required |

**Response:** `{ success, user }`

---

### Utility Tools

#### `motion_get_rate_limit_status`

Check current rate limit status. Use before batch operations.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (none) | - | - | No parameters required |

**Response:**
```json
{
  "success": true,
  "max_requests": 12,
  "window_seconds": 60,
  "remaining_requests": 10,
  "can_proceed": true,
  "wait_seconds": 0
}
```

---

## MCP Tool Examples

### List Tasks

```json
{
  "tool": "motion_list_tasks",
  "arguments": {
    "workspace_id": "ws_123",
    "status": "In Progress"
  }
}
```

### Create Task

```json
{
  "tool": "motion_create_task",
  "arguments": {
    "name": "Review PR #42",
    "workspace_id": "ws_123",
    "due_date": "2024-12-31T17:00:00Z",
    "duration": 30,
    "priority": "HIGH",
    "project_id": "proj_456",
    "description": "Review and merge the authentication refactor PR"
  }
}
```

### Update Task

```json
{
  "tool": "motion_update_task",
  "arguments": {
    "task_id": "task_789",
    "status": "Done",
    "priority": "LOW"
  }
}
```

### Check Rate Limit Before Batch Operations

```json
{
  "tool": "motion_get_rate_limit_status",
  "arguments": {}
}
```

## Development

```powershell
# Run linter
make lint

# Format code
make format

# Run tests
make test

# Clean build artifacts
make clean
```

## Docker

Build and run in Docker:

```powershell
# Build image
make build
# OR
docker build -t motion-mcp:latest .

# Run container
docker run -d \
  -e MOTION_API_KEY=your-api-key \
  -p 8081:8081 \
  -v motion-data:/app/data \
  motion-mcp:latest
```

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  motion-mcp:
    build:
      context: ./MCPS/motion
      dockerfile: Dockerfile
    environment:
      - MOTION_API_KEY=${MOTION_API_KEY}
      - MOTION_ACCOUNT_TYPE=individual
    ports:
      - "8081:8081"
    volumes:
      - motion-data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  motion-data:
```

## Project Structure

```
MCPS/motion/
├── src/
│   ├── __init__.py
│   ├── server.py         # FastMCP server and MCP tools
│   ├── client.py         # Motion API client with rate limiting
│   ├── rate_limiter.py   # Token bucket rate limiter with SQLite
│   └── models/
│       ├── __init__.py
│       ├── common.py     # Shared models
│       ├── tasks.py      # Task models
│       ├── projects.py   # Project models
│       ├── workspaces.py # Workspace models
│       └── users.py      # User models
├── tests/                # Test suite
├── pyproject.toml        # Project configuration
├── uv.lock               # Dependency lockfile
├── Dockerfile            # Container build
├── Makefile              # Development commands
├── README.md             # This file
├── MOTION_MCP_PLAN.md    # Implementation plan
└── .env.example          # Example configuration
```

## Motion API Reference

This server integrates with the Motion REST API. For complete API documentation, see:

- [Motion API Docs](https://docs.usemotion.com/)
- [Rate Limits](https://docs.usemotion.com/cookbooks/rate-limits/)
- [API Reference](https://docs.usemotion.com/docs/motion-rest-api/44e37c461ba67-motion-rest-api)

## Error Handling

All tools return consistent error responses:

```json
{
  "success": false,
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please wait 45.2 seconds before retrying.",
  "wait_seconds": 45.2
}
```

Error types:
- `rate_limit_exceeded` - Too many requests, wait before retrying
- `authentication_error` - Invalid API key
- `not_found` - Resource not found
- `api_error` - General API error with details
- `unexpected_error` - Unexpected server error

## Roadmap

See [MOTION_MCP_PLAN.md](./MOTION_MCP_PLAN.md) for the full implementation plan.

### Planned Features

- [ ] Comments support (list, create)
- [ ] Recurring tasks (list, create, delete)
- [ ] Schedules (list)
- [ ] Statuses (list)
- [ ] Custom fields (CRUD)
- [ ] Batch operations with rate limit awareness
- [ ] Webhook support for real-time updates

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

## Support

For issues with this MCP server, please open an issue in the repository.

For Motion API questions, refer to [Motion Help Center](https://help.usemotion.com/).
