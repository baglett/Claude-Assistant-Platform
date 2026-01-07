# Motion MCP Server Implementation Plan

## Overview

This document outlines the implementation plan for a Python-based MCP (Model Context Protocol) server that integrates with Motion's AI-powered calendar and task management API.

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| Research | Completed | API documentation, community implementations reviewed |
| Planning | Completed | This document |
| Implementation | Completed | Core MCP server with 14 tools |
| Testing | In Progress | Unit tests for rate limiter (11 passing) |
| Documentation | Completed | README and API documentation |

## Architecture Decision

### Why Python (FastMCP)?

Following the existing pattern in this project (see `MCPS/telegram/`), we'll use:
- **Python 3.12+** with modern type hints
- **FastMCP** - Official MCP library for Python
- **FastAPI** - HTTP endpoints for direct access
- **httpx** - Async HTTP client
- **Pydantic** - Data validation and settings
- **uv** - Package management

This approach ensures consistency with the telegram-mcp implementation and the broader Backend architecture.

## Motion API Overview

### Base URL
```
https://api.usemotion.com/v1
```

### Authentication
- **Header:** `X-API-Key: <your-api-key>`

### Rate Limits (CRITICAL)

| Account Type | Limit | Notes |
|--------------|-------|-------|
| Individual | 12 requests/minute | Default for personal accounts |
| Team | 120 requests/minute | For team/business accounts |
| Enterprise | Custom | Contact Motion for higher limits |

**Rate limiting strategy:**
1. Token bucket algorithm with sliding window
2. Persistent state (SQLite) to survive restarts
3. Configurable account type via environment variable
4. Automatic retry with exponential backoff
5. Clear error messages indicating wait time

## API Endpoints to Implement

### Tasks (Priority: High)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/tasks` | GET | `motion_list_tasks` |
| `/tasks/{id}` | GET | `motion_get_task` |
| `/tasks` | POST | `motion_create_task` |
| `/tasks/{id}` | PATCH | `motion_update_task` |
| `/tasks/{id}` | DELETE | `motion_delete_task` |
| `/tasks/{id}/move` | POST | `motion_move_task` |
| `/tasks/{id}/unassign` | POST | `motion_unassign_task` |

### Projects (Priority: High)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/projects` | GET | `motion_list_projects` |
| `/projects/{id}` | GET | `motion_get_project` |
| `/projects` | POST | `motion_create_project` |

### Workspaces (Priority: Medium)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/workspaces` | GET | `motion_list_workspaces` |

### Users (Priority: Medium)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/users` | GET | `motion_list_users` |
| `/users/me` | GET | `motion_get_current_user` |

### Comments (Priority: Medium)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/comments` | GET | `motion_list_comments` |
| `/comments` | POST | `motion_create_comment` |

### Recurring Tasks (Priority: Low)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/recurring-tasks` | GET | `motion_list_recurring_tasks` |
| `/recurring-tasks` | POST | `motion_create_recurring_task` |
| `/recurring-tasks/{id}` | DELETE | `motion_delete_recurring_task` |

### Schedules (Priority: Low)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/schedules` | GET | `motion_list_schedules` |

### Statuses (Priority: Low)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/statuses` | GET | `motion_list_statuses` |

### Custom Fields (Priority: Low)
| Endpoint | Method | Tool Name |
|----------|--------|-----------|
| `/custom-fields` | GET | `motion_list_custom_fields` |
| `/custom-fields` | POST | `motion_create_custom_field` |
| `/custom-fields/{id}` | DELETE | `motion_delete_custom_field` |

## Project Structure

```
MCPS/motion/
├── src/
│   ├── __init__.py
│   ├── server.py           # Main FastMCP server
│   ├── client.py           # Motion API client with rate limiting
│   ├── rate_limiter.py     # Token bucket rate limiter
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tasks.py        # Task-related Pydantic models
│   │   ├── projects.py     # Project-related Pydantic models
│   │   ├── workspaces.py   # Workspace-related Pydantic models
│   │   ├── users.py        # User-related Pydantic models
│   │   └── common.py       # Shared models
│   └── tools/
│       ├── __init__.py
│       ├── tasks.py        # Task tools
│       ├── projects.py     # Project tools
│       ├── workspaces.py   # Workspace tools
│       └── users.py        # User tools
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_rate_limiter.py
│   └── test_tools.py
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── Makefile
├── README.md
├── MOTION_MCP_PLAN.md      # This file
└── .env.example
```

