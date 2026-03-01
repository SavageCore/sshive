"""SSHive - SSH Connection Manager.

Main entry point for the application.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QSettings, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from sshive.ui.main_window import MainWindow


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

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
