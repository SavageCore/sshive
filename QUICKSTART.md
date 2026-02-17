# SSHive Quick Start Guide

Get up and running with SSHive in 5 minutes!

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/SavageCore/sshive.git
cd sshive

# Install
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Using pip

```bash
git clone https://github.com/SavageCore/sshive.git
cd sshive
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## First Run

```bash
# Start SSHive
sshive

# Or
python -m sshive.main
```

## Adding Your First Connection

1. Click **"➕ Add Connection"** button
2. Fill in the details:
   ```
   Name: My Server
   Host: example.com
   User: myuser
   Port: 22
   SSH Key: ~/.ssh/id_rsa (optional)
   Group: Work
   ```
3. Click **"OK"**

## Connecting to a Server

- **Double-click** any server in the list
- Or select a server and click **"🚀 Connect"**

Your terminal will open automatically!

## Tips & Tricks

### Organize with Groups

Group your servers by project, environment, or purpose:

- Work
- Personal
- Development
- Production
- Clients

### Keyboard Shortcuts

- `Ctrl+Shift+N` - New connection (coming soon)
- `Enter` - Connect to selected server (coming soon)
- `Delete` - Delete selected connection (coming soon)

### Using SSH Keys

For passwordless authentication:

```bash
# Generate a key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy to server
ssh-copy-id user@hostname

# Add key path to SSHive connection
~/.ssh/id_ed25519
```

### Import Existing Connections

You can manually edit `~/.config/sshive/connections.json`:

```json
{
  "version": "1.0",
  "connections": [
    {
      "id": "unique-id",
      "name": "Server Name",
      "host": "hostname.com",
      "user": "username",
      "port": 22,
      "key_path": "~/.ssh/id_rsa",
      "group": "Group Name"
    }
  ]
}
```

See `examples/connections.json` for a complete example.

## Troubleshooting

### Terminal Won't Launch

**Issue:** "Failed to launch terminal"

**Solution:** Install a supported terminal:

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

### Dark Mode Issues

The app automatically detects system theme. If it looks wrong:

1. Check your system theme settings
2. Try restarting SSHive
3. Report as a bug if it persists

## Next Steps

- Read the full [README.md](README.md)
- Check [CONTRIBUTING.md](CONTRIBUTING.md) if you want to help
- Star the project on GitHub! ⭐

## Getting Help

- 📖 [Full Documentation](README.md)
- 🐛 [Report Issues](https://github.com/SavageCore/sshive/issues)
- 💬 [Discussions](https://github.com/SavageCore/sshive/discussions)

Happy SSHing! 🐝
