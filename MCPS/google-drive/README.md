# Google Drive MCP Server

MCP server providing Google Drive API tools for the Claude Assistant Platform.

## Features

- **File Operations**: Upload, download, list, and delete files
- **Folder Management**: Create folders, move files between folders
- **Sharing**: Generate shareable links, manage file permissions
- **Search**: Find files by name, type, or content
- **Resume Storage**: Dedicated support for storing generated resumes

## Prerequisites

- Python 3.12+
- Google Cloud Console project with Drive API enabled
- OAuth 2.0 credentials (Desktop App type)

## Setup

### 1. Google Cloud Console Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials:
   - Application type: Desktop App
   - Download the credentials JSON

### 2. Environment Variables

Create a `.env` file in the project root (or parent directory):

```bash
# Google Drive OAuth (required)
GOOGLE_DRIVE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret

# Optional: For containerized deployments
GOOGLE_DRIVE_REFRESH_TOKEN=your-refresh-token

# Server configuration
GOOGLE_DRIVE_MCP_HOST=0.0.0.0
GOOGLE_DRIVE_MCP_PORT=8087
```

### 3. Installation

```bash
# Using uv (recommended)
make install

# Or directly
uv sync --no-dev
```

### 4. Authentication

For local development, run the server and complete OAuth:

```bash
make run
```

A browser window will open for authentication. After granting permissions,
the token will be saved to `data/drive_token.json`.

For production/Docker, set `GOOGLE_DRIVE_REFRESH_TOKEN` environment variable.

## Usage

### Local Development

```bash
make run
```

Server starts on `http://localhost:8087`

### Docker

```bash
# Build image
make docker-build

# Run container
make docker-run
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/status` | GET | Authentication status |
| `/auth/url` | GET | Get OAuth URL |
| `/files` | GET | List files |
| `/files` | POST | Upload file |
| `/files/{id}` | GET | Get file info |
| `/files/{id}` | DELETE | Delete file |
| `/folders` | POST | Create folder |
| `/share/{id}` | POST | Create shareable link |

## MCP Tools

| Tool | Description |
|------|-------------|
| `check_auth_status` | Check authentication status |
| `get_auth_url` | Get OAuth authorization URL |
| `upload_file` | Upload a file to Drive |
| `list_files` | List files in a folder |
| `get_file` | Get file metadata |
| `delete_file` | Move file to trash |
| `create_folder` | Create a new folder |
| `create_shareable_link` | Generate a shareable link |
| `search_files` | Search for files |

## Project Structure

```
google-drive/
├── src/
│   ├── __init__.py
│   ├── auth.py        # OAuth 2.0 authentication
│   ├── client.py      # Drive API client wrapper
│   ├── models.py      # Pydantic models
│   └── server.py      # FastMCP server
├── data/              # Token storage (gitignored)
├── Dockerfile
├── Makefile
├── pyproject.toml
└── README.md
```

## Development

```bash
# Install dev dependencies
make dev

# Run linting
make lint

# Format code
make format

# Run tests
make test
```

## License

MIT
