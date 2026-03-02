"""UI utility functions."""

import os

from platformdirs import user_downloads_path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from sshive.models.connection import SSHConnection


def is_wayland() -> bool:
    """Check if the current session is running under Wayland."""
    return (
        os.environ.get("WAYLAND_DISPLAY") is not None
        or os.environ.get("QT_QPA_PLATFORM") == "wayland"
    )


def show_connection_test_debug_dialog(
    parent, title: str, connection: SSHConnection, summary: str, debug_log: str
):
    """Show modal dialog with connection test debug output (shared between main window and add dialog).

    Args:
        parent: Parent widget for dialog
        title: Dialog window title
        connection: SSHConnection being tested
        summary: Test summary/result message
        debug_log: Full debug log text (e.g., ssh -vvv output)
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumSize(700, 450)

    layout = QVBoxLayout(dialog)

    header = QLabel(f"Connection: {connection.name}\n{summary}\n")
    header.setWordWrap(True)
    layout.addWidget(header)

    log_view = QTextEdit()
    log_view.setReadOnly(True)
    log_view.setPlainText(debug_log)
    layout.addWidget(log_view)

    buttons_layout = QHBoxLayout()
    buttons_layout.addStretch()

    copy_btn = QPushButton("Copy All")

    def _copy_to_clipboard():
        QApplication.clipboard().setText(log_view.toPlainText())
        # Show feedback
        original_text = copy_btn.text()
        copy_btn.setText("Copied!")
        copy_btn.setEnabled(False)
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: (copy_btn.setText(original_text), copy_btn.setEnabled(True)))
        timer.start(2000)

    copy_btn.clicked.connect(_copy_to_clipboard)
    buttons_layout.addWidget(copy_btn)

    save_btn = QPushButton("Save Log")

    def _save_log():
        downloads_dir = user_downloads_path()
        default_filename = f"{connection.name.replace(' ', '_')}_ssh_debug.log"
        default_path = os.path.join(downloads_dir, default_filename)

        file_path, _ = QFileDialog.getSaveFileName(
            dialog,
            "Save SSH Debug Log",
            default_path,
            "Log Files (*.log *.txt);;All Files (*)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(log_view.toPlainText())
            QMessageBox.information(dialog, "Save Successful", f"Log saved to:\n{file_path}")
        except OSError as exc:
            QMessageBox.warning(dialog, "Save Failed", str(exc))

    save_btn.clicked.connect(_save_log)
    buttons_layout.addWidget(save_btn)

    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dialog.accept)
    buttons_layout.addWidget(close_btn)

    layout.addLayout(buttons_layout)
    dialog.exec()
