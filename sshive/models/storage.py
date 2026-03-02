"""Storage module for SSH connections."""

import json
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from sshive.models.connection import SSHConnection


class ConnectionStorage:
    """Handles persistence of SSH connections to JSON file.

    Storage location:
        - Linux/macOS: ~/.config/sshive/connections.json
        - Windows: %APPDATA%/sshive/connections.json
    """

    def __init__(self, config_path: Path | None = None):
        """Initialize storage.

        Args:
            config_path: Custom config file path (optional, mainly for testing)
        """
        if config_path:
            self.config_file = config_path
        else:
            self.config_file = self._get_default_config_path()

        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize empty config if doesn't exist
        if not self.config_file.exists():
            self.save_connections([])

    @staticmethod
    def _get_default_config_path() -> Path:
        """Get platform-specific config file path."""
        config_dir = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        )
        return config_dir / "connections.json"

    def _load_data(self) -> dict:
        """Load raw storage JSON with defaults.

        Returns:
            Parsed storage payload with required keys.
        """
        with open(self.config_file, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Storage file must contain a JSON object")

        data.setdefault("version", "1.0")
        data.setdefault("connections", [])
        data.setdefault("recent_connections", [])
        return data

    def _save_data(self, data: dict) -> None:
        """Save full storage payload to disk."""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_connections(self) -> list[SSHConnection]:
        """Load all connections from storage.

        Returns:
            List of SSHConnection objects
        """
        try:
            data = self._load_data()

            raw_connections = data.get("connections", [])
            needs_migration = False

            # Check if migration is needed (missing IDs)
            for conn_data in raw_connections:
                if not conn_data.get("id"):
                    needs_migration = True
                    break

            connections = [SSHConnection.from_dict(conn_data) for conn_data in raw_connections]

            if needs_migration:
                self.save_connections(connections)

            return connections

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading connections: {e}")
            return []

    def save_connections(self, connections: list[SSHConnection]) -> None:
        """Save all connections to storage.

        Args:
            connections: List of SSHConnection objects to save
        """
        try:
            data = self._load_data()
        except (json.JSONDecodeError, OSError, ValueError):
            data = {"version": "1.0", "recent_connections": []}

        data["version"] = "1.0"
        data["connections"] = [conn.to_dict() for conn in connections]
        self._save_data(data)

    def add_connection(self, connection: SSHConnection) -> None:
        """Add a new connection.

        Args:
            connection: SSHConnection to add
        """
        connections = self.load_connections()
        connections.append(connection)
        self.save_connections(connections)

    def update_connection(self, connection: SSHConnection) -> None:
        """Update an existing connection or add if not found.

        Args:
            connection: SSHConnection with updated data
        """
        connections = self.load_connections()
        found = False

        # Find and replace connection with matching ID
        for i, conn in enumerate(connections):
            if conn.id == connection.id:
                connections[i] = connection
                found = True
                break

        if not found:
            connections.append(connection)

        self.save_connections(connections)

    def delete_connection(self, connection_id: str) -> None:
        """Delete a connection by ID.

        Args:
            connection_id: ID of connection to delete
        """
        connections = self.load_connections()
        connections = [conn for conn in connections if conn.id != connection_id]
        self.save_connections(connections)

        try:
            data = self._load_data()
            data["recent_connections"] = [
                entry
                for entry in data.get("recent_connections", [])
                if entry.get("id") != connection_id
            ]
            self._save_data(data)
        except (json.JSONDecodeError, OSError, ValueError):
            return

    def get_groups(self) -> list[str]:
        """Get list of unique group names.

        Returns:
            Sorted list of group names
        """
        connections = self.load_connections()
        groups = {conn.group for conn in connections if conn.group}
        return sorted(groups)

    def get_recent_connections(self, limit: int = 10) -> list[dict]:
        """Return recent connection usage entries in newest-first order."""
        try:
            data = self._load_data()
        except (json.JSONDecodeError, OSError, ValueError):
            return []

        recent = data.get("recent_connections", [])
        if not isinstance(recent, list):
            return []

        sanitized: list[dict] = []
        for entry in recent:
            if not isinstance(entry, dict):
                continue

            connection_id = str(entry.get("id", "")).strip()
            if not connection_id:
                continue

            sanitized.append(
                {
                    "id": connection_id,
                    "name": str(entry.get("name", "")).strip(),
                    "host": str(entry.get("host", "")).strip(),
                    "user": str(entry.get("user", "")).strip(),
                    "port": int(entry.get("port", 22)),
                    "last_connected_at": str(entry.get("last_connected_at", "")).strip(),
                }
            )

            if len(sanitized) >= limit:
                break

        return sanitized

    def record_connection_used(self, connection: SSHConnection, max_entries: int = 10) -> None:
        """Record a successful connection launch in recent history."""
        try:
            data = self._load_data()
        except (json.JSONDecodeError, OSError, ValueError):
            return

        recent = data.get("recent_connections", [])
        if not isinstance(recent, list):
            recent = []

        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        entry = {
            "id": connection.id,
            "name": connection.name,
            "host": connection.host,
            "user": connection.user,
            "port": connection.port,
            "last_connected_at": timestamp,
        }

        deduplicated = [
            item for item in recent if isinstance(item, dict) and item.get("id") != connection.id
        ]
        deduplicated.insert(0, entry)

        data["recent_connections"] = deduplicated[:max_entries]
        self._save_data(data)

    def clear_recent_connections(self) -> None:
        """Clear all recent connection history entries."""
        try:
            data = self._load_data()
        except (json.JSONDecodeError, OSError, ValueError):
            return

        data["recent_connections"] = []
        self._save_data(data)
