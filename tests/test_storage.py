"""Tests for connection storage."""

import json
import tempfile
import time
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

        # Cleanup - remove all files and directories
        import shutil

        if temp_path.parent.exists():
            shutil.rmtree(temp_path.parent)

    @pytest.fixture
    def storage(self, temp_config):
        """Create storage instance with temporary config."""
        return ConnectionStorage(temp_config, max_backups=3)

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

    def test_record_connection_used_persists_recent_history(self, storage):
        """Successful connection usage is persisted in recent history."""
        conn = SSHConnection(name="Prod", host="prod.example.com", user="root", port=2222)
        storage.add_connection(conn)

        storage.record_connection_used(conn)
        recent = storage.get_recent_connections()

        assert len(recent) == 1
        assert recent[0]["id"] == conn.id
        assert recent[0]["name"] == "Prod"
        assert recent[0]["host"] == "prod.example.com"
        assert recent[0]["user"] == "root"
        assert recent[0]["port"] == 2222
        assert recent[0]["last_connected_at"]

    def test_record_connection_used_deduplicates_and_bubbles_to_top(self, storage):
        """Reconnecting to an entry moves it to the top without duplicates."""
        conn_a = SSHConnection(name="A", host="a.example.com", user="alice")
        conn_b = SSHConnection(name="B", host="b.example.com", user="bob")
        storage.save_connections([conn_a, conn_b])

        storage.record_connection_used(conn_a)
        storage.record_connection_used(conn_b)
        storage.record_connection_used(conn_a)

        recent = storage.get_recent_connections()
        assert [item["id"] for item in recent] == [conn_a.id, conn_b.id]

    def test_record_connection_used_respects_max_entries(self, storage):
        """Recent history keeps only configured max number of entries."""
        connections = [
            SSHConnection(name=f"Server {i}", host=f"h{i}.example.com", user="user")
            for i in range(12)
        ]
        storage.save_connections(connections)

        for conn in connections:
            storage.record_connection_used(conn, max_entries=10)

        recent = storage.get_recent_connections(limit=20)
        assert len(recent) == 10

    def test_delete_connection_removes_recent_history_entry(self, storage):
        """Deleting a connection also removes it from recent history."""
        keep_conn = SSHConnection(name="Keep", host="keep.example.com", user="k")
        drop_conn = SSHConnection(name="Drop", host="drop.example.com", user="d")
        storage.save_connections([keep_conn, drop_conn])

        storage.record_connection_used(keep_conn)
        storage.record_connection_used(drop_conn)
        storage.delete_connection(drop_conn.id)

        recent = storage.get_recent_connections()
        assert [item["id"] for item in recent] == [keep_conn.id]

    def test_save_connections_preserves_recent_history(self, storage):
        """Saving connections does not wipe existing recent history."""
        conn = SSHConnection(name="Persist", host="persist.example.com", user="user")
        storage.add_connection(conn)
        storage.record_connection_used(conn)

        updated = SSHConnection(
            name="Persist Updated",
            host="persist.example.com",
            user="user",
            id=conn.id,
        )
        storage.save_connections([updated])

        recent = storage.get_recent_connections()
        assert len(recent) == 1
        assert recent[0]["id"] == conn.id

    def test_clear_recent_connections_removes_all_entries(self, storage):
        """clear_recent_connections removes all saved recent history entries."""
        conn = SSHConnection(name="Clear Me", host="clear.example.com", user="user")
        storage.add_connection(conn)
        storage.record_connection_used(conn)

        storage.clear_recent_connections()

        assert storage.get_recent_connections() == []

    def test_create_auto_backup(self, storage):
        """Test auto backup creation with log rotation."""
        conn = SSHConnection(name="Backup Test", host="backup.example.com", user="user")
        storage.add_connection(conn)

        # Verify backup was created automatically
        backup_dir = storage.get_backup_dir()
        backups = sorted(backup_dir.glob("connections-backup-*.json"))
        assert len(backups) >= 1

        backup_file = backups[-1]
        assert backup_file.exists()
        assert "connections-backup-" in backup_file.name
        assert backup_file.suffix == ".json"

        # Verify backup contains the connection
        with open(backup_file) as f:
            data = json.load(f)
        assert len(data["connections"]) == 1
        assert data["connections"][0]["name"] == "Backup Test"

    def test_auto_backup_log_rotation(self, storage):
        """Test that old backups are deleted when exceeding max_backups."""
        # Storage is configured with max_backups=3 in the fixture
        conn = SSHConnection(name="Rotation Test", host="rotation.example.com", user="user")
        storage.add_connection(conn)

        # Create 4 more backups, spacing them out to ensure unique timestamps
        # (first backup was created by add_connection)
        for i in range(3):
            time.sleep(1.1)  # Ensure unique timestamps
            conn2 = SSHConnection(
                name=f"Rotation Test {i}",
                host=f"rotation{i}.example.com",
                user="user",
            )
            storage.add_connection(conn2)

        backup_dir = storage.get_backup_dir()
        all_backups = sorted(backup_dir.glob("connections-backup-*.json"))

        # Should only keep 3 backups (as configured in fixture)
        assert len(all_backups) <= 3

    def test_export_connections(self, storage):
        """Test exporting connections to a file."""
        conn1 = SSHConnection(name="Export1", host="export1.example.com", user="user1")
        conn2 = SSHConnection(name="Export2", host="export2.example.com", user="user2")
        storage.add_connection(conn1)
        storage.add_connection(conn2)

        export_path = storage.config_file.parent / "export_test.json"

        success = storage.export_connections(export_path)

        assert success
        assert export_path.exists()

        with open(export_path) as f:
            data = json.load(f)

        assert len(data["connections"]) == 2
        assert data["connections"][0]["name"] == "Export1"
        assert data["connections"][1]["name"] == "Export2"

        # Cleanup
        export_path.unlink()

    def test_import_connections_replace(self, storage):
        """Test importing connections with replace mode."""
        # Create original connections
        original = SSHConnection(name="Original", host="original.example.com", user="user")
        storage.add_connection(original)
        assert len(storage.load_connections()) == 1

        # Create import file with different connections
        import_data = {
            "version": "1.0",
            "connections": [
                {
                    "id": "test-id-1",
                    "name": "Imported1",
                    "host": "imported1.example.com",
                    "user": "user1",
                    "port": 22,
                    "key": None,
                    "group": "default",
                    "tunnels": [],
                }
            ],
        }
        import_path = storage.config_file.parent / "import_test.json"
        with open(import_path, "w") as f:
            json.dump(import_data, f)

        # Import with replace=False
        success = storage.import_connections(import_path, merge=False)

        assert success
        loaded = storage.load_connections()
        assert len(loaded) == 1
        assert loaded[0].name == "Imported1"

        # Cleanup
        import_path.unlink()

    def test_import_connections_merge(self, storage):
        """Test importing connections with merge mode."""
        # Create original connections
        original = SSHConnection(name="Original", host="original.example.com", user="user")
        storage.add_connection(original)

        # Create import file
        import_data = {
            "version": "1.0",
            "connections": [
                {
                    "id": "test-id-2",
                    "name": "Imported2",
                    "host": "imported2.example.com",
                    "user": "user2",
                    "port": 22,
                    "key": None,
                    "group": "default",
                    "tunnels": [],
                }
            ],
        }
        import_path = storage.config_file.parent / "merge_test.json"
        with open(import_path, "w") as f:
            json.dump(import_data, f)

        # Import with merge=True
        success = storage.import_connections(import_path, merge=True)

        assert success
        loaded = storage.load_connections()
        assert len(loaded) == 2

        names = {conn.name for conn in loaded}
        assert "Original" in names
        assert "Imported2" in names

        # Cleanup
        import_path.unlink()

    def test_import_connections_merge_avoids_duplicates(self, storage):
        """Test that merge mode avoids duplicate IDs."""
        # Create original connections
        conn_id = "shared-id-123"
        original = SSHConnection(
            id=conn_id, name="Original", host="original.example.com", user="user"
        )
        storage.add_connection(original)

        # Create import file with same ID
        import_data = {
            "version": "1.0",
            "connections": [
                {
                    "id": conn_id,
                    "name": "Duplicate",
                    "host": "duplicate.example.com",
                    "user": "user",
                    "port": 22,
                    "key": None,
                    "group": "default",
                    "tunnels": [],
                }
            ],
        }
        import_path = storage.config_file.parent / "dup_test.json"
        with open(import_path, "w") as f:
            json.dump(import_data, f)

        # Import with merge=True
        success = storage.import_connections(import_path, merge=True)

        assert success
        loaded = storage.load_connections()
        # Should still be 1 connection (duplicate skipped)
        assert len(loaded) == 1
        assert loaded[0].name == "Original"  # Original kept, not overwritten

        # Cleanup
        import_path.unlink()

    def test_import_invalid_file(self, storage):
        """Test importing from invalid file."""
        invalid_path = storage.config_file.parent / "invalid.json"
        with open(invalid_path, "w") as f:
            f.write("not valid json{")

        success = storage.import_connections(invalid_path, merge=False)

        assert not success
        # Original connections should be unchanged
        assert len(storage.load_connections()) == 0

        # Cleanup
        invalid_path.unlink()
