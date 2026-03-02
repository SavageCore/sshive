"""Storage module for SSH connections."""

import json
from datetime import datetime, timezone
from pathlib import Path

import platformdirs

from sshive.models.connection import SSHConnection
from sshive.models.putty_importer import PuTTYImporter


class ConnectionStorage:
    """Handles persistence of SSH connections to JSON file.

    Storage location determined by platformdirs:
        - Linux: ~/.config/sshive/connections.json
        - macOS: ~/Library/Application Support/sshive/connections.json
        - Windows: %APPDATA%\\sshive\\connections.json
    """

    def __init__(self, config_path: Path | None = None, max_backups: int = 10):
        """Initialize storage.

        Args:
            config_path: Custom config file path (optional, mainly for testing)
            max_backups: Maximum number of automatic backups to keep (default 10)
        """
        if config_path:
            self.config_file = config_path
        else:
            self.config_file = self._get_default_config_path()

        self.max_backups = max_backups
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize empty config if doesn't exist
        if not self.config_file.exists():
            self._save_data({"version": "1.0", "connections": [], "recent_connections": []})

    @staticmethod
    def _get_default_config_path() -> Path:
        """Get platform-specific config file path."""
        config_dir = Path(platformdirs.user_config_dir("sshive"))
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

        # Create automatic backup after saving changes
        self.create_auto_backup()

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

    def get_backup_dir(self) -> Path:
        """Get backup directory path, creating it if needed."""
        backup_dir = self.config_file.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def create_auto_backup(self) -> Path | None:
        """Create automatic timestamped backup in config directory.

        Keeps only the most recent backups (count set by max_backups),
        deleting older ones automatically.

        Returns:
            Path to created backup file, or None if backup failed
        """
        try:
            backup_dir = self.get_backup_dir()
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            backup_file = backup_dir / f"connections-backup-{timestamp}.json"

            # Copy current connections file to backup
            with open(self.config_file, encoding="utf-8") as src:
                data = json.load(src)

            with open(backup_file, "w", encoding="utf-8") as dst:
                json.dump(data, dst, indent=2)

            # Clean up old backups (keep only max_backups most recent)
            backups = sorted(backup_dir.glob("connections-backup-*.json"))
            if len(backups) > self.max_backups:
                for old_backup in backups[: -self.max_backups]:
                    old_backup.unlink()

            return backup_file

        except (json.JSONDecodeError, OSError, ValueError):
            return None

    def export_connections(self, export_path: Path) -> bool:
        """Export connections to a file in user-chosen location.

        Args:
            export_path: Destination file path for export

        Returns:
            True if export succeeded, False otherwise
        """
        try:
            data = self._load_data()
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True
        except (json.JSONDecodeError, OSError, ValueError):
            return False

    def import_connections(self, import_path: Path, merge: bool = False) -> bool:
        """Import connections from a file.

        Args:
            import_path: Source file path to import from
            merge: If True, merge with existing connections. If False, replace all.

        Returns:
            True if import succeeded, False otherwise
        """
        try:
            with open(import_path, encoding="utf-8") as f:
                import_data = json.load(f)

            if not isinstance(import_data, dict):
                return False

            import_connections = import_data.get("connections", [])
            if not isinstance(import_connections, list):
                return False

            if merge:
                # Merge: load existing and add new ones (avoiding duplicates by ID)
                existing = self.load_connections()
                existing_ids = {conn.id for conn in existing}

                for conn_data in import_connections:
                    if isinstance(conn_data, dict):
                        # If it's a duplicate ID, skip it
                        if conn_data.get("id") not in existing_ids:
                            try:
                                new_conn = SSHConnection.from_dict(conn_data)
                                existing.append(new_conn)
                            except (KeyError, ValueError):
                                continue

                self.save_connections(existing)
            else:
                # Replace: load imported data and save
                new_connections = [
                    SSHConnection.from_dict(conn_data)
                    for conn_data in import_connections
                    if isinstance(conn_data, dict)
                ]
                self.save_connections(new_connections)

            return True

        except (json.JSONDecodeError, OSError, ValueError):
            return False

    def import_putty_connections(
        self, import_paths: Path | list[Path], merge: bool = False
    ) -> tuple[bool, int]:
        """Import connections from PuTTY/KiTTY configuration file(s).

        Args:
            import_paths: Path (or list of Paths) to PuTTY or KiTTY configuration file(s)
            merge: If True, merge with existing connections. If False, replace all.

        Returns:
            Tuple of (success: bool, count: int) where count is number of imported connections
        """
        try:
            # Handle both single path and list of paths
            if isinstance(import_paths, Path):
                paths = [import_paths]
            else:
                paths = import_paths

            all_connections = []
            for path in paths:
                connections = PuTTYImporter.import_from_file(path)
                all_connections.extend(connections)

            if not all_connections:
                return False, 0

            if merge:
                existing = self.load_connections()
                existing.extend(all_connections)
                self.save_connections(existing)
            else:
                self.save_connections(all_connections)

            return True, len(all_connections)

        except (OSError, ValueError) as e:
            print(f"Error importing from PuTTY/KiTTY: {e}")
            return False, 0
