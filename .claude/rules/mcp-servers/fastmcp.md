---
paths:
  - "MCPS/**/*.py"
---

# MCP Server Development

## Overview

MCP (Model Context Protocol) servers provide tool interfaces for AI agents to interact with external services. Each MCP server is a containerized Python service using the FastMCP framework.

## Project Structure

```
MCPS/
├── telegram/
│   ├── src/
│   │   └── server.py      # FastMCP server implementation
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md
├── github/
├── gmail/
├── google-calendar/
└── motion/
```

## FastMCP Tool Definition

```python
from mcp.server.fastmcp import FastMCP

# Initialize server
mcp = FastMCP("telegram-mcp")

@mcp.tool()
async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str | None = None,
) -> dict:
    """
    Send a text message to a Telegram chat.

    Args:
        chat_id: The unique identifier for the target chat.
        text: Text of the message to be sent (1-4096 characters).
        parse_mode: Mode for parsing entities (HTML, Markdown, MarkdownV2).

    Returns:
        dict: The sent message object from Telegram API.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            },
        )
        response.raise_for_status()
        return response.json()["result"]
```

## HTTP Endpoints

Expose tools as HTTP endpoints for debugging and direct access:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class SendMessageRequest(BaseModel):
    chat_id: int
    text: str
    parse_mode: str | None = None

@app.post("/tools/send_message")
async def http_send_message(request: SendMessageRequest) -> dict:
    """HTTP endpoint wrapper for send_message tool."""
    try:
        return await send_message(
            chat_id=request.chat_id,
            text=request.text,
            parse_mode=request.parse_mode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "telegram-mcp"}
```

## Dockerfile Pattern

```dockerfile
# Multi-stage build for smaller image
FROM python:3.14-slim AS builder

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.14-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ ./src/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run server
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Environment Variables

Each MCP server requires specific credentials:

```python
import os
from functools import lru_cache

@lru_cache
def get_settings():
    return {
        "bot_token": os.environ["TELEGRAM_BOT_TOKEN"],
        "api_base": f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}",
    }
```

## Error Handling

Return structured errors for better debugging:

```python
@mcp.tool()
async def get_chat_info(chat_id: int) -> dict:
    """Get information about a Telegram chat."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_settings()['api_base']}/getChat",
                params={"chat_id": chat_id},
            )
            response.raise_for_status()
            return response.json()["result"]
    except httpx.HTTPStatusError as e:
        return {
            "error": True,
            "status_code": e.response.status_code,
            "message": f"Telegram API error: {e.response.text}",
        }
    except Exception as e:
        return {
            "error": True,
            "message": str(e),
        }
```

## Docker Compose Integration

```yaml
services:
  telegram-mcp:
    build: ./MCPS/telegram
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    networks:
      - internal
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Key Rules

1. **One service per MCP** - Focused, single-purpose servers
2. **FastMCP for tools** - Use @mcp.tool() decorator
3. **HTTP fallback** - Expose tools as HTTP endpoints
4. **Health checks** - Required for orchestration
5. **Environment variables** - Never hardcode credentials
6. **Structured errors** - Return error objects, don't raise

## Anti-Patterns

- **DON'T** combine multiple services in one MCP server
- **DON'T** hardcode API keys or credentials (use environment variables)
- **DON'T** raise exceptions from tools (return structured error objects)
- **DON'T** skip health check endpoints
- **DON'T** skip HTTP fallback endpoints (needed for debugging)
- **DON'T** use complex nested types in tool parameters (keep flat)
- **DON'T** forget docstrings on tools (they become MCP descriptions)
- **DON'T** expose MCP ports externally in production (internal network only)
- **DON'T** skip validation on tool inputs (use Pydantic)
