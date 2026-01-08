# Claude Assistant Platform

A self-hosted, local network AI assistant platform powered by the Claude Agents SDK. Interact with Claude via Telegram from your phone to manage tasks, automate workflows, and integrate with your personal tools.

## Overview

This platform provides a personal AI assistant that:

- Receives commands via Telegram from your phone
- Uses an orchestrator agent to parse requests and delegate to specialized sub-agents
- Integrates with external services via MCP (Model Context Protocol) servers
- Manages and executes todo items autonomously

## Features

- **Telegram Interface**: Text your assistant from anywhere on your phone
- **Orchestrator Agent**: Intelligent task routing and management
- **Sub-Agent System**: Specialized agents for different domains (GitHub, Email, Calendar, Obsidian)
- **MCP Integration**: Extensible tool access via Model Context Protocol
- **Todo Management**: Persistent task tracking with automatic execution
- **Local Network Deployment**: Runs on your own infrastructure

## Tech Stack

### Backend
- **Language**: Python 3.12+
- **API Framework**: FastAPI
- **Agent Framework**: Claude Agents SDK
- **Containerization**: Docker & Docker Compose
- **Message Interface**: Telegram Bot API (via MCP)

### Frontend
- **Framework**: Next.js
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: DaisyUI
- **State Management**: Zustand
- **UI Library**: React 18+

## Quick Start

### Prerequisites

- Python 3.12 or higher
- Docker and Docker Compose
- Anthropic API key
- Telegram Bot Token (from @BotFather)
- Your Telegram User ID (from @userinfobot)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-assistant-platform.git
cd claude-assistant-platform

# Copy environment template
cp .env.example .env

# Configure your environment variables
# Edit .env with your API keys and tokens

# Start with Docker Compose
docker-compose up -d
```

### Configuration

See `.env.example` for all available configuration options.

### Telegram Setup

1. **Create a Telegram Bot:**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot` and follow the prompts
   - Copy the bot token provided

2. **Get Your User ID:**
   - Search for `@userinfobot` in Telegram
   - Send `/start` to get your user ID

3. **Configure Environment:**
   ```bash
   # In your .env file
   TELEGRAM_BOT_TOKEN=your-bot-token-here
   TELEGRAM_ALLOWED_USER_IDS=your-user-id-here

   # Optional: Add multiple users (comma-separated)
   TELEGRAM_ALLOWED_USER_IDS=123456789,987654321
   ```

4. **Start the Platform:**
   ```bash
   docker-compose up -d
   ```

5. **Test the Bot:**
   - Open a chat with your bot in Telegram
   - Send `/start` for a welcome message
   - Send a message like "Hello!" to start chatting with Claude

### Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and initial setup |
| `/help` | Display available commands |
| `/new` | Start a fresh conversation (clears context) |
| `/clear` | Clear messages in current conversation |
| `/status` | Show session info and message count |

### Todo Management

The assistant can create and manage todos through natural conversation:

```
You: "Add a task to review the PR for the auth feature"
Assistant: I've created a todo "Review PR for auth feature" assigned to the GitHub agent.

You: "What's on my todo list?"
Assistant: Here are your pending todos:
  1. Review PR for auth feature (GitHub, priority: normal)
  2. Send weekly report email (Email, priority: high)

You: "Mark the first one as done"
Assistant: Done! I've marked "Review PR for auth feature" as completed.
```

**Agent Assignment:** Todos can be assigned to specialized agents:
- `github` - Repository and code tasks
- `email` - Email operations
- `calendar` - Scheduling and events
- `obsidian` - Note-taking
- `orchestrator` - General tasks

**Background Execution:** A background executor periodically checks for pending todos and processes them through the appropriate agent.

### Telegram Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | (required) |
| `TELEGRAM_ALLOWED_USER_IDS` | Comma-separated list of allowed user IDs | (required) |
| `TELEGRAM_POLLING_TIMEOUT` | Long-polling timeout in seconds | 30 |
| `TELEGRAM_ENABLED` | Enable/disable Telegram integration | true |
| `TELEGRAM_MCP_HOST` | Telegram MCP server hostname | telegram-mcp |
| `TELEGRAM_MCP_PORT` | Telegram MCP server port | 8080 |

### Todo Executor Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TODO_EXECUTOR_INTERVAL` | Seconds between checking for pending todos | 30 |
| `TODO_EXECUTOR_BATCH_SIZE` | Max todos to process per cycle | 5 |
| `TODO_EXECUTOR_ENABLED` | Enable/disable background executor | true |

### Troubleshooting Telegram

