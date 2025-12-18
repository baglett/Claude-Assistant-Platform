# Claude Assistant Platform - Development Guide

## Project Overview

This is a self-hosted AI assistant platform using the Claude Agents SDK. The system uses an orchestrator pattern where a main agent delegates to specialized sub-agents, each with access to specific MCP servers.

## Architecture Summary

- **Orchestrator Agent**: Main entry point, parses user intent, delegates tasks
- **Sub-Agents**: Specialized agents (GitHub, Email, Calendar, Obsidian)
- **MCP Servers**: Tool providers for external service integration
- **Telegram MCP**: User interface via Telegram bot
- **FastAPI**: REST API layer for internal communication and webhooks

## Development Notes

### Hard Requirements

- Python 3.14+ (use modern Python features, type hints required)
- FastAPI for all HTTP endpoints
- Docker Compose for orchestration
- All services must be containerized
- **uv** for Python package and project management (not pip)

### Shell Commands

- **Always use PowerShell 7 (pwsh)** for all shell commands
- Use PowerShell cmdlets and syntax (e.g., `Get-ChildItem`, `New-Item`, `Remove-Item`, `Copy-Item`)
- Avoid bash/cmd syntax unless running inside Docker containers
- Example commands:
  ```powershell
  # Correct - PowerShell 7
  Get-ChildItem -Recurse -Filter "*.py"
  New-Item -ItemType Directory -Path "./src/agents"
  Remove-Item -Path "./temp" -Recurse -Force

  # Incorrect - Bash syntax
  ls -la
  mkdir -p src/agents
  rm -rf temp
  ```

### Code Standards

- Follow PEP 8 and PEP 257 (docstrings)
- Use type hints throughout
- Async/await patterns for I/O operations
- Pydantic models for data validation
- Comprehensive error handling

### Key Patterns

1. **Agent Handoffs**: Orchestrator hands off to sub-agents, never executes domain tasks directly
2. **MCP Tool Calls**: All external service interactions go through MCP servers
3. **Todo Persistence**: Tasks survive restarts, stored in persistent volume
4. **Approval Flows**: Destructive actions require user confirmation via Telegram

## Environment Variables

Required environment variables (see `.env.example`):

- `ANTHROPIC_API_KEY` - Claude API access (required)
- `TELEGRAM_BOT_TOKEN` - Telegram bot authentication (required for Telegram)
- `TELEGRAM_ALLOWED_USER_IDS` - Comma-separated whitelist of user IDs
- `TELEGRAM_POLLING_TIMEOUT` - Long-polling timeout (default: 30)
- `TELEGRAM_ENABLED` - Enable/disable Telegram (default: true)
- `GITHUB_TOKEN` - GitHub MCP access (optional)
- Additional MCP-specific credentials as needed

## Dependency Management (uv)

This project uses **uv** for Python package and project management. uv is a fast, modern replacement for pip and pip-tools.

### Common uv Commands

```powershell
# Initialize a new project (already done)
uv init

# Add a dependency
uv add fastapi

# Add a dev dependency
uv add --dev pytest

# Remove a dependency
uv remove package-name

# Sync dependencies (install from pyproject.toml/uv.lock)
uv sync

# Update all dependencies
uv lock --upgrade

# Run a command in the virtual environment
uv run python script.py
uv run pytest
```

### Key Files

- `pyproject.toml` - Project metadata and dependencies
- `uv.lock` - Lockfile for reproducible builds (commit this to git)

## Running Locally

```powershell
# Sync dependencies first
uv sync

# Development mode
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or via Docker
docker-compose up --build
```

## Testing

```powershell
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

## Changelog

### [Unreleased]

#### Telegram Integration (Phase 1)

**Backend Configuration:**
- Added Telegram settings to `Backend/src/config/settings.py`
  - `telegram_bot_token`, `telegram_allowed_user_ids`, `telegram_polling_timeout`
  - `telegram_enabled`, `telegram_mcp_host`, `telegram_mcp_port`
  - Computed properties: `telegram_allowed_user_ids_list`, `telegram_mcp_url`, `telegram_is_configured`

**Telegram Services:**
- Created `Backend/src/services/telegram/` package:
  - `models.py` - Pydantic models for Telegram API data structures (User, Chat, Message, Update)
  - `poller.py` - TelegramPoller with long-polling, user whitelist, exponential backoff
  - `message_handler.py` - TelegramMessageHandler with bot commands, session management, typing indicators
- Created `Backend/src/services/telegram_session_service.py`:
  - Maps Telegram chat IDs to internal database chat sessions
  - Supports `/new` command for fresh conversation context
  - Supports `/clear` command to clear messages in current chat
  - Supports `/status` command to show session info

**Bot Commands:**
- `/start` - Welcome message and initial setup
- `/help` - Display available commands
- `/new` - Start fresh conversation (new internal chat)
- `/clear` - Clear messages but keep same session
- `/status` - Show session info and message count

**Database:**
- Added `Backend/database/migrations/002_create_telegram_sessions.sql`
- Created `TelegramSession` model mapping Telegram chat IDs to internal chats

**API Integration:**
- Updated `Backend/src/api/main.py` lifespan to:
  - Initialize OrchestratorAgent on startup
  - Initialize TelegramPoller and TelegramMessageHandler
  - Start poller as background task
  - Graceful shutdown of poller and handler

**Telegram MCP Server:**
- Created `docker/telegram-mcp/` Telegram MCP Server:
  - FastMCP server with tools: `send_message`, `get_chat_info`, `send_typing_action`
  - FastAPI HTTP endpoints for direct tool access
  - Dockerfile with multi-stage build
  - Health check endpoint at `/health`

**Docker Updates:**
- Updated `docker-compose.yml`:
  - Added `telegram-mcp` service on internal network
  - Added Telegram environment variables to backend service
  - Backend depends on telegram-mcp service health
- Updated `.env.example` with comprehensive Telegram configuration

#### Previous
- Initial project scaffolding
- Architecture and requirements documentation
- Adopted uv for Python package management (replacing pip)

## Known Issues

- None yet (project in planning phase)

## Future Considerations

- Voice message support via Telegram
- Web dashboard for task visualization
- Additional MCP integrations (Slack, Discord, etc.)
- Multi-user support with authentication
- Always update CLAUDE.md and ARCHITECTURE.md and README.md if appropriate.
- always remove dead or unused code
- always consider the REQUIREMENTS.md to abide by the project requirements for any new changes
- never commit credentials to git