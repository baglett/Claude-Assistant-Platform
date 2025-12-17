# =============================================================================
# Claude Assistant Platform - Frontend Makefile
# =============================================================================

# Load environment variables from root .env
-include ../.env
export

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
NPM = npm
PORT = 3000

# -----------------------------------------------------------------------------
# Default target
# -----------------------------------------------------------------------------
.PHONY: help
help:
	@echo "Claude Assistant Platform - Frontend"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  run        Run the frontend dev server (port $(PORT))"
	@echo "  dev        Alias for run"
	@echo "  build      Build for production"
	@echo "  start      Start production server"
	@echo "  install    Install dependencies"
	@echo "  lint       Run linter"
	@echo "  clean      Remove node_modules and build artifacts"

# -----------------------------------------------------------------------------
# Run targets
# -----------------------------------------------------------------------------
.PHONY: run
run: node_modules
	@echo "Starting frontend server on http://localhost:$(PORT)"
	$(NPM) run dev

.PHONY: dev
dev: run

.PHONY: start
start: node_modules
	@echo "Starting production server on http://localhost:$(PORT)"
	$(NPM) run start

# -----------------------------------------------------------------------------
# Build targets
# -----------------------------------------------------------------------------
.PHONY: build
build: node_modules
	$(NPM) run build

# -----------------------------------------------------------------------------
# Setup targets
# -----------------------------------------------------------------------------
.PHONY: install
install:
	$(NPM) install

node_modules: install

# -----------------------------------------------------------------------------
# Lint targets
# -----------------------------------------------------------------------------
.PHONY: lint
lint: node_modules
	$(NPM) run lint

# -----------------------------------------------------------------------------
# Clean targets
# -----------------------------------------------------------------------------
.PHONY: clean
clean:
	@echo "Cleaning up..."
	-rmdir /s /q node_modules 2>nul || rm -rf node_modules
	-rmdir /s /q .next 2>nul || rm -rf .next
	-rmdir /s /q out 2>nul || rm -rf out
