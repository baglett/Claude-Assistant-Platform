# Obsidian MCP Server

MCP (Model Context Protocol) server for interacting with Obsidian vaults through the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin.

## Overview

This MCP server enables AI agents to:
- Read, create, update, and delete notes in an Obsidian vault
- Search notes by content or using Dataview DQL queries
- Manage periodic notes (daily, weekly, monthly, etc.)
- List files and directories in the vault
- Execute Obsidian commands
- Get the currently active file

## Architecture

### How It Works

The MCP server does **not** access your vault files directly. Instead, it communicates with the **Obsidian application** via HTTP, and Obsidian handles all file operations.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Machine                              │
│                                                                  │
│  ┌──────────────┐      HTTP API       ┌──────────────────────┐  │
│  │ Obsidian MCP │ ──────────────────► │     Obsidian App     │  │
│  │   Server     │    localhost:27124  │                      │  │
│  │  (Docker or  │                     │  ┌────────────────┐  │  │
│  │   local)     │                     │  │ Local REST API │  │  │
│  └──────────────┘                     │  │    Plugin      │  │  │
│                                       │  └────────────────┘  │  │
│                                       │          │           │  │
│                                       │          ▼           │  │
│                                       │  ┌────────────────┐  │  │
│                                       │  │  Your Vault    │  │  │
│                                       │  │  (filesystem)  │  │  │
│                                       │  └────────────────┘  │  │
│                                       └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Requirements

| Component | Location | Notes |
|-----------|----------|-------|
| **Obsidian App** | Must be running | The desktop application |
| **Local REST API Plugin** | Inside Obsidian | Exposes the HTTP API |
| **Your Vault** | Accessible to Obsidian | Wherever Obsidian opens it from |
| **MCP Server** | Can reach Obsidian's API | Same machine or network-accessible |

### Key Limitation

**Obsidian must be running** for the MCP to work. The MCP server cannot:
- Read vault files directly (it uses the API)
- Start Obsidian for you
- Work when Obsidian is closed

## Deployment Options

### Option 1: MCP Server Runs Locally (Recommended)

The simplest setup - MCP server and Obsidian on the same machine.

```env
OBSIDIAN_HOST=127.0.0.1
OBSIDIAN_PORT=27124
```

**Pros:**
- Simple configuration
- No network exposure
- Works with any vault location

**Cons:**
- MCP only works on the machine running Obsidian

### Option 2: MCP Server in Docker (Same Machine)

MCP runs in a container, Obsidian runs on the host.

```env
OBSIDIAN_HOST=host.docker.internal  # Docker Desktop (Windows/Mac)
# or use your machine's IP for Linux
OBSIDIAN_PORT=27124
```

**Pros:**
- Containerized deployment
- Consistent environment
- Easy to deploy with other services

**Cons:**
- Still requires Obsidian running on host
- Slightly more complex networking

### Option 3: Remote Obsidian (Advanced - Not Recommended)

One central Obsidian instance accessible from multiple machines.

```env
OBSIDIAN_HOST=192.168.1.100  # Remote machine IP
OBSIDIAN_PORT=27124
```

**Requirements:**
- Expose Local REST API to network (security risk!)
- Configure firewall/VPN
- All MCP servers point to that one Obsidian instance

**Why not recommended:**
- The Local REST API plugin is designed for localhost
- Security implications of exposing the API
- Single point of failure

## Multi-Machine Vault Sync (Git/GitHub)

If you sync your Obsidian vault via Git across multiple machines, each machine operates independently:

```
Machine A (Work)                    Machine B (Home)
┌─────────────────────┐            ┌─────────────────────┐
│ Vault (git clone)   │◄──────────►│ Vault (git clone)   │
│        ▲            │   GitHub   │        ▲            │
│        │            │            │        │            │
│   Obsidian App      │            │   Obsidian App      │
│        ▲            │            │        ▲            │
│        │            │            │        │            │
│   MCP Server        │            │   MCP Server        │
│   (localhost)       │            │   (localhost)       │
└─────────────────────┘            └─────────────────────┘
```

### What Each Machine Needs

1. Its own copy of the vault (via git clone)
2. Obsidian running with the Local REST API plugin
3. The MCP server configured to connect to `localhost:27124`
4. The same `OBSIDIAN_API_KEY` (or each machine can have its own)

### Typical Workflow

