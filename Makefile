.PHONY: help install dev test lint format clean run sync package-prep deb rpm flatpak arch

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

watch: ## Watch for changes and restart app
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

run: ## Run application
	PYTHONPATH=. uv run python -m sshive.main

build:  ## Build wheel package
	uv build

lock:  ## Update lock file
	uv lock

all: dev fix test  ## Complete workflow: sync, fix, test

# Packaging targets
package-prep:  ## Prepare packaging root
	rm -rf dist/package-root
	mkdir -p dist/package-root/usr/bin
	mkdir -p dist/package-root/usr/share/sshive
	uv pip install . --target dist/package-root/usr/share/sshive --no-deps
	@echo '#!/usr/bin/python3' > dist/package-root/usr/bin/sshive
	@echo 'import sys' >> dist/package-root/usr/bin/sshive
	@echo 'sys.path.insert(0, "/usr/share/sshive")' >> dist/package-root/usr/bin/sshive
	@echo 'from sshive.main import main' >> dist/package-root/usr/bin/sshive
	@echo 'if __name__ == "__main__":' >> dist/package-root/usr/bin/sshive
	@echo '    main()' >> dist/package-root/usr/bin/sshive
	chmod +x dist/package-root/usr/bin/sshive

deb: package-prep ## Build .deb package using nfpm
	nfpm pkg --target dist/sshive.deb

rpm: package-prep ## Build .rpm package using nfpm
	nfpm pkg --target dist/sshive.rpm

flatpak-deps: ## Generate Flatpak dependencies
	uv run --with requirements-parser python3 scripts/vendor/flatpak-pip-generator.py hatchling "packaging>=24.2" qtawesome --build-only

flatpak: ## Build Flatpak package
	flatpak-builder --user --install --force-clean build-dir org.sshive.SSHive.json

flatpak-run: ## Run Flatpak package
	flatpak run org.sshive.SSHive

arch: ## Instructions for Arch Linux package
	@echo "To build the Arch Linux package, run:"
	@echo "makepkg -si"

## Install app locally to ~/.local/bin
install-app:
	uv pip install . --user
	mkdir -p ~/.local/share/applications/
	mkdir -p ~/.local/share/icons/hicolor/512x512/apps/
	cp scripts/sshive.desktop ~/.local/share/applications/
	cp sshive/resources/icon.png ~/.local/share/icons/hicolor/512x512/apps/sshive.png
	update-desktop-database ~/.local/share/applications || true

# Install and run rpm for testing
install-rpm:
	make rpm
	sudo dnf reinstall ./dist/sshive.rpm -y
	/usr/bin/sshive


