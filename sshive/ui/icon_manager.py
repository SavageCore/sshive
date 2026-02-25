"""Icon manager for retrieving and caching selfh.st icons."""

import json
from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, QUrl, Signal
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class IconManager(QObject):
    """Manages fetching and caching of icons."""

    # Signal emitted when an icon is loaded: (name, icon_path)
    icon_loaded = Signal(str, str)

    BASE_URL = "https://cdn.jsdelivr.net/gh/selfhst/icons/webp"
    MANIFEST_URL = "https://raw.githubusercontent.com/selfhst/icons/main/index.json"

    @staticmethod
    def instance() -> "IconManager":
        """Get global instance."""
        return get_icon_manager()

    def __init__(self):
        """Initialize icon manager."""
        super().__init__()
        self.network = QNetworkAccessManager(self)
        self.pending_replies: set[QNetworkReply] = set()
        self.cache_dir = (
            Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation))
            / "icons"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.valid_icons: set[str] = set()
        self._load_manifest()

    def cleanup(self):
        """Clean up resources and abort pending requests."""
        for reply in list(self.pending_replies):
            try:
                reply.finished.disconnect()
            except Exception:
                pass
            if reply.isRunning():
                reply.abort()
            reply.deleteLater()
        self.pending_replies.clear()
        self.valid_icons.clear()

    def __del__(self):
        """Ensure cleanup on destruction."""
        pass

    def _track_reply(self, reply: QNetworkReply):
        """Track a reply to ensure it can be aborted if needed."""
        self.pending_replies.add(reply)
        reply.finished.connect(self._on_reply_finished)

    def _on_reply_finished(self):
        """Remove finished reply from tracking."""
        reply = self.sender()
        if reply in self.pending_replies:
            self.pending_replies.discard(reply)

    def _load_manifest(self):
        """Load icon manifest from cache or network."""
        manifest_path = self.cache_dir / "icons.json"

        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    data = json.load(f)
                    self._parse_manifest(data)
            except Exception as e:
                print(f"Failed to load cached manifest: {e}")

        # Fetch update
        request = QNetworkRequest(QUrl(self.MANIFEST_URL))
        reply = self.network.get(request)
        self._track_reply(reply)
        reply.finished.connect(self._on_manifest_downloaded_finished)

    def _on_manifest_downloaded_finished(self):
        """Internal slot for manifest download completion."""
        reply = self.sender()
        self._on_manifest_downloaded(reply)

    def _on_manifest_downloaded(self, reply: QNetworkReply):
        """Handle manifest download."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll().data()
            try:
                json_data = json.loads(data)
                self._parse_manifest(json_data)

                # Cache it
                with open(self.cache_dir / "icons.json", "wb") as f:
                    f.write(data)
            except Exception as e:
                print(f"Failed to parse manifest: {e}")
        reply.deleteLater()

    def _parse_manifest(self, data: list | dict):
        """Parse manifest data to populate valid icons set."""
        self.valid_icons.clear()
        if isinstance(data, list):
            for item in data:
                # Structure: ["proxmox", "home-assistant", ...]
                if isinstance(item, str):
                    self.valid_icons.add(item)

    def get_icon(self, name: str) -> QIcon | None:
        """Get icon if cached, otherwise trigger fetch."""
        if not name:
            return None

        icon_path = self.cache_dir / f"{name}.webp"
        if icon_path.exists():
            return QIcon(str(icon_path))

        # Trigger fetch
        self.fetch_icon(name)
        return None

    def get_icon_path(self, name: str) -> str | None:
        """Get local path to icon if it exists."""
        if not name:
            return None

        icon_path = self.cache_dir / f"{name}.webp"
        if icon_path.exists():
            return str(icon_path)
        return None

    def fetch_icon(self, name: str):
        """Fetch icon from network."""
        if not name:
            return

        icon_path = self.cache_dir / f"{name}.webp"
        if icon_path.exists():
            self.icon_loaded.emit(name, str(icon_path))
            return

        url = f"{self.BASE_URL}/{name}.webp"
        request = QNetworkRequest(QUrl(url))
        reply = self.network.get(request)
        self._track_reply(reply)
        # Use dynamic property to pass data to callback safely
        reply.setProperty("icon_name", name)
        reply.setProperty("icon_path", str(icon_path))
        reply.finished.connect(self._on_icon_downloaded_finished)

    def _on_icon_downloaded_finished(self):
        """Internal slot for icon download completion."""
        reply = self.sender()
        name = reply.property("icon_name")
        path = Path(reply.property("icon_path"))
        self._on_icon_downloaded(reply, name, path)

    def _on_icon_downloaded(self, reply: QNetworkReply, name: str, path: Path):
        """Handle icon download."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll().data()
            if data:
                with open(path, "wb") as f:
                    f.write(data)
                self.icon_loaded.emit(name, str(path))
        else:
            pass
        reply.deleteLater()


# Global instance
_instance = None


def reset_icon_manager():
    """Reset the global icon manager instance (primarily for tests)."""
    global _instance
    if _instance is not None:
        _instance.cleanup()
        _instance.deleteLater()
        _instance = None


def get_icon_manager() -> IconManager:
    global _instance
    if _instance is None:
        _instance = IconManager()
    return _instance
