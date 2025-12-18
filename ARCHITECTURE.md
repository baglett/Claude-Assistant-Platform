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
- **TelegramPoller**: Continuously polls Telegram API for updates using `getUpdates`
- **TelegramMessageHandler**: Routes messages to orchestrator and sends responses
- **Telegram MCP Server**: Provides tools for sending messages (optional)

**Flow:**
```
[User Phone] → [Telegram Cloud] → [Backend Poller] → [Orchestrator]
                                                          ↓
[User Phone] ← [Telegram Cloud] ← [Message Handler] ←────┘
```

### 2. Orchestrator Agent

The central coordinator built with Claude Agents SDK.

**Responsibilities:**
- Parse user intent from natural language
- Maintain conversation context
- Delegate to appropriate sub-agents via handoffs
- Aggregate and format responses
- Manage todo list state

**Configuration:**
```python
orchestrator = Agent(
    name="orchestrator",
    model="claude-sonnet-4-20250514",
    instructions="...",
    tools=[telegram_respond, todo_manager],
    handoffs=[github_agent, email_agent, calendar_agent, obsidian_agent]
)
```

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

### 5. Todo/Task System

Persistent task management with execution capabilities.

**Data Model:**
```python
class Todo:
    id: str
    content: str
    status: Literal["pending", "in_progress", "completed", "failed"]
    agent: str  # Which sub-agent should handle this
    created_at: datetime
    completed_at: Optional[datetime]
    result: Optional[str]
```

**Storage:**
- SQLite database in Docker volume for persistence
- Survives container restarts

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
6. Orchestrator parses intent
7. Orchestrator creates todo(s) if needed
8. Orchestrator hands off to sub-agent(s) (future)
9. Sub-agent executes via MCP tools (future)
10. Results return to orchestrator
11. Orchestrator formats response
12. MessageHandler sends response via Telegram API (or MCP)
```

### Todo Execution Flow

```
1. Orchestrator creates todo with assigned agent
2. Todo stored in database (status: pending)
3. Execution triggered (immediate or scheduled)
4. Status updated to in_progress
5. Sub-agent executes task via MCP
6. Status updated to completed/failed
7. User notified of result via Telegram
```

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
