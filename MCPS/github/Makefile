# =============================================================================
# GitHub MCP Server - Makefile
# =============================================================================
# Development convenience commands
# =============================================================================

# Load environment variables from root .env file
-include ../../.env
export

.PHONY: install dev run test lint format clean docker-build docker-run

# Install production dependencies
install:
	uv sync --no-dev

# Install all dependencies including dev
dev:
	uv sync

# Run the server locally
run:
	uv run python -m src.server

# Run tests
test:
	uv run pytest -v

# Run tests with coverage
test-cov:
	uv run pytest --cov=src --cov-report=term-missing

# Run linting
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff format .

# Clean up generated files
clean:
	rm -rf .venv .pytest_cache .ruff_cache __pycache__
	rm -rf src/__pycache__ src/models/__pycache__ tests/__pycache__
	rm -rf .coverage htmlcov dist *.egg-info

# Build Docker image
docker-build:
	docker build -t github-mcp .

# Run Docker container
docker-run:
	docker run -d --name github-mcp -p 8083:8083 --env-file .env github-mcp

# Stop and remove Docker container
docker-stop:
	docker stop github-mcp || true
	docker rm github-mcp || true

# View logs
docker-logs:
	docker logs -f github-mcp

# Health check
health:
	curl -s http://localhost:8083/health | python -m json.tool

# Check rate limit
rate-limit:
	curl -s http://localhost:8083/tools/github_check_rate_limit | python -m json.tool
