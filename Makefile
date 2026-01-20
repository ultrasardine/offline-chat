# Offline Chat - Makefile
# ========================
# Build and development tasks for the Offline Chat application
#
# Usage: make <target>
# Run 'make help' to see all available targets

.PHONY: help install install-dev run test test-verbose test-coverage test-pbt lint lint-fix format format-check clean clean-all check all bump bump-minor bump-major changelog agents models history agent-info connections migrate

.DEFAULT_GOAL := help

# ============================================================================
# Help
# ============================================================================

help: ## Display this help message with all available targets
	@echo ""
	@echo "Offline Chat - Makefile Targets"
	@echo "================================"
	@echo ""
	@echo "Installation:"
	@grep -E '^(install|install-dev):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Running:"
	@grep -E '^(run):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Agent Management:"
	@grep -E '^(agents|models|history|agent-info):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Database Management:"
	@grep -E '^(connections|migrate):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Testing:"
	@grep -E '^(test|test-verbose|test-coverage|test-pbt):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Code Quality:"
	@grep -E '^(lint|lint-fix|format|format-check|check):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Versioning:"
	@grep -E '^(bump|bump-minor|bump-major|changelog):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Cleanup:"
	@grep -E '^(clean|clean-all|clean-data):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Composite:"
	@grep -E '^(all|dev):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Installation
# ============================================================================

install: ## Install project dependencies using uv
	uv sync

install-dev: ## Install project with dev dependencies (testing, linting)
	uv sync --all-extras

# ============================================================================
# Running
# ============================================================================

run: ## Start the CLI application
	uv run python main.py

# ============================================================================
# Agent Management
# ============================================================================

agents: ## List all created agents
	@uv run python -c "from offline_chat import AgentManager; m = AgentManager(); agents = m.list_agents(); \
	print('\nCreated Agents:\n' + '='*50) if agents else print('\nNo agents created yet.'); \
	[print(f'  {a.name:<20} {a.display_name:<25} ({a.base_model})') for a in agents]; \
	print()"

models: ## List available Ollama models
	@echo "\nAvailable Ollama Models:"
	@echo "========================"
	@ollama list
	@echo ""

history: ## Show chat history for an agent (usage: make history AGENT=agent-name)
	@if [ -z "$(AGENT)" ]; then \
		echo "Usage: make history AGENT=agent-name"; \
		echo ""; \
		echo "Available agents:"; \
		ls -1 ~/.offline-chat/history/ 2>/dev/null | sed 's/.json//' | sed 's/^/  /' || echo "  No agents found"; \
	else \
		cat ~/.offline-chat/history/$(AGENT).json 2>/dev/null | python -m json.tool || echo "No history found for agent '$(AGENT)'"; \
	fi

agent-info: ## Show agent configuration (usage: make agent-info AGENT=agent-name)
	@if [ -z "$(AGENT)" ]; then \
		echo "Usage: make agent-info AGENT=agent-name"; \
		echo ""; \
		echo "Available agents:"; \
		ls -1 ~/.offline-chat/agents/ 2>/dev/null | sed 's/^/  /' || echo "  No agents found"; \
	else \
		echo "\nAgent Configuration:"; \
		echo "===================="; \
		cat ~/.offline-chat/agents/$(AGENT)/config.json 2>/dev/null | python -m json.tool || echo "Agent '$(AGENT)' not found"; \
		echo "\nModelfile:"; \
		echo "=========="; \
		cat ~/.offline-chat/agents/$(AGENT)/Modelfile 2>/dev/null || echo "Modelfile not found"; \
	fi

# ============================================================================
# Database Management
# ============================================================================

connections: ## List all database connections
	@uv run python -c "from offline_chat.database import DatabaseConnectionManager; m = DatabaseConnectionManager(); conns = m.list_connections(); \
	print('\nDatabase Connections:\n' + '='*50) if conns else print('\nNo database connections configured.'); \
	[print(f'  {c.name:<20} {c.database_type:<12} {c.host or \"N/A\":<20}') for c in conns]; \
	print()"

migrate: ## Run migration from inline database configs to centralized connections
	@echo "\nRunning database configuration migration..."
	@echo "==========================================="
	@uv run python -c "from offline_chat import AgentManager, DatabaseConnectionManager; \
	am = AgentManager(DatabaseConnectionManager()); \
	results = am.migrate_inline_configs(); \
	print(f'\nMigration complete: {len(results)} agent(s) migrated') if results else print('\nNo agents require migration'); \
	[print(f'  {agent} -> {conn}') for agent, conn in results.items()]; \
	print()"

# ============================================================================
# Testing
# ============================================================================

test: ## Run the test suite using pytest
	uv run pytest

test-verbose: ## Run tests with verbose output
	uv run pytest -v --tb=short

test-coverage: ## Run tests with coverage report
	uv run pytest --cov=offline_chat --cov-report=term-missing

test-pbt: ## Run only property-based tests (hypothesis)
	uv run pytest -v -k "property"

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run code quality checks using ruff
	uv run ruff check .

lint-fix: ## Run linter and automatically fix issues
	uv run ruff check --fix .

format: ## Format code using ruff
	uv run ruff format .

format-check: ## Check code formatting without making changes
	uv run ruff format --check .

check: ## Run all code quality checks (lint + format check)
	@echo "Running linter..."
	uv run ruff check .
	@echo ""
	@echo "Checking formatting..."
	uv run ruff format --check .
	@echo ""
	@echo "All checks passed!"

# ============================================================================
# Versioning (Semantic Versioning with Conventional Commits)
# ============================================================================

bump: ## Bump version based on conventional commits (auto-detect)
	uv run cz bump --changelog

bump-minor: ## Bump minor version (new features)
	uv run cz bump --increment MINOR --changelog

bump-major: ## Bump major version (breaking changes)
	uv run cz bump --increment MAJOR --changelog

changelog: ## Generate/update CHANGELOG.md from commits
	uv run cz changelog

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Remove Python caches and build artifacts
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf offline_chat/__pycache__
	rm -rf tests/__pycache__
	rm -rf *.egg-info
	rm -rf dist
	rm -rf build
	rm -rf .coverage
	rm -rf htmlcov
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-data: ## Remove runtime data (local ./data only, not ~/.offline-chat)
	rm -rf data

clean-all: clean clean-data ## Remove all generated files including data
	rm -rf .hypothesis
	rm -rf .venv

# ============================================================================
# Composite Targets
# ============================================================================

all: check test ## Run all checks and tests

dev: install-dev lint format test ## Full development workflow: install, lint, format, test
