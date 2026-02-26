"""Update checker logic for SSHive."""

import json
import sys
from datetime import datetime, timezone

from packaging import version
from PySide6.QtCore import QObject, QSettings, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class UpdateChecker(QObject):
    """Handles checking for updates via GitHub API and downloading artifacts."""

    update_available = Signal(str, str, str)  # version, url, release_notes
    no_update_found = Signal()
    error_occurred = Signal(str)
    download_progress = Signal(int, int)
    download_finished = Signal(str)

    def __init__(self, current_version, parent=None):
        """Initialize update checker.

        Args:
            current_version: Current application version string
            parent: Parent QObject
        """
        super().__init__(parent)
        self.current_version = current_version
        self.manager = QNetworkAccessManager(self)
        self.settings = QSettings()

    def check_for_updates(self, force=False):
        """Check for updates on GitHub.

        Args:
            force: If True, skip the 4-hour cooldown
        """
        if not force:
            last_check_str = self.settings.value("updater/last_check")
            if last_check_str:
                try:
                    last_check = datetime.fromisoformat(last_check_str)
                    # 4 hour cooldown
                    if (datetime.now(timezone.utc) - last_check).total_seconds() < 14400:
                        return
                except (ValueError, TypeError):
                    pass

        url = QUrl("https://api.github.com/repos/SavageCore/sshive/releases/latest")
        request = QNetworkRequest(url)
        request.setRawHeader(b"User-Agent", b"SSHive-Updater")
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, True)

        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_check_finished(reply))

    def _on_check_finished(self, reply):
        """Handle API response."""
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.error_occurred.emit(f"Network error: {reply.errorString()}")
            reply.deleteLater()
            return

        try:
            data = json.loads(reply.readAll().data())
            latest_version_str = data.get("tag_name", "").lstrip("v")
            release_notes = data.get("body", "No release notes available.")
            html_url = data.get("html_url", "")

            if not latest_version_str:
                self.error_occurred.emit("Invalid response from GitHub API")
                return

            # Store successful check time
            self.settings.setValue("updater/last_check", datetime.now(timezone.utc).isoformat())

            current = version.parse(self.current_version)
            latest = version.parse(latest_version_str)

            if latest > current:
                # Find appropriate asset for platform
                download_url = self._find_platform_asset(data)
                self.update_available.emit(
                    latest_version_str, download_url or html_url, release_notes
                )
            else:
                self.no_update_found.emit()

        except Exception as e:
            self.error_occurred.emit(f"Failed to parse update data: {str(e)}")
        finally:
            reply.deleteLater()

    def _find_platform_asset(self, data):
        """Find the best download URL for the current platform."""
        assets = data.get("assets", [])
        if not assets:
            return None

        # Platform identification
        if sys.platform == "win32":
            pattern = ".exe"
        elif sys.platform == "darwin":
            pattern = ".app.zip"
        else:
            # Prefer AppImage for Linux, then deb/rpm
            for asset in assets:
                if asset["name"].endswith(".AppImage"):
                    return asset["browser_download_url"]
            # Fallback to general release URL if no AppImage
            return None

        for asset in assets:
            if asset["name"].endswith(pattern):
                return asset["browser_download_url"]

        return None

    def download_update(self, url):
        """Download the selected update asset."""
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", b"SSHive-Updater")
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, True)

        reply = self.manager.get(request)
        reply.downloadProgress.connect(self.download_progress.emit)
        reply.finished.connect(lambda: self._on_download_finished(reply))

    def _on_download_finished(self, reply):
        """Handle download completion."""
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.error_occurred.emit(f"Download error: {reply.errorString()}")
            reply.deleteLater()
            return

        try:
            # Determine filename - prioritize Content-Disposition
            content_disposition = (
                reply.rawHeader(b"Content-Disposition").data().decode("utf-8", "ignore")
            )
            filename = None
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[1].strip('"')

            if not filename:
                # Fallback to URL fileName, but avoid common generic names
                filename = reply.url().fileName()
                if not filename or filename in ["latest", "releases", "download"]:
                    filename = "sshive-update"

            import tempfile
            from pathlib import Path

            # Create a dedicated temp folder to avoid clutter/collisions
            temp_dir = Path(tempfile.gettempdir()) / "sshive-updates"
            temp_dir.mkdir(parents=True, exist_ok=True)

            save_path = temp_dir / filename
            save_path.write_bytes(reply.readAll().data())

            self.download_finished.emit(str(save_path))
        except Exception as e:
            self.error_occurred.emit(f"Failed to save update: {str(e)}")
        finally:
            reply.deleteLater()
