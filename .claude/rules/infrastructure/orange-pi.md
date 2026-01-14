---
paths:
  - "**/Dockerfile"
  - "**/docker-compose*.yml"
  - "Jenkinsfile"
  - "Backend/**/*.py"
  - "MCPS/**/*.py"
---

# Orange Pi Deployment Rules

All code in this project must be compatible with deployment to an Orange Pi 5 (ARM64).

## Target Platform

| Property | Value |
|----------|-------|
| Device | Orange Pi 5 |
| Architecture | ARM64 (aarch64) |
| IP Address | 192.168.50.35 |
| Docker Registry | 192.168.50.35:5000 |
| Jenkins | 192.168.50.35:8080 |

## ARM64 Compatibility Requirements

### Docker Builds

**ALWAYS** specify platform for builds:

```bash
# In Jenkinsfile - REQUIRED
docker build --platform linux/arm64/v8 -t $IMAGE .
```

### Base Images

Use images with ARM64 support:

```dockerfile
# Good - official multi-arch images
FROM python:3.14-slim
FROM node:20-alpine
FROM postgres:16-alpine

# Bad - may not have ARM64 variant
FROM some-obscure-image:latest
```

### Python Dependencies

Some packages need ARM64-compatible wheels. Before adding a dependency:

1. Check if it's pure Python (always works)
2. Check PyPI for ARM64 wheels
3. Test build locally with `--platform linux/arm64`

```toml
# pyproject.toml - safe dependencies
dependencies = [
    "httpx>=0.28.0",      # Pure Python
    "pydantic>=2.10.0",   # Has ARM64 wheels
    "uvicorn>=0.34.0",    # Pure Python
    "fastapi>=0.115.0",   # Pure Python
]
```

Packages requiring verification:
- NumPy (has ARM64 wheels)
- Pandas (has ARM64 wheels)
- Any package with C extensions

## Resource Constraints

Orange Pi has limited resources. Write efficient code.

### Memory Management

```python
# Good - streaming for large responses
async for chunk in response.aiter_bytes():
    process(chunk)

# Good - generators for large datasets
def process_items(items):
    for item in items:
        yield transform(item)

# Bad - loading everything into memory
data = response.read()  # Could be huge
all_items = list(get_all_items())  # Could be huge
```

### Concurrent Operations

Limit concurrent tasks to avoid overwhelming the system:

```python
import asyncio

# Limit concurrent MCP calls
semaphore = asyncio.Semaphore(10)

async def call_mcp_tool(tool: str, params: dict):
    async with semaphore:
        return await _make_request(tool, params)
```

### Container Resources

In production, all containers share Orange Pi resources:
- Don't assume unlimited CPU
- Don't cache large objects in memory
- Use database for persistence, not in-memory stores
- Close connections promptly

## Network Configuration

### Internal Communication

Services communicate via Docker network using container names:

```python
# Good - use environment variables
MCP_HOST = os.getenv("GITHUB_MCP_HOST", "claude-assistant-github-mcp")
MCP_PORT = os.getenv("GITHUB_MCP_PORT", "8083")
MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}"

# Bad - hardcoded addresses
MCP_URL = "http://localhost:8083"  # Won't work in Docker
MCP_URL = "http://192.168.50.35:8083"  # Bypasses Docker network
```

### Port Mapping

| Service | Internal Port | External Port |
|---------|---------------|---------------|
| Backend | 8000 | 8000 |
| Frontend | 3000 | 3000 |
| Telegram MCP | 8080 | 8081 |
| Motion MCP | 8081 | 8082 |
| GitHub MCP | 8083 | 8083 |
| Google Calendar MCP | 8084 | 8084 |
| Gmail MCP | 8085 | 8085 |

## Dockerfile Best Practices for ARM64

```dockerfile
# Multi-stage build reduces final image size
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy and install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.14-slim

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment
COPY --from=builder /app/.venv /app/.venv

# Copy source
COPY --chown=appuser:appuser src/ ./src/

# Environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Non-root user
USER appuser

# Health check - REQUIRED
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing ARM64 Locally

Before pushing, verify ARM64 compatibility:

```bash
# Build for ARM64 (requires Docker buildx)
docker buildx build --platform linux/arm64 -t test-image .

# Verify architecture
docker inspect test-image | jq '.[0].Architecture'
# Should return: "arm64"

# If buildx not available, enable QEMU emulation first
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker buildx create --use
```

## Health Checks

All services MUST have health check endpoints:

```python
@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": "my-service",
        "version": os.getenv("IMAGE_VERSION", "unknown"),
    }
```

## Anti-Patterns

- **DON'T** assume x86 architecture (always use `--platform linux/arm64/v8`)
- **DON'T** use base images without ARM64 support
- **DON'T** add Python packages with C extensions without verifying ARM64 wheels
- **DON'T** cache large objects in memory (Orange Pi has limited RAM)
- **DON'T** spawn unlimited concurrent tasks (use semaphores)
- **DON'T** use `localhost` for service-to-service communication (use container names)
- **DON'T** hardcode IP addresses in code (use environment variables)
- **DON'T** skip health checks (critical for container orchestration)
- **DON'T** run containers as root
- **DON'T** use `latest` tag for base images (pin specific versions)
- **DON'T** leave debug logging enabled in production (impacts performance)
