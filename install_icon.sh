#!/bin/bash
# SSHive Icon & Desktop File Installer

set -e

echo "🐝 Installing SSHive icon and desktop file..."

# Directories
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_SOURCE="sshive/resources/icon.jpg"

# Create directories
mkdir -p "$ICON_DIR"
mkdir -p "$DESKTOP_DIR"

# Check if icon exists
if [ ! -f "$ICON_SOURCE" ]; then
    echo "❌ Error: Icon not found at $ICON_SOURCE"
    echo "Please make sure icon.jpg is in sshive/resources/"
    exit 1
fi

# Install icon (convert JPG to PNG if needed)
if command -v convert &> /dev/null; then
    echo "Converting JPG to PNG..."
    convert "$ICON_SOURCE" "$ICON_DIR/sshive.png"
else
    echo "ImageMagick not found, copying as-is..."
    cp "$ICON_SOURCE" "$ICON_DIR/sshive.png"
fi

echo "✅ Icon installed to $ICON_DIR/sshive.png"

# Create desktop file
cat > "$DESKTOP_DIR/sshive.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=SSHive
GenericName=SSH Connection Manager
Comment=Manage and launch SSH connections with a beautiful UI
Exec=sshive
Icon=sshive
Terminal=false
Categories=Network;RemoteAccess;Utility;System;
Keywords=ssh;terminal;remote;connection;server;
StartupWMClass=sshive
StartupNotify=true
EOF

echo "✅ Desktop file installed to $DESKTOP_DIR/sshive.desktop"

# Update caches
if command -v gtk-update-icon-cache &> /dev/null; then
    echo "Updating icon cache..."
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor/" 2>/dev/null || true
fi

if command -v update-desktop-database &> /dev/null; then
    echo "Updating desktop database..."
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Restart SSHive if it's running"
echo "2. If icon still doesn't show, restart KDE Plasma:"
echo "   kquitapp5 plasmashell && kstart5 plasmashell"
echo ""
echo "You can now launch SSHive from your application menu!"
