"""Simulation script for SSHive updates.
Run with: PYTHONPATH=. uv run python scripts/simulate_update.py
"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sshive.ui.main_window import MainWindow


def simulate():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    def trigger():
        print("Triggering mock update notification...")
        # version, download_url, release_notes
        window.updater.update_available.emit(
            "9.9.9",
            "https://github.com/SavageCore/sshive/releases/download/v9.9.9/SSHive-9.9.9-x86_64.AppImage",
            "### 🚀 SSHive v9.9.9 Simulation\n\n"
            "This is a mocked update to test the UI flow.\n\n"
            "**New Features:**\n"
            "- Ultra-fast connection pooling\n"
            "- Darker-than-dark theme mode\n"
            "- Telepathic server selection\n\n"
            "**Bug Fixes:**\n"
            "- Fixed issue where buttons were too shiny",
        )

    # Wait for the app to settle before showing the notification
    QTimer.singleShot(3000, trigger)
    sys.exit(app.exec())


if __name__ == "__main__":
    simulate()