```
1. You're on Machine A (Work)
   - git pull (get latest vault changes)
   - Open Obsidian (auto-loads vault)
   - MCP server connects to localhost Obsidian
   - Work with notes via AI agent
   - git commit && git push (sync changes)

2. Switch to Machine B (Home)
   - git pull (get changes from Machine A)
   - Open Obsidian on Machine B
   - MCP server on Machine B connects to its localhost
   - Continue working
   - git commit && git push
```

### Configuration Per Machine

Each machine uses the same environment variables:

```env
# Same on all machines
OBSIDIAN_HOST=127.0.0.1
OBSIDIAN_PORT=27124
OBSIDIAN_PROTOCOL=https
OBSIDIAN_VERIFY_SSL=false

# API key can be the same or different per machine
# (each Obsidian instance generates its own key)
OBSIDIAN_API_KEY=your-api-key-for-this-machine
```

## Alternative Approaches (Trade-offs)

This MCP uses the Local REST API approach. Here's how it compares to alternatives:

| Approach | Obsidian Running? | Features | Complexity |
|----------|-------------------|----------|------------|
| **Local REST API** (this MCP) | Required | Full (commands, Dataview, plugins) | Medium |
| **Direct File Access** | Not required | Basic (read/write only) | Low |
| **Obsidian URI Scheme** | Required | Limited (open files only) | Low |
| **CouchDB LiveSync** | Not required | Full sync, multi-device | High |

We chose Local REST API because:
- Full access to Obsidian features (commands, Dataview queries)
- Proper handling of frontmatter and metadata
- Plugin ecosystem integration
- Official plugin with active maintenance

## Prerequisites

### 1. Obsidian Local REST API Plugin

The server communicates with Obsidian through the **Local REST API** plugin (v3.2.0+).

#### Installation

1. Open Obsidian
2. Go to **Settings** > **Community plugins**
3. Click **Browse** and search for "Local REST API"
4. Install and enable the plugin

#### Configuration

