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
   ```

4. **Start the Platform:**
   ```bash
   docker-compose up -d
   ```

5. **Test the Bot:**
   - Open a chat with your bot in Telegram
   - Send a message like "Hello!"
   - The bot should respond via Claude

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
├── docker/                   # Docker configurations
│   └── telegram-mcp/         # Telegram MCP server
│       ├── src/server.py     # FastMCP server
│       ├── pyproject.toml
│       └── Dockerfile
├── docker-compose.yml        # Container orchestration
└── .env.example              # Environment template
```

## Documentation

- [Architecture](./ARCHITECTURE.md) - System design and component overview
- [Requirements](./REQUIREMENTS.md) - Functional and technical requirements
- [Development Guide](./CLAUDE.md) - Development notes and AI-assisted changelog

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please read the contributing guidelines before submitting PRs.
