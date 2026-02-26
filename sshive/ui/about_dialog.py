"""About dialog for SSHive."""

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from sshive import __version__


class AboutDialog(QDialog):
    """Dialog showing application information and licenses."""

    def __init__(self, parent=None):
        """Initialize about dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(self.tr("About SSHive"))
        self.setFixedSize(450, 400)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Header with Logo (placeholder for now or text)
        header_layout = QHBoxLayout()

        # App Info
        info_layout = QVBoxLayout()
        app_name = QLabel(self.tr("<b>SSHive</b>"))
        app_name.setStyleSheet("font-size: 24px;")

        version_label = QLabel(self.tr("Version {}").format(__version__))
        version_label.setStyleSheet("color: gray;")

        info_layout.addWidget(app_name)
        info_layout.addWidget(version_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        description = QLabel(
            self.tr(
                "Your hive of SSH connections - A modern SSH connection manager "
                "built with Python and PySide6.",
            )
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Tabs or sections for License
        layout.addSpacing(10)
        license_label = QLabel(self.tr("<b>License Information:</b>"))
        layout.addWidget(license_label)

        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setHtml("""
            <p><b>SSHive</b><br>
            Copyright &copy; 2026 SSHive Contributors<br>
            Licensed under the MIT License.</p>

            <hr>

            <p><b>Third-Party Libraries:</b></p>
            <ul>
                <li><b>PySide6</b>: LGPL v3 / GPL v2</li>
                <li><b>QtAwesome</b>: MIT License</li>
                <li><b>packaging</b>: BSD 3-Clause / Apache 2.0</li>
                <li><b>qtawesome</b>: MIT License</li>
            </ul>
        """)
        layout.addWidget(license_text)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton(self.tr("Close"))
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
