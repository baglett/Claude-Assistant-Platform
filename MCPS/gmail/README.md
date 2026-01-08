# Gmail MCP Server

MCP server providing Gmail API tools for the Claude Assistant Platform.

## Features

- **Message Management**: List, search, read, and trash messages
- **Email Sending**: Send new emails with HTML support
- **Draft Support**: Create and send draft emails
- **Label Management**: List, create, and apply labels
- **Archive & Read Status**: Archive messages, mark read/unread

## Tools

| Tool | Description |
|------|-------------|
| `check_auth_status` | Check OAuth authentication status |
| `get_auth_url` | Get OAuth authorization URL |
| `list_labels` | List all mailbox labels |
| `create_label` | Create a new label |
| `list_messages` | List messages with optional filtering |
| `get_message` | Get full message content by ID |
| `search_messages` | Search using Gmail query syntax |
| `send_email` | Send a new email |
| `trash_message` | Move message to trash |
| `mark_as_read` | Mark message as read |
| `mark_as_unread` | Mark message as unread |
| `archive_message` | Archive a message |
| `add_label` | Add label to message |
| `remove_label` | Remove label from message |
| `create_draft` | Create draft email |
| `send_draft` | Send existing draft |
| `list_drafts` | List all drafts |

## Gmail Search Syntax

The `search_messages` and `list_messages` tools support Gmail's search operators:

| Operator | Example | Description |
|----------|---------|-------------|
| `from:` | `from:alice@example.com` | Messages from sender |
| `to:` | `to:bob@example.com` | Messages to recipient |
| `subject:` | `subject:meeting` | Subject contains word |
| `is:unread` | `is:unread` | Unread messages |
| `is:starred` | `is:starred` | Starred messages |
| `has:attachment` | `has:attachment` | Has attachments |
| `label:` | `label:work` | Has specific label |
| `after:` | `after:2024/01/01` | After date |
| `newer_than:` | `newer_than:7d` | Newer than period |

## Setup

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing (can share with Calendar MCP)
3. Enable the **Gmail API**
4. Go to **APIs & Services** > **Credentials**
5. Create **OAuth 2.0 Client ID** (Desktop application type)
6. Add `gmail.modify` scope to OAuth consent screen

### 2. Environment Variables

```env
# Required
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret

# Optional
GMAIL_TOKEN_PATH=./data/gmail_token.json
GMAIL_OAUTH_PORT=8086
GMAIL_MCP_HOST=0.0.0.0
GMAIL_MCP_PORT=8085
```

### 3. First-Time Authentication

```bash
# Local development
uv sync
uv run python -m src.server

# Get auth URL and complete OAuth flow
curl http://localhost:8085/auth/url
```

## Development

```bash
# Install dependencies
make dev

# Run server
make run

# Run tests
make test

# Lint code
make lint
```

## Docker

```bash
# Build image
make docker-build

# Run container
docker run -p 8085:8085 \
  -e GMAIL_CLIENT_ID=$GMAIL_CLIENT_ID \
  -e GMAIL_CLIENT_SECRET=$GMAIL_CLIENT_SECRET \
  -v gmail-data:/app/data \
  gmail-mcp
```

## API Endpoints

### Health Check
```
GET /health
```

### Authentication
```
GET /auth/status
GET /auth/url
POST /auth/authenticate
```

### Labels
```
GET /labels
```

### Messages
```
GET /messages
GET /messages/{id}
POST /messages/send
DELETE /messages/{id}
```

### Drafts
```
GET /drafts
```

## Security Notes

- OAuth tokens are stored locally in the configured token path
- Email content is never logged
- Use minimal required scopes (`gmail.modify`)
- Regularly review and revoke unused access

## License

MIT
