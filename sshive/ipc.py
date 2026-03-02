"""Single-instance IPC mechanism using Unix sockets."""

import json
import logging
import socket
from pathlib import Path

logger = logging.getLogger(__name__)


def get_ipc_socket_path() -> Path:
    """Get the path to the IPC socket file."""
    runtime_dir = Path.home() / ".cache" / "sshive"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / "ipc.sock"


class IPCServer:
    """Simple IPC server for receiving commands from other instances."""

    def __init__(self):
        """Initialize IPC server."""
        self.socket_path = get_ipc_socket_path()
        self.server_socket: socket.socket | None = None
        self.is_running = False

    def start(self) -> bool:
        """Start the IPC server.

        Returns:
            True if server started successfully, False if another instance is already running.
        """
        # Remove stale socket file if it exists
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                logger.debug(f"Could not remove stale socket {self.socket_path}")
                return False

        try:
            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(str(self.socket_path))
            self.server_socket.listen(1)
            self.server_socket.setblocking(False)
            self.is_running = True
            logger.debug(f"IPC server started on {self.socket_path}")
            return True
        except OSError as e:
            logger.debug(f"Could not start IPC server: {e}")
            return False

    def send_command(self, commands: list[str]) -> bool:
        """Send command to running instance.

        Args:
            commands: List of command flags to send.

        Returns:
            True if command was sent successfully.
        """
        socket_path = get_ipc_socket_path()
        if not socket_path.exists():
            return False

        try:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(str(socket_path))
            message = json.dumps({"action": "command", "args": commands})
            client_socket.sendall(message.encode() + b"\n")
            client_socket.close()
            logger.debug(f"Sent IPC command: {commands}")
            return True
        except (OSError, json.JSONDecodeError) as e:
            logger.debug(f"Could not send IPC command: {e}")
            return False

    def accept_commands(self) -> dict | None:
        """Accept and parse a single incoming command.

        Returns:
            Parsed command dict if available, None otherwise.
        """
        if not self.server_socket or not self.is_running:
            return None

        try:
            connection, _ = self.server_socket.accept()
            data = connection.recv(1024).decode().strip()
            connection.close()

            if data:
                message = json.loads(data)
                logger.debug(f"Received IPC command: {message}")
                return message
        except (OSError, json.JSONDecodeError):
            pass

        return None

    def cleanup(self):
        """Clean up server resources."""
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass

        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass

        self.is_running = False
