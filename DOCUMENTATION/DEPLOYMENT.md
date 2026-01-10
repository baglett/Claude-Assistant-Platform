# Claude Assistant Platform - Deployment Reference

This document contains infrastructure configuration, port mappings, and deployment details for the Claude Assistant Platform.

## Table of Contents

- [Port Configuration](#port-configuration)
- [Container Reference](#container-reference)
- [Network Configuration](#network-configuration)
- [Volume Mounts](#volume-mounts)
- [Jenkins Credentials](#jenkins-credentials)
- [Google OAuth Setup](#google-oauth-setup)
- [Environment Variables](#environment-variables)
- [Infrastructure Endpoints](#infrastructure-endpoints)
- [First-Time OAuth Authentication](#first-time-oauth-authentication)

---

## Port Configuration

### Production Deployment (Jenkins Pipeline)

| Service | Container Port | Host Port | Protocol | Description |
|---------|---------------|-----------|----------|-------------|
| Backend | 8000 | 8000 | HTTP | Main FastAPI backend |
| Frontend | 3000 | 3000 | HTTP | Next.js web interface |
| Telegram MCP | 8080 | 8081 | HTTP | Telegram Bot API tools |
| Motion MCP | 8081 | 8082 | HTTP | Motion task management tools |
| Google Calendar MCP | 8084 | 8084 | HTTP | Google Calendar API tools |
| Gmail MCP | 8085 | 8085 | HTTP | Gmail API tools |
| PostgreSQL | 5432 | 5432 | TCP | Database (external to Docker) |

### Local Development (docker-compose)

| Service | Container Port | Host Port | Protocol | Description |
|---------|---------------|-----------|----------|-------------|
| Backend | 8000 | 8000 | HTTP | Main FastAPI backend |
| Frontend | 3000 | 3000 | HTTP | Next.js web interface |
| Telegram MCP | 8080 | — | HTTP | Internal only |
| Motion MCP | 8081 | — | HTTP | Internal only |
| Google Calendar MCP | 8084 | — | HTTP | Internal only |
| Gmail MCP | 8085 | — | HTTP | Internal only |
| PostgreSQL | 5432 | 5432 | TCP | Database container |

### Port Allocation Strategy

- **8000-8009**: Backend services and APIs
- **8080-8089**: MCP servers (internal communication)
  - 8080: Telegram MCP
  - 8081: Motion MCP
  - 8084: Google Calendar MCP
  - 8085: Gmail MCP
- **3000-3099**: Frontend services
- **5432**: PostgreSQL database

---

## Container Reference

### Production Containers

| Container Name | Image Name | Registry Path |
|----------------|------------|---------------|
| `claude-assistant-backend` | `claude-assistant-backend` | `192.168.50.35:5000/claude-assistant-backend` |
| `claude-assistant-frontend` | `claude-assistant-frontend` | `192.168.50.35:5000/claude-assistant-frontend` |
| `claude-assistant-telegram-mcp` | `claude-assistant-telegram-mcp` | `192.168.50.35:5000/claude-assistant-telegram-mcp` |
| `claude-assistant-motion-mcp` | `claude-assistant-motion-mcp` | `192.168.50.35:5000/claude-assistant-motion-mcp` |
| `claude-assistant-google-calendar-mcp` | `claude-assistant-google-calendar-mcp` | `192.168.50.35:5000/claude-assistant-google-calendar-mcp` |
| `claude-assistant-gmail-mcp` | `claude-assistant-gmail-mcp` | `192.168.50.35:5000/claude-assistant-gmail-mcp` |

### Development Containers

| Container Name | Build Context | Dockerfile |
|----------------|---------------|------------|
| `claude-assistant-backend` | `./Backend` | `Backend/Dockerfile` |
| `claude-assistant-frontend` | `./Frontend` | `Frontend/Dockerfile` |
| `claude-assistant-telegram-mcp` | `./MCPS/telegram` | `MCPS/telegram/Dockerfile` |
| `claude-assistant-motion-mcp` | `./MCPS/motion` | `MCPS/motion/Dockerfile` |
| `claude-assistant-google-calendar-mcp` | `./MCPS/google-calendar` | `MCPS/google-calendar/Dockerfile` |
| `claude-assistant-gmail-mcp` | `./MCPS/gmail` | `MCPS/gmail/Dockerfile` |
| `claude-assistant-db` | `postgres:16-alpine` | — |

---

## Network Configuration

### Docker Network

| Property | Value |
|----------|-------|
| Network Name | `claude-assistant-network` |
| Driver | `bridge` |
| Scope | All platform containers |

### Internal Service Discovery

Services communicate using container names as hostnames:

| Service | Internal Hostname | Internal Port |
|---------|-------------------|---------------|
| Backend | `claude-assistant-backend` | 8000 |
| Telegram MCP | `claude-assistant-telegram-mcp` | 8080 |
| Motion MCP | `claude-assistant-motion-mcp` | 8081 |
| Google Calendar MCP | `claude-assistant-google-calendar-mcp` | 8084 |
| Gmail MCP | `claude-assistant-gmail-mcp` | 8085 |
| Database | `db` (dev) / `192.168.50.35` (prod) | 5432 |

---

## Volume Mounts

### Persistent Volumes

| Volume Name | Container | Mount Path | Purpose |
|-------------|-----------|------------|---------|
| `claude-assistant-pgdata` | `db` | `/var/lib/postgresql/data` | PostgreSQL data |
| `claude-assistant-motion-data` | `motion-mcp` | `/app/data` | Rate limit database |
| `claude-assistant-google-calendar-data` | `google-calendar-mcp` | `/app/data` | OAuth tokens |
| `claude-assistant-gmail-data` | `gmail-mcp` | `/app/data` | OAuth tokens |
| `motion-data` | `motion-mcp` (prod) | `/app/data` | Rate limit database |
| `google-calendar-data` | `google-calendar-mcp` (prod) | `/app/data` | OAuth tokens |
| `gmail-data` | `gmail-mcp` (prod) | `/app/data` | OAuth tokens |

### Development Bind Mounts

| Host Path | Container | Mount Path | Purpose |
|-----------|-----------|------------|---------|
| `./Backend/src` | `backend` | `/app/src:ro` | Hot reload |

---

## Jenkins Credentials

### Required Credentials

Configure in: **Jenkins → Manage Jenkins → Credentials → System → Global credentials**

| Credential ID | Type | Description | Source |
|---------------|------|-------------|--------|
| `anthropic-api-key` | Secret text | Anthropic API key | [console.anthropic.com](https://console.anthropic.com/) |
| `telegram-bot-token` | Secret text | Telegram bot token | [@BotFather](https://t.me/botfather) |
| `telegram-allowed-user-ids` | Secret text | Allowed user IDs (comma-separated) | [@userinfobot](https://t.me/userinfobot) |
| `postgres-db-user` | Secret text | PostgreSQL username | Database config |
| `postgres-db-password` | Secret text | PostgreSQL password | Database config |
| `motion-api-key` | Secret text | Motion API key | [app.usemotion.com](https://app.usemotion.com/web/settings/api) |
| `google-calendar-client-id` | Secret text | Google OAuth Client ID | [Google Cloud Console](https://console.cloud.google.com/) |
| `google-calendar-client-secret` | Secret text | Google OAuth Client Secret | [Google Cloud Console](https://console.cloud.google.com/) |
| `google-calendar-refresh-token` | Secret text | Google OAuth Refresh Token | Run MCP locally, complete OAuth |
| `gmail-client-id` | Secret text | Google OAuth Client ID | [Google Cloud Console](https://console.cloud.google.com/) |
| `gmail-client-secret` | Secret text | Google OAuth Client Secret | [Google Cloud Console](https://console.cloud.google.com/) |
| `gmail-refresh-token` | Secret text | Google OAuth Refresh Token | Run MCP locally, complete OAuth |

**Notes:**
- You can use the same OAuth Client ID/Secret for both Google Calendar and Gmail if they're from the same Google Cloud project with both APIs enabled.
- The refresh tokens are different for each service (they are scoped to different APIs).

### Adding Credentials

1. Click "Add Credentials"
2. Kind: **Secret text**
3. Scope: **Global**
4. Secret: *paste value*
5. ID: *exact ID from table above*
6. Click "Create"

---

## Google OAuth Setup

Both Google Calendar MCP and Gmail MCP require OAuth 2.0 credentials from Google Cloud Console. You can use a single set of credentials for both services.

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name: `Claude Assistant Platform`
4. Click "Create"

### Step 2: Enable APIs

1. Go to **APIs & Services** → **Library**
2. Search for and enable:
   - **Google Calendar API**
   - **Gmail API**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. User Type: **External** (or **Internal** for Google Workspace)
3. Fill in required fields:
   - App name: `Claude Assistant Platform`
   - User support email: *your email*
   - Developer contact: *your email*
4. Click "Save and Continue"
5. **Scopes**: Click "Add or Remove Scopes" and add:
   - `https://www.googleapis.com/auth/calendar` (full calendar access)
   - `https://www.googleapis.com/auth/gmail.modify` (read/write email, no delete)
6. Click "Save and Continue"
7. **Test users**: Add your Google account email
8. Click "Save and Continue"

### Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app** (important for refresh tokens!)
4. Name: `Claude Assistant Platform`
5. Click "Create"
6. Copy the **Client ID** and **Client Secret**

### Step 5: Add to Jenkins

Add the following credentials to Jenkins:

| Credential ID | Value |
|---------------|-------|
| `google-calendar-client-id` | *Client ID from step 4* |
| `google-calendar-client-secret` | *Client Secret from step 4* |
| `gmail-client-id` | *Same Client ID (or separate)* |
| `gmail-client-secret` | *Same Client Secret (or separate)* |

---

## Environment Variables

### Backend Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Model to use |
| `APP_ENV` | No | `development` | Environment mode |
| `DEBUG` | No | `true` | Debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `API_HOST` | No | `0.0.0.0` | API bind address |
| `API_PORT` | No | `8000` | API port |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | CORS allowed hosts |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_HOST` | Yes | `db` | Database hostname |
| `POSTGRES_PORT` | No | `5432` | Database port |
| `POSTGRES_DB` | No | `claude_assistant_platform` | Database name |
| `POSTGRES_USER` | No | `postgres` | Database user |
| `POSTGRES_PASSWORD` | Yes | — | Database password |

### Telegram Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from BotFather |
| `TELEGRAM_DEV_BOT_TOKEN` | No | — | Dev bot token (local dev) |
| `TELEGRAM_ALLOWED_USER_IDS` | Yes | — | Comma-separated user IDs |
| `TELEGRAM_ENABLED` | No | `true` | Enable Telegram |
| `TELEGRAM_POLLING_TIMEOUT` | No | `30` | Polling timeout (seconds) |
| `TELEGRAM_MCP_HOST` | No | `telegram-mcp` | MCP server hostname |
| `TELEGRAM_MCP_PORT` | No | `8080` | MCP server port |

### Motion Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MOTION_API_KEY` | Yes | — | Motion API key |
| `MOTION_ENABLED` | No | `true` | Enable Motion |
| `MOTION_ACCOUNT_TYPE` | No | `team` | Account type for rate limits |
| `MOTION_RATE_LIMIT_OVERRIDE` | No | `0` | Override rate limit (0=default) |
| `MOTION_RATE_LIMIT_WINDOW` | No | `60` | Rate limit window (seconds) |
| `MOTION_MCP_HOST` | No | `motion-mcp` | MCP server hostname |
| `MOTION_MCP_PORT` | No | `8081` | MCP server port |

### Google Calendar Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CALENDAR_CLIENT_ID` | Yes | — | OAuth Client ID |
| `GOOGLE_CALENDAR_CLIENT_SECRET` | Yes | — | OAuth Client Secret |
| `GOOGLE_CALENDAR_TOKEN_PATH` | No | `/app/data/token.json` | Path to OAuth token file |
| `GOOGLE_CALENDAR_DEFAULT_TIMEZONE` | No | `America/New_York` | Default timezone for events |
| `GOOGLE_CALENDAR_MCP_HOST` | No | `0.0.0.0` | MCP server bind address |
| `GOOGLE_CALENDAR_MCP_PORT` | No | `8084` | MCP server port |

### Gmail Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GMAIL_CLIENT_ID` | Yes | — | OAuth Client ID |
| `GMAIL_CLIENT_SECRET` | Yes | — | OAuth Client Secret |
| `GMAIL_TOKEN_PATH` | No | `/app/data/token.json` | Path to OAuth token file |
| `GMAIL_MCP_HOST` | No | `0.0.0.0` | MCP server bind address |
| `GMAIL_MCP_PORT` | No | `8085` | MCP server port |

### Todo Executor

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TODO_EXECUTOR_ENABLED` | No | `true` | Enable background executor |
| `TODO_EXECUTOR_INTERVAL` | No | `30` | Check interval (seconds) |
| `TODO_EXECUTOR_BATCH_SIZE` | No | `5` | Todos per cycle |

---

## Infrastructure Endpoints

### Production (192.168.50.35)

| Service | URL | Health Check |
|---------|-----|--------------|
| Backend API | `http://192.168.50.35:8000` | `/health` |
| Frontend | `http://192.168.50.35:3000` | `/` |
| Telegram MCP | `http://192.168.50.35:8081` | `/health` |
| Motion MCP | `http://192.168.50.35:8082` | `/health` |
| Google Calendar MCP | `http://192.168.50.35:8084` | `/health` |
| Gmail MCP | `http://192.168.50.35:8085` | `/health` |
| Docker Registry | `http://192.168.50.35:5000` | `/v2/` |

### Local Development

| Service | URL | Health Check |
|---------|-----|--------------|
| Backend API | `http://localhost:8000` | `/health` |
| Frontend | `http://localhost:3000` | `/` |
| PostgreSQL | `localhost:5432` | `pg_isready` |

---

## First-Time OAuth Authentication

Google Calendar and Gmail MCPs require a one-time OAuth authentication flow that involves a browser. This must be done before the containers will function.

### Option 1: Local Pre-Authentication (Recommended)

Run the servers locally first to generate OAuth tokens, then copy them to production volumes.

**Google Calendar:**
```bash
cd MCPS/google-calendar
uv sync
uv run python -m src.server

# In another terminal or browser:
# Visit http://localhost:8084/auth/url
# Copy the URL and open in browser
# Complete Google sign-in
# Token saved to ./data/token.json
```

**Gmail:**
```bash
cd MCPS/gmail
uv sync
uv run python -m src.server

# Visit http://localhost:8085/auth/url
# Complete Google sign-in
# Token saved to ./data/token.json
```

**Copy tokens to production:**
```bash
# SSH to production server
ssh user@192.168.50.35

# Create volumes if they don't exist
docker volume create google-calendar-data
docker volume create gmail-data

# Copy token files into volumes
# (You'll need to transfer the token.json files to the server first)
docker run --rm -v google-calendar-data:/data -v /path/to/local:/local alpine \
  cp /local/google_calendar_token.json /data/token.json

docker run --rm -v gmail-data:/data -v /path/to/local:/local alpine \
  cp /local/gmail_token.json /data/token.json
```

### Option 2: Remote Authentication via API

If containers are already deployed but not authenticated:

1. Check auth status:
   ```bash
   curl http://192.168.50.35:8084/auth/status
   curl http://192.168.50.35:8085/auth/status
   ```

2. Get OAuth URL:
   ```bash
   curl http://192.168.50.35:8084/auth/url
   curl http://192.168.50.35:8085/auth/url
   ```

3. Open the returned URL in your browser and complete sign-in

4. The OAuth callback will redirect to `localhost` (which will fail), but the token should still be saved if you complete the flow

### Verifying Authentication

After authentication, verify the services are working:

```bash
# Check Google Calendar auth
curl http://192.168.50.35:8084/auth/status
# Should return: {"authenticated": true, ...}

# Check Gmail auth
curl http://192.168.50.35:8085/auth/status
# Should return: {"authenticated": true, ...}

# Test Calendar API
curl http://192.168.50.35:8084/calendars

# Test Gmail API
curl http://192.168.50.35:8085/labels
```

---

## Quick Reference Commands

### Check Container Status

```bash
docker ps --filter "name=claude-assistant"
```

### View Container Logs

```bash
docker logs claude-assistant-backend
docker logs claude-assistant-telegram-mcp
docker logs claude-assistant-motion-mcp
docker logs claude-assistant-google-calendar-mcp
docker logs claude-assistant-gmail-mcp
docker logs claude-assistant-frontend
```

### Health Checks

```bash
# Backend
curl http://localhost:8000/health

# Telegram MCP
curl http://localhost:8081/health

# Motion MCP
curl http://localhost:8082/health

# Google Calendar MCP
curl http://localhost:8084/health

# Gmail MCP
curl http://localhost:8085/health
```

### Google OAuth Status

```bash
# Check if authenticated
curl http://localhost:8084/auth/status
curl http://localhost:8085/auth/status

# Get auth URL (if not authenticated)
curl http://localhost:8084/auth/url
curl http://localhost:8085/auth/url
```

### Network Inspection

```bash
docker network inspect claude-assistant-network
```

### Restart Services

```bash
# Single service
docker restart claude-assistant-backend

# All services
docker restart $(docker ps -q --filter "name=claude-assistant")
```

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-01-08 | Added Google Calendar MCP (port 8084) and Gmail MCP (port 8085) | Claude |
| 2025-01-08 | Added Google OAuth setup instructions | Claude |
| 2025-01-08 | Added first-time OAuth authentication guide | Claude |
| 2025-01-08 | Added Motion MCP (port 8082) | Claude |
| 2025-01-08 | Initial deployment documentation | Claude |
