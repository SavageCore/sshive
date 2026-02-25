---
trigger: always_on
---

Use `make` commands (via `uv run` internally):

- Check/lint only: `make lint`
- Auto-fix linting + imports: `make lint-fix`
- Format code: `make format`
- Check formatting without changing: `make format-check`
- Full fix (lint + format): `make fix`
- Full check (lint + format check): `make check`

> Import sorting is configured in `pyproject.toml` (`select = ["I"]`), so `make fix` handles imports automatically.

- All imports MUST be at the top of files. Never use inline imports within functions or methods.
