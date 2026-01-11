# Claude Assistant Platform - Deployment Reference

This document contains infrastructure configuration, port mappings, and deployment details for the Claude Assistant Platform.

## Table of Contents

- [Port Configuration](#port-configuration)
- [Container Reference](#container-reference)
- [Network Configuration](#network-configuration)
- [Volume Mounts](#volume-mounts)
- [Jenkins Credentials](#jenkins-credentials)
- [Environment Variables](#environment-variables)
- [Infrastructure Endpoints](#infrastructure-endpoints)

---

## Port Configuration

### Production Deployment (Jenkins Pipeline)

| Service | Container Port | Host Port | Protocol | Description |
|---------|---------------|-----------|----------|-------------|
| Backend | 8000 | 8000 | HTTP | Main FastAPI backend |
| Frontend | 3000 | 3000 | HTTP | Next.js web interface |
| Telegram MCP | 8080 | 8081 | HTTP | Telegram Bot API tools |
| Motion MCP | 8081 | 8082 | HTTP | Motion task management tools |
| GitHub MCP | 8083 | 8083 | HTTP | GitHub Issues/PRs/Branches tools |
| Google Calendar MCP | 8084 | 8084 | HTTP | Google Calendar tools |
| Gmail MCP | 8085 | 8085 | HTTP | Gmail tools |
| PostgreSQL | 5432 | 5432 | TCP | Database (external to Docker) |

### Local Development (docker-compose)

| Service | Container Port | Host Port | Protocol | Description |
|---------|---------------|-----------|----------|-------------|
| Backend | 8000 | 8000 | HTTP | Main FastAPI backend |
| Frontend | 3000 | 3000 | HTTP | Next.js web interface |
| Telegram MCP | 8080 | — | HTTP | Internal only |
| Motion MCP | 8081 | — | HTTP | Internal only |
| GitHub MCP | 8083 | — | HTTP | Internal only |
| Google Calendar MCP | 8084 | — | HTTP | Internal only |
| Gmail MCP | 8085 | — | HTTP | Internal only |
| PostgreSQL | 5432 | 5432 | TCP | Database container |

### Port Allocation Strategy

- **8000-8099**: Backend services and APIs
- **8080-8089**: MCP servers (internal communication)
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
| `claude-assistant-github-mcp` | `claude-assistant-github-mcp` | `192.168.50.35:5000/claude-assistant-github-mcp` |
| `claude-assistant-google-calendar-mcp` | `claude-assistant-google-calendar-mcp` | `192.168.50.35:5000/claude-assistant-google-calendar-mcp` |
| `claude-assistant-gmail-mcp` | `claude-assistant-gmail-mcp` | `192.168.50.35:5000/claude-assistant-gmail-mcp` |

### Development Containers

| Container Name | Build Context | Dockerfile |
|----------------|---------------|------------|
| `claude-assistant-backend` | `./Backend` | `Backend/Dockerfile` |
| `claude-assistant-frontend` | `./Frontend` | `Frontend/Dockerfile` |
| `claude-assistant-telegram-mcp` | `./MCPS/telegram` | `MCPS/telegram/Dockerfile` |
| `claude-assistant-motion-mcp` | `./MCPS/motion` | `MCPS/motion/Dockerfile` |
| `claude-assistant-github-mcp` | `./MCPS/github` | `MCPS/github/Dockerfile` |
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
| GitHub MCP | `claude-assistant-github-mcp` | 8083 |
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
| `motion-data` | `motion-mcp` (prod) | `/app/data` | Rate limit database |

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
| `github-token` | Secret text | GitHub fine-grained PAT | [github.com/settings/tokens](https://github.com/settings/tokens?type=beta) |
| `google-calendar-client-id` | Secret text | Google OAuth client ID | [Google Cloud Console](https://console.cloud.google.com/) |
| `google-calendar-client-secret` | Secret text | Google OAuth client secret | Google Cloud Console |
| `google-calendar-refresh-token` | Secret text | Google Calendar refresh token | OAuth flow |
| `gmail-client-id` | Secret text | Gmail OAuth client ID | Google Cloud Console |
| `gmail-client-secret` | Secret text | Gmail OAuth client secret | Google Cloud Console |
| `gmail-refresh-token` | Secret text | Gmail refresh token | OAuth flow |

### Adding Credentials

1. Click "Add Credentials"
2. Kind: **Secret text**
3. Scope: **Global**
4. Secret: *paste value*
5. ID: *exact ID from table above*
6. Click "Create"

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

### GitHub Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | — | Fine-grained PAT |
| `GITHUB_ENABLED` | No | `true` | Enable GitHub |
| `GITHUB_MCP_HOST` | No | `github-mcp` | MCP server hostname |
| `GITHUB_MCP_PORT` | No | `8083` | MCP server port |

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
| GitHub MCP | `http://192.168.50.35:8083` | `/health` |
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
docker logs claude-assistant-github-mcp
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

# GitHub MCP
curl http://localhost:8083/health

# Google Calendar MCP
curl http://localhost:8084/health

# Gmail MCP
curl http://localhost:8085/health
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
| 2025-01-11 | Added GitHub MCP (port 8083) | Claude |
| 2025-01-08 | Added Gmail MCP (port 8085) | Claude |
| 2025-01-08 | Added Google Calendar MCP (port 8084) | Claude |
| 2025-01-08 | Added Motion MCP (port 8082) | Claude |
| 2025-01-08 | Initial deployment documentation | Claude |
