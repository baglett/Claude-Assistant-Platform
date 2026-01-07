# =============================================================================
# Motion MCP Server - Dockerfile
# =============================================================================
# Multi-stage build for the Motion MCP server
# =============================================================================

# -----------------------------------------------------------------------------
# Build Stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src ./src

# -----------------------------------------------------------------------------
# Runtime Stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY --from=builder /app/src ./src

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Create directory for rate limit database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8081/health')" || exit 1

# Run the server
CMD ["python", "-m", "src.server"]
