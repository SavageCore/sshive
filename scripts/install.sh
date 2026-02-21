#!/bin/bash
set -e

# Define paths
INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
BINARY_SRC="dist/sshive"
ICON_SRC="sshive/resources/icon.jpg"

# Colors
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing SSHive...${NC}"

# Ensure directories exist
mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# Install binary
if [ -f "$BINARY_SRC" ]; then
    echo "Installing binary to $INSTALL_DIR/sshive..."
    cp "$BINARY_SRC" "$INSTALL_DIR/sshive"
    chmod +x "$INSTALL_DIR/sshive"
else
    echo "Error: Binary not found at $BINARY_SRC. Run 'make dist' first."
    exit 1
fi

# Install icon
if [ -f "$ICON_SRC" ]; then
    echo "Installing icon to $ICON_DIR/sshive.png..."
    cp "$ICON_SRC" "$ICON_DIR/sshive.png"
else
    echo "Warning: Icon not found at $ICON_SRC."
fi

# Create desktop entry
echo "Creating desktop entry..."
cat > "$DESKTOP_DIR/sshive.desktop" << EOF
[Desktop Entry]
Name=SSHive
Comment=SSH Connection Manager
Exec=$INSTALL_DIR/sshive
Icon=sshive
Terminal=false
Type=Application
Categories=Utility;Network;
EOF

# Update desktop database
if command -v update-desktop-database >/dev/null; then
    update-desktop-database "$DESKTOP_DIR"
fi

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor"
fi

# Update KDE cache (if applicable)
if command -v kbuildsycoca6 >/dev/null; then
    kbuildsycoca6 --noincremental
elif command -v kbuildsycoca5 >/dev/null; then
    kbuildsycoca5 --noincremental
fi

echo -e "${GREEN}Installation complete!${NC}"
echo "You may need to log out and back in to see the app in your launcher."
