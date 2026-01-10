# =============================================================================
# Gmail MCP Server - Makefile
# =============================================================================

# Load environment variables from root .env file
-include ../../.env
export

.PHONY: install dev run test lint format clean docker-build docker-run

# Install production dependencies
install:
	uv sync --no-dev

# Install with development dependencies
dev:
	uv sync

# Run the server locally
run:
	uv run python -m src.server

# Run tests
test:
	uv run pytest

# Run linting
lint:
	uv run ruff check src/

# Format code
format:
	uv run ruff format src/

# Clean build artifacts
clean:
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Build Docker image
docker-build:
	docker build -t gmail-mcp .

# Run Docker container
docker-run:
	docker run -p 8085:8085 \
		-e GMAIL_CLIENT_ID=$(GMAIL_CLIENT_ID) \
		-e GMAIL_CLIENT_SECRET=$(GMAIL_CLIENT_SECRET) \
		-v gmail-data:/app/data \
		gmail-mcp
