# Requirements Specification

## Functional Requirements

### FR-1: Telegram Interface

- **FR-1.1**: System shall receive text messages from a Telegram bot
- **FR-1.2**: System shall send responses back via the same Telegram bot
- **FR-1.3**: System shall support conversation context across multiple messages
- **FR-1.4**: System shall handle message queuing when processing long tasks

### FR-2: Orchestrator Agent

- **FR-2.1**: System shall parse natural language requests to determine user intent
- **FR-2.2**: System shall route requests to appropriate sub-agents based on intent
- **FR-2.3**: System shall aggregate responses from multiple sub-agents when needed
- **FR-2.4**: System shall maintain conversation history for context

### FR-3: Sub-Agent System

- **FR-3.1**: GitHub Agent shall create issues, PRs, and manage repositories
- **FR-3.2**: Email Agent shall read, draft, and send emails
- **FR-3.3**: Calendar Agent shall create events and check availability
- **FR-3.4**: Obsidian Agent shall create and search notes in vault
- **FR-3.5**: Each sub-agent shall only access its designated MCP server

### FR-4: Todo Management

- **FR-4.1**: System shall create todo items from user requests
- **FR-4.2**: System shall persist todos across restarts
- **FR-4.3**: System shall track todo status (pending, in_progress, completed)
- **FR-4.4**: System shall execute todos automatically or on-demand
- **FR-4.5**: System shall report task completion status to user

### FR-5: MCP Integration

- **FR-5.1**: System shall connect to MCP servers for external tool access
- **FR-5.2**: System shall support adding new MCP servers without code changes
- **FR-5.3**: System shall handle MCP server failures gracefully

---

## Non-Functional Requirements

### NFR-1: Technology Stack

**Project Structure**: Monorepo with `frontend/` and `backend/` directories

#### Backend Stack

| Requirement | Specification |
|-------------|---------------|
| **NFR-1.1** | Python 3.14 or higher |
| **NFR-1.2** | FastAPI for HTTP/API endpoints |
| **NFR-1.3** | Docker containerization for all services |
| **NFR-1.4** | Docker Compose for orchestration |
| **NFR-1.5** | Claude Agents SDK for agent implementation |
| **NFR-1.6** | uv for Python package and project management |

#### Frontend Stack

| Requirement | Specification |
|-------------|---------------|
| **NFR-1.7** | Next.js (React framework) |
| **NFR-1.8** | TypeScript for type safety |
| **NFR-1.9** | Tailwind CSS for styling |
| **NFR-1.10** | DaisyUI for component library |
| **NFR-1.11** | Zustand for state management |
| **NFR-1.12** | React 18+ |

### NFR-2: Performance

- **NFR-2.1**: System shall respond to simple queries within 10 seconds
- **NFR-2.2**: System shall handle concurrent requests without blocking
- **NFR-2.3**: System shall provide progress updates for long-running tasks

### NFR-3: Security

- **NFR-3.1**: All API keys and tokens shall be stored in environment variables
- **NFR-3.2**: System shall run only on local network (not exposed to internet)
- **NFR-3.3**: Telegram bot shall authenticate users before processing requests
- **NFR-3.4**: Sensitive actions shall require explicit user confirmation

### NFR-4: Reliability

- **NFR-4.1**: System shall recover gracefully from container restarts
- **NFR-4.2**: System shall persist critical state (todos, conversation history)
- **NFR-4.3**: System shall log errors for debugging

### NFR-5: Maintainability

- **NFR-5.1**: Code shall follow PEP 8 style guidelines
- **NFR-5.2**: All functions shall include type hints
- **NFR-5.3**: All public APIs shall include docstrings
- **NFR-5.4**: Code shall be organized in modular, testable components

---

## Integration Requirements

### IR-1: MCP Servers (Planned)

| MCP Server | Purpose | Priority |
|------------|---------|----------|
| Telegram | User interface | P0 (Required) |
| GitHub | Repository management | P1 (High) |
| Obsidian | Note-taking integration | P1 (High) |
| Google Calendar | Scheduling | P2 (Medium) |
| Email (Gmail/IMAP) | Email management | P2 (Medium) |

### IR-2: External APIs

- **IR-2.1**: Anthropic Claude API for agent reasoning
- **IR-2.2**: Telegram Bot API for messaging

---

## Constraints

- **C-1**: Must run on local network infrastructure
- **C-2**: Must use Claude as the LLM provider (Anthropic API)
- **C-3**: All services must be containerized
- **C-4**: Must support Windows host environment (Docker Desktop)
