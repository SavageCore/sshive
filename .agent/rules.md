## Code Style

Use `make` commands (via `uv run` internally):

- Check/lint only: `make lint`
- Auto-fix linting + imports: `make lint-fix`
- Format code: `make format`
- Check formatting without changing: `make format-check`
- Full fix (lint + format): `make fix`
- Full check (lint + format check): `make check`

> Import sorting is configured in `pyproject.toml` (`select = ["I"]`), so `make fix` handles imports automatically.

## Testing

- Run tests: `make test`
- Run tests with coverage: `make test-cov`
- Run tests in watch mode: `make test-watch`
- Always create comprehensive `pytest` tests for any changes made, covering edge cases where possible.

## Common Workflows

- Full workflow (sync, fix, test): `make all`
- Install dependencies: `make install`
- Install with dev dependencies: `make dev`
