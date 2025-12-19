# System Architecture

## Overview

The Claude Assistant Platform follows a multi-agent orchestration pattern. A central orchestrator agent receives user requests via Telegram, delegates to specialized sub-agents, and aggregates results.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOCAL NETWORK                                     │
│                                                                             │
│  ┌─────────────┐      ┌─────────────────────────────────────────────────┐  │
│  │  Telegram   │      │            Claude Assistant Platform            │  │
│  │    Bot      │◄────►│                                                 │  │
│  │ (MCP Server)│      │  ┌───────────────────────────────────────────┐  │  │
│  └─────────────┘      │  │           Orchestrator Agent              │  │  │
│                       │  │      (Claude Agents SDK - Main Loop)      │  │  │
│                       │  └─────────────────┬─────────────────────────┘  │  │
│                       │                    │                            │  │
│                       │       ┌────────────┼────────────┐               │  │
│                       │       ▼            ▼            ▼               │  │
│                       │  ┌────────┐  ┌──────────┐  ┌─────────┐          │  │
│                       │  │ GitHub │  │ Calendar │  │  Email  │          │  │
│                       │  │ Agent  │  │  Agent   │  │  Agent  │          │  │
│                       │  └───┬────┘  └────┬─────┘  └────┬────┘          │  │
│                       │      │            │             │               │  │
│                       └──────┼────────────┼─────────────┼───────────────┘  │
│                              │            │             │                  │
│  ┌─────────────┐        ┌────┴────┐  ┌────┴────┐  ┌─────┴────┐            │
│  │  Obsidian   │◄───────│ GitHub  │  │ Calendar│  │  Email   │            │
│  │ MCP Server  │        │   MCP   │  │   MCP   │  │   MCP    │            │
│  └─────────────┘        └─────────┘  └─────────┘  └──────────┘            │
│                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
        ▲
        │ (Internet via Telegram API)
        ▼
   ┌──────────┐
   │  Phone   │
   │(Telegram)│
   └──────────┘
```

## Component Details

### 1. API Layer (FastAPI)

The FastAPI application serves as the HTTP backbone for the platform.

**Responsibilities:**
- Manage application lifecycle (including Telegram poller)
- Expose health check and status endpoints
- Provide internal API for agent communication
- Handle async task queuing

**Endpoints:**
```
GET  /health               - Health check
GET  /api/chat             - Chat API endpoints
GET  /tasks                - List current tasks (future)
POST /tasks/{id}/execute   - Manually trigger task execution (future)
```

### 1.1 Telegram Integration

The Telegram integration uses a **long-polling** approach rather than webhooks, making it suitable for local network deployment without requiring public endpoints.

**Components:**
- **TelegramPoller** (`Backend/src/services/telegram/poller.py`): Long-polling client that fetches updates from the Telegram API using `getUpdates`. Implements automatic reconnection with exponential backoff and validates users against a whitelist.
- **TelegramMessageHandler** (`Backend/src/services/telegram/message_handler.py`): Routes incoming messages to the orchestrator and sends responses back. Handles bot commands, typing indicators, and message splitting for long responses.
- **TelegramSessionService** (`Backend/src/services/telegram_session_service.py`): Maps Telegram chat IDs to internal database chat sessions. Supports creating new sessions (`/new`) and clearing history (`/clear`).
- **Telegram MCP Server** (`docker/telegram-mcp/`): Containerized FastMCP server providing tools for outbound Telegram operations.

**Bot Commands:**
| Command | Description |
|---------|-------------|
| `/start` | Welcome message and initial session setup |
| `/help` | Display available commands and usage tips |
| `/new` | Start a fresh conversation (new chat context) |
| `/clear` | Clear messages in current conversation without starting new session |
| `/status` | Show current session info (chat ID, message count) |

**Session Management:**
- Each Telegram chat maps to an internal database chat via `TelegramSession`
- Users can create new chat contexts with `/new` to change topics
- Message history is persisted in PostgreSQL for context continuity
- `conversation_id` format: `telegram_{chat_id}`

**Flow:**
```
[User Phone] → [Telegram Cloud] → [Backend Poller] → [Session Service]
                                                          ↓
                                                    [Orchestrator]
                                                          ↓
