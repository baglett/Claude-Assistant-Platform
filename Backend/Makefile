# =============================================================================
# Claude Assistant Platform - Backend Makefile
# =============================================================================
# Uses uv for Python package management
# =============================================================================

# Load environment variables from root .env
-include ../.env
export

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
UV = uv
HOST = 127.0.0.1
PORT = 8000

# -----------------------------------------------------------------------------
# Default target
# -----------------------------------------------------------------------------
.PHONY: help
help:
	@echo "Claude Assistant Platform - Backend"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install    Install dependencies using uv"
	@echo "  run        Run the backend server locally (port $(PORT))"
	@echo "  dev        Run with auto-reload for development"
	@echo "  test       Run tests"
	@echo "  lint       Run linter (ruff)"
	@echo "  format     Format code (ruff)"
	@echo "  clean      Remove virtual environment and cache"
	@echo "  lock       Update uv.lock file"

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
	@echo "Starting backend server on http://$(HOST):$(PORT)"
	$(UV) run uvicorn src.api.main:app --host $(HOST) --port $(PORT)

.PHONY: dev
dev:
	@echo "Starting backend server in development mode on http://$(HOST):$(PORT)"
	$(UV) run uvicorn src.api.main:app --host $(HOST) --port $(PORT) --reload

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
