"""SSH connection data model."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PortForward:
    """Represents a single port forwarding rule.

    Attributes:
        name: Display name (e.g., "Database proxy")
        forward_type: Type of forward - "local" (-L), "remote" (-R), or "dynamic" (-D)
        local_port: Local port number
        remote_port: Remote port number (ignored for dynamic)
        remote_bind_address: Remote bind address (usually "localhost" or "127.0.0.1")
        id: Unique identifier (auto-generated)
    """

    name: str
    forward_type: str  # "local", "remote", "dynamic"
    local_port: int
    remote_port: int = 0  # 0 for dynamic proxies
    remote_bind_address: str = "localhost"
    id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex)

    def __post_init__(self):
        """Validate port forward data."""
        if not self.name:
            raise ValueError("Port forward name cannot be empty")
        if self.forward_type not in ("local", "remote", "dynamic"):
            raise ValueError(
                f"Invalid forward type: {self.forward_type}. "
                'Must be "local", "remote", or "dynamic"'
            )
        if self.local_port < 1 or self.local_port > 65535:
            raise ValueError(f"Invalid local port: {self.local_port}")
        if self.forward_type != "dynamic":
            if self.remote_port < 1 or self.remote_port > 65535:
                raise ValueError(f"Invalid remote port: {self.remote_port}")

    def to_dict(self) -> dict:
        """Convert port forward to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "forward_type": self.forward_type,
            "local_port": self.local_port,
            "remote_port": self.remote_port,
            "remote_bind_address": self.remote_bind_address,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PortForward":
        """Create port forward from dictionary."""
        if not data.get("id"):
            data["id"] = __import__("uuid").uuid4().hex
        return cls(
            id=data["id"],
            name=data["name"],
            forward_type=data["forward_type"],
            local_port=data["local_port"],
            remote_port=data.get("remote_port", 0),
            remote_bind_address=data.get("remote_bind_address", "localhost"),
        )


@dataclass
class SSHConnection:
    """Represents a single SSH connection configuration.

    Attributes:
        name: Display name for the connection
        host: Hostname or IP address
        user: SSH username
        port: SSH port number (default: 22)
        key_path: Path to SSH private key (optional)
        group: Organizational group name (optional)
        id: Unique identifier (auto-generated)
        icon: Icon name from selfh.st (optional)
        connection_type: Type of connection - "shell" or "tunnel" (default: "shell")
        port_forwards: List of PortForward configurations (only used if connection_type is "tunnel")
    """

    name: str
    host: str
    user: str
    port: int = 22
    key_path: str | None = None
    password: str | None = None
    group: str | None = "Default"
    icon: str | None = None
    connection_type: str = "shell"  # "shell" or "tunnel"
    port_forwards: list[PortForward] = field(default_factory=list)
    id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex)

    def __post_init__(self):
        """Validate connection data."""
        if not self.name:
            raise ValueError("Connection name cannot be empty")
        if not self.host:
            raise ValueError("Host cannot be empty")
        if not self.user:
            raise ValueError("User cannot be empty")
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")
        if self.connection_type not in ("shell", "tunnel"):
            raise ValueError(
                f'Invalid connection type: {self.connection_type}. Must be "shell" or "tunnel"'
            )
        if self.key_path:
            # Expand ~ to home directory
            self.key_path = str(Path(self.key_path).expanduser())

    def to_dict(self) -> dict:
        """Convert connection to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "user": self.user,
            "port": self.port,
            "key_path": self.key_path,
            "password": self.password,
            "group": self.group,
            "icon": self.icon,
            "connection_type": self.connection_type,
            "port_forwards": [pf.to_dict() for pf in self.port_forwards],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SSHConnection":
        """Create connection from dictionary."""
        # Ensure ID exists (for backward compatibility)
        if not data.get("id"):
            data["id"] = __import__("uuid").uuid4().hex

        # Parse port forwards if present
        port_forwards = []
        if "port_forwards" in data and data["port_forwards"]:
            port_forwards = [PortForward.from_dict(pf) for pf in data["port_forwards"]]

        return cls(
            id=data["id"],
            name=data["name"],
            host=data["host"],
            user=data["user"],
            port=data.get("port", 22),
            key_path=data.get("key_path"),
            password=data.get("password"),
            group=data.get("group", "Default"),
            icon=data.get("icon"),
            connection_type=data.get("connection_type", "shell"),
            port_forwards=port_forwards,
        )

    def get_ssh_command(self) -> list[str]:
        """Generate base SSH command arguments.

        Returns:
            List of command arguments suitable for subprocess
        """
        cmd = ["ssh"]

        if self.key_path:
            cmd.extend(["-i", self.key_path])

        if self.port != 22:
            cmd.extend(["-p", str(self.port)])

        cmd.append(f"{self.user}@{self.host}")

        return cmd

    def get_tunnel_command(self) -> list[str]:
        """Generate SSH tunnel command with all port forwards.

        Returns:
            List of command arguments suitable for subprocess
        """
        cmd = self.get_ssh_command()

        # Add -N to prevent remote command execution
        cmd.insert(-1, "-N")

        # Add port forwarding arguments
        for forward in self.port_forwards:
            if forward.forward_type == "local":
                # -L local_port:remote_bind_address:remote_port
                forward_arg = (
                    f"{forward.local_port}:{forward.remote_bind_address}:{forward.remote_port}"
                )
                cmd.insert(-1, "-L")
                cmd.insert(-1, forward_arg)
            elif forward.forward_type == "remote":
                # -R remote_port:local_bind_address:local_port
                forward_arg = f"{forward.remote_port}:localhost:{forward.local_port}"
                cmd.insert(-1, "-R")
                cmd.insert(-1, forward_arg)
            elif forward.forward_type == "dynamic":
                # -D local_port (SOCKS proxy)
                cmd.insert(-1, "-D")
                cmd.insert(-1, str(forward.local_port))

        return cmd

    def __str__(self) -> str:
        """String representation for display."""
        return f"{self.name} ({self.user}@{self.host}:{self.port})"
