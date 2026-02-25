# SSHive Quick Start Guide

Get up and running with SSHive in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- Git
- [uv](https://github.com/astral-sh/uv) package manager

## Step 1: Install uv (if you haven't already)

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Verify installation
uv --version
```

## Step 2: Get SSHive

```bash
# Clone the repository
git clone https://github.com/SavageCore/sshive.git
cd sshive

# Install dependencies (no venv needed!)
uv sync
```

That's it! No virtual environment activation required with uv. ✨

## Step 3: Run SSHive

```bash
uv run sshive
```

The app will open with an empty connection list.

## Step 4: Native Linux Packages (Recommended)

If you prefer native packages, you can download `.deb` or `.rpm` files from our [Releases page](https://github.com/SavageCore/sshive/releases).

### Debian/Ubuntu (.deb)

```bash
sudo dpkg -i sshive.deb
# If dependencies missing:
sudo apt-get install -f
```

### Fedora/RHEL (.rpm)

```bash
sudo dnf install ./sshive.rpm
```

### Arch Linux

We provide a `PKGBUILD` in the repository. To build and install:

```bash
git clone https://github.com/SavageCore/sshive.git
cd sshive
makepkg -si
```

### Flatpak

```bash
# Build and install locally
make flatpak
```

## Step 5: Add Your First Connection

1. Click **"➕ Add Connection"** button
2. Fill in the form:
   ```
   Name:     My Server
   Host:     example.com
   User:     myuser
   Port:     22
   SSH Key:  ~/.ssh/id_rsa  (optional)
   Group:    Work
   ```
3. Click **"OK"**

## Step 5: Connect!

- **Double-click** the connection to open terminal and connect
- Or click once to select, then click **"🚀 Connect"**

Your terminal will launch automatically! 🎉

## Optional: Install Icon

To see the SSHive icon in your taskbar/launcher:

```bash
chmod +x install_icon.sh
./install_icon.sh
```

Restart SSHive, and you'll see the beautiful honeycomb icon! 🐝

## Quick Tips

### Organize with Groups

Create groups to organize your connections:

- **Work** - Company servers
- **Personal** - Your VPS, home server
- **Development** - Test environments
- **Clients** - Customer servers

Groups appear as collapsible folders in the tree.

### SSH Keys for Passwordless Login

If you haven't set up SSH keys:

```bash
# Generate a key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy to server
ssh-copy-id user@hostname

# Add key path to SSHive connection
~/.ssh/id_ed25519
```

### Right-Click for Options

Right-click any connection for quick access to:

- 🚀 Connect
- ✏️ Edit
- 🗑️ Delete

### Keyboard Shortcuts (Coming Soon)

- `Enter` - Connect to selected server
- `Delete` - Delete selected connection
- `Ctrl+N` - New connection

## Common Commands

```bash
# Run the app
uv run sshive

# Run tests
uv run pytest

# Check code quality
uv run ruff check .

# Format code
uv run ruff format .

# Or use the Makefile
make run      # Run app
make test     # Run tests
make fix      # Fix code issues
```

## Using Traditional pip/venv?

If you prefer not to use uv:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install
pip install -e ".[dev]"

# Run
sshive
```

## Configuration File Location

Your connections are saved in JSON:

- **Linux/macOS**: `~/.config/sshive/connections.json`
- **Windows**: `%APPDATA%\sshive\connections.json`

You can manually edit this file or back it up for safekeeping.

## Example Connection File

```json
{
  "version": "1.0",
  "connections": [
    {
      "id": "unique-id-123",
      "name": "Production Server",
      "host": "prod.example.com",
      "user": "deploy",
      "port": 22,
      "key_path": "~/.ssh/id_rsa",
      "group": "Work"
    },
    {
      "id": "unique-id-456",
      "name": "Home Server",
      "host": "192.168.1.100",
      "user": "admin",
      "port": 2222,
      "key_path": "~/.ssh/home_key",
      "group": "Personal"
    }
  ]
}
```

See `examples/connections.json` for more examples.

## Troubleshooting

### "Failed to launch terminal"

**Problem:** No supported terminal emulator found.

**Solution:** Install a terminal:

```bash
# Ubuntu/Debian
sudo apt install konsole

# Fedora/Nobara
sudo dnf install konsole

# macOS
brew install --cask iterm2
```

### "Permission denied (publickey)"

**Problem:** SSH key authentication failing.

**Solution:**

1. Check key exists: `ls -la ~/.ssh/id_rsa`
2. Correct permissions: `chmod 600 ~/.ssh/id_rsa`
3. Key is on server: `ssh-copy-id user@host`
4. Test manually: `ssh -i ~/.ssh/id_rsa user@host`

### Icon not showing in taskbar

**Problem:** Icon appears in window but not taskbar.

**Solution:**

```bash
./install_icon.sh
# Then restart SSHive

# If still not working, restart KDE Plasma
kquitapp5 plasmashell && kstart5 plasmashell
```

See `ICON_INSTALLATION.md` for detailed instructions.

### ModuleNotFoundError

**Problem:** Package not found when running.

**Solution:**

```bash
# Re-sync dependencies
uv sync

# Or if using pip
source .venv/bin/activate
pip install -e ".[dev]"
```

### Dark mode looks wrong

The app automatically follows your system theme. To force light mode, check your system settings:

- **KDE Plasma**: System Settings → Appearance → Global Theme
- **GNOME**: Settings → Appearance → Style

## Why uv?

You might wonder why we use `uv` instead of traditional pip:

✅ **10-100x faster** - Installs packages in seconds  
✅ **Lock file** - Consistent installs across machines (`uv.lock`)  
✅ **No activation needed** - `uv run` just works  
✅ **Better dependency resolution** - Smarter conflict handling  
✅ **Drop-in replacement** - Can still use pip if you prefer

## uv Quick Reference

```bash
# Install dependencies
uv sync                     # From pyproject.toml + uv.lock

# Add new packages
uv add package-name         # Updates pyproject.toml automatically
uv add --dev pytest-watch   # Add dev dependency

# Run commands (no venv activation!)
uv run sshive              # Run app
uv run pytest              # Run tests
uv run ruff check .        # Lint code

# Update dependencies
uv lock --upgrade          # Update lock file
uv sync                    # Apply updates
```

## What's Next?

### Explore Features

- Try organizing connections into different groups
- Set up SSH keys for passwordless authentication
- Customize connection settings (ports, keys)
- Right-click connections for quick actions

### Customize

- Edit the icon if you want (`sshive/resources/icon.jpg`)
- Modify colors/theme in `sshive/ui/theme.py`
- Add your own features!

### Share

- Export your connections for backup
- Share connection templates with your team
- Contribute to the project on GitHub

### Learn More

- 📖 [Full README](README.md) - Complete feature documentation
- 🛠️ [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
- 🎨 [ICON_INSTALLATION.md](ICON_INSTALLATION.md) - Icon setup details
- 🐛 [GitHub Issues](https://github.com/SavageCore/sshive/issues) - Report bugs

## Common Workflows

### Daily Use

```bash
cd sshive
uv run sshive              # Launch app
# Use GUI to connect to servers
```

### Development

```bash
cd sshive
uv sync                    # Ensure dependencies up to date
# Make changes to code
uv run pytest              # Test changes
make fix                   # Fix code style
git commit -m "..."        # Commit
```

### Adding a Feature

```bash
cd sshive
uv sync                    # Get latest deps
# Edit code
uv add new-package         # If you need new dependency
uv run pytest              # Test
make fix                   # Format
git push                   # Share
```

## Pro Tips

💡 **Create a shell alias:**

```bash
# Add to ~/.bashrc or ~/.zshrc
alias ssh-manager='cd ~/sshive && uv run sshive'

# Then just run:
ssh-manager
```

💡 **Pin to taskbar/favorites** after installing the icon

💡 **Backup your connections:**

```bash
cp ~/.config/sshive/connections.json ~/sshive-backup.json
```

💡 **Share connections across machines:**

- Keep `connections.json` in git (private repo!)
- Or use a sync service (Dropbox, Syncthing)
- Symlink: `ln -s ~/Dropbox/sshive.json ~/.config/sshive/connections.json`

## Getting Help

- 📖 Full docs: `README.md`
- 🐛 Found a bug? [Open an issue](https://github.com/SavageCore/sshive/issues)
- 💬 Questions? [Start a discussion](https://github.com/SavageCore/sshive/discussions)
- ⭐ Like it? Star the project!

---

**Welcome to SSHive! 🐝**

You're now ready to manage all your SSH connections in style. No more remembering hosts, ports, and key paths - just double-click and go!

Happy SSHing!
