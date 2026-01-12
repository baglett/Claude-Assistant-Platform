# Changelog

All notable changes to the Claude Assistant Platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Three-Tier Hybrid Router (Phase 1)

**Goal:** Minimize latency by bypassing the orchestrator's LLM call for clear-intent queries.

**Architecture:**
- Tier 1 (Regex): Pattern matching for high-confidence routing (<1ms)
- Tier 2 (Hybrid): BM25 + embedding similarity (10-50ms) - Phase 2
- Tier 3 (LLM): Haiku fallback for ambiguous queries (200-500ms) - Phase 3

**Database Changes:**
- Created `Backend/database/migrations/005_create_routing_tables.sql`:
  - Enabled `pgvector` extension for vector similarity search
  - Created `routing` schema with 3 tables:
    - `routing.agents` - Agent definitions with keywords, regex patterns, embeddings
    - `routing.tools` - Tool definitions for future tool-level routing
    - `routing.decisions` - Decision logging for analytics
  - Seeded 5 agents: github, todo, email, calendar, motion
  - Created ivfflat indexes for vector similarity search

**New Files:**
- `Backend/src/database/routing_models.py`:
  - `RoutingAgent` - ORM model for agent routing data
  - `RoutingTool` - ORM model for tool routing data (Phase 2+)
  - `RoutingDecision` - ORM model for decision logging
  - Uses `pgvector.sqlalchemy.Vector` for embedding columns
- `Backend/src/services/cache_service.py`:
  - Redis async caching for routing system
  - Caches embeddings (1hr TTL), routing decisions (5min TTL), agent data (1hr TTL)
  - Graceful degradation when Redis unavailable
- `Backend/src/services/router_service.py`:
  - Core 3-tier routing logic
  - Tier 1 regex patterns for all 5 agents
  - Placeholder methods for Tier 2/3 (Phase 2-3)
  - Confidence scoring and decision logging
- `Backend/src/agents/router.py`:
  - `AgentRouter` class for orchestrator integration
  - `RouterStats` for performance tracking
  - Direct agent execution bypass when confident

**Modified Files:**
- `Backend/src/config/settings.py`:
  - Added Redis settings (host, port, db, password)
  - Added Router settings (enabled, tier1_only, confidence_threshold)
  - Added OpenAI settings for embeddings (Phase 2)
- `Backend/src/agents/orchestrator.py`:
  - Router initialization on startup
  - Router bypass logic in `_execute_task`
  - Router stats and refresh methods
- `Backend/src/api/main.py`:
  - Router initialization after agent registration
  - Cache service cleanup on shutdown
- `docker-compose.yml`:
  - Added Redis service (redis:7-alpine, port 6379)
  - Added redis-data volume
  - Added Redis environment variables to backend

**New Dependencies:**
- `redis[hiredis]>=5.2.0` - Async Redis client with hiredis
- `pgvector>=0.3.6` - PostgreSQL vector operations
- `rank-bm25>=0.2.2` - BM25 text matching (Phase 2)
- `openai>=1.58.0` - Embedding generation (Phase 2)
- `numpy>=2.2.0` - Vector operations

**Configuration:**
| Setting | Default | Description |
|---------|---------|-------------|
| `ROUTER_ENABLED` | `true` | Enable/disable hybrid router |
| `ROUTER_TIER1_ONLY` | `false` | Use only regex tier |
| `ROUTER_CONFIDENCE_THRESHOLD` | `0.75` | Minimum confidence to bypass orchestrator |
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `OPENAI_API_KEY` | - | Required for Phase 2 embeddings |

**Expected Impact:**
- Phase 1 (Regex): 60-70% of clear-intent queries bypass orchestrator
- Phase 2 (BM25+Embedding): 80-90% bypass rate
- Phase 3 (LLM fallback): 95%+ bypass rate

### Motion MCP Jenkins Integration

**Jenkinsfile Updates:**
- Added `motion-api-key` credential reference
- Added Motion MCP image build stage (parallel)
- Added Motion MCP image push stage (parallel)
- Added Motion MCP container stop/remove in cleanup
- Added Motion MCP container start stage (port 8082:8081)
- Added Motion environment variables to backend container
- Fixed Telegram MCP path casing (`./MCPS/telegram`)

**Documentation:**
- Created `DEPLOYMENT.md` - Comprehensive deployment reference
  - Port configuration tables (prod and dev)
  - Container reference with registry paths
  - Network configuration details
  - Volume mount documentation
  - Jenkins credentials setup guide
  - Environment variables reference
  - Infrastructure endpoints
  - Quick reference commands
- Updated `README.md` with Jenkins CI/CD section
- Updated project structure to include MCPS folder

**Port Allocation:**
| Service | Internal | External (Prod) |
|---------|----------|-----------------|
| Backend | 8000 | 8000 |
| Frontend | 3000 | 3000 |
| Telegram MCP | 8080 | 8081 |
| Motion MCP | 8081 | 8082 |

### Todo Tracking System

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

### Development/Production Bot Separation

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

### Telegram Integration (Phase 1)

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

### Initial Setup

- Initial project scaffolding
- Architecture and requirements documentation
- Adopted uv for Python package management (replacing pip)
