# Telegram MCP Server

MCP (Model Context Protocol) server providing Telegram Bot API tools for the Claude Assistant Platform.

## Overview

This service exposes Telegram Bot API functionality as MCP tools that can be called by agents for **proactive messaging** - sending messages initiated by the system rather than in response to user input.

**Note:** User replies (responses to incoming messages) are handled directly by the backend's `TelegramMessageHandler` using the Telegram Bot API for lower latency. This MCP server is specifically for agent-initiated notifications, reminders, and alerts.

## Use Cases

- **Scheduled reminders**: "Hey, your todo is due!"
- **Task completion notifications**: "I finished processing your request"
- **Proactive alerts**: "PR #42 was merged - want me to deploy?"
- **Daily summaries**: "Here's what happened today..."

## Features

- **send_message** - Send text messages to Telegram chats
- **get_chat_info** - Get information about a Telegram chat
- **send_typing_action** - Show typing indicator in a chat

## Requirements

- Python 3.12+
- `TELEGRAM_BOT_TOKEN` environment variable

## Installation

```powershell
# Install dependencies
make install
```

## Usage

### Running the Server

```powershell
# Production mode
make run

# Development mode (with hot-reload)
make dev
```

The server runs on port 8080 by default.

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/tools/send_message` | POST | Send a message |
| `/tools/get_chat_info` | POST | Get chat information |
| `/tools/send_typing_action` | POST | Send typing indicator |

### Example: Send a Message

```bash
curl -X POST http://localhost:8080/tools/send_message \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 123456789, "text": "Hello from MCP!"}'
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Required |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8080` |

## Development

```powershell
# Run linter
make lint

# Format code
make format

# Run tests
make test
```

## Docker

This service is designed to run in Docker as part of the Claude Assistant Platform:

```powershell
docker-compose up telegram-mcp
```

## Architecture

```
User Message Flow (Low Latency):
  Telegram → Poller → MessageHandler → Direct API → Telegram

Agent-Initiated Flow (via MCP):
  Agent decides to notify → MCP tool call → This server → Telegram
```
