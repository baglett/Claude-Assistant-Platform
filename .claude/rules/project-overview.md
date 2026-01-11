# Project Overview

## Architecture

This is a self-hosted AI assistant platform using the Claude API with an orchestrator pattern:

- **Orchestrator Agent**: Central coordinator that parses user intent and delegates to sub-agents
- **Sub-Agents**: Specialized agents (GitHub, Email, Calendar, Obsidian, Todo) with focused capabilities
- **MCP Servers**: Tool providers for external service integration (containerized)
- **Telegram**: Primary user interface via long-polling bot
- **FastAPI**: REST API layer for internal communication

## Hard Requirements

- **Python 3.14+**: Use modern features (type hints, match statements, structural pattern matching)
- **FastAPI**: For ALL HTTP endpoints
- **Docker Compose**: For orchestration - all services must be containerized
- **uv**: For Python package management (NOT pip)
  - `uv add <package>` to add dependencies
  - `uv sync` to install from lockfile
  - `uv run <command>` to execute in venv

## Key Patterns

1. **Agent Handoffs**: Orchestrator delegates to sub-agents, never executes domain tasks directly
2. **MCP Tool Calls**: All external service interactions go through MCP servers
3. **Todo Persistence**: Tasks survive restarts, stored in PostgreSQL
4. **Approval Flows**: Destructive actions require user confirmation via Telegram
5. **Execution Logging**: All agent invocations are tracked with tokens, thinking, tool calls

## Environment Variables

See `.env.example` for the complete list. Key variables:

- `ANTHROPIC_API_KEY` - Claude API access (required)
- `TELEGRAM_BOT_TOKEN` - Production Telegram bot
- `TELEGRAM_DEV_BOT_TOKEN` - Development bot (use when `APP_ENV=development`)
- `TELEGRAM_ALLOWED_USER_IDS` - Comma-separated whitelist
- `DATABASE_URL` - PostgreSQL connection string

## Development vs Production

- Set `APP_ENV=development` for local work (uses dev bot token)
- Set `APP_ENV=production` for deployed instances
- Dev and prod use separate Telegram bots to prevent polling conflicts

## Documentation References

- `DOCUMENTATION/ARCHITECTURE.md` - Detailed system architecture
- `DOCUMENTATION/REQUIREMENTS.md` - Functional and non-functional requirements
- `DOCUMENTATION/DEPLOYMENT.md` - Deployment configuration
- `README.md` - Getting started guide
