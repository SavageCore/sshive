"""Update notification dialog for SSHive."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class UpdateDialog(QDialog):
    """Dialog to notify user of a new version and handle the update process."""

    def __init__(self, version, release_notes, download_url, updater, parent=None):
        """Initialize update dialog.

        Args:
            version: New version string
            release_notes: Release notes in markdown/text
            download_url: URL to download the update
            updater: UpdateChecker instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.version = version
        self.download_url = download_url
        self.updater = updater

        self.setWindowTitle("Update Available")
        self.setMinimumSize(500, 400)

        self._setup_ui(release_notes)
        self._connect_signals()

    def _setup_ui(self, release_notes):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        header = QLabel(f"<b>A new version of SSHive is available: {self.version}</b>")
        header.setStyleSheet("font-size: 14px;")
        layout.addWidget(header)

        notes_label = QLabel("Release Notes:")
        layout.addWidget(notes_label)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(release_notes)
        self.notes_edit.setReadOnly(True)
        layout.addWidget(self.notes_edit)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Not Now")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        if sys.platform == "win32":
            self.update_btn = QPushButton("Download && Install")  # Ampersand escapes the ampersand
        else:
            self.update_btn = QPushButton("Download")
        self.update_btn.setDefault(True)
        self.update_btn.clicked.connect(self._start_update)
        button_layout.addWidget(self.update_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect updater signals to UI."""
        self.updater.download_progress.connect(self._on_progress)
        self.updater.download_finished.connect(self._on_finished)
        self.updater.error_occurred.connect(self._on_error)

    def _start_update(self):
        """Start the update download."""
        self.update_btn.setEnabled(False)
        self.cancel_btn.setText("Close")
        self.progress_bar.setVisible(True)
        self.status_label.setText("Downloading update...")
        self.updater.download_update(self.download_url)

    def _on_progress(self, received, total):
        """Update progress bar."""
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(received)

    def _on_finished(self, file_path):
        """Handle download completion and trigger installation."""
        self.status_label.setText("Download complete. Installing...")
        self.progress_bar.setVisible(False)

        path = Path(file_path)

        # Platform-specific "install" logic
        if sys.platform == "win32" and path.suffix == ".exe":
            try:
                # Start the installer and exit
                os.startfile(file_path)
                sys.exit(0)
            except Exception as e:
                self._on_error(f"Failed to launch installer: {str(e)}")
        else:
            # For macOS/Linux, opening the folder is the safest "auto" action
            # unless we implement complex self-replacement logic.
            # Especially for AppImage, we should probably just notify the user.
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
            self.status_label.setText(f"Update saved to {path}. Please replace the old version.")
            self.update_btn.setText("Open Folder")
            self.update_btn.setEnabled(True)
            self.update_btn.clicked.disconnect()
            self.update_btn.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
            )

    def _on_error(self, message):
        """Handle errors."""
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("color: red;")
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Retry")
