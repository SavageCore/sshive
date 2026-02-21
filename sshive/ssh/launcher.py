"""SSH connection launcher with terminal detection."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from sshive.models.connection import SSHConnection


class SSHLauncher:
    """Handles launching SSH connections in appropriate terminal emulators."""

    @staticmethod
    def detect_terminal() -> tuple[str, list[str]]:
        """Detect available terminal emulator.

        Returns:
            Tuple of (terminal_name, command_template)
            command_template uses {cmd} placeholder for SSH command
        """
        # Linux terminals
        terminals = {
            "konsole": ["konsole", "-e"],
            "gnome-terminal": ["gnome-terminal", "--"],
            "xfce4-terminal": ["xfce4-terminal", "-e"],
            "alacritty": ["alacritty", "-e"],
            "kitty": ["kitty"],
            "tilix": ["tilix", "-e"],
            "terminator": ["terminator", "-e"],
            "xterm": ["xterm", "-e"],
        }

        # macOS terminals
        if sys.platform == "darwin":
            terminals = {
                "iTerm": ["open", "-a", "iTerm"],
                "Terminal": ["open", "-a", "Terminal"],
                "alacritty": ["alacritty", "-e"],
            }

        # Windows/WSL
        elif sys.platform == "win32":
            terminals = {
                "wt": ["wt.exe"],  # Windows Terminal
                "cmd": ["cmd", "/c", "start"],
            }

        # Find first available terminal
        for term_name, cmd_template in terminals.items():
            if shutil.which(cmd_template[0]):
                return term_name, cmd_template

        # Fallback
        return "xterm", ["xterm", "-e"]

    @staticmethod
    def launch(connection: SSHConnection) -> bool:
        """Launch SSH connection in terminal.

        Args:
            connection: SSHConnection to launch

        Returns:
            True if launch successful, False otherwise
        """
        try:
            terminal_name, terminal_cmd = SSHLauncher.detect_terminal()
            ssh_cmd = connection.get_ssh_command()

            # Build full command
            if terminal_name in [
                "konsole",
                "gnome-terminal",
                "xfce4-terminal",
                "alacritty",
                "tilix",
                "terminator",
                "xterm",
            ]:
                # These terminals support -e or -- followed by command
                full_cmd = terminal_cmd + ssh_cmd

            elif terminal_name in ["kitty"]:
                # kitty takes command directly
                full_cmd = terminal_cmd + ssh_cmd

            elif terminal_name == "wt":
                # Windows Terminal
                full_cmd = terminal_cmd + ssh_cmd

            elif terminal_name in ["iTerm", "Terminal"]:
                # macOS - need to create temporary script
                script = f"ssh {' '.join(ssh_cmd[1:])}"
                full_cmd = terminal_cmd + [script]

            else:
                # Generic fallback
                full_cmd = terminal_cmd + ssh_cmd

            # Clean up environment variables so PyInstaller bundles don't
            # break system terminal apps (e.g. Konsole using wrong Qt versions)
            env = os.environ.copy()
            if getattr(sys, "frozen", False):
                for var in ["LD_LIBRARY_PATH", "PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH"]:
                    orig_var = f"{var}_ORIG"
                    if orig_var in env:
                        env[var] = env[orig_var]
                    else:
                        env.pop(var, None)

            # Launch in background
            subprocess.Popen(
                full_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )

            return True

        except Exception as e:
            print(f"Failed to launch SSH connection: {e}")
            return False

    @staticmethod
    def test_connection(connection: SSHConnection) -> bool:
        """Test if SSH connection is possible (doesn't actually connect).

        Args:
            connection: SSHConnection to test

        Returns:
            True if SSH command exists and key file is valid (if specified)
        """
        # Check if ssh command exists
        if not shutil.which("ssh"):
            return False

        # Check if key file exists (if specified)
        if connection.key_path:
            key_path = Path(connection.key_path).expanduser()
            if not key_path.exists():
                return False

        return True
