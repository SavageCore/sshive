"""SSH connection data model."""

from dataclasses import dataclass, field
from pathlib import Path


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
    """

    name: str
    host: str
    user: str
    port: int = 22
    key_path: str | None = None
    group: str | None = "Default"
    icon: str | None = None
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
            "group": self.group,
            "icon": self.icon,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SSHConnection":
        """Create connection from dictionary."""
        # Ensure ID exists (for backward compatibility)
        if not data.get("id"):
            data["id"] = __import__("uuid").uuid4().hex

        return cls(
            id=data["id"],
            name=data["name"],
            host=data["host"],
            user=data["user"],
            port=data.get("port", 22),
            key_path=data.get("key_path"),
            group=data.get("group", "Default"),
            icon=data.get("icon"),
        )

    def get_ssh_command(self) -> list[str]:
        """Generate SSH command arguments.

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

    def __str__(self) -> str:
        """String representation for display."""
        return f"{self.name} ({self.user}@{self.host}:{self.port})"
