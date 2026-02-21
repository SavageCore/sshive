# SSHive 🐝

[![lint](https://github.com/SavageCore/sshive/actions/workflows/lint.yml/badge.svg)](https://github.com/SavageCore/sshive/actions/workflows/lint.yml)
[![test](https://github.com/SavageCore/sshive/actions/workflows/test.yml/badge.svg)](https://github.com/SavageCore/sshive/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/SavageCore/sshive/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/SavageCore/sshive)
[![release](https://img.shields.io/github/v/release/SavageCore/sshive)](https://github.com/SavageCore/sshive/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Your hive of SSH connections** - A modern, cross-platform SSH connection manager built with PySide6.

Organize your SSH connections into groups, double-click to connect, and never type `ssh user@host` again.

## Features

- 🗂️ **Organize connections** into collapsible groups
- 🚀 **One-click connect** - double-click any server to launch your terminal
- 🔑 **SSH key support** - configure custom keys per connection
- 🎨 **Dark/Light mode** - automatically follows your system theme
- 💾 **Simple storage** - connections saved in JSON (`~/.config/sshive/connections.json`)
- 🖥️ **Cross-platform** - works on Linux, macOS, and Windows (WSL)
- 🔍 **Smart terminal detection** - auto-detects konsole, gnome-terminal, alacritty, etc.

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

### Standalone Executable (Recommended)

SSHive is distributed as a single executable file. No Python installation required!

1.  Download the latest release from the [Releases page](https://github.com/SavageCore/sshive/releases).
2.  Make it executable:
    ```bash
    chmod +x sshive
    ```
3.  Run it:
    ```bash
    ./sshive
    ```

### Install from Source

You can build and install SSHive locally using `uv`:

```bash
# Clone the repository
git clone https://github.com/SavageCore/sshive.git
cd sshive

# Install dependencies
uv sync

# Build and Install (binary, icon, desktop entry)
make install-app
```

This will install `sshive` to `~/.local/bin/` and create a launcher icon. You may need to log out and back in.

## Running from Source

### With uv

```bash
uv run sshive
```

### With venv

```bash
source .venv/bin/activate
sshive
# or
python -m sshive.main
```

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
uv sync

# Or with pip
pip install -e ".[dev]"
```

### Code Quality

This project uses `ruff` for linting and formatting:

```bash
# Check code quality
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Run both (recommended before committing)
uv run ruff check --fix . && uv run ruff format .
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=sshive --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py

# Watch mode (requires pytest-watch)
uv run ptw
```

### Using Makefile

Common development tasks:

```bash
make help        # Show all commands
make sync        # Install/sync dependencies
make test        # Run tests
make test-cov    # Run tests with coverage
make lint        # Check code
make format      # Format code
make fix         # Fix all issues
make run         # Run SSHive
make clean       # Clean build artifacts
```

### Adding Dependencies

```bash
# Add a new package (updates pyproject.toml automatically)
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Sync to install new dependencies
uv sync
```

### Project Structure

```
sshive/
├── sshive/              # Main package
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── resources/       # Icons and assets
│   │   └── icon.jpg
│   ├── ui/              # UI components
│   │   ├── main_window.py
│   │   ├── add_dialog.py
│   │   └── theme.py
│   ├── models/          # Data models
│   │   ├── connection.py
│   │   └── storage.py
│   └── ssh/             # SSH launcher
│       └── launcher.py
├── tests/               # Test suite
│   ├── test_models.py
│   ├── test_storage.py
│   ├── test_launcher.py
│   └── test_ui.py
├── pyproject.toml       # Project configuration
├── uv.lock             # Dependency lock file
├── install_icon.sh      # Icon installation script
└── README.md
```

## Usage

### Adding a Connection

1. Click **"➕ Add Connection"** button
2. Fill in the details:
   - **Name**: Friendly name (e.g., "Production Server")
   - **Host**: Hostname or IP
   - **Port**: SSH port (default: 22)
   - **User**: SSH username
   - **SSH Key**: Path to private key (optional)
   - **Group**: Organize into groups (e.g., "Work", "Personal")
3. Click **"Save"**

### Connecting

- **Double-click** any connection to launch your terminal and connect
- Connections are organized by group (collapsible)
- **Right-click** for context menu with options

### Terminal Support

SSHive auto-detects your terminal emulator:

- **Linux**: konsole, gnome-terminal, alacritty, kitty, xterm, tilix, terminator
- **macOS**: Terminal.app, iTerm2, Alacritty
- **Windows**: Windows Terminal, WSL

## Configuration

Configuration is stored in JSON:

- **Linux/macOS**: `~/.config/sshive/connections.json`
- **Windows**: `%APPDATA%\sshive\connections.json`

Example configuration:

```json
{
  "version": "1.0",
  "connections": [
    {
      "id": "abc123",
      "name": "Production Server",
      "host": "prod.example.com",
      "port": 22,
      "user": "deploy",
      "key_path": "~/.ssh/id_rsa",
      "group": "Work"
    }
  ]
}
```

See `examples/connections.json` for more examples.

## Building & Distribution

To build the standalone executable locally:

```bash
# Install build dependencies
uv sync

# Build executable (output in dist/sshive)
make dist

# Install to ~/.local/bin
make install-app
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Start for Contributors

```bash
# Fork and clone
git clone https://github.com/SavageCore/sshive.git
cd sshive

# Install dev dependencies
uv sync

# Make your changes

# Run quality checks
make fix      # Fix linting and formatting
make test     # Ensure all tests pass

# Commit and push
git add .
git commit -m "Add feature: description"
git push origin feature-branch
```

## uv Workflow Reference

```bash
# Installation & Setup
uv sync                          # Install all dependencies from lock file
uv sync --all-extras            # Install with all optional dependencies

# Running
uv run sshive                   # Run the app (no venv activation needed!)
uv run pytest                   # Run tests
uv run ruff check .             # Lint code

# Managing Dependencies
uv add qtawesome                # Add package (updates pyproject.toml)
uv add --dev pytest-watch       # Add dev dependency
uv remove package-name          # Remove package
uv lock                         # Update lock file
uv lock --upgrade               # Upgrade all dependencies

# Building
uv build                        # Build distribution packages
```

## Why uv?

- **Fast**: 10-100x faster than pip
- **Modern**: Better dependency resolution with lock files
- **Reliable**: Consistent installs across machines (via `uv.lock`)
- **Simple**: No need to activate virtual environments with `uv run`
- **Compatible**: Drop-in replacement for pip

## Troubleshooting

### Icon Not Showing in Taskbar

Run the icon installation script:

```bash
./install_icon.sh
```

Then restart SSHive and/or KDE Plasma. See `ICON_INSTALLATION.md` for details.

### Terminal Won't Launch

**Issue:** "Failed to launch terminal"

**Solution:** Install a supported terminal emulator:

```bash
# Ubuntu/Debian
sudo apt install konsole

# Fedora/RHEL
sudo dnf install konsole

# macOS (via Homebrew)
brew install --cask iterm2
```

### Connection Fails

**Issue:** "Cannot connect to server"

**Check:**

1. SSH is installed: `which ssh`
2. Key file exists: `ls -la ~/.ssh/id_rsa`
3. Can connect manually: `ssh user@host`
4. Correct permissions on key: `chmod 600 ~/.ssh/id_rsa`

### Package Not Found

If you get "ModuleNotFoundError" after adding a package:

```bash
# Make sure to sync after editing pyproject.toml
uv sync

# Or if you used uv add, it should auto-sync
uv add package-name
```

### Using Wrong Python

```bash
# Check which Python uv is using
uv run python --version

# Should match your system Python 3.10+
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Roadmap

- [x] Basic connection management
- [x] SSH key support
- [x] Dark/light mode
- [x] Terminal auto-detection
- [x] Beautiful icon
- [ ] Import from PuTTY/KiTTY sessions
- [ ] Export/backup connections
- [ ] Search/filter connections
- [ ] Recent connections history
- [ ] Custom terminal command templates
- [ ] Connection testing (ping/connectivity check)
- [ ] Port forwarding/tunneling support
- [ ] Connection sharing between machines
- [ ] Global keyboard shortcuts
- [ ] System tray integration

## Acknowledgments

Built with:

- [PySide6](https://wiki.qt.io/Qt_for_Python) - Qt for Python
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- [ruff](https://github.com/astral-sh/ruff) - Fast Python linter & formatter
- [QtAwesome](https://github.com/spyder-ide/qtawesome) - Icon fonts for Qt

## Support

- 📖 [Documentation](README.md)
- 🚀 [Quick Start Guide](QUICKSTART.md)
- 🐛 [Report Issues](https://github.com/SavageCore/sshive/issues)
- 💬 [Discussions](https://github.com/SavageCore/sshive/discussions)

---

Made with 🐝 for SSH enthusiasts everywhere.
