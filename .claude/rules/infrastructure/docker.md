---
paths:
  - "**/Dockerfile"
  - "**/docker-compose*.yml"
  - "**/docker-compose*.yaml"
---

# Docker Patterns

## Port Allocation

| Service | Internal Port | External (Prod) | External (Dev) |
|---------|--------------|-----------------|----------------|
| Backend | 8000 | 8000 | 8000 |
| Frontend | 3000 | 3000 | 3000 |
| PostgreSQL | 5432 | - | 5432 |
| Telegram MCP | 8080 | 8081 | 8081 |
| Motion MCP | 8081 | 8082 | 8082 |
| GitHub MCP | 8080 | 8083 | 8083 |

## Dockerfile Multi-Stage Build

```dockerfile
# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files first (better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Production - Minimal runtime image
# =============================================================================
FROM python:3.14-slim

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY --chown=appuser:appuser src/ ./src/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker Compose Structure

```yaml
version: "3.8"

services:
  # ==========================================================================
  # Core Services
  # ==========================================================================
  backend:
    build:
      context: ./Backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    depends_on:
      db:
        condition: service_healthy
      telegram-mcp:
        condition: service_healthy
    networks:
      - internal
    restart: unless-stopped

  frontend:
    build:
      context: ./Frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - internal
    restart: unless-stopped

  # ==========================================================================
  # Database
  # ==========================================================================
  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - internal
    restart: unless-stopped

  # ==========================================================================
  # MCP Servers
  # ==========================================================================
  telegram-mcp:
    build:
      context: ./MCPS/telegram
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - internal
    restart: unless-stopped

networks:
  internal:
    driver: bridge

volumes:
  pgdata:
```

## Health Check Patterns

Always include health checks for orchestration:

```yaml
# Database
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
  interval: 10s
  timeout: 5s
  retries: 5

# HTTP service
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  start_period: 10s
  retries: 3
```

## Network Configuration

- Use internal network for service-to-service communication
- Only expose necessary ports to host
- Reference services by name within Docker network

```yaml
# Internal communication (within Docker network)
TELEGRAM_MCP_URL=http://telegram-mcp:8080

# External access (from host)
BACKEND_URL=http://localhost:8000
```

## Volume Mounts

```yaml
volumes:
  # Named volume for database persistence
  pgdata:

  # Bind mount for development (hot reload)
  # Only use in development!
  backend-dev:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./Backend/src
```

## Environment Variables

Never hardcode secrets in Dockerfile or docker-compose.yml:

```yaml
# Good: Use .env file or environment
environment:
  - DATABASE_URL=${DATABASE_URL}
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# Bad: Hardcoded values
environment:
  - DATABASE_URL=postgres://user:password@db:5432/mydb
```

## Key Rules

1. **Multi-stage builds** - Smaller production images
2. **Non-root user** - Security best practice
3. **Health checks** - Required for all services
4. **Named volumes** - For data persistence
5. **Internal network** - For service isolation
6. **No hardcoded secrets** - Use environment variables

## Anti-Patterns

- **DON'T** hardcode secrets in Dockerfile or docker-compose.yml
- **DON'T** use `latest` tag for base images (pin versions)
- **DON'T** run containers as root when avoidable
- **DON'T** expose ports that don't need external access
- **DON'T** skip health checks for services
- **DON'T** use multiple RUN commands when they can be combined
- **DON'T** copy entire directories when only specific files are needed
- **DON'T** skip .dockerignore (exclude node_modules, __pycache__, etc.)
- **DON'T** use ADD when COPY is sufficient (COPY is more explicit)

## Orange Pi ARM64 Requirements

All Docker builds in this project MUST target ARM64 for deployment to the Orange Pi.

### Build Command

```bash
# Always specify platform in Jenkinsfile
docker build --platform linux/arm64/v8 -t $IMAGE .
```

### Base Image Compatibility

| Image | ARM64 Support | Notes |
|-------|---------------|-------|
| `python:3.14-slim` | ✅ | Official multi-arch |
| `node:20-alpine` | ✅ | Official multi-arch |
| `postgres:16-alpine` | ✅ | Official multi-arch |
| `alpine:3.19` | ✅ | Official multi-arch |

Before using a base image, verify it has ARM64 support:
```bash
docker manifest inspect <image> | grep arm64
```

### Verifying Builds

```bash
# Build for ARM64
docker buildx build --platform linux/arm64 -t test-image .

# Verify architecture
docker inspect test-image | jq '.[0].Architecture'
# Should return: "arm64"
```

### Python Package Compatibility

Some Python packages with C extensions need ARM64 wheels. Before adding:
1. Check PyPI for ARM64 wheels
2. Prefer pure Python packages when possible
3. Test the build locally with `--platform linux/arm64`

See `.claude/rules/infrastructure/orange-pi.md` for detailed ARM64 guidelines.
