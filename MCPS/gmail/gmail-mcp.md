# Gmail MCP Server - Implementation Plan

## Research Summary

### Official Google MCP Support
Google has announced official MCP support, but **Gmail is NOT currently listed** among the available services.

Reference: [Google Cloud MCP Announcement](https://cloud.google.com/blog/products/ai-machine-learning/announcing-official-mcp-support-for-google-services)

### Community MCP Servers Evaluated

| Repository | Language | License | Tools | Key Features |
|------------|----------|---------|-------|--------------|
| [jeremyjordan/mcp-gmail](https://github.com/jeremyjordan/mcp-gmail) | Python | MIT | 9 | Clean MCP SDK implementation, resources support |
| [GongRzhe/Gmail-MCP-Server](https://github.com/GongRzhe/Gmail-MCP-Server) | Node.js | MIT | 18 | Attachments, filters, batch ops, international chars |
| [theposch/gmail-mcp](https://github.com/theposch/gmail-mcp) | Python | GPL-3.0 | 15+ | Drafts, folders, archive, comprehensive labels |
| [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) | Python | - | Multi | Full Workspace (Gmail + Calendar + Drive + Docs) |

---

## Recommendation

**Build our own MCP server** following the established pattern from our Google Calendar MCP:
1. **Pattern**: Python, FastMCP, FastAPI, Pydantic
2. **Feature reference**: Combine best features from `jeremyjordan/mcp-gmail` and `theposch/gmail-mcp`
3. **Shared auth**: Can share OAuth credentials with Google Calendar MCP (same Google Cloud project)

### Rationale
- Consistent with our existing MCP pattern (Telegram, Google Calendar)
- MIT-compatible licensing (avoid GPL-3.0)
- Can use same Google Cloud OAuth app as Calendar MCP
- Full control over security and feature set

---

## Architecture

### Directory Structure
```
MCPS/gmail/
├── src/
│   ├── __init__.py
│   ├── server.py           # FastMCP server + FastAPI HTTP endpoints
│   ├── client.py           # Gmail API client wrapper
│   ├── auth.py             # OAuth 2.0 flow handler
│   ├── models.py           # Pydantic models for messages, labels
│   └── utils.py            # Email parsing, MIME handling
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   └── test_tools.py
├── Dockerfile
├── Makefile
├── pyproject.toml
├── README.md
└── gmail-mcp.md            # This file
```

### Technology Stack
| Component | Technology | Notes |
|-----------|------------|-------|
| MCP Protocol | `mcp>=1.9.0` (FastMCP) | Matches other MCPs |
| HTTP Server | `fastapi>=0.115.0` + `uvicorn` | For direct HTTP access |
| Google API | `google-api-python-client` | Gmail API v1 |
| OAuth | `google-auth-oauthlib` | Desktop app flow |
| HTTP Client | `httpx>=0.28.0` | Async HTTP requests |
| Validation | `pydantic>=2.10.0` | Request/response models |

---

## MCP Tools Definition

### Phase 1: Core Tools (MVP)

| Tool | Description | Priority |
|------|-------------|----------|
| `list_messages` | List messages with query filtering | P0 |
| `get_message` | Get full message by ID | P0 |
| `search_messages` | Search using Gmail query syntax | P0 |
| `send_email` | Send a new email | P0 |
| `trash_message` | Move message to trash | P0 |
| `list_labels` | List all available labels | P0 |

### Phase 2: Enhanced Features

| Tool | Description | Priority |
|------|-------------|----------|
| `create_draft` | Create a draft email | P1 |
| `send_draft` | Send an existing draft | P1 |
| `mark_as_read` | Mark message as read | P1 |
| `mark_as_unread` | Mark message as unread | P1 |
| `add_label` | Add label to message | P1 |
| `remove_label` | Remove label from message | P1 |
| `archive_message` | Archive a message | P1 |

### Phase 3: Advanced Features

| Tool | Description | Priority |
|------|-------------|----------|
| `create_label` | Create a new label | P2 |
| `delete_label` | Delete a label | P2 |
| `get_attachment` | Download attachment | P2 |
| `reply_to_message` | Reply to a thread | P2 |
| `forward_message` | Forward a message | P2 |
| `batch_modify` | Batch modify messages | P2 |

---

## Tool Specifications

### `list_messages`
```python
@mcp.tool()
async def list_messages(
    query: str | None = None,
    max_results: int = 10,
    label_ids: list[str] | None = None,
    include_spam_trash: bool = False,
) -> dict:
    """
    List messages in the user's mailbox.

    Args:
        query: Gmail search query (e.g., "from:alice@example.com is:unread").
        max_results: Maximum number of messages to return (default: 10).
        label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"]).
        include_spam_trash: Include spam and trash in results.

    Returns:
        Dictionary containing list of message summaries.
    """
```

### `get_message`
```python
@mcp.tool()
async def get_message(
    message_id: str,
    format: str = "full",
) -> dict:
    """
    Get a specific message by ID.

    Args:
        message_id: The message ID.
        format: Response format - "full", "metadata", "minimal", or "raw".

    Returns:
        Dictionary containing message details including headers, body, attachments.
    """
```

### `send_email`
```python
@mcp.tool()
async def send_email(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html_body: str | None = None,
    reply_to: str | None = None,
    thread_id: str | None = None,
) -> dict:
    """
    Send a new email.

    Args:
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Plain text body content.
        cc: CC recipients.
        bcc: BCC recipients.
        html_body: HTML body (optional, for rich formatting).
        reply_to: Reply-to address.
        thread_id: Thread ID if replying to existing thread.

    Returns:
        Dictionary containing sent message details.
    """
```

### `search_messages`
```python
@mcp.tool()
async def search_messages(
    query: str,
    max_results: int = 25,
) -> dict:
    """
    Search messages using Gmail query syntax.

    Supports operators like:
    - from:, to:, subject:, has:attachment
    - is:unread, is:starred, is:important
    - before:, after:, newer_than:, older_than:
    - label:, category:, filename:

    Args:
        query: Gmail search query string.
        max_results: Maximum results to return (default: 25).

    Returns:
        Dictionary containing matching messages with snippets.
    """
```

### `create_draft`
```python
@mcp.tool()
async def create_draft(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    html_body: str | None = None,
) -> dict:
    """
    Create a draft email without sending.

    Args:
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Plain text body content.
        cc: CC recipients.
        html_body: HTML body (optional).

    Returns:
        Dictionary containing draft details including draft ID.
    """
```

---

## Authentication Strategy

### OAuth 2.0 Scopes
```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",  # Read, compose, send, delete
    # OR more restrictive:
    # "https://www.googleapis.com/auth/gmail.readonly",  # Read-only
    # "https://www.googleapis.com/auth/gmail.send",      # Send only
    # "https://www.googleapis.com/auth/gmail.compose",   # Create drafts and send
]
```

### Shared Credentials with Calendar MCP
Since both Gmail and Calendar use Google OAuth, we can:
1. Use the same Google Cloud project
2. Add Gmail API scope to existing OAuth consent screen
3. Store separate token files per service

---

## Environment Variables

```env
# Gmail MCP Configuration
GMAIL_CLIENT_ID=<oauth-client-id>           # Can be same as Calendar
GMAIL_CLIENT_SECRET=<oauth-client-secret>   # Can be same as Calendar
GMAIL_TOKEN_PATH=/app/data/gmail_token.json
GMAIL_OAUTH_PORT=8086

# Server Configuration
GMAIL_MCP_HOST=0.0.0.0
GMAIL_MCP_PORT=8085
```

---

## Docker Integration

### Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install .

COPY src/ ./src/

RUN mkdir -p /app/data
VOLUME ["/app/data"]

ENV GMAIL_TOKEN_PATH=/app/data/token.json
ENV GMAIL_MCP_HOST=0.0.0.0
ENV GMAIL_MCP_PORT=8085

EXPOSE 8085

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8085/health').raise_for_status()"

CMD ["python", "-m", "src.server"]
```

### docker-compose.yml Addition
```yaml
services:
  gmail-mcp:
    build:
      context: ./MCPS/gmail
      dockerfile: Dockerfile
    container_name: claude-assistant-gmail-mcp
    environment:
      - GMAIL_CLIENT_ID=${GMAIL_CLIENT_ID}
      - GMAIL_CLIENT_SECRET=${GMAIL_CLIENT_SECRET}
      - GMAIL_TOKEN_PATH=/app/data/token.json
      - GMAIL_MCP_PORT=8085
    volumes:
      - gmail-data:/app/data
    ports:
      - "8085:8085"
    networks:
      - internal

volumes:
  gmail-data:
```

---

## Gmail Query Syntax Reference

For the `search_messages` and `list_messages` tools:

| Operator | Example | Description |
|----------|---------|-------------|
| `from:` | `from:alice@example.com` | Messages from sender |
| `to:` | `to:bob@example.com` | Messages to recipient |
| `subject:` | `subject:meeting` | Subject contains word |
| `is:unread` | `is:unread` | Unread messages |
| `is:starred` | `is:starred` | Starred messages |
| `is:important` | `is:important` | Important messages |
| `has:attachment` | `has:attachment` | Has attachments |
| `label:` | `label:work` | Has specific label |
| `after:` | `after:2024/01/01` | After date |
| `before:` | `before:2024/12/31` | Before date |
| `newer_than:` | `newer_than:7d` | Newer than period |
| `older_than:` | `older_than:1m` | Older than period |
| `filename:` | `filename:pdf` | Attachment filename |
| `larger:` | `larger:5M` | Larger than size |
| `smaller:` | `smaller:1M` | Smaller than size |

---

## Implementation Phases

### Phase 1: Foundation (MVP)
- [ ] Set up project structure matching Calendar MCP pattern
- [ ] Implement OAuth 2.0 flow with token storage
- [ ] Create GmailClient wrapper class
- [ ] Implement core tools: `list_messages`, `get_message`, `send_email`
- [ ] Add `search_messages`, `trash_message`, `list_labels`
- [ ] FastAPI HTTP endpoints
- [ ] Dockerfile and docker-compose integration

### Phase 2: Drafts & Labels
- [ ] Implement `create_draft`, `send_draft`
- [ ] Add `mark_as_read`, `mark_as_unread`
- [ ] Implement `add_label`, `remove_label`, `archive_message`
- [ ] Unit tests

### Phase 3: Advanced Features
- [ ] Add attachment download support
- [ ] Implement `create_label`, `delete_label`
- [ ] Add `reply_to_message`, `forward_message`
- [ ] Batch operations
- [ ] Integration tests

---

## Security Considerations

1. **OAuth Token Security**
   - Store tokens encrypted at rest
   - Separate token files from Calendar
   - Use minimal required scopes

2. **Email Content Handling**
   - Never log email content/bodies
   - Sanitize HTML in email bodies
   - Handle attachments carefully (don't persist)

3. **Rate Limiting**
   - Gmail API quota: 250 quota units/second
   - Implement exponential backoff
   - Batch operations when possible

---

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api/reference/rest)
- [Gmail Search Operators](https://support.google.com/mail/answer/7190)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [jeremyjordan/mcp-gmail](https://github.com/jeremyjordan/mcp-gmail) - Reference implementation
- [theposch/gmail-mcp](https://github.com/theposch/gmail-mcp) - Feature reference
