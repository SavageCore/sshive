# Contributing to SSHive

Thank you for your interest in contributing to SSHive! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- Git

### Getting Started

1. **Fork and clone the repository:**

   ```bash
   git clone https://github.com/SavageCore/sshive.git
   cd sshive
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

3. **Run the application to verify setup:**
   ```bash
   python -m sshive.main
   ```

## Development Workflow

### Code Quality

We use `ruff` for linting and formatting. Before submitting a PR:

```bash
# Check and fix linting issues
make lint-fix

# Format code
make format

# Or do both at once
make fix
```

### Testing

All new features should include tests:

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Watch mode during development (requires pytest-watcher)
make test-watch

# Watch mode for application
make watch
```

### Makefile Commands

We provide a Makefile for common tasks:

```bash
make help        # Show all available commands
make dev         # Install dev dependencies
make test        # Run tests
make lint        # Check code
make format      # Format code
make fix         # Fix all issues
make run         # Run the application
make clean       # Clean build artifacts
```

## Code Style

- **Line length:** 100 characters
- **Imports:** Organized by ruff (stdlib, third-party, local)
- **Type hints:** Use type hints for function signatures
- **Docstrings:** Use Google-style docstrings
- **Naming:**
  - Classes: `PascalCase`
  - Functions/methods: `snake_case`
  - Constants: `UPPER_CASE`
  - Private members: `_leading_underscore`

### Example Docstring

```python
def add_connection(self, connection: SSHConnection) -> None:
    """Add a new SSH connection to storage.

    Args:
        connection: SSHConnection object to add

    Raises:
        ValueError: If connection validation fails
    """
```

## Pull Request Process

1. **Create a feature branch:**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write code following the style guide
   - Add tests for new functionality
   - Update documentation if needed

3. **Run quality checks:**

   ```bash
   make fix      # Fix linting and formatting
   make test     # Ensure all tests pass
   ```

4. **Commit your changes:**

   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

   Commit message format:
   - `Add feature: description` - for new features
   - `Fix: description` - for bug fixes
   - `Docs: description` - for documentation
   - `Test: description` - for tests
   - `Refactor: description` - for refactoring

5. **Push and create PR:**

   ```bash
   git push origin feature/your-feature-name
   ```

   Then create a Pull Request on GitHub with:
   - Clear description of changes
   - Screenshots for UI changes
   - Reference to any related issues

## Testing Guidelines

### Unit Tests

- Test individual functions and classes
- Use pytest fixtures for common setup
- Mock external dependencies

```python
def test_connection_creation():
    """Test creating a basic SSH connection."""
    conn = SSHConnection(name="Test", host="example.com", user="user")
    assert conn.name == "Test"
```

### UI Tests

- Use `pytest-qt` for PySide6 testing
- Test user interactions
- Verify widget state changes

```python
def test_button_click(qtbot):
    """Test that button click triggers action."""
    window = MainWindow()
    qtbot.addWidget(window)
    qtbot.mouseClick(window.add_btn, Qt.LeftButton)
    # Verify expected outcome
```

### Integration Tests

- Test complete workflows
- Verify components work together
- Use temporary files for storage tests

## Project Structure

```
sshive/
├── sshive/              # Main package
│   ├── models/          # Data models
│   ├── ui/              # UI components
│   └── ssh/             # SSH launcher
├── tests/               # Test suite
├── docs/                # Documentation (future)
└── scripts/             # Helper scripts (future)
```

## Adding New Features

### 1. Connection Features

Example: Adding connection tags

1. Update `SSHConnection` model in `sshive/models/connection.py`
2. Update storage serialization
3. Update UI dialog to include tags field
4. Add tests for tag functionality

### 2. UI Features

Example: Adding search/filter

1. Add search widget to main window
2. Implement filter logic
3. Update tree view population
4. Add keyboard shortcuts
5. Write UI tests

### 3. Terminal Features

Example: Supporting a new terminal

1. Update `SSHLauncher.detect_terminal()` in `sshive/ssh/launcher.py`
2. Add terminal-specific command format
3. Test on target platform
4. Update documentation

## Bug Reports

When reporting bugs, include:

- **Description:** Clear description of the issue
- **Steps to reproduce:** Step-by-step instructions
- **Expected behavior:** What should happen
- **Actual behavior:** What actually happens
- **Environment:**
  - OS and version
  - Python version
  - SSHive version
  - Terminal emulator

## Feature Requests

For feature requests:

- Check existing issues first
- Describe the use case
- Explain why it's useful
- Provide examples if possible

## Questions?

- Open a discussion on GitHub
- Check existing issues and PRs
- Read the documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
