# Execution Plan

## Project Status Overview

| Component | Status | Priority |
|-----------|--------|----------|
| Project scaffolding | Placeholder files created | P0 |
| Backend core | Not started | P0 |
| Frontend core | Not started | P1 |
| Orchestrator agent | Not started | P0 |
| Telegram MCP | Not started | P0 |
| Sub-agents | Not started | P2 |
| Additional MCPs | Not started | P2 |

---

## Phase 1: Foundation (P0 - Critical Path)

### 1.1 Project Configuration

- [ ] **1.1.1** Create `.gitignore` with Python, Node, Docker, and IDE exclusions
- [ ] **1.1.2** Create `.env.example` with all required environment variables
- [ ] **1.1.3** Create root `docker-compose.yml` with all services
- [ ] **1.1.4** Verify `.env` is in `.gitignore` (security)

### 1.2 Backend Scaffolding

- [ ] **1.2.1** Populate `Backend/requirements.txt` with dependencies
- [ ] **1.2.2** Create `Backend/Dockerfile` for Python 3.12 FastAPI app
- [ ] **1.2.3** Create directory structure:
  ```
  Backend/
  ├── src/
  │   ├── __init__.py
  │   ├── api/
  │   │   ├── __init__.py
  │   │   ├── main.py          # FastAPI app entry
  │   │   ├── routes/
  │   │   │   ├── __init__.py
  │   │   │   ├── health.py
  │   │   │   ├── tasks.py
  │   │   │   └── webhook.py
  │   │   └── dependencies.py
  │   ├── agents/
  │   │   ├── __init__.py
  │   │   ├── orchestrator.py
  │   │   └── base.py
  │   ├── models/
  │   │   ├── __init__.py
  │   │   ├── task.py
  │   │   └── conversation.py
  │   ├── services/
  │   │   ├── __init__.py
  │   │   ├── task_service.py
  │   │   └── telegram_service.py
  │   └── config/
  │       ├── __init__.py
  │       └── settings.py
  ├── tests/
  │   └── __init__.py
  ├── requirements.txt
  ├── Dockerfile
  └── README.md
  ```
- [ ] **1.2.4** Implement `config/settings.py` with Pydantic Settings
- [ ] **1.2.5** Implement basic FastAPI app with health endpoint
- [ ] **1.2.6** Test backend container builds and runs

### 1.3 Frontend Scaffolding

- [ ] **1.3.1** Initialize Next.js project with TypeScript
- [ ] **1.3.2** Install and configure Tailwind CSS + DaisyUI
- [ ] **1.3.3** Install Zustand for state management
- [ ] **1.3.4** Create `Frontend/Dockerfile` for Next.js production build
- [ ] **1.3.5** Create basic directory structure:
  ```
  Frontend/
  ├── src/
  │   ├── app/
  │   │   ├── layout.tsx
  │   │   ├── page.tsx
  │   │   └── globals.css
  │   ├── components/
  │   │   └── ui/
  │   ├── stores/
  │   │   └── taskStore.ts
  │   └── lib/
  │       └── api.ts
  ├── package.json
  ├── Dockerfile
  └── README.md
  ```
- [ ] **1.3.6** Create basic landing page with DaisyUI components
- [ ] **1.3.7** Test frontend container builds and runs

### 1.4 Docker Integration

- [ ] **1.4.1** Complete `docker-compose.yml` with frontend, backend, db services
- [ ] **1.4.2** Configure Docker networking between services
- [ ] **1.4.3** Set up PostgreSQL with volume persistence
- [ ] **1.4.4** Test full stack with `docker-compose up`

**Phase 1 Milestone**: Backend and frontend containers run, health endpoints accessible.

---

## Phase 2: Orchestrator Agent (P0 - Core Functionality)

### 2.1 Agent Foundation

- [ ] **2.1.1** Research Claude Agents SDK patterns and best practices
- [ ] **2.1.2** Implement `agents/base.py` with common agent utilities
- [ ] **2.1.3** Implement `agents/orchestrator.py` with basic Claude SDK integration
- [ ] **2.1.4** Create orchestrator system prompt for task routing
- [ ] **2.1.5** Implement conversation context management

### 2.2 Task System

- [ ] **2.2.1** Implement `models/task.py` with Pydantic models
- [ ] **2.2.2** Create database schema for tasks (SQLAlchemy or raw SQL)
- [ ] **2.2.3** Implement `services/task_service.py` for CRUD operations
- [ ] **2.2.4** Add task status tracking and updates
- [ ] **2.2.5** Implement task execution queue (async)

### 2.3 API Integration

- [ ] **2.3.1** Implement `/api/chat` endpoint for orchestrator interaction
- [ ] **2.3.2** Implement `/api/tasks` CRUD endpoints
- [ ] **2.3.3** Add WebSocket endpoint for real-time updates (optional)
- [ ] **2.3.4** Test orchestrator via API calls (curl/Postman)

**Phase 2 Milestone**: Can send messages to orchestrator via API, receive responses, tasks persist.

---

## Phase 3: Telegram Integration (P0 - Primary Interface)

### 3.1 Telegram Bot Setup

- [ ] **3.1.1** Create Telegram bot via BotFather, obtain token
- [ ] **3.1.2** Implement `services/telegram_service.py`
- [ ] **3.1.3** Implement webhook endpoint `/webhook/telegram`
- [ ] **3.1.4** Configure Telegram webhook URL (ngrok for dev, or local polling)
- [ ] **3.1.5** Implement user authentication (whitelist by Telegram user ID)

