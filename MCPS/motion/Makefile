# =============================================================================
# Motion MCP Server - Makefile
# =============================================================================
# Common development tasks for the Motion MCP server
# =============================================================================

# Load environment variables from root .env file
-include ../../.env
export

.PHONY: help install dev run lint format test clean build

# Default target
help:
	@echo "Motion MCP Server - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install   Install dependencies"
	@echo "  dev       Run development server with hot-reload"
	@echo "  run       Run production server"
	@echo "  lint      Run linter"
	@echo "  format    Format code"
	@echo "  test      Run tests"
	@echo "  clean     Clean build artifacts"
	@echo "  build     Build Docker image"

# Install dependencies
install:
	uv sync

# Run development server with hot-reload
dev:
	uv run uvicorn src.server:fastapi_app --reload --host 0.0.0.0 --port 8081

# Run production server
run:
	uv run motion-mcp

# Run linter
lint:
	uv run ruff check src tests

# Format code
format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

# Run tests
test:
	uv run pytest -v --cov=src --cov-report=term-missing

# Clean build artifacts
clean:
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf src/models/__pycache__
	rm -rf src/tools/__pycache__
	rm -rf tests/__pycache__
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf *.egg-info

# Build Docker image
build:
	docker build -t motion-mcp:latest .
