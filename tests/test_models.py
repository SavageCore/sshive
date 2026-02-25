"""Tests for SSH connection model."""

import pytest

from sshive.models.connection import SSHConnection


class TestSSHConnection:
    """Test cases for SSHConnection class."""

    def test_create_basic_connection(self):
        """Test creating a basic SSH connection."""
        conn = SSHConnection(name="Test Server", host="example.com", user="testuser")

        assert conn.name == "Test Server"
        assert conn.host == "example.com"
        assert conn.user == "testuser"
        assert conn.port == 22  # Default port
        assert conn.key_path is None
        assert conn.group == "Default"
        assert conn.id is not None

    def test_create_connection_with_custom_port(self):
        """Test creating connection with custom port."""
        conn = SSHConnection(name="Test Server", host="example.com", user="testuser", port=2222)

        assert conn.port == 2222

    def test_create_connection_with_key(self):
        """Test creating connection with SSH key."""
        conn = SSHConnection(
            name="Test Server", host="example.com", user="testuser", key_path="~/.ssh/id_rsa"
        )

        assert conn.key_path is not None
        assert "/.ssh/id_rsa" in conn.key_path  # Path expanded

    def test_create_connection_with_group(self):
        """Test creating connection with group."""
        conn = SSHConnection(
            name="Test Server", host="example.com", user="testuser", group="Production"
        )

        assert conn.group == "Production"

    def test_validation_empty_name(self):
        """Test validation fails with empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            SSHConnection(name="", host="example.com", user="testuser")

    def test_validation_empty_host(self):
        """Test validation fails with empty host."""
        with pytest.raises(ValueError, match="Host cannot be empty"):
            SSHConnection(name="Test", host="", user="testuser")

    def test_validation_empty_user(self):
        """Test validation fails with empty user."""
        with pytest.raises(ValueError, match="User cannot be empty"):
            SSHConnection(name="Test", host="example.com", user="")

    def test_validation_invalid_port(self):
        """Test validation fails with invalid port."""
        with pytest.raises(ValueError, match="Invalid port"):
            SSHConnection(name="Test", host="example.com", user="testuser", port=99999)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        conn = SSHConnection(
            name="Test Server",
            host="example.com",
            user="testuser",
            port=2222,
            key_path="~/.ssh/id_rsa",
            password="testpass",
            group="Work",
        )

        data = conn.to_dict()

        assert data["name"] == "Test Server"
        assert data["host"] == "example.com"
        assert data["user"] == "testuser"
        assert data["port"] == 2222
        assert data["key_path"] == conn.key_path
        assert data["password"] == "testpass"
        assert data["group"] == "Work"
        assert data["id"] is not None

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "test123",
            "name": "Test Server",
            "host": "example.com",
            "user": "testuser",
            "port": 2222,
            "key_path": "~/.ssh/id_rsa",
            "password": "testpass",
            "group": "Work",
        }

        conn = SSHConnection.from_dict(data)

        assert conn.id == "test123"
        assert conn.name == "Test Server"
        assert conn.host == "example.com"
        assert conn.user == "testuser"
        assert conn.port == 2222
        assert conn.password == "testpass"
        assert conn.group == "Work"

    def test_get_ssh_command_basic(self):
        """Test SSH command generation for basic connection."""
        conn = SSHConnection(name="Test", host="example.com", user="testuser")

        cmd = conn.get_ssh_command()

        assert cmd == ["ssh", "testuser@example.com"]

    def test_get_ssh_command_with_key(self):
        """Test SSH command generation with key."""
        conn = SSHConnection(
            name="Test", host="example.com", user="testuser", key_path="~/.ssh/id_rsa"
        )

        cmd = conn.get_ssh_command()

        assert cmd[0] == "ssh"
        assert "-i" in cmd
        assert "testuser@example.com" in cmd

    def test_get_ssh_command_with_custom_port(self):
        """Test SSH command generation with custom port."""
        conn = SSHConnection(name="Test", host="example.com", user="testuser", port=2222)

        cmd = conn.get_ssh_command()

        assert "-p" in cmd
        assert "2222" in cmd

    def test_str_representation(self):
        """Test string representation."""
        conn = SSHConnection(name="My Server", host="example.com", user="testuser", port=22)

        str_repr = str(conn)

        assert "My Server" in str_repr
        assert "testuser@example.com" in str_repr