1. Go to **Settings** > **Local REST API**
2. Note the **API Key** (you'll need this for the MCP server)
3. Note the server settings:
   - Default HTTPS port: `27124` (uses self-signed certificate)
   - Default HTTP port: `27123` (if enabled)

### 2. Optional: Dataview Plugin

For advanced search queries using Dataview DQL, install the **Dataview** plugin:

1. Open Obsidian
2. Go to **Settings** > **Community plugins**
3. Search for "Dataview" and install it

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OBSIDIAN_API_KEY` | Yes | - | API key from Local REST API plugin settings |
| `OBSIDIAN_HOST` | No | `127.0.0.1` | Hostname where Obsidian is running |
| `OBSIDIAN_PORT` | No | `27124` | Port for the Local REST API |
| `OBSIDIAN_PROTOCOL` | No | `https` | Protocol (`http` or `https`) |
| `OBSIDIAN_VERIFY_SSL` | No | `false` | Verify SSL certificates |

### Example `.env` Configuration

```env
# Obsidian MCP Configuration
OBSIDIAN_API_KEY=your-api-key-from-obsidian-settings
OBSIDIAN_HOST=127.0.0.1
OBSIDIAN_PORT=27124
OBSIDIAN_PROTOCOL=https
OBSIDIAN_VERIFY_SSL=false
```

## Available Tools

### Note Operations

| Tool | Description |
|------|-------------|
| `read_note` | Read a note's content and optionally its metadata |
| `create_note` | Create a new note or append to existing |
| `update_note` | Update a note using patch operations (append, prepend, replace) |
| `delete_note` | Delete a note from the vault |

### Vault Navigation

| Tool | Description |
|------|-------------|
| `list_vault_files` | List files and directories in the vault |
| `get_active_file` | Get the currently open file in Obsidian |
| `open_file` | Open a file in Obsidian |

### Search

| Tool | Description |
|------|-------------|
| `search_vault` | Simple text search across all notes |
| `search_dataview` | Execute Dataview DQL queries (requires Dataview plugin) |

### Periodic Notes

| Tool | Description |
|------|-------------|
| `get_daily_note` | Get a daily note (today or specific date) |
| `get_weekly_note` | Get the current weekly note |
| `append_to_daily_note` | Append content to today's daily note |

### Commands

| Tool | Description |
|------|-------------|
| `list_commands` | List all available Obsidian commands |
| `execute_command` | Execute an Obsidian command by ID |

### System

| Tool | Description |
|------|-------------|
| `check_connection` | Verify connection to Obsidian |

## Tool Usage Examples

### Reading a Note

```python
# Simple read
result = await read_note(path="Projects/my-project.md")

# Read with metadata (frontmatter, tags, file stats)
result = await read_note(path="Projects/my-project.md", include_metadata=True)
```

### Creating Notes

```python
# Create a new note
result = await create_note(
    path="Notes/new-note.md",
    content="# New Note\n\nThis is my new note.",
    overwrite=False  # Append if exists
)
```

### Updating Notes

```python
# Append to end of note
result = await update_note(
    path="Notes/existing-note.md",
    content="\n## New Section\n\nAdded content.",
    operation="append"
)

# Insert under a specific heading
result = await update_note(
    path="Notes/existing-note.md",
    content="- New task item",
    operation="append",
    target_type="heading",
    target="Tasks"
)
```

### Searching

```python
# Simple text search
result = await search_vault(query="project meeting", context_length=150)

# Dataview DQL query
result = await search_dataview(
    query='TABLE file.name, file.mtime FROM "Projects" WHERE status = "active" SORT file.mtime DESC'
)
```

### Daily Notes

```python
# Get today's daily note
result = await get_daily_note()

# Get a specific day's note
result = await get_daily_note(year=2025, month=1, day=7)

# Append to today's daily note
result = await append_to_daily_note(content="\n- Completed important task")
```

## Running the Server

### Local Development

```powershell
# Install dependencies
make install

# Run with auto-reload
make dev

# Or run normally
make run
```

### Docker

```powershell
# Build the image
docker build -t obsidian-mcp .

# Run the container
docker run -p 8080:8080 \
  -e OBSIDIAN_API_KEY=your-api-key \
  -e OBSIDIAN_HOST=host.docker.internal \
  obsidian-mcp
```

**Note for Docker**: Since Obsidian runs on your host machine, use `host.docker.internal` (on Docker Desktop) or your machine's IP address as `OBSIDIAN_HOST`.

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  obsidian-mcp:
    build:
      context: ./MCPS/obsidian
      dockerfile: Dockerfile
    environment:
      - OBSIDIAN_API_KEY=${OBSIDIAN_API_KEY}
      - OBSIDIAN_HOST=host.docker.internal  # or your host IP
      - OBSIDIAN_PORT=27124
      - OBSIDIAN_PROTOCOL=https
      - OBSIDIAN_VERIFY_SSL=false
    ports:
      - "8081:8080"
    networks:
      - claude-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

## API Endpoints

The server exposes both MCP tools and HTTP endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Obsidian connection status |
| `/tools/list_files` | GET | List vault files |
| `/tools/read_note` | GET | Read a note |
| `/tools/search` | POST | Search the vault |

## Troubleshooting

### Connection Issues

1. **Verify Obsidian is running** with the Local REST API plugin enabled
2. **Check the API key** matches the one in Obsidian settings
3. **Verify the port** - HTTPS uses 27124, HTTP uses 27123
4. **SSL certificate issues** - Set `OBSIDIAN_VERIFY_SSL=false` for self-signed certs

### Common Errors

| Error | Solution |
|-------|----------|
| "Connection refused" | Ensure Obsidian is running with the plugin enabled |
| "401 Unauthorized" | Check your API key is correct |
| "SSL certificate verify failed" | Set `OBSIDIAN_VERIFY_SSL=false` |
| "404 Not Found" | Check the file path is correct |

### Checking Connection

```powershell
# Using make
make status

# Or curl directly
curl http://localhost:8080/status
```

## Security Considerations

1. **API Key Protection**: Never commit your API key to version control
2. **Network Access**: The Local REST API only listens on localhost by default
3. **SSL**: Use HTTPS (port 27124) for encrypted communication
4. **Firewall**: If exposing the MCP server, ensure proper firewall rules

## References

- [Obsidian Local REST API Plugin](https://github.com/coddingtonbear/obsidian-local-rest-api)
- [Local REST API Documentation](https://coddingtonbear.github.io/obsidian-local-rest-api/)
- [Dataview Plugin](https://github.com/blacksmithgu/obsidian-dataview)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## Community MCP Implementations Referenced

This implementation was informed by these community projects:

- [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) - Python MCP with 7 tools
- [cyanheads/obsidian-mcp-server](https://github.com/cyanheads/obsidian-mcp-server) - TypeScript MCP with caching
- [StevenStavrakis/obsidian-mcp](https://github.com/StevenStavrakis/obsidian-mcp) - Simple MCP with direct vault access
