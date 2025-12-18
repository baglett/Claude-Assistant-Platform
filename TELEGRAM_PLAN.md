# Telegram Integration Plan

## Overview

Integrate Telegram as a user interface for the Claude Assistant Platform. Users can message the bot from anywhere (off-network), and the assistant responds via Telegram.

## Architecture

```
[User Phone] → [Telegram Cloud] → [Backend Poller] → [Orchestrator]
                                                           ↓
[User Phone] ← [Telegram Cloud] ← [Telegram MCP Server] ←─┘
```

**Two components:**

1. **Telegram Poller** (in Backend) - Long-polls Telegram API for incoming messages
2. **Telegram MCP Server** (separate Docker container) - Provides tools for sending messages back

## Prerequisites

1. Create a Telegram bot via [@BotFather](https://t.me/botfather) → get `TELEGRAM_BOT_TOKEN`
2. Get your Telegram user ID via [@userinfobot](https://t.me/userinfobot) → for whitelist

## New Files to Create

```
Backend/src/services/telegram/
├── __init__.py              # Package exports
├── models.py                # Pydantic models (TelegramMessage, TelegramUpdate, etc.)
├── poller.py                # TelegramPoller class (long-polling loop)
└── message_handler.py       # Routes messages to orchestrator, sends responses via MCP

docker/telegram-mcp/
├── Dockerfile               # Python 3.12-slim container
├── pyproject.toml           # Dependencies (mcp, httpx, fastapi)
└── src/
    ├── __init__.py
    └── server.py            # FastMCP server with send_message, get_chat_info tools
```

## Files to Modify

| File | Changes |
|------|---------|
| `Backend/src/config/settings.py` | Add Telegram settings (bot token, allowed users, MCP URL) |
| `Backend/src/api/main.py` | Start/stop poller in lifespan, store in app.state |
| `docker-compose.yml` | Add telegram-mcp service |
| `.env.example` | Add TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_IDS |

## Environment Variables

```bash
# -----------------------------------------------------------------------------
# Telegram Bot Configuration
# -----------------------------------------------------------------------------
# Create a bot via @BotFather on Telegram to get this token
TELEGRAM_BOT_TOKEN=your-bot-token-here

# Comma-separated list of allowed Telegram user IDs (get via @userinfobot)
# Only users in this list can interact with the bot
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321

# Polling configuration
TELEGRAM_POLLING_TIMEOUT=30

# -----------------------------------------------------------------------------
# Telegram MCP Server (internal Docker network)
# -----------------------------------------------------------------------------
TELEGRAM_MCP_HOST=telegram-mcp
TELEGRAM_MCP_PORT=8080
```

## Implementation Steps

### Phase 1: Backend Telegram Service

1. Update `settings.py` with Telegram configuration properties
2. Create `Backend/src/services/telegram/models.py` - Pydantic models for:
   - `TelegramUser` - User info (id, username, first_name)
   - `TelegramChat` - Chat info (id, type, title)
   - `TelegramMessage` - Incoming message (text, chat, from_user)
   - `TelegramUpdate` - Update wrapper (update_id, message)
3. Create `Backend/src/services/telegram/poller.py` - TelegramPoller class:
   - Long-polls Telegram API via `getUpdates`
   - Filters messages by allowed user IDs
   - Routes to message handler
4. Create `Backend/src/services/telegram/message_handler.py`:
   - Receives messages from poller
   - Calls orchestrator with `conversation_id = f"telegram_{chat_id}"`
   - Sends response via Telegram MCP
5. Create `Backend/src/services/telegram/__init__.py` - Package exports
6. Update `Backend/src/api/main.py`:
   - Start poller as background task in lifespan
   - Store in `app.state.telegram_poller`
   - Cancel task on shutdown

### Phase 2: Telegram MCP Server

1. Create `docker/telegram-mcp/` directory structure
2. Create `docker/telegram-mcp/pyproject.toml`:
   ```toml
   [project]
   name = "telegram-mcp"
   dependencies = ["mcp>=1.24.0", "httpx>=0.28.0", "fastapi>=0.115.0", "uvicorn>=0.32.0"]
   ```
3. Create `docker/telegram-mcp/src/server.py` - FastMCP server with tools:
   - `send_message(chat_id, text, parse_mode, reply_to_message_id)` - Send text message
   - `get_chat_info(chat_id)` - Get chat details
   - `send_typing_action(chat_id)` - Show typing indicator
4. Create `docker/telegram-mcp/Dockerfile` - Python 3.12-slim

### Phase 3: Docker Integration

1. Update `docker-compose.yml` - Add telegram-mcp service:
   ```yaml
   telegram-mcp:
     build: ./docker/telegram-mcp
     environment:
       - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
     networks:
       - claude-network
     healthcheck:
       test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
   ```
2. Update backend service to depend on telegram-mcp
3. Update `.env.example` with Telegram variables

### Phase 4: Documentation

1. Update CLAUDE.md with Telegram setup instructions
2. Update README.md with Telegram section
3. Update ARCHITECTURE.md with Telegram components

## Key Patterns

### Conversation Tracking

```python
# Use chat_id as conversation_id for context persistence
conversation_id = f"telegram_{message.chat.id}"
response, tokens = await orchestrator.process_message(message.text, conversation_id)
```

### User Authentication

```python
# Check whitelist before processing
if user_id not in self._allowed_users:
    logger.warning(f"Unauthorized user {user_id}")
    return
```

### Background Task

```python
# Start poller as cancellable task
poller_task = asyncio.create_task(telegram_poller.start())

# On shutdown
poller_task.cancel()
try:
    await poller_task
except asyncio.CancelledError:
    pass
```

### MCP Tool Definition

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("telegram-mcp")

@mcp.tool()
async def send_message(chat_id: int, text: str) -> dict:
    """Send a message to a Telegram chat."""
    # Call Telegram API
    return {"success": True, "message_id": result["message_id"]}
```

## Security Considerations

- **User Whitelist**: Only users in `TELEGRAM_ALLOWED_USER_IDS` can interact
- **Token Security**: Bot token stored only in environment variables, never logged
- **Network Isolation**: MCP server only accessible within Docker network
- **Input Validation**: All Telegram data validated via Pydantic models

## Testing Checklist

- [ ] Create bot via @BotFather
- [ ] Get user ID via @userinfobot
- [ ] Set `TELEGRAM_BOT_TOKEN` in .env
- [ ] Set `TELEGRAM_ALLOWED_USER_IDS` in .env
- [ ] Run `docker-compose up`
- [ ] Send message to bot
- [ ] Verify response received
- [ ] Test with unauthorized user (should be rejected)

## Potential Enhancements

- [ ] Message queuing for high volume
- [ ] Rate limiting with exponential backoff
- [ ] Message splitting for responses > 4096 chars
- [ ] Support for Telegram commands (/start, /help, /clear)
- [ ] Inline keyboard for confirmations
- [ ] Voice message transcription
