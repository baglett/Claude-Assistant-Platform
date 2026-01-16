# =============================================================================
# Google Drive MCP Server - Makefile
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
	docker build -t google-drive-mcp .

# Run Docker container
docker-run:
	docker run -p 8087:8087 \
		-e GOOGLE_DRIVE_CLIENT_ID=$(GOOGLE_DRIVE_CLIENT_ID) \
		-e GOOGLE_DRIVE_CLIENT_SECRET=$(GOOGLE_DRIVE_CLIENT_SECRET) \
		-v google-drive-data:/app/data \
		google-drive-mcp
