.PHONY: help install dev test lint format clean run build

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies using uv
	uv pip install -e .

dev:  ## Install dependencies including dev tools
	uv pip install -e ".[dev]"

test:  ## Run tests with pytest
	pytest

test-cov:  ## Run tests with coverage report
	pytest --cov=sshive --cov-report=html --cov-report=term-missing

lint:  ## Check code with ruff
	ruff check .

lint-fix:  ## Auto-fix linting issues with ruff
	ruff check --fix .

format:  ## Format code with ruff
	ruff format .

format-check:  ## Check code formatting without making changes
	ruff format --check .

check:  ## Run all checks (lint + format check)
	ruff check .
	ruff format --check .

fix:  ## Fix all issues (lint fix + format)
	ruff check --fix .
	ruff format .

clean:  ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:  ## Run SSHive
	python -m sshive.main

build:  ## Build wheel package
	uv build

watch-test:  ## Run tests in watch mode (requires pytest-watch)
	ptw

all: clean lint-fix format test  ## Run complete workflow: clean, fix, format, test
