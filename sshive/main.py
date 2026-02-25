"""SSHive - SSH Connection Manager.

Main entry point for the application.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from sshive.ui.main_window import MainWindow
from sshive.ui.theme import ThemeManager


def get_resource_path(filename: str) -> str:
    """Get path to resource file."""
    if getattr(sys, "frozen", False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
        return str(base_path / "sshive" / "resources" / filename)

    resource_dir = Path(__file__).parent / "resources"
    return str(resource_dir / filename)


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Force Fusion style for absolute consistency across all platforms and packages
    app.setStyle("Fusion")

    # Set application metadata
    app.setApplicationName("sshive")
    app.setDesktopFileName("sshive")
    app.setOrganizationName("sshive")
    app.setApplicationVersion("0.0.0")

    # Set application icon
    icon_path = get_resource_path("icon.png")
    if Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))

    # Apply theme based on system settings
    ThemeManager.apply_theme(app)

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
