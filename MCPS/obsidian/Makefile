# =============================================================================
# Obsidian MCP Server - Makefile
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
	@echo "Obsidian MCP Server"
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
	@echo "  status     Check connection to Obsidian"
	@echo ""
	@echo "Required environment variables:"
	@echo "  OBSIDIAN_API_KEY    - API key from Obsidian Local REST API plugin"
	@echo ""
	@echo "Optional environment variables:"
	@echo "  OBSIDIAN_HOST       - Obsidian host (default: 127.0.0.1)"
	@echo "  OBSIDIAN_PORT       - Obsidian port (default: 27124 for HTTPS)"
	@echo "  OBSIDIAN_PROTOCOL   - Protocol (default: https)"
	@echo "  OBSIDIAN_VERIFY_SSL - Verify SSL (default: false)"

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
run: install
	@echo "============================================"
	@echo "Starting Obsidian MCP Server"
	@echo "============================================"
	@echo "Server: http://localhost:$(PORT)"
	@echo "Health: http://localhost:$(PORT)/health"
	@echo "Status: http://localhost:$(PORT)/status"
	@echo "============================================"
	$(UV) run python -m src.server

.PHONY: dev
dev: install
	@echo "============================================"
	@echo "Starting Obsidian MCP Server (DEV)"
	@echo "============================================"
	@echo "Server: http://localhost:$(PORT)"
	@echo "Health: http://localhost:$(PORT)/health"
	@echo "Status: http://localhost:$(PORT)/status"
	@echo "============================================"
	$(UV) run uvicorn src.server:fastapi_app --host $(HOST) --port $(PORT) --reload

.PHONY: status
status:
	@echo "Checking Obsidian connection..."
	@curl -s http://localhost:$(PORT)/status | python -m json.tool 2>/dev/null || echo "Server not running or connection failed"

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