**Bot not responding:**
- Check that your user ID is in `TELEGRAM_ALLOWED_USER_IDS`
- Verify the bot token is correct with `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Check backend logs: `docker logs claude-assistant-backend`

**Connection errors:**
- Ensure the `telegram-mcp` container is healthy: `docker ps`
- Check MCP server logs: `docker logs claude-assistant-telegram-mcp`

**Message not being processed:**
- The bot only responds to text messages (no images/stickers yet)
- Unauthorized users are logged but receive no response

## Jenkins CI/CD Deployment

The platform includes a Jenkinsfile for automated deployment to your infrastructure.

### Jenkins Credentials Configuration

Before running the pipeline, configure the following credentials in Jenkins:

1. **Navigate to credentials:**
   - Jenkins → Manage Jenkins → Credentials → System → Global credentials (unrestricted)

2. **Add each credential as "Secret text":**

   | Credential ID | Description | How to Obtain |
   |---------------|-------------|---------------|
   | `anthropic-api-key` | Anthropic API key for Claude | [console.anthropic.com](https://console.anthropic.com/) |
   | `telegram-bot-token` | Production Telegram bot token | Create via [@BotFather](https://t.me/botfather) |
   | `telegram-allowed-user-ids` | Comma-separated Telegram user IDs | Get from [@userinfobot](https://t.me/userinfobot) |
   | `postgres-db-user` | PostgreSQL username | Your database configuration |
   | `postgres-db-password` | PostgreSQL password | Your database configuration |
   | `motion-api-key` | Motion API key for task management | [app.usemotion.com/web/settings/api](https://app.usemotion.com/web/settings/api) |

3. **Adding a credential step-by-step:**
   - Click "Add Credentials"
   - Kind: **Secret text**
   - Scope: **Global**
   - Secret: *paste your secret value*
   - ID: *use the exact ID from the table above*
   - Description: *optional but helpful*
   - Click "Create"

### Port Configuration

The pipeline deploys containers with the following port mappings:

| Service | Internal Port | External Port |
|---------|---------------|---------------|
| Backend | 8000 | 8000 |
| Frontend | 3000 | 3000 |
| Telegram MCP | 8080 | 8081 |
| Motion MCP | 8081 | 8082 |

### Pipeline Stages

1. **Prepare** - Determine version from git commit hash
2. **Verify Docker CLI** - Confirm Docker is available
3. **Create Docker Network** - Create `claude-assistant-network` if needed
4. **Build Docker Images** - Build all images in parallel (arm64)
5. **Push Docker Images** - Push to local registry
6. **Stop and Remove Containers** - Clean up existing containers
7. **Start Telegram MCP** - Start Telegram MCP server
8. **Start Motion MCP** - Start Motion MCP server
9. **Start Backend** - Start main backend API
10. **Start Frontend** - Start Next.js frontend
11. **Verify Deployment** - Display deployment status

### Running the Pipeline

```bash
# Trigger manually from Jenkins UI
# Or configure webhook for automatic deployment on push

# The pipeline expects:
# - Docker registry at 192.168.50.35:5000
# - PostgreSQL at 192.168.50.35:5432
# - ARM64 architecture (Orange Pi / Raspberry Pi)
```

### Customizing Deployment

Edit the `Jenkinsfile` environment variables to match your infrastructure:

```groovy
environment {
    DOCKER_REGISTRY = '192.168.50.35:5000'  // Your registry
    POSTGRES_HOST = '192.168.50.35'          // Your DB host
    POSTGRES_PORT = '5432'                   // Your DB port
}
```

## Project Structure

```
claude-assistant-platform/
├── Frontend/                 # Next.js frontend application
│   ├── src/
│   │   ├── app/              # Next.js app router
│   │   ├── components/       # React components
│   │   ├── stores/           # Zustand state stores
│   │   └── lib/              # Utilities and helpers
│   ├── package.json
│   └── Dockerfile
├── Backend/                  # Python backend application
│   ├── src/
│   │   ├── agents/           # Agent definitions (orchestrator)
│   │   ├── api/              # FastAPI endpoints
│   │   ├── config/           # Settings and configuration
│   │   ├── services/         # Business logic services
│   │   │   └── telegram/     # Telegram integration
│   │   │       ├── models.py       # Pydantic models
│   │   │       ├── poller.py       # Long-polling client
│   │   │       └── message_handler.py  # Message routing
│   │   └── models/           # Data models and schemas
│   ├── tests/                # Test suite
│   ├── pyproject.toml        # Python dependencies (uv)
│   └── Dockerfile
├── MCPS/                     # MCP (Model Context Protocol) servers
│   ├── telegram/             # Telegram MCP server
│   │   ├── src/server.py     # FastMCP server for Telegram
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── motion/               # Motion MCP server
│       ├── src/
│       │   ├── server.py     # FastMCP server for Motion API
│       │   ├── client.py     # Motion API client with rate limiting
│       │   ├── rate_limiter.py  # Rate limit enforcement
│       │   └── models/       # Pydantic models for Motion API
│       ├── pyproject.toml
│       └── Dockerfile
├── Jenkinsfile               # CI/CD pipeline configuration
├── docker-compose.yml        # Container orchestration
└── .env.example              # Environment template
```

## Documentation

- [Architecture](./ARCHITECTURE.md) - System design and component overview
- [Requirements](./REQUIREMENTS.md) - Functional and technical requirements
- [Deployment Reference](./DEPLOYMENT.md) - Ports, containers, credentials, and infrastructure
- [Development Guide](./CLAUDE.md) - Development notes and AI-assisted changelog

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please read the contributing guidelines before submitting PRs.
