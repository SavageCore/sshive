"""Settings dialog for SSHive."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, parent=None, settings=None, column_names=None, hidden_columns=None):
        """Initialize settings dialog.

        Args:
            parent: Parent widget
            settings: QSettings instance
            column_names: List of all column names
            hidden_columns: List of indices for currently hidden columns
        """
        super().__init__(parent)
        self.settings = settings
        self.column_names = column_names or []
        self.hidden_columns = hidden_columns or []

        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # General settings
        gen_group = QGroupBox("General")
        gen_layout = QVBoxLayout()

        self.verify_check = QCheckBox("Verify credentials before connecting")
        self.verify_check.setToolTip(
            "Performs a quick background check before launching the terminal."
        )
        # Default to True if not set
        verify_val = self.settings.value("verify_credentials", "true")
        self.verify_check.setChecked(verify_val == "true" or verify_val is True)

        help_text = QLabel(
            "Prevents terminal flashing by checking credentials first. "
            "Adds a slight delay to connection launch."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: gray; font-size: 10px; margin-left: 20px;")

        gen_layout.addWidget(self.verify_check)
        gen_layout.addWidget(help_text)

        # Theme Preference
        theme_label = QLabel("Theme Preference:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Dark", "Light"])
        theme_val = self.settings.value("theme_preference", "System")
        self.theme_combo.setCurrentText(theme_val)
        gen_layout.addWidget(theme_label)
        gen_layout.addWidget(self.theme_combo)

        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)

        # Columns Visibility
        col_group = QGroupBox("Visible Columns")
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

    def get_settings(self):
        """Get the updated settings from the dialog.

        Returns:
            Dictionary of settings
        """
        return {
            "verify_credentials": self.verify_check.isChecked(),
            "theme_preference": self.theme_combo.currentText(),
            "column_visibility": {idx: check.isChecked() for idx, check in self.col_checks},
        }
