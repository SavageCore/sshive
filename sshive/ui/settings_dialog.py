"""Settings dialog for SSHive."""

from pathlib import Path

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

# Maps locale code -> human-readable name shown in the combo box
_LANGUAGE_NAMES: dict[str, str] = {
    "system": "System Default",
    "en": "English",
    "nl": "Dutch (Nederlands)",
}


def _get_available_languages(i18n_dir: Path | None = None) -> list[tuple[str, str]]:
    """Return (code, display_name) pairs for all available .qm files plus System Default.

    Args:
        i18n_dir: Directory to scan for .qm files. Defaults to the bundled i18n directory.

    Returns:
        List of (locale_code, display_name) tuples, always starting with ("system", ...).
    """
    if i18n_dir is None:
        i18n_dir = Path(__file__).parent.parent / "i18n"
    languages: list[tuple[str, str]] = [("system", _LANGUAGE_NAMES["system"])]

    for qm_file in sorted(i18n_dir.glob("*.qm")):
        code = qm_file.stem
        if code in _LANGUAGE_NAMES:
            display = _LANGUAGE_NAMES[code]
        else:
            # Fall back to Qt's locale name for unmapped codes
            locale = QLocale(code)
            display = locale.nativeLanguageName().capitalize() or code
        languages.append((code, display))

    return languages


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(
        self, parent=None, settings=None, column_names=None, hidden_columns=None, i18n_dir=None
    ):
        """Initialize settings dialog.

        Args:
            parent: Parent widget
            settings: QSettings instance
            column_names: List of all column names
            hidden_columns: List of indices for currently hidden columns
            i18n_dir: Directory to scan for .qm files (for testing)
        """
        super().__init__(parent)
        self.settings = settings
        self.column_names = column_names or []
        self.hidden_columns = hidden_columns or []
        self._languages = _get_available_languages(i18n_dir=i18n_dir)

        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # General settings
        gen_group = QGroupBox(self.tr("General"))
        gen_layout = QVBoxLayout()

        self.verify_check = QCheckBox(self.tr("Verify credentials before connecting"))
        self.verify_check.setToolTip(
            self.tr("Performs a quick background check before launching the terminal.")
        )
        # Default to True if not set
        verify_val = self.settings.value("verify_credentials", "true")
        self.verify_check.setChecked(verify_val == "true" or verify_val is True)

        self.update_check = QCheckBox(self.tr("Check for updates on startup"))
        self.update_check.setToolTip(
            self.tr("Automatically check for new versions when the app starts.")
        )
        update_val = self.settings.value("check_updates_startup", "true")
        self.update_check.setChecked(update_val == "true" or update_val is True)

        help_text = QLabel(
            self.tr(
                "Prevents terminal flashing by checking credentials first. "
                "Adds a slight delay to connection launch."
            )
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: gray; font-size: 10px; margin-left: 20px;")

        gen_layout.addWidget(self.verify_check)
        gen_layout.addWidget(help_text)
        gen_layout.addWidget(self.update_check)

        # Theme Preference
        theme_label = QLabel(self.tr("Theme Preference:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([self.tr("System"), self.tr("Dark"), self.tr("Light")])
        theme_val = self.settings.value("theme_preference", "System")
        # Match by index so translations don't break the lookup
        theme_index = {"System": 0, "Dark": 1, "Light": 2}.get(theme_val, 0)
        self.theme_combo.setCurrentIndex(theme_index)
        gen_layout.addWidget(theme_label)
        gen_layout.addWidget(self.theme_combo)

        # Language selection
        lang_label = QLabel(self.tr("Language:"))
        self.lang_combo = QComboBox()
        saved_lang = self.settings.value("language", "system")
        selected_index = 0
        for i, (code, display) in enumerate(self._languages):
            self.lang_combo.addItem(display, userData=code)
            if code == saved_lang:
                selected_index = i
        self.lang_combo.setCurrentIndex(selected_index)
        gen_layout.addWidget(lang_label)
        gen_layout.addWidget(self.lang_combo)

        self.lang_restart_label = QLabel(
            self.tr("⚠ A restart is required to apply the language change.")
        )
        self.lang_restart_label.setWordWrap(True)
        self.lang_restart_label.setStyleSheet("color: orange; font-size: 10px; margin-left: 0px;")
        self.lang_restart_label.setVisible(False)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        gen_layout.addWidget(self.lang_restart_label)

        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)

        # Columns Visibility
        col_group = QGroupBox(self.tr("Visible Columns"))
        col_layout = QVBoxLayout()

        self.col_checks = []
        # Column 0 is always "Name", don't allow hiding it
        for i in range(1, len(self.column_names)):
            name = self.column_names[i]
            check = QCheckBox(name)
            check.setChecked(i not in self.hidden_columns)
            col_layout.addWidget(check)
            self.col_checks.append((i, check))

        col_group.setLayout(col_layout)
        layout.addWidget(col_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_lang_changed(self, index: int):
        """Show restart warning when the language selection changes."""
        saved_lang = self.settings.value("language", "system")
        new_lang = self.lang_combo.itemData(index)
        self.lang_restart_label.setVisible(new_lang != saved_lang)

    def get_settings(self):
        """Get the updated settings from the dialog.

        Returns:
            Dictionary of settings
        """
        theme_map = {0: "System", 1: "Dark", 2: "Light"}
        return {
            "verify_credentials": self.verify_check.isChecked(),
            "check_updates_startup": self.update_check.isChecked(),
            "theme_preference": theme_map.get(self.theme_combo.currentIndex(), "System"),
            "language": self.lang_combo.currentData(),
            "column_visibility": {idx: check.isChecked() for idx, check in self.col_checks},
        }
