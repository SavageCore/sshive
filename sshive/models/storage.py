"""Storage module for SSH connections."""

import json
from pathlib import Path
from typing import Optional

from sshive.models.connection import SSHConnection


class ConnectionStorage:
    """Handles persistence of SSH connections to JSON file.
    
    Storage location:
        - Linux/macOS: ~/.config/sshive/connections.json
        - Windows: %APPDATA%/sshive/connections.json
    """

    def __init__(self, config_path: Optional[Path] = None):
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
        if Path.home().joinpath(".config").exists():  # Linux/macOS
            return Path.home() / ".config" / "sshive" / "connections.json"
        else:  # Windows
            appdata = Path.home() / "AppData" / "Roaming"
            return appdata / "sshive" / "connections.json"

    def load_connections(self) -> list[SSHConnection]:
        """Load all connections from storage.
        
        Returns:
            List of SSHConnection objects
        """
        try:
            with open(self.config_file, encoding="utf-8") as f:
                data = json.load(f)
            
            connections = [
                SSHConnection.from_dict(conn_data) 
                for conn_data in data.get("connections", [])
            ]
            return connections
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading connections: {e}")
            return []

    def save_connections(self, connections: list[SSHConnection]) -> None:
        """Save all connections to storage.
        
        Args:
            connections: List of SSHConnection objects to save
        """
        data = {
            "version": "1.0",
            "connections": [conn.to_dict() for conn in connections]
        }
        
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_connection(self, connection: SSHConnection) -> None:
        """Add a new connection.
        
        Args:
            connection: SSHConnection to add
        """
        connections = self.load_connections()
        connections.append(connection)
        self.save_connections(connections)

    def update_connection(self, connection: SSHConnection) -> None:
        """Update an existing connection.
        
        Args:
            connection: SSHConnection with updated data
        """
        connections = self.load_connections()
        
        # Find and replace connection with matching ID
        for i, conn in enumerate(connections):
            if conn.id == connection.id:
                connections[i] = connection
                break
        
        self.save_connections(connections)

    def delete_connection(self, connection_id: str) -> None:
        """Delete a connection by ID.
        
        Args:
            connection_id: ID of connection to delete
        """
        connections = self.load_connections()
        connections = [conn for conn in connections if conn.id != connection_id]
        self.save_connections(connections)

    def get_groups(self) -> list[str]:
        """Get list of unique group names.
        
        Returns:
            Sorted list of group names
        """
        connections = self.load_connections()
        groups = {conn.group for conn in connections if conn.group}
        return sorted(groups)
