.PHONY: help install dev test lint format clean run sync

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

sync:  ## Sync dependencies from lock file
	uv sync

install:  ## Install dependencies
	uv sync

dev:  ## Install with dev dependencies
	uv sync --all-extras

test:  ## Run tests with pytest
	uv run pytest

test-cov:  ## Run tests with coverage report
	uv run pytest --cov=sshive --cov-report=html --cov-report=term-missing


test-watch:  ## Run tests in watch mode
	uv run ptw .

watch:  ## Run application in watch mode
	uv run python scripts/dev_watch.py


lint:  ## Check code with ruff
	uv run ruff check .

lint-fix:  ## Auto-fix linting issues
	uv run ruff check --fix .

format:  ## Format code with ruff
	uv run ruff format .

format-check:  ## Check formatting
	uv run ruff format --check .

check:  ## Run all checks
	uv run ruff check .
	uv run ruff format --check .

fix:  ## Fix all issues
	uv run ruff check --fix .
	uv run ruff format .

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .ruff_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

run:  ## Run SSHive
	uv run sshive

build:  ## Build wheel package
	uv build

lock:  ## Update lock file
	uv lock

all: dev fix test  ## Complete workflow: sync, fix, test