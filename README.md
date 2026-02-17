# SSHive 🐝

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

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/SavageCore/sshive.git
cd sshive

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Clone and enter directory
git clone https://github.com/SavageCore/sshive.git
cd sshive

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install
pip install -e ".[dev]"
```

## Running SSHive

```bash
# If installed
sshive

# Or run directly
python -m sshive.main
```

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

### Code Quality

This project uses `ruff` for linting and formatting:

```bash
# Check code quality
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Run both (recommended before committing)
ruff check --fix . && ruff format .
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sshive --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run tests in watch mode (requires pytest-watch)
ptw
```

### Project Structure

```
sshive/
├── sshive/              # Main package
│   ├── __init__.py
│   ├── main.py          # Entry point
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
└── README.md
```

## Usage

### Adding a Connection

1. Click **"Add Connection"** button
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

### Terminal Support

SSHive auto-detects your terminal emulator:

- **Linux**: konsole, gnome-terminal, alacritty, kitty, xterm
- **macOS**: Terminal.app, iTerm2, Alacritty
- **Windows**: Windows Terminal, WSL

## Configuration

Configuration is stored in JSON:

- **Linux/macOS**: `~/.config/sshive/connections.json`
- **Windows**: `%APPDATA%\sshive\connections.json`

Example configuration:

```json
{
  "connections": [
    {
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

## Building

```bash
# Build wheel
uv build

# Install from wheel
uv pip install dist/sshive-0.1.0-py3-none-any.whl
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting:
   ```bash
   ruff check --fix . && ruff format .
   pytest
   ```
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Roadmap

- [ ] Import from PuTTY/KiTTY sessions
- [ ] Export/backup connections
- [ ] Connection search/filter
- [ ] Recent connections history
- [ ] Custom terminal command templates
- [ ] Connection testing (ping/connectivity check)
- [ ] Tunneling/port forwarding support

## Acknowledgments

Built with:

- [PySide6](https://wiki.qt.io/Qt_for_Python) - Qt for Python
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- [ruff](https://github.com/astral-sh/ruff) - Fast Python linter
