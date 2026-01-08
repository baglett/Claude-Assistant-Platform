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
- `TELEGRAM_BOT_TOKEN` - Production Telegram bot token (required for deployed instances)
- `TELEGRAM_DEV_BOT_TOKEN` - Development Telegram bot token (optional, for local dev)
- `TELEGRAM_ALLOWED_USER_IDS` - Comma-separated whitelist of user IDs
- `TELEGRAM_POLLING_TIMEOUT` - Long-polling timeout (default: 30)
- `TELEGRAM_ENABLED` - Enable/disable Telegram (default: true)
- `GITHUB_TOKEN` - GitHub MCP access (optional)
- Additional MCP-specific credentials as needed

## Development vs Production Telegram Bots

The platform supports separate development and production Telegram bots to prevent polling conflicts when running locally alongside a deployed production instance.

### Why Two Bots?

Telegram only allows one client to poll updates for a bot at a time. If you run locally while production is deployed, both instances will fight for updates, causing messages to be randomly delivered to either instance.

### Setup

1. **Create two bots via @BotFather:**
   - Production bot (e.g., `MyAssistantBot`)
   - Development bot (e.g., `MyAssistantDevBot`)

2. **Configure your `.env`:**
   ```env
   APP_ENV=development
   TELEGRAM_BOT_TOKEN=<production-bot-token>
   TELEGRAM_DEV_BOT_TOKEN=<dev-bot-token>
   ```

3. **How it works:**
   - When `APP_ENV=development` and `TELEGRAM_DEV_BOT_TOKEN` is set, the dev bot is used
   - When `APP_ENV=production` or `APP_ENV=staging`, the production bot is always used
   - If `TELEGRAM_DEV_BOT_TOKEN` is not set, falls back to production token

### Running Local Frontend Against Production Bot

To test the local frontend with the production bot (while backend uses dev bot):
- The frontend doesn't directly interact with Telegram
- Frontend connects to the backend API which uses the appropriate bot based on `APP_ENV`
- To use prod bot locally, set `APP_ENV=production` or leave `TELEGRAM_DEV_BOT_TOKEN` empty

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

#### Todo Tracking System

**Database Infrastructure:**
- Created `Backend/src/database/manager.py` - Universal `DatabaseManager` interface
  - `DatabaseConfig` dataclass for immutable configuration
  - `DatabaseManagerProtocol` for type-safe dependency injection
  - `DatabaseManager` class with async context manager support
  - Connection pooling, health checks, session management
- Migrated from `asyncpg` to `psycopg[binary,pool]>=3.2.0`
- Updated `settings.py` to use `postgresql+psycopg://` dialect
- Refactored `connection.py` as backwards-compatible wrapper

**Todo Database Layer:**
- Created `Backend/database/migrations/003_create_todos_table.sql`
  - New `tasks` schema for todo management
  - Full status tracking (pending, in_progress, completed, failed, cancelled)
  - Agent assignment (github, email, calendar, obsidian, orchestrator)
  - Priority levels (1-5), scheduling, subtask support
  - Execution result and error storage
- Added `Todo` ORM model to `Backend/src/database/models.py`
- Created Pydantic schemas in `Backend/src/models/todo.py`
  - `TodoStatus`, `AgentType`, `TodoPriority` enums
  - `TodoCreate`, `TodoUpdate` request models
  - `TodoResponse`, `TodoListResponse`, `TodoStats` response models

**Todo Service & API:**
- Created `Backend/src/services/todo_service.py`
  - CRUD operations with filtering and pagination
  - Status transitions with timestamp handling
  - Statistics aggregation
  - Execution queue support
- Created `Backend/src/api/routes/todos.py` with endpoints:
  - `POST /api/todos` - Create todo
  - `GET /api/todos` - List with filters
  - `GET /api/todos/stats` - Statistics
  - `GET /api/todos/{id}` - Get single todo
  - `GET /api/todos/{id}/subtasks` - Get subtasks
  - `PATCH /api/todos/{id}` - Update todo
  - `DELETE /api/todos/{id}` - Delete todo
  - `POST /api/todos/{id}/execute` - Trigger execution
  - `POST /api/todos/{id}/cancel` - Cancel todo

**Multi-Agent Architecture:**
- Created `Backend/database/migrations/004_create_agent_executions_table.sql`:
  - New `agents.executions` table for tracking all agent invocations
  - Stores thinking, tool calls, input/output tokens, execution time
  - Supports nested agent calls via `parent_execution_id`
- Created `Backend/src/agents/base.py`:
  - `AgentContext` dataclass - context passed to agents (chat_id, task, session, etc.)
  - `AgentResult` dataclass - result from agent execution with delegation support
  - `BaseAgent` abstract class - base for all agents with automatic execution logging
  - `AgentRegistry` class - registry for looking up agents by name
  - `AgentProtocol` - type-safe protocol for agents
- Created `Backend/src/agents/todo_agent.py`:
  - First specialized sub-agent implementation
  - 6 tools: create_todo, list_todos, get_todo, update_todo, delete_todo, get_todo_stats
  - Uses Claude tool calling loop for natural language task processing
  - Extends BaseAgent for automatic execution logging
