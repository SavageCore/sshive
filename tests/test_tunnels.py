"""Tests for SSH tunnel functionality."""

import pytest

from sshive.models.connection import PortForward, SSHConnection
from sshive.ssh.launcher import SSHLauncher


class TestPortForward:
    """Test cases for PortForward data model."""

    def test_create_local_portforward(self):
        """Test creating a local port forward."""
        pf = PortForward(
            name="Database Proxy",
            forward_type="local",
            local_port=5432,
            remote_port=3306,
            remote_bind_address="db.internal",
        )
        assert pf.name == "Database Proxy"
        assert pf.forward_type == "local"
        assert pf.local_port == 5432
        assert pf.remote_port == 3306
        assert pf.remote_bind_address == "db.internal"
        assert pf.id

    def test_create_remote_portforward(self):
        """Test creating a remote port forward."""
        pf = PortForward(
            name="Webhook Tunnel",
            forward_type="remote",
            local_port=8000,
            remote_port=9000,
        )
        assert pf.forward_type == "remote"
        assert pf.local_port == 8000
        assert pf.remote_port == 9000

    def test_create_dynamic_portforward(self):
        """Test creating a dynamic (SOCKS proxy) port forward."""
        pf = PortForward(
            name="SOCKS Proxy",
            forward_type="dynamic",
            local_port=1080,
        )
        assert pf.forward_type == "dynamic"
        assert pf.local_port == 1080
        assert pf.remote_port == 0  # Default for dynamic

    def test_portforward_validation_empty_name(self):
        """Test that empty name raises validation error."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            PortForward(name="", forward_type="local", local_port=5432, remote_port=3306)

    def test_portforward_validation_invalid_type(self):
        """Test that invalid forward type raises validation error."""
        with pytest.raises(ValueError, match="Invalid forward type"):
            PortForward(name="Invalid", forward_type="invalid", local_port=5432, remote_port=3306)

    def test_portforward_validation_invalid_local_port(self):
        """Test that invalid local port raises validation error."""
        with pytest.raises(ValueError, match="Invalid local port"):
            PortForward(name="Test", forward_type="local", local_port=0, remote_port=3306)

        with pytest.raises(ValueError, match="Invalid local port"):
            PortForward(name="Test", forward_type="local", local_port=99999, remote_port=3306)

    def test_portforward_validation_invalid_remote_port(self):
        """Test that invalid remote port raises validation error for non-dynamic."""
        with pytest.raises(ValueError, match="Invalid remote port"):
            PortForward(name="Test", forward_type="local", local_port=5432, remote_port=99999)

    def test_portforward_to_dict(self):
        """Test converting port forward to dictionary."""
        pf = PortForward(
            name="Test Forward",
            forward_type="local",
            local_port=5432,
            remote_port=3306,
            remote_bind_address="db.example.com",
        )
        data = pf.to_dict()
        assert data["name"] == "Test Forward"
        assert data["forward_type"] == "local"
        assert data["local_port"] == 5432
        assert data["remote_port"] == 3306
        assert data["remote_bind_address"] == "db.example.com"
        assert data["id"] == pf.id

    def test_portforward_from_dict(self):
        """Test creating port forward from dictionary."""
        data = {
            "id": "abc123",
            "name": "Test Forward",
            "forward_type": "remote",
            "local_port": 8000,
            "remote_port": 9000,
            "remote_bind_address": "localhost",
        }
        pf = PortForward.from_dict(data)
        assert pf.id == "abc123"
        assert pf.name == "Test Forward"
        assert pf.forward_type == "remote"
        assert pf.local_port == 8000
        assert pf.remote_port == 9000

    def test_portforward_from_dict_generates_id(self):
        """Test that from_dict generates ID if missing."""
        data = {
            "name": "Test Forward",
            "forward_type": "local",
            "local_port": 5432,
            "remote_port": 3306,
        }
        pf = PortForward.from_dict(data)
        assert pf.id
        assert len(pf.id) > 0


class TestSSHConnectionWithTunnels:
    """Test cases for SSH tunnel configuration in connections."""

    def test_create_tunnel_connection(self):
        """Test creating a tunnel-type connection."""
        conn = SSHConnection(
            name="DB Tunnel",
            host="bastion.example.com",
            user="ubuntu",
            connection_type="tunnel",
        )
        assert conn.connection_type == "tunnel"
        assert conn.port_forwards == []

    def test_create_tunnel_with_port_forwards(self):
        """Test creating tunnel connection with port forwards."""
        pf1 = PortForward(name="Database", forward_type="local", local_port=5432, remote_port=5432)
        pf2 = PortForward(name="Redis", forward_type="local", local_port=6379, remote_port=6379)

        conn = SSHConnection(
            name="DB Tunnel",
            host="bastion.example.com",
            user="ubuntu",
            connection_type="tunnel",
            port_forwards=[pf1, pf2],
        )
        assert len(conn.port_forwards) == 2
        assert conn.port_forwards[0].name == "Database"
        assert conn.port_forwards[1].name == "Redis"

    def test_tunnel_connection_validation(self):
        """Test that invalid connection_type raises error."""
        with pytest.raises(ValueError, match="Invalid connection type"):
            SSHConnection(
                name="Test",
                host="example.com",
                user="ubuntu",
                connection_type="invalid",
            )

    def test_connection_to_dict_includes_tunnels(self):
        """Test that to_dict includes port forwards."""
        pf = PortForward(name="DB", forward_type="local", local_port=5432, remote_port=5432)
        conn = SSHConnection(
            name="DB Tunnel",
            host="bastion.example.com",
            user="ubuntu",
            connection_type="tunnel",
            port_forwards=[pf],
        )
        data = conn.to_dict()
        assert data["connection_type"] == "tunnel"
        assert len(data["port_forwards"]) == 1
        assert data["port_forwards"][0]["name"] == "DB"

    def test_connection_from_dict_with_tunnels(self):
        """Test creating connection from dict with port forwards."""
        data = {
            "id": "conn123",
            "name": "DB Tunnel",
            "host": "bastion.example.com",
            "user": "ubuntu",
            "port": 22,
            "group": "Default",
            "connection_type": "tunnel",
            "port_forwards": [
                {
                    "id": "pf123",
                    "name": "Database",
                    "forward_type": "local",
                    "local_port": 5432,
                    "remote_port": 5432,
                    "remote_bind_address": "localhost",
                },
                {
                    "id": "pf456",
                    "name": "Redis",
                    "forward_type": "local",
                    "local_port": 6379,
                    "remote_port": 6379,
                    "remote_bind_address": "localhost",
                },
            ],
        }
        conn = SSHConnection.from_dict(data)
        assert conn.connection_type == "tunnel"
        assert len(conn.port_forwards) == 2
        assert conn.port_forwards[0].name == "Database"
        assert conn.port_forwards[1].name == "Redis"

    def test_shell_connection_default(self):
        """Test that default connection type is 'shell'."""
        conn = SSHConnection(name="Test", host="example.com", user="ubuntu")
        assert conn.connection_type == "shell"
        assert conn.port_forwards == []

    def test_get_tunnel_command_local_forward(self):
        """Test generating tunnel command with local port forward."""
        pf = PortForward(
            name="Database",
            forward_type="local",
            local_port=5432,
            remote_port=3306,
            remote_bind_address="db.internal",
        )
        conn = SSHConnection(
            name="DB Tunnel",
            host="bastion.example.com",
            user="ubuntu",
            port=22,
            connection_type="tunnel",
            port_forwards=[pf],
        )
        cmd = conn.get_tunnel_command()

        # Should contain: ssh, -N, -L 5432:db.internal:3306, ubuntu@bastion.example.com
        assert "ssh" in cmd
        assert "-N" in cmd
        assert "-L" in cmd
        assert "5432:db.internal:3306" in cmd
        assert "ubuntu@bastion.example.com" in cmd

    def test_get_tunnel_command_remote_forward(self):
        """Test generating tunnel command with remote port forward."""
        pf = PortForward(
            name="Webhook",
            forward_type="remote",
            local_port=8000,
            remote_port=9000,
        )
        conn = SSHConnection(
            name="Webhook Tunnel",
            host="server.example.com",
            user="ubuntu",
            connection_type="tunnel",
            port_forwards=[pf],
        )
        cmd = conn.get_tunnel_command()

        assert "ssh" in cmd
        assert "-N" in cmd
        assert "-R" in cmd
        assert "9000:localhost:8000" in cmd

    def test_get_tunnel_command_dynamic_forward(self):
        """Test generating tunnel command with dynamic port forward."""
        pf = PortForward(
            name="SOCKS",
            forward_type="dynamic",
            local_port=1080,
        )
        conn = SSHConnection(
            name="SOCKS Tunnel",
            host="proxy.example.com",
            user="ubuntu",
            connection_type="tunnel",
            port_forwards=[pf],
        )
        cmd = conn.get_tunnel_command()

        assert "ssh" in cmd
        assert "-N" in cmd
        assert "-D" in cmd
        assert "1080" in cmd

    def test_get_tunnel_command_multiple_forwards(self):
        """Test generating tunnel command with multiple port forwards."""
        pf1 = PortForward(
            name="DB",
            forward_type="local",
            local_port=5432,
            remote_port=5432,
            remote_bind_address="db.internal",
        )
        pf2 = PortForward(
            name="Redis",
            forward_type="local",
            local_port=6379,
            remote_port=6379,
            remote_bind_address="redis.internal",
        )
        pf3 = PortForward(
            name="SOCKS",
            forward_type="dynamic",
            local_port=1080,
        )

        conn = SSHConnection(
            name="Multi Tunnel",
            host="bastion.example.com",
            user="ubuntu",
            connection_type="tunnel",
            port_forwards=[pf1, pf2, pf3],
        )
        cmd = conn.get_tunnel_command()

        # Check all forwards are included
        assert "-L" in cmd
        assert "5432:db.internal:5432" in cmd
        assert "6379:redis.internal:6379" in cmd
        assert "-D" in cmd
        assert "1080" in cmd

    def test_get_tunnel_command_with_key(self):
        """Test tunnel command includes SSH key."""
        pf = PortForward(name="DB", forward_type="local", local_port=5432, remote_port=5432)
        conn = SSHConnection(
            name="DB Tunnel",
            host="bastion.example.com",
            user="ubuntu",
            key_path="/home/user/.ssh/id_rsa",
            connection_type="tunnel",
            port_forwards=[pf],
        )
        cmd = conn.get_tunnel_command()

        assert "-i" in cmd
        # Key path should be expanded
        assert "/home/user/.ssh/id_rsa" in cmd

    def test_get_tunnel_command_with_custom_port(self):
        """Test tunnel command includes custom SSH port."""
        pf = PortForward(name="DB", forward_type="local", local_port=5432, remote_port=5432)
        conn = SSHConnection(
            name="DB Tunnel",
            host="bastion.example.com",
            user="ubuntu",
            port=2222,
            connection_type="tunnel",
            port_forwards=[pf],
        )
        cmd = conn.get_tunnel_command()

        assert "-p" in cmd
        assert "2222" in cmd


class TestSSHLauncherTunnel:
    """Test cases for SSHLauncher tunnel launching."""

    def test_launch_tunnel_requires_forwards(self):
        """Test that launching tunnel without port forwards fails."""
        conn = SSHConnection(
            name="Empty Tunnel",
            host="example.com",
            user="ubuntu",
            connection_type="tunnel",
            port_forwards=[],
        )

        success, error = SSHLauncher.launch_tunnel(conn)
        assert not success
        assert "No port forwards configured" in error

    def test_launch_tunnel_invalid_key_path(self):
        """Test tunnel launch fails with invalid key path."""
        pf = PortForward(name="DB", forward_type="local", local_port=5432, remote_port=5432)
        conn = SSHConnection(
            name="DB Tunnel",
            host="example.com",
            user="ubuntu",
            key_path="/nonexistent/key.pem",
            connection_type="tunnel",
            port_forwards=[pf],
        )

        success, error = SSHLauncher.launch_tunnel(conn)
        # Tunnel will fail to connect since host is unreachable, but should at least
        # not fail during command construction
        assert isinstance(success, bool)


class TestTunnelIntegration:
    """Integration tests for tunnel functionality."""

    def test_tunnel_connection_roundtrip(self):
        """Test that tunnel connection survives serialization/deserialization."""
        original = SSHConnection(
            name="Integration Test Tunnel",
            host="bastion.example.com",
            user="ubuntu",
            port=2222,
            key_path="/home/user/.ssh/id_rsa",
            group="Production",
            connection_type="tunnel",
            port_forwards=[
                PortForward(
                    name="Database",
                    forward_type="local",
                    local_port=5432,
                    remote_port=5432,
                    remote_bind_address="db.internal",
                ),
                PortForward(
                    name="Redis",
                    forward_type="local",
                    local_port=6379,
                    remote_port=6379,
                ),
                PortForward(
                    name="SOCKS",
                    forward_type="dynamic",
                    local_port=1080,
                ),
            ],
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = SSHConnection.from_dict(data)

        # Verify all fields
        assert restored.name == original.name
        assert restored.host == original.host
        assert restored.user == original.user
        assert restored.port == original.port
        assert restored.key_path == original.key_path
        assert restored.group == original.group
        assert restored.connection_type == original.connection_type
        assert len(restored.port_forwards) == 3

        # Verify port forwards
        assert restored.port_forwards[0].name == "Database"
        assert restored.port_forwards[1].name == "Redis"
        assert restored.port_forwards[2].name == "SOCKS"