[User Phone] ← [Telegram Cloud] ← [Message Handler] ←────┘
```

**Security:**
- User whitelist via `TELEGRAM_ALLOWED_USER_IDS` environment variable
- Unauthorized users are logged but receive no response
- If no whitelist is configured, a warning is logged (dev mode)

### 2. Orchestrator Agent

The central coordinator using direct Anthropic Claude API with tool calling.

**Responsibilities:**
- Parse user intent from natural language
- Maintain conversation context (stored in database)
- Manage todos via integrated tool calling
- Delegate to appropriate sub-agents via todo assignment
- Aggregate and format responses

**Implementation:** `Backend/src/agents/orchestrator.py`
```python
# Tool calling loop with automatic iteration
response = client.messages.create(
    model=model,
    tools=TOOL_DEFINITIONS,  # 7 todo management tools
    messages=messages,
)
# Handle tool_use blocks, execute via TodoToolHandler, continue loop
```

**Available Tools:**
| Tool | Description |
|------|-------------|
| `create_todo` | Create a new task with optional agent assignment |
| `list_todos` | List todos with filtering by status, agent, priority |
| `get_todo` | Get details of a specific todo |
| `update_todo` | Modify todo fields (title, priority, status, etc.) |
| `delete_todo` | Permanently delete a todo |
| `execute_todo` | Trigger immediate execution of a pending todo |
| `get_todo_stats` | Get aggregated statistics about todos |

**Tool Handler:** `Backend/src/agents/tools/todo_tools.py`
- `TodoToolHandler` class processes tool calls from Claude
- Executes operations via `TodoService`
- Links todos to chat context and creator

### 3. Sub-Agents

Specialized agents with focused capabilities.

| Agent | MCP Access | Capabilities |
|-------|------------|--------------|
| **GitHub Agent** | github-mcp | Create/close issues, open PRs, check CI status, search code |
| **Email Agent** | email-mcp | Read inbox, draft/send emails, search messages |
| **Calendar Agent** | gcal-mcp | Create events, check availability, list upcoming |
| **Obsidian Agent** | obsidian-mcp | Create notes, search vault, update existing notes |

### 4. MCP Servers

Model Context Protocol servers provide tool interfaces to external services.

**Hosting Options:**
- **Sidecar containers**: Each MCP server runs in its own Docker container
- **Subprocess**: MCP servers spawn as child processes of the main app

**Communication:**
- MCP uses JSON-RPC over stdio or HTTP
- Each sub-agent connects to its designated MCP server
- HTTP fallback available for direct tool invocation

#### 4.1 Telegram MCP Server

The Telegram MCP Server (`docker/telegram-mcp/`) provides tools for outbound Telegram operations.

**Why MCP vs Direct API?**

The backend already uses the Telegram API directly for basic request/response flows:
- `TelegramPoller` calls `getUpdates` to receive messages
- `TelegramMessageHandler` calls `sendMessage` to respond

The MCP server serves a different purpose - it allows the **AI agent** to initiate outbound Telegram actions:

| Scenario | Who Sends | Method |
|----------|-----------|--------|
| Responding to user message | MessageHandler | Direct API |
| Agent notifies user proactively | Orchestrator/Sub-agents | MCP Tools |
| Agent sends typing during long task | Orchestrator | MCP Tools |
| Task completion notification | Sub-agents | MCP Tools |

This follows the architectural pattern: **Agents interact with external services through MCP tools, not direct API calls.** This keeps agents decoupled from API implementation details and maintains consistency with other integrations (GitHub MCP, Email MCP, etc.).

**Implementation:**
- Built with FastMCP framework
- Exposes both MCP tools and HTTP endpoints
- Runs as a sidecar container on the internal Docker network
- MessageHandler supports both direct API and MCP paths (configurable)

**Available Tools:**
| Tool | Description |
|------|-------------|
| `send_message` | Send a text message to a Telegram chat. Supports parse modes (HTML, Markdown, MarkdownV2), reply threading, and silent notifications. |
| `get_chat_info` | Get information about a Telegram chat (type, title, username). |
| `send_typing_action` | Send a typing indicator to show the bot is processing. |

**HTTP Endpoints:**
```
GET  /health                    - Health check
POST /tools/send_message        - Send message (JSON body)
POST /tools/get_chat_info       - Get chat info (query param: chat_id)
POST /tools/send_typing_action  - Send typing indicator (JSON body)
```

**Configuration:**
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather (required)
- Listens on port 8080 within Docker network
- Health check ensures container is ready before backend starts

### 5. Todo/Task System

Persistent task management with execution capabilities. Implemented in `tasks` schema.

**Data Model (ORM):**
```python
class Todo(Base):
    __tablename__ = "todos"
    __table_args__ = {"schema": "tasks"}

    id: UUID                          # Primary key
    title: str                        # Short description (max 500 chars)
    description: Optional[str]        # Detailed information
    status: str                       # pending, in_progress, completed, failed, cancelled
    assigned_agent: Optional[str]     # github, email, calendar, obsidian, orchestrator
    priority: int                     # 1 (critical) to 5 (lowest)
    scheduled_at: Optional[datetime]  # When to execute (None = manual)
    result: Optional[str]             # Agent output after execution
    error_message: Optional[str]      # Error details if failed
    execution_attempts: int           # Retry tracking
    chat_id: Optional[UUID]           # Link to originating conversation
    parent_todo_id: Optional[UUID]    # For subtask hierarchies
    task_metadata: dict               # JSONB for agent-specific parameters
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]    # When execution began
    completed_at: Optional[datetime]  # When finished
    created_by: Optional[str]         # User/source identifier
