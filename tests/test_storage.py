"""Tests for connection storage."""

import json
import tempfile
from pathlib import Path

import pytest

from sshive.models.connection import SSHConnection
from sshive.models.storage import ConnectionStorage


class TestConnectionStorage:
    """Test cases for ConnectionStorage class."""

    @pytest.fixture
    def temp_config(self):
        """Create temporary config file path for testing."""
        # Don't create the file - just get a path
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir) / "test_config.json"

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
        temp_path.parent.rmdir()

    @pytest.fixture
    def storage(self, temp_config):
        """Create storage instance with temporary config."""
        return ConnectionStorage(temp_config)

    def test_init_creates_config_file(self, temp_config):
        """Test that initialization creates config file."""
        ConnectionStorage(temp_config)

        assert temp_config.exists()

        with open(temp_config) as f:
            data = json.load(f)

        assert "connections" in data
        assert data["connections"] == []

    def test_save_and_load_connections(self, storage):
        """Test saving and loading connections."""
        connections = [
            SSHConnection(name="Server1", host="host1.com", user="user1"),
            SSHConnection(name="Server2", host="host2.com", user="user2"),
        ]

        storage.save_connections(connections)
        loaded = storage.load_connections()

        assert len(loaded) == 2
        assert loaded[0].name == "Server1"
        assert loaded[1].name == "Server2"

    def test_add_connection(self, storage):
        """Test adding a single connection."""
        conn = SSHConnection(name="Test", host="example.com", user="testuser")

        storage.add_connection(conn)
        loaded = storage.load_connections()

        assert len(loaded) == 1
        assert loaded[0].name == "Test"

    def test_update_connection(self, storage):
        """Test updating an existing connection."""
        # Add initial connection
        conn = SSHConnection(name="Original", host="example.com", user="testuser")
        storage.add_connection(conn)

        # Update it
        conn.name = "Updated"
        conn.port = 2222
        storage.update_connection(conn)

        # Load and verify
        loaded = storage.load_connections()

        assert len(loaded) == 1
        assert loaded[0].name == "Updated"
        assert loaded[0].port == 2222

    def test_delete_connection(self, storage):
        """Test deleting a connection."""
        # Add two connections
        conn1 = SSHConnection(name="Keep", host="host1.com", user="user1")
        conn2 = SSHConnection(name="Delete", host="host2.com", user="user2")

        storage.add_connection(conn1)
        storage.add_connection(conn2)

        # Delete one
        storage.delete_connection(conn2.id)

        # Verify only one remains
        loaded = storage.load_connections()

        assert len(loaded) == 1
        assert loaded[0].name == "Keep"

    def test_get_groups(self, storage):
        """Test getting unique group names."""
        connections = [
            SSHConnection(name="S1", host="h1.com", user="u1", group="Work"),
            SSHConnection(name="S2", host="h2.com", user="u2", group="Work"),
            SSHConnection(name="S3", host="h3.com", user="u3", group="Personal"),
            SSHConnection(name="S4", host="h4.com", user="u4", group="Personal"),
        ]

        storage.save_connections(connections)
        groups = storage.get_groups()

        assert len(groups) == 2
        assert "Work" in groups
        assert "Personal" in groups

    def test_load_empty_connections(self, storage):
        """Test loading when no connections exist."""
        loaded = storage.load_connections()

        assert loaded == []

    def test_load_corrupted_file(self, temp_config):
        """Test handling of corrupted JSON file."""
        # Write invalid JSON
        with open(temp_config, "w") as f:
            f.write("{ invalid json }")

        storage = ConnectionStorage(temp_config)
        loaded = storage.load_connections()

        # Should return empty list rather than crash
        assert loaded == []

    def test_connection_persistence(self, temp_config):
        """Test that connections persist across storage instances."""
        # Create connection with first instance
        storage1 = ConnectionStorage(temp_config)
        conn = SSHConnection(name="Persistent", host="example.com", user="testuser")
        storage1.add_connection(conn)

        # Create new storage instance pointing to same file
        storage2 = ConnectionStorage(temp_config)
        loaded = storage2.load_connections()

        assert len(loaded) == 1
        assert loaded[0].name == "Persistent"

    def test_save_preserves_all_fields(self, storage):
        """Test that all connection fields are preserved."""
        conn = SSHConnection(
            name="Full Test",
            host="example.com",
            user="testuser",
            port=2222,
            key_path="~/.ssh/custom_key",
            group="TestGroup",
        )

        storage.add_connection(conn)
        loaded = storage.load_connections()

        assert loaded[0].name == "Full Test"
        assert loaded[0].host == "example.com"
        assert loaded[0].user == "testuser"
        assert loaded[0].port == 2222
        assert "custom_key" in loaded[0].key_path
        assert loaded[0].group == "TestGroup"
