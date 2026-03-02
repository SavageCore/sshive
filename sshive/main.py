"""SSHive - SSH Connection Manager.

Main entry point for the application.
"""

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QSettings, QTimer, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from sshive.ipc import IPCServer
from sshive.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def get_resource_path(filename: str) -> str:
    """Get path to resource file."""
    if getattr(sys, "frozen", False):
        # Handle PyInstaller temporary folder path
        base_path = Path(sys._MEIPASS)
        return str(base_path / "sshive" / "resources" / filename)

    resource_dir = Path(__file__).parent / "resources"
    return str(resource_dir / filename)


def _install_translator(app: QApplication, locale_code: str) -> QTranslator | None:
    """Load and install the .qm file for the given locale code.

    Args:
        app: The QApplication instance.
        locale_code: A locale code like 'nl', 'en_GB', or 'system'.

    Returns:
        The installed QTranslator, or None if no matching file was found.
    """
    i18n_dir = Path(__file__).parent / "i18n"
    translator = QTranslator(app)

    # Try exact match first
    qm_path = i18n_dir / f"{locale_code}.qm"
    if qm_path.exists():
        translator.load(str(qm_path))
        app.installTranslator(translator)
        return translator

    # Strip region code (e.g. 'en_US' -> 'en')
    if "_" in locale_code:
        base_code = locale_code.split("_")[0]
        qm_path = i18n_dir / f"{base_code}.qm"
        if qm_path.exists():
            translator.load(str(qm_path))
            app.installTranslator(translator)
            return translator

    return None


def _resolve_locale(settings: QSettings) -> str:
    """Return the locale code to use, honouring the saved setting.

    Args:
        settings: The application QSettings instance.

    Returns:
        A locale code string such as 'nl', 'en', or the system locale name.
    """
    saved = settings.value("language", "system")
    if saved and saved != "system":
        return saved
    return QLocale.system().name()


def main():
    """Main application entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        prog="sshive",
        description="SSHive - SSH Connection Manager",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show/focus the main window (toggle if already visible)",
    )
    parser.add_argument(
        "--quick-connect",
        action="store_true",
        help="Open the quick connection search dialog",
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        help="Show the recent connections menu",
    )
    args = parser.parse_args()

    # Collect commands to send
    commands = []
    if args.show:
        commands.append("--show")
    if args.quick_connect:
        commands.append("--quick-connect")
    if args.recent:
        commands.append("--recent")

    # If any command-line flags were given, try to send them to a running instance
    if commands:
        ipc_server = IPCServer()
        if ipc_server.send_command(commands):
            sys.exit(0)  # Command sent successfully, exit this instance
        # If send fails, fall through to start a new instance

    app = QApplication(sys.argv)

    # Use Fusion style for cross-platform consistency
    app.setStyle("Fusion")

    # Set application metadata early for QStandardPaths
    app.setApplicationName("sshive")
    app.setOrganizationName("")  # Prevent nested config folder
    app.setApplicationVersion("0.0.0")
    app.setDesktopFileName("sshive")

    # Load saved language preference (requires app metadata to be set first)
    settings = QSettings("sshive", "sshive")
    locale_code = _resolve_locale(settings)
    _install_translator(app, locale_code)

    # Set application icon
    icon_path = get_resource_path("icon.png")
    if Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))

    # Start IPC server for receiving commands from other instances
    ipc_server = IPCServer()
    ipc_server_started = ipc_server.start()

    # Create and show main window
    window = MainWindow()

    # If we started a new instance with commands (first launch scenario),
    # process those commands now that the window exists
    if commands:
        window.handle_ipc_command(commands)
        # Hide window to tray if we're only showing quick connect/recent
        # (keep window shown if just --show was called)
        if "--show" not in commands:
            window.hide()
    else:
        window.show()

    # Setup IPC command handler
    if ipc_server_started:

        def check_ipc_commands():
            """Check for incoming IPC commands."""
            message = ipc_server.accept_commands()
            if message and message.get("action") == "command":
                window.handle_ipc_command(message.get("args", []))

        ipc_timer = QTimer()
        ipc_timer.timeout.connect(check_ipc_commands)
        ipc_timer.start(200)  # Check every 200ms

        # Cleanup on exit
        def cleanup_ipc():
            ipc_timer.stop()
            ipc_server.cleanup()

        app.aboutToQuit.connect(cleanup_ipc)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