```

**API Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/todos` | Create a new todo |
| `GET` | `/api/todos` | List todos with filtering |
| `GET` | `/api/todos/stats` | Get statistics |
| `GET` | `/api/todos/{id}` | Get single todo |
| `GET` | `/api/todos/{id}/subtasks` | Get subtasks |
| `PATCH` | `/api/todos/{id}` | Update todo fields |
| `DELETE` | `/api/todos/{id}` | Delete todo and subtasks |
| `POST` | `/api/todos/{id}/execute` | Trigger execution |
| `POST` | `/api/todos/{id}/cancel` | Cancel todo |

**Storage:**
- PostgreSQL in `tasks.todos` table (same database as messaging)
- Survives container restarts via persistent volume

**Key Features:**
- Agent assignment for execution routing
- Priority-based ordering
- Scheduled execution support
- Subtask hierarchies
- Execution result/error tracking
- JSONB metadata for flexible agent parameters

## Frontend Architecture

The web dashboard provides a visual interface for managing the assistant.

**Tech Stack:**
- Next.js with App Router
- TypeScript for type safety
- Tailwind CSS + DaisyUI for styling
- Zustand for state management

**Key Features:**
- Real-time task monitoring dashboard
- Conversation history viewer
- Agent status and health monitoring
- Manual task triggering interface
- Configuration management UI

**Communication:**
- REST API calls to backend FastAPI endpoints
- WebSocket for real-time updates (optional)

## Docker Architecture

```yaml
services:
  frontend:
    # Next.js web dashboard
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  backend:
    # FastAPI + Orchestrator Agent
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db]

  telegram-mcp:
    # Telegram bot MCP server
    build: ./docker/telegram-mcp

  github-mcp:
    # GitHub MCP server
    build: ./docker/github-mcp

  db:
    # PostgreSQL for persistence
    image: postgres:16-alpine
    volumes: ["pgdata:/var/lib/postgresql/data"]
```

## Data Flow

### Request Processing

```
1. User sends Telegram message
2. Telegram API stores message
3. Backend TelegramPoller fetches updates via getUpdates (long-polling)
4. Poller validates user against whitelist
5. TelegramMessageHandler routes to OrchestratorAgent
6. Orchestrator calls Claude API with tool definitions
7. If Claude returns tool_use blocks:
   a. TodoToolHandler executes each tool call
   b. Results sent back to Claude
   c. Loop continues until Claude returns end_turn
8. Orchestrator extracts final text response
9. MessageHandler sends response via Telegram API
```

### Todo Execution Flow

**Immediate (via tool call):**
```
1. User asks to create/execute a todo via Telegram
2. Orchestrator receives tool_use from Claude
3. TodoToolHandler calls TodoService
4. Todo created/updated in database
5. Result returned to Claude for response formatting
```

**Background (via TodoExecutor):**
```
1. TodoExecutor polls database every N seconds
2. Queries for pending todos (scheduled_at <= now)
3. For each todo:
   a. Status updated to in_progress
   b. Routed to agent-specific handler
   c. Status updated to completed/failed with result
4. (Future) User notified of completion via Telegram MCP
```

**Configuration:**
- `TODO_EXECUTOR_INTERVAL`: Check interval in seconds (default: 30)
- `TODO_EXECUTOR_BATCH_SIZE`: Todos per cycle (default: 5)
- `TODO_EXECUTOR_ENABLED`: Enable/disable executor (default: true)

## Security Considerations

- **Network Isolation**: Platform runs on local network only
- **Secret Management**: All credentials via environment variables
- **User Authentication**: Telegram user ID whitelist
- **Action Confirmation**: Destructive actions require explicit approval

## Scalability Notes

Current design targets single-user, single-instance deployment. Future considerations:

- Message queue (Redis/RabbitMQ) for async task processing
- Multiple worker containers for parallel execution
- Rate limiting for API calls to external services
