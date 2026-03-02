"""Tests for PuTTY/KiTTY session importer."""

import tempfile
from pathlib import Path

from sshive.models.connection import SSHConnection
from sshive.models.putty_importer import PuTTYImporter


class TestPuTTYImporter:
    """Test PuTTY registry and INI format parsing."""

    def test_parse_putty_registry_export(self):
        """Test parsing PuTTY Windows registry export format."""
        reg_content = """Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\Software\\SimonTatham\\PuTTY\\Sessions\\My Server]
"HostName"="example.com"
"UserName"="ubuntu"
"PortNumber"=dword:00000016
"PublicKeyFile"="C:\\\\Users\\\\john\\\\.ssh\\\\id_rsa"

[HKEY_CURRENT_USER\\Software\\SimonTatham\\PuTTY\\Sessions\\Another Server]
"HostName"="another.example.com"
"UserName"="admin"
"PortNumber"=dword:00000017
"""
        sessions = PuTTYImporter.parse_putty_registry_export(reg_content)

        assert len(sessions) == 2
        assert sessions[0]["HostName"] == "example.com"
        assert sessions[0]["UserName"] == "ubuntu"
        assert sessions[0]["PortNumber"] == 22  # 0x16 = 22
        assert sessions[1]["HostName"] == "another.example.com"
        assert sessions[1]["PortNumber"] == 23  # 0x17 = 23

    def test_parse_putty_ini(self):
        """Test parsing PuTTY INI format."""
        ini_content = """[Default Settings]
HostName=
UserName=
PortNumber=22

[Production Server]
HostName=prod.example.com
UserName=produser
PortNumber=2222
PublicKeyFile=/home/user/.ssh/prod_key

[Staging Server]
HostName=staging.example.com
UserName=staginguser
PortNumber=22
"""
        sessions = PuTTYImporter.parse_putty_ini(ini_content)

        # Should include Default Settings, Production, and Staging
        assert len(sessions) == 3

        # Find production server
        prod = next((s for s in sessions if s.get("HostName") == "prod.example.com"), None)
        assert prod is not None
        assert prod["UserName"] == "produser"
        assert prod["PortNumber"] == 2222

    def test_parse_kitty_ini(self):
        """Test parsing KiTTY INI format (same as PuTTY)."""
        ini_content = """[My Session]
HostName=server.example.com
UserName=kittyuser
PortNumber=22
"""
        sessions = PuTTYImporter.parse_kitty_ini(ini_content)

        assert len(sessions) == 1
        assert sessions[0]["HostName"] == "server.example.com"
        assert sessions[0]["UserName"] == "kittyuser"

    def test_normalize_session(self):
        """Test session normalization."""
        session = {
            "HostName": "example.com",
            "UserName": "testuser",
            "PortNumber": 2222,
        }

        normalized = PuTTYImporter._normalize_session(session)

        assert normalized is not None
        assert normalized["host"] == "example.com"
        assert normalized["user"] == "testuser"
        assert normalized["port"] == 2222

    def test_normalize_session_missing_required_fields(self):
        """Test that sessions without hostname are rejected."""
        session = {
            "UserName": "testuser",
            "PortNumber": 22,
        }

        normalized = PuTTYImporter._normalize_session(session)

        assert normalized is None

    def test_normalize_session_defaults(self):
        """Test default values in normalization."""
        session = {
            "HostName": "example.com",
        }

        normalized = PuTTYImporter._normalize_session(session)

        assert normalized is not None
        assert normalized["user"] == "root"
        assert normalized["port"] == 22

    def test_normalize_session_with_key_path(self):
        """Test key path expansion in normalization."""
        with tempfile.NamedTemporaryFile(suffix=".pem") as tmp:
            session = {
                "HostName": "example.com",
                "UserName": "user",
                "PublicKeyFile": tmp.name,
            }

            normalized = PuTTYImporter._normalize_session(session)

            assert normalized is not None
            assert normalized.get("key_path") == tmp.name

    def test_normalize_session_ignores_nonexistent_key(self):
        """Test that non-existent key paths are ignored."""
        session = {
            "HostName": "example.com",
            "UserName": "user",
            "PublicKeyFile": "/nonexistent/path/to/key.pem",
        }

        normalized = PuTTYImporter._normalize_session(session)

        assert normalized is not None
        assert "key_path" not in normalized

    def test_import_from_putty_registry(self):
        """Test converting PuTTY registry export to SSHConnection objects."""
        reg_content = """Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\Software\\SimonTatham\\PuTTY\\Sessions\\Test Server]
"HostName"="test.example.com"
"UserName"="testuser"
"PortNumber"=dword:00000016
"""
        connections = PuTTYImporter.import_from_putty_registry(reg_content)

        assert len(connections) == 1
        assert isinstance(connections[0], SSHConnection)
        assert connections[0].host == "test.example.com"
        assert connections[0].user == "testuser"
        assert connections[0].port == 22
        assert connections[0].group == "Imported from PuTTY"

    def test_import_from_putty_ini(self):
        """Test converting PuTTY INI format to SSHConnection objects."""
        ini_content = """[My Server]
HostName=myserver.com
UserName=myuser
PortNumber=2222

[Another Server]
HostName=anotherserver.com
UserName=anotheruser
PortNumber=22
"""
        connections = PuTTYImporter.import_from_putty_ini(ini_content)

        assert len(connections) == 2
        assert all(isinstance(c, SSHConnection) for c in connections)
        assert connections[0].group == "Imported from PuTTY"
        assert connections[1].group == "Imported from PuTTY"

    def test_import_from_file_registry_format(self):
        """Test auto-detection and import from registry format file."""
        reg_content = """Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\Software\\SimonTatham\\PuTTY\\Sessions\\File Test]
"HostName"="filetest.com"
"UserName"="fileuser"
"PortNumber"=dword:00000016
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".reg", delete=False) as tmp:
            tmp.write(reg_content)
            tmp.flush()

            try:
                connections = PuTTYImporter.import_from_file(Path(tmp.name))

                assert len(connections) == 1
                assert connections[0].host == "filetest.com"
                assert connections[0].user == "fileuser"
            finally:
                Path(tmp.name).unlink()

    def test_import_from_file_ini_format(self):
        """Test auto-detection and import from INI format file."""
        ini_content = """[Test Session]
