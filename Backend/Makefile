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
HOST = 0.0.0.0
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
	@echo "  run        Run backend with Telegram bot (port $(PORT))"
	@echo "  dev        Run with auto-reload for development"
	@echo "  test       Run tests"
	@echo "  lint       Run linter (ruff)"
	@echo "  format     Format code (ruff)"
	@echo "  clean      Remove virtual environment and cache"
	@echo "  lock       Update uv.lock file"
	@echo ""
	@echo "Note: Set TELEGRAM_BOT_TOKEN in ../.env for Telegram integration"

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
	@echo "Starting Claude Assistant Backend"
	@echo "============================================"
	@echo "API: http://localhost:$(PORT)"
	@echo "Docs: http://localhost:$(PORT)/docs"
	@echo ""
	@echo "Telegram: Will auto-start if TELEGRAM_BOT_TOKEN is set"
	@echo "============================================"
	$(UV) run python run.py --host $(HOST) --port $(PORT)

.PHONY: dev
dev:
	@echo "============================================"
	@echo "Starting Claude Assistant Backend (DEV)"
	@echo "============================================"
	@echo "API: http://localhost:$(PORT)"
	@echo "Docs: http://localhost:$(PORT)/docs"
	@echo ""
	@echo "Telegram: Will auto-start if TELEGRAM_BOT_TOKEN is set"
	@echo "============================================"
	$(UV) run python run.py --host $(HOST) --port $(PORT) --reload

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
