# =============================================================================
# Google Drive MCP Server - Dockerfile
# =============================================================================
# Multi-stage build for the Google Drive MCP server
# =============================================================================

# -----------------------------------------------------------------------------
# Build Stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files (README.md required by hatchling for package metadata)
COPY pyproject.toml README.md ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install .

# -----------------------------------------------------------------------------
# Runtime Stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY src/ ./src/

# Create data directory for token storage
RUN mkdir -p /app/data

# Set environment defaults
ENV GOOGLE_DRIVE_TOKEN_PATH=/app/data/drive_token.json
ENV GOOGLE_DRIVE_MCP_HOST=0.0.0.0
ENV GOOGLE_DRIVE_MCP_PORT=8087

# Expose the server port
EXPOSE 8087

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8087/health').raise_for_status()"

# Run the server
CMD ["python", "-m", "src.server"]