HostName=ini.example.com
UserName=iniuser
PortNumber=22
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as tmp:
            tmp.write(ini_content)
            tmp.flush()

            try:
                connections = PuTTYImporter.import_from_file(Path(tmp.name))

                assert len(connections) == 1
                assert connections[0].host == "ini.example.com"
                assert connections[0].user == "iniuser"
            finally:
                Path(tmp.name).unlink()

    def test_import_from_file_nonexistent(self):
        """Test import from non-existent file."""
        connections = PuTTYImporter.import_from_file(Path("/nonexistent/file.reg"))

        assert connections == []

    def test_import_from_file_invalid_format(self):
        """Test import from file with invalid format."""
        invalid_content = "This is not a valid PuTTY or KiTTY config file."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write(invalid_content)
            tmp.flush()

            try:
                connections = PuTTYImporter.import_from_file(Path(tmp.name))

                assert connections == []
            finally:
                Path(tmp.name).unlink()

    def test_import_from_file_linux_single_session_no_extension(self, tmp_path):
        """Test importing a Linux PuTTY single session file without extension."""
        session_file = tmp_path / "seedbox.example.com"
        session_file.write_text("HostName=seedbox.example.com\nUserName=seeduser\nPortNumber=22\n")

        connections = PuTTYImporter.import_from_file(session_file)

        assert len(connections) == 1
        assert connections[0].name == "seedbox.example.com"
        assert connections[0].host == "seedbox.example.com"
        assert connections[0].user == "seeduser"
        assert connections[0].port == 22
        assert connections[0].group == "Imported from PuTTY"