### 3.2 Message Flow

- [ ] **3.2.1** Parse incoming Telegram messages
- [ ] **3.2.2** Route messages to orchestrator
- [ ] **3.2.3** Format orchestrator responses for Telegram
- [ ] **3.2.4** Send responses back via Telegram API
- [ ] **3.2.5** Handle long-running tasks with progress updates

### 3.3 Telegram MCP (Alternative)

- [ ] **3.3.1** Evaluate existing Telegram MCP implementations
- [ ] **3.3.2** If using MCP: integrate as sidecar container
- [ ] **3.3.3** Configure orchestrator to use Telegram MCP tools

**Phase 3 Milestone**: Can text the bot from phone, receive intelligent responses.

---

## Phase 4: Frontend Dashboard (P1 - Enhanced UX)

### 4.1 Core Pages

- [ ] **4.1.1** Create dashboard layout with navigation
- [ ] **4.1.2** Implement task list page with status indicators
- [ ] **4.1.3** Implement conversation history page
- [ ] **4.1.4** Implement agent status/health page

### 4.2 API Integration

- [ ] **4.2.1** Create API client in `lib/api.ts`
- [ ] **4.2.2** Implement Zustand stores for tasks and conversations
- [ ] **4.2.3** Add real-time updates (polling or WebSocket)
- [ ] **4.2.4** Implement manual task execution from UI

### 4.3 Polish

- [ ] **4.3.1** Add loading states and error handling
- [ ] **4.3.2** Implement responsive design
- [ ] **4.3.3** Add dark/light mode toggle (DaisyUI themes)

**Phase 4 Milestone**: Web dashboard shows live task status and conversation history.

---

## Phase 5: Sub-Agents & MCPs (P2 - Extended Functionality)

### 5.1 GitHub Agent

- [ ] **5.1.1** Research/select GitHub MCP implementation
- [ ] **5.1.2** Implement `agents/github_agent.py`
- [ ] **5.1.3** Configure GitHub MCP container
- [ ] **5.1.4** Add handoff from orchestrator to GitHub agent
- [ ] **5.1.5** Test issue creation, PR management via Telegram

### 5.2 Obsidian Agent

- [ ] **5.2.1** Research Obsidian MCP options (file-based)
- [ ] **5.2.2** Implement `agents/obsidian_agent.py`
- [ ] **5.2.3** Configure Obsidian vault path mounting
- [ ] **5.2.4** Test note creation and search via Telegram

### 5.3 Calendar Agent

- [ ] **5.3.1** Research Google Calendar MCP
- [ ] **5.3.2** Implement `agents/calendar_agent.py`
- [ ] **5.3.3** Configure OAuth for Google Calendar API
- [ ] **5.3.4** Test event creation and availability check

### 5.4 Email Agent

- [ ] **5.4.1** Research Gmail/IMAP MCP options
- [ ] **5.4.2** Implement `agents/email_agent.py`
- [ ] **5.4.3** Configure email credentials securely
- [ ] **5.4.4** Implement approval flow for sending emails

**Phase 5 Milestone**: All sub-agents functional, accessible via Telegram commands.

---

## Phase 6: Hardening & Polish (P2)

### 6.1 Security

- [ ] **6.1.1** Audit all credential handling
- [ ] **6.1.2** Implement action confirmation for destructive operations
- [ ] **6.1.3** Add rate limiting
- [ ] **6.1.4** Security scan dependencies

### 6.2 Reliability

- [ ] **6.2.1** Add comprehensive error handling
- [ ] **6.2.2** Implement retry logic for external APIs
- [ ] **6.2.3** Add structured logging
- [ ] **6.2.4** Create health check endpoints for all services

### 6.3 Testing

- [ ] **6.3.1** Write unit tests for services
- [ ] **6.3.2** Write integration tests for API endpoints
- [ ] **6.3.3** Write E2E tests for critical flows
- [ ] **6.3.4** Set up CI/CD pipeline (optional)

### 6.4 Documentation

- [ ] **6.4.1** Update README with final setup instructions
- [ ] **6.4.2** Document all API endpoints
- [ ] **6.4.3** Create user guide for Telegram commands
- [ ] **6.4.4** Document MCP configuration

**Phase 6 Milestone**: Production-ready deployment on local network.

---

## Recommended Execution Order

```
Week 1-2: Phase 1 (Foundation)
   └── Get containers running, basic API working

Week 2-3: Phase 2 (Orchestrator)
   └── Core agent logic, task persistence

Week 3-4: Phase 3 (Telegram)
   └── Primary interface functional

Week 4-5: Phase 4 (Dashboard)
   └── Visual monitoring and control

Week 5+: Phase 5-6 (Sub-agents & Polish)
   └── Extended functionality, hardening
```

---

## Dependencies & Blockers

| Dependency | Required For | Notes |
|------------|--------------|-------|
| Anthropic API Key | Phase 2+ | Required for orchestrator |
| Telegram Bot Token | Phase 3 | Create via BotFather |
| GitHub Token | Phase 5.1 | Personal access token |
| Google OAuth | Phase 5.3 | Calendar API access |
| Email Credentials | Phase 5.4 | App password or OAuth |

---

## Next Immediate Actions

1. **Populate `.gitignore`** - Security and cleanliness
2. **Populate `.env.example`** - Document required variables
3. **Create `Backend/requirements.txt`** - Pin dependencies
4. **Create `Backend/Dockerfile`** - Container definition
5. **Implement basic FastAPI app** - Health endpoint
6. **Test with `docker-compose up`** - Validate foundation
