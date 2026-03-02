"""Integration tests for PuTTY importer with storage."""

import tempfile
from pathlib import Path

from sshive.models.storage import ConnectionStorage


class TestPuTTYStorageIntegration:
    """Test PuTTY/KiTTY import integration with storage."""

    def test_import_putty_ini_via_storage(self, tmp_path):
        """Test importing PuTTY INI format via storage."""
        config_file = tmp_path / "connections.json"
        storage = ConnectionStorage(config_path=config_file)

        ini_content = """[Server 1]
HostName=server1.example.com
UserName=user1
PortNumber=22

[Server 2]
HostName=server2.example.com
UserName=user2
PortNumber=2222
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as tmp:
            tmp.write(ini_content)
            tmp.flush()

            try:
                success, count = storage.import_putty_connections(Path(tmp.name), merge=False)

                assert success
                assert count == 2

                connections = storage.load_connections()
                assert len(connections) == 2
                assert connections[0].host == "server1.example.com"
                assert connections[1].host == "server2.example.com"
                assert all(c.group == "Imported from PuTTY" for c in connections)
            finally:
                Path(tmp.name).unlink()

    def test_import_putty_with_merge(self, tmp_path):
        """Test importing PuTTY configs with merge mode."""
        config_file = tmp_path / "connections.json"
        storage = ConnectionStorage(config_path=config_file)

        # Add an initial connection
        from sshive.models.connection import SSHConnection

        initial_conn = SSHConnection(
            name="Initial Server",
            host="initial.example.com",
            user="initialuser",
            port=22,
            group="Manual",
        )
        storage.add_connection(initial_conn)

        # Create PuTTY config
        ini_content = """[PuTTY Server]
HostName=putty.example.com
UserName=puttyuser
PortNumber=22
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as tmp:
            tmp.write(ini_content)
            tmp.flush()

            try:
                # Import with merge
                success, count = storage.import_putty_connections(Path(tmp.name), merge=True)

                assert success
                assert count == 1

                connections = storage.load_connections()
                assert len(connections) == 2  # Initial + imported
                assert connections[0].name == "Initial Server"  # Initial is preserved
                assert connections[1].host == "putty.example.com"  # Imported is added
            finally:
                Path(tmp.name).unlink()

    def test_import_putty_replace_mode(self, tmp_path):
        """Test importing PuTTY configs in replace mode."""
        config_file = tmp_path / "connections.json"
        storage = ConnectionStorage(config_path=config_file)

        # Add an initial connection
        from sshive.models.connection import SSHConnection

        initial_conn = SSHConnection(
            name="Initial Server",
            host="initial.example.com",
            user="initialuser",
            port=22,
        )
        storage.add_connection(initial_conn)

        assert len(storage.load_connections()) == 1

        # Create PuTTY config
        ini_content = """[PuTTY Server]
HostName=putty.example.com
UserName=puttyuser
PortNumber=22
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as tmp:
            tmp.write(ini_content)
            tmp.flush()

            try:
                # Import with replace
                success, count = storage.import_putty_connections(Path(tmp.name), merge=False)

                assert success
                assert count == 1

                connections = storage.load_connections()
                assert len(connections) == 1  # Initial is replaced
                assert connections[0].host == "putty.example.com"
            finally:
                Path(tmp.name).unlink()

    def test_import_invalid_file(self, tmp_path):
        """Test importing from invalid file."""
        config_file = tmp_path / "connections.json"
        storage = ConnectionStorage(config_path=config_file)

        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("This is not a valid PuTTY config")

        success, count = storage.import_putty_connections(invalid_file, merge=False)

        assert not success
        assert count == 0
        assert len(storage.load_connections()) == 0
