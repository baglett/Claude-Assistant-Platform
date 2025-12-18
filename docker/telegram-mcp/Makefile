# =============================================================================
# Telegram MCP Server - Makefile
# =============================================================================
# Uses uv for Python package management
# =============================================================================

# Load environment variables from root .env
-include ../../.env
export

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
UV = uv
HOST = 0.0.0.0
PORT = 8080

# -----------------------------------------------------------------------------
# Default target
# -----------------------------------------------------------------------------
.PHONY: help
help:
	@echo "Telegram MCP Server"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install    Install dependencies using uv"
	@echo "  run        Run MCP server (port $(PORT))"
	@echo "  dev        Run with auto-reload for development"
	@echo "  test       Run tests"
	@echo "  lint       Run linter (ruff)"
	@echo "  format     Format code (ruff)"
	@echo "  clean      Remove virtual environment and cache"
	@echo "  lock       Update uv.lock file"
	@echo ""
	@echo "Note: Set TELEGRAM_BOT_TOKEN in ../../.env for Telegram integration"

# -----------------------------------------------------------------------------
# Setup targets
# -----------------------------------------------------------------------------
.PHONY: install
install:
	$(UV) sync

.PHONY: lock
lock:
	$(UV) lock

# -----------------------------------------------------------------------------
# Run targets
# -----------------------------------------------------------------------------
.PHONY: run
run:
	@echo "============================================"
	@echo "Starting Telegram MCP Server"
	@echo "============================================"
	@echo "Server: http://localhost:$(PORT)"
	@echo "Health: http://localhost:$(PORT)/health"
	@echo "============================================"
	$(UV) run python -m src.server

.PHONY: dev
dev:
	@echo "============================================"
	@echo "Starting Telegram MCP Server (DEV)"
	@echo "============================================"
	@echo "Server: http://localhost:$(PORT)"
	@echo "Health: http://localhost:$(PORT)/health"
	@echo "============================================"
	$(UV) run uvicorn src.server:fastapi_app --host $(HOST) --port $(PORT) --reload

# -----------------------------------------------------------------------------
# Test & Lint targets
# -----------------------------------------------------------------------------
.PHONY: test
test:
	$(UV) run pytest tests/ -v

.PHONY: lint
lint:
	$(UV) run ruff check src/

.PHONY: format
format:
	$(UV) run ruff format src/

# -----------------------------------------------------------------------------
# Clean targets
# -----------------------------------------------------------------------------
.PHONY: clean
clean:
	@echo "Cleaning up..."
	-rmdir /s /q .venv 2>nul || rm -rf .venv
	-rmdir /s /q __pycache__ 2>nul || rm -rf __pycache__
	-rmdir /s /q .pytest_cache 2>nul || rm -rf .pytest_cache
	-rmdir /s /q .ruff_cache 2>nul || rm -rf .ruff_cache