- Created `Backend/src/services/agent_execution_service.py`:
  - Service layer for agent execution logging
  - Methods: start_execution, complete_execution, fail_execution, cancel_execution
  - Logging: log_thinking, log_tool_call
  - Queries: get_by_chat, get_by_todo, get_execution_tree, get_failed_executions
  - Statistics: get_token_usage_by_agent
- Refactored `Backend/src/agents/orchestrator.py`:
  - Now extends BaseAgent for consistent execution logging
  - Uses AgentRegistry to manage and invoke sub-agents
  - New tools: `delegate_to_agent`, `get_available_agents`
  - Dynamic system prompt populated with registered agents
  - Delegation creates child executions linked to parent
- Updated `Backend/src/api/main.py`:
  - Registers TodoAgent with orchestrator on startup
- Updated `Backend/src/services/todo_executor.py`:
  - Uses registered agents from orchestrator's registry
  - Falls back to placeholder methods for unregistered agents
  - Creates proper AgentContext for background execution
- Added `AgentExecution` ORM model to `Backend/src/database/models.py`

**Legacy Tool Integration:**
- Created `Backend/src/agents/tools/` package for orchestrator tools
- Created `Backend/src/agents/tools/todo_tools.py`:
  - 7 tool definitions for direct Claude API integration (legacy path)
  - `TodoToolHandler` class for processing tool calls
  - Tools: `create_todo`, `list_todos`, `get_todo`, `update_todo`, `delete_todo`, `execute_todo`, `get_todo_stats`
- Updated `Backend/src/services/telegram/message_handler.py`:
  - Passes `created_by` identifier for todo tracking

**Background Executor:**
- Created `Backend/src/services/todo_executor.py`:
  - Background task for processing pending todos
  - Agent-based routing (github, email, calendar, obsidian, orchestrator)
  - Retry logic with configurable max attempts
  - Manual execution support via API
- Added executor settings to `Backend/src/config/settings.py`:
  - `todo_executor_interval` - Check interval in seconds (default: 30)
  - `todo_executor_batch_size` - Todos per cycle (default: 5)
  - `todo_executor_enabled` - Enable/disable executor
- Integrated executor lifecycle in `Backend/src/api/main.py`:
  - Starts as background task on startup
  - Graceful shutdown on application stop

#### Development/Production Bot Separation

**Settings Updates:**
- Added `telegram_dev_bot_token` setting for development bot token
- Added `telegram_active_bot_token` computed property that selects appropriate token based on `APP_ENV`
- Added `telegram_is_dev_bot` computed property to check which bot is active
- Updated `telegram_is_configured` to check active token instead of production token
- Updated `Backend/src/api/main.py` to use active bot token with logging of bot mode

**Configuration:**
- Updated `.env.example` with comprehensive dev/prod bot documentation
- Added `TELEGRAM_DEV_BOT_TOKEN` environment variable
- Updated `CLAUDE.md` with dev bot setup instructions

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

#### Obsidian MCP Server

**Research & Design:**
- Evaluated existing MCP implementations:
  - No official Obsidian MCP exists
  - Reviewed community implementations: MarkusPfundstein/mcp-obsidian (Python), cyanheads/obsidian-mcp-server (TypeScript)
  - Selected Obsidian Local REST API plugin (v3.2.0) as integration point
- Analyzed Local REST API capabilities:
  - Vault file operations (CRUD), periodic notes, search, commands
  - HTTPS (27124) with self-signed cert or HTTP (27123)
  - Bearer token authentication

**MCP Server Implementation:**
- Created `MCPS/obsidian/src/server.py` - Full MCP server with 15 tools:
  - **Note Operations**: `read_note`, `create_note`, `update_note`, `delete_note`
  - **Vault Navigation**: `list_vault_files`, `get_active_file`, `open_file`
  - **Search**: `search_vault` (text search), `search_dataview` (DQL queries)
  - **Periodic Notes**: `get_daily_note`, `get_weekly_note`, `append_to_daily_note`
  - **Commands**: `list_commands`, `execute_command`
  - **System**: `check_connection`
- Implemented `ObsidianClient` class:
  - Async HTTP client using httpx
  - SSL handling for self-signed certificates
  - Full API coverage for Local REST API endpoints
  - URL encoding for file paths
- Dual server setup: FastMCP tools + FastAPI HTTP endpoints

**Project Structure:**
- Created `MCPS/obsidian/pyproject.toml` - Project config with dependencies
- Created `MCPS/obsidian/Dockerfile` - Multi-stage build matching Telegram pattern
- Created `MCPS/obsidian/Makefile` - Build/run targets (install, run, dev, lint, format)
- Created `MCPS/obsidian/README.md` - Comprehensive documentation with:
  - Plugin setup instructions
  - Environment variable reference
  - Tool usage examples
  - Docker deployment guide
  - Troubleshooting section

**Configuration Updates:**
- Updated `docker-compose.yml`:
  - Added `obsidian-mcp` service
  - Configured host.docker.internal for host-to-container communication
  - Added extra_hosts for Linux Docker compatibility
- Updated `.env.example`:
  - Added Obsidian configuration section
  - Documented all environment variables
  - Setup instructions for Local REST API plugin

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