## Rate Limiting Implementation

### Token Bucket Algorithm

```python
class RateLimiter:
    """
    Token bucket rate limiter with persistence.

    Features:
    - Sliding window approach
    - SQLite persistence for restart survival
    - Configurable limits per account type
    - Automatic wait time calculation
    """

    def __init__(
        self,
        max_requests: int,           # 12 or 120
        window_seconds: int = 60,    # 1 minute window
        db_path: str = "rate_limit.db"
    ):
        ...
```

### Configuration

```env
# .env.example
MOTION_API_KEY=your-api-key-here
MOTION_ACCOUNT_TYPE=individual  # individual | team | enterprise
MOTION_RATE_LIMIT_OVERRIDE=0    # 0 = use default, >0 = custom limit
MOTION_API_BASE_URL=https://api.usemotion.com/v1
```

## Implementation Phases

### Phase 1: Core Infrastructure
1. Clean up existing incorrect files
2. Create project structure
3. Implement rate limiter with SQLite persistence
4. Implement Motion API client with rate limiting
5. Basic health check endpoint

### Phase 2: Task Management
1. Implement all task-related tools
2. Create Pydantic models for task data
3. Unit tests for task operations

### Phase 3: Project & Workspace Management
1. Implement project tools
2. Implement workspace tools
3. Implement user tools

### Phase 4: Additional Features
1. Comments support
2. Recurring tasks
3. Schedules
4. Custom fields
5. Statuses

### Phase 5: Testing & Documentation
1. Comprehensive unit tests
2. Integration tests
3. README documentation
4. API reference

## Community Implementation References

### Evaluated Repositories (by priority)

1. **[RF-D/motion-mcp](https://github.com/RF-D/motion-mcp)** - 20 stars
   - 32+ tools
   - TypeScript implementation
   - Rate limiting via environment variable
   - Most actively maintained

2. **[devondragon/MotionMCP](https://github.com/devondragon/MotionMCP)** - 11 stars
   - Configurable tool sets (3-10 tools)
   - Consolidated tool approach
   - Smart workspace resolution
   - Updated September 2025

3. **[h3ro-dev/motion-mcp-server](https://github.com/h3ro-dev/motion-mcp-server)**
   - 20 tools
   - SQLite persistence for rate limits
   - Token bucket algorithm
   - Comprehensive error handling

### Key Patterns Adopted

- SQLite persistence for rate limit state (from h3ro-dev)
- Comprehensive tool coverage (from RF-D)
- Clear error messages with wait times
- Configurable account types

## Risk Mitigation

### Rate Limit Protection (CRITICAL)

The user's Motion account can be banned for exceeding rate limits. Mitigations:

1. **Hard enforcement:** Never allow requests to exceed limit
2. **Graceful degradation:** Return clear errors instead of making requests
3. **Persistence:** Remember rate limit state across restarts
4. **Logging:** Log all rate limit events for debugging
5. **Testing:** Test rate limiting behavior thoroughly

### Error Handling

1. Network errors: Retry with exponential backoff
2. API errors: Parse and return meaningful messages
3. Rate limits: Calculate and return wait time
4. Authentication: Clear error for invalid API key

## Success Criteria

- [ ] All 20+ MCP tools implemented
- [ ] Rate limiting prevents account ban
- [ ] Comprehensive test coverage (>80%)
- [ ] Documentation complete
- [ ] Docker support for deployment
- [ ] Consistent with telegram-mcp patterns

## Changelog

### 2025-01-07
- Initial plan created
- Research completed on Motion API and community implementations
- Architecture decisions finalized
- Implemented complete Motion MCP server with 14 tools:
  - Task management (7 tools): list, get, create, update, delete, move, unassign
  - Project management (3 tools): list, get, create
  - Workspace management (1 tool): list
  - User management (2 tools): list, get current
  - Rate limit monitoring (1 tool): get status
- Implemented robust rate limiting with SQLite persistence
- Created 11 unit tests for rate limiter (all passing)
- Documentation: README.md with full usage guide
