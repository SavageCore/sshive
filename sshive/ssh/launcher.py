"""SSH connection launcher with terminal detection."""

import os
import shutil
import socket
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

            # Prepare SSH command
            ssh_cmd = connection.get_ssh_command()

            # Handle PPK conversion if necessary (Linux/macOS)
            temp_key = None
            if (
                connection.key_path
                and connection.key_path.lower().endswith(".ppk")
                and sys.platform != "win32"
            ):
                puttygen = shutil.which("puttygen")
                if puttygen:
                    import tempfile
                    from pathlib import Path

                    # Create a temporary file for the converted key
                    fd, temp_key_path = tempfile.mkstemp(prefix="sshive_key_", suffix=".key")
                    os.close(fd)
                    temp_key = Path(temp_key_path)

                    try:
                        # Convert unencrypted PPK to OpenSSH format
                        subprocess.run(
                            [
                                puttygen,
                                connection.key_path,
                                "-O",
                                "private-openssh",
                                "-o",
                                temp_key_path,
                            ],
                            check=True,
                            capture_output=True,
                        )

                        # Update ssh_cmd to use the converted key
                        for i, arg in enumerate(ssh_cmd):
                            if (
                                arg == "-i"
                                and i + 1 < len(ssh_cmd)
                                and ssh_cmd[i + 1] == connection.key_path
                            ):
                                ssh_cmd[i + 1] = temp_key_path
                                break
                    except Exception as e:
                        print(f"Failed to convert PPK key: {e}")
                        if temp_key.exists():
                            temp_key.unlink()
                        temp_key = None

            env = os.environ.copy()

            # Handle Passwords
            if connection.password:
                if sys.platform != "win32":
                    # Linux/macOS - use sshpass
                    if shutil.which("sshpass"):
                        env["SSHPASS"] = connection.password
                        ssh_cmd = ["sshpass", "-e"] + ssh_cmd
                else:
                    # Windows - try plink or klink
                    plink = shutil.which("plink.exe") or shutil.which("klink.exe")
                    if plink:
                        # plink has different flags
                        ssh_cmd = [plink, "-pw", connection.password]
                        if connection.key_path:
                            ssh_cmd.extend(["-i", connection.key_path])
                        if connection.port != 22:
                            ssh_cmd.extend(["-P", str(connection.port)])
                        ssh_cmd.append(f"{connection.user}@{connection.host}")

            # Build full command
            if (
                terminal_name
                in [
                    "konsole",
                    "gnome-terminal",
                    "xfce4-terminal",
                    "alacritty",
                    "tilix",
                    "terminator",
                    "xterm",
                ]
                and sys.platform != "win32"
            ):
                # Wrap Linux command in bash to keep window open on failure
                cmd_str = " ".join([f'"{arg}"' if " " in arg else arg for arg in ssh_cmd])
                wrapped_cmd = f"{cmd_str} || {{ echo -v; echo '----------------------------------------'; echo 'Connection failed or closed.'; read -p 'Press Enter to close...'; }}"
                full_cmd = terminal_cmd + ["bash", "-c", wrapped_cmd]

            elif terminal_name in ["kitty"]:
                # kitty takes command directly
                full_cmd = terminal_cmd + ssh_cmd

            elif terminal_name == "wt":
                # Windows Terminal handles plink directly
                full_cmd = terminal_cmd + ssh_cmd

            elif terminal_name in ["iTerm", "Terminal"]:
                # macOS - already a script
                script = f"ssh {' '.join(ssh_cmd[1:])}"
                full_cmd = terminal_cmd + [script]

            else:
                # Generic fallback
                full_cmd = terminal_cmd + ssh_cmd

            # Clean environment variables to prevent bundling conflicts with system terminals
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

            # Delete temporary key after a short delay to give terminal time to start
            if temp_key:

                def cleanup():
                    import time

                    time.sleep(5)  # Wait for SSH to read key
                    try:
                        if temp_key.exists():
                            temp_key.unlink()
                    except Exception:
                        pass

                import threading

                threading.Thread(target=cleanup, daemon=True).start()

            return True

        except Exception as e:
            print(f"Failed to launch SSH connection: {e}")
            return False

    @staticmethod
    def launch_tunnel(connection: SSHConnection) -> tuple[bool, str | None]:
        """Launch SSH tunnel in background.

        Creates a persistent SSH tunnel with all configured port forwards.
        Tunnel runs silently in the background with -N (no shell).

        Args:
            connection: SSHConnection with tunnel configuration (connection_type="tunnel")

        Returns:
            Tuple of (Success Status, Error Message or None)
        """
        if not connection.port_forwards:
            return False, "No port forwards configured for tunnel."

        try:
            # Get tunnel command with all port forwards
            tunnel_cmd = connection.get_tunnel_command()

            # Handle password authentication if needed
            env = os.environ.copy()
            if connection.password:
                if sys.platform != "win32":
                    if shutil.which("sshpass"):
                        env["SSHPASS"] = connection.password
                        tunnel_cmd = ["sshpass", "-e"] + tunnel_cmd
                    else:
                        return False, "Password authentication requires 'sshpass' to be installed."
                else:
                    # Windows doesn't easily support background tunnels with passwords
                    return (
                        False,
                        "Tunnel mode with password authentication is not supported on Windows.",
                    )

            # Handle PPK conversion if necessary (Linux/macOS)
            temp_key = None
            if (
                connection.key_path
                and connection.key_path.lower().endswith(".ppk")
                and sys.platform != "win32"
            ):
                puttygen = shutil.which("puttygen")
                if puttygen:
                    import tempfile

                    fd, temp_key_path = tempfile.mkstemp(prefix="sshive_tunnel_", suffix=".key")
                    os.close(fd)
                    temp_key = Path(temp_key_path)

                    try:
                        subprocess.run(
                            [
                                puttygen,
                                connection.key_path,
                                "-O",
                                "private-openssh",
                                "-o",
                                temp_key_path,
                            ],
                            check=True,
                            capture_output=True,
                        )

                        # Update tunnel_cmd to use converted key
                        for i, arg in enumerate(tunnel_cmd):
                            if (
                                arg == "-i"
                                and i + 1 < len(tunnel_cmd)
                                and tunnel_cmd[i + 1] == connection.key_path
                            ):
                                tunnel_cmd[i + 1] = temp_key_path
                                break
                    except Exception as e:
                        if temp_key.exists():
                            temp_key.unlink()
                        return False, f"Failed to convert PPK key: {e}"

            # Clean environment variables
            if getattr(sys, "frozen", False):
                for var in ["LD_LIBRARY_PATH", "PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH"]:
                    orig_var = f"{var}_ORIG"
                    if orig_var in env:
                        env[var] = env[orig_var]
                    else:
                        env.pop(var, None)

            # Launch tunnel in background - use Popen instead of subprocess.run
            # to allow it to stay running independently
            subprocess.Popen(
                tunnel_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )

            # Clean up temporary key after a delay if needed
            if temp_key:

                def cleanup():
                    import time

                    time.sleep(5)
                    try:
                        if temp_key.exists():
                            temp_key.unlink()
                    except Exception:
                        pass

                import threading

                threading.Thread(target=cleanup, daemon=True).start()

            return True, None

        except Exception as e:
            return False, f"Failed to launch tunnel: {e}"

    @staticmethod
    def test_connection(connection: SSHConnection) -> tuple[bool, str | None]:
        """Test if SSH connection is possible (doesn't actually connect).

        Args:
            connection: SSHConnection to test

        Returns:
            Tuple of (Success Status, Error Message)
        """
        # Check if ssh command exists
        if not shutil.which("ssh"):
            return False, "SSH command ('ssh') not found in PATH."

        # Check if key file exists (if specified)
        if connection.key_path:
            key_path = Path(connection.key_path).expanduser()
            if not key_path.exists():
                return False, f"SSH key file doesn't exist: {connection.key_path}"

        # Check for password providers
        if connection.password:
            if sys.platform != "win32":
                if not shutil.which("sshpass"):
                    return False, "Password authentication requires 'sshpass' to be installed."
            else:
                if not (shutil.which("plink.exe") or shutil.which("klink.exe")):
                    return (
                        False,
                        "Password authentication on Windows requires 'PuTTY' (plink.exe) or 'KiTTY' (klink.exe) in your PATH.",
                    )

        return True, None

    @staticmethod
    def test_full_connection(connection: SSHConnection) -> tuple[bool, str]:
        """Run comprehensive connection test: preflight + reachability + auth check.

        Args:
            connection: SSHConnection to test

        Returns:
            Tuple of (success, detailed status message)
        """
        # Stage 1: Preflight checks
        preflight_ok, preflight_err = SSHLauncher.test_connection(connection)
        if not preflight_ok:
            return False, f"Preflight check failed:\n{preflight_err}"

        # Stage 2: Network/port reachability
        reach_ok, reach_msg = SSHLauncher.test_connectivity(connection)
        if not reach_ok:
            return False, f"Network connectivity failed:\n{reach_msg}"

        # Stage 3: Credential validation (if credentials provided)
        if connection.password or connection.key_path:
            auth_ok, auth_err = SSHLauncher.check_credentials(connection)
            if not auth_ok:
                return False, f"Authentication check failed:\n{auth_err}"
            return (
                True,
                f"Full connection test passed.\n\n{reach_msg}\n\nAuthentication successful.",
            )

        return True, f"Full connection test passed.\n\n{reach_msg}"

    @staticmethod
    def test_connectivity(
        connection: SSHConnection, timeout_seconds: float = 1.5
    ) -> tuple[bool, str]:
        """Check host reachability via ping and SSH port connectivity.

        Args:
            connection: SSHConnection to test
            timeout_seconds: Timeout for ping and port checks

        Returns:
            Tuple of (success, status message)
        """
        host = connection.host.strip()
        if not host:
            return False, "Host is empty."

        ping_available = shutil.which("ping") is not None
        ping_ok: bool | None = None
        ping_message = "Ping skipped (ping command not found)."

        if ping_available:
            try:
                if sys.platform == "win32":
                    ping_cmd = ["ping", "-n", "1", "-w", str(int(timeout_seconds * 1000)), host]
                else:
                    ping_cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout_seconds))), host]

                ping_result = subprocess.run(
                    ping_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=max(1, timeout_seconds + 0.5),
                )
                ping_ok = ping_result.returncode == 0
                if ping_ok:
                    ping_message = "Ping successful."
                else:
                    ping_message = "Host did not respond to ping."
            except Exception:
                ping_ok = False
                ping_message = "Ping failed to execute."

        try:
            with socket.create_connection((host, connection.port), timeout=timeout_seconds):
                pass

            if ping_ok is False:
                return True, (
                    f"SSH port {connection.port} is reachable, but ping failed. "
                    "(This may be expected if ICMP is blocked.)"
                )

            if ping_ok is True:
                return True, f"Ping successful and SSH port {connection.port} is reachable."

            return True, f"SSH port {connection.port} is reachable. {ping_message}"
        except OSError as exc:
            if ping_ok is True:
                return (
                    False,
                    f"Ping successful but SSH port {connection.port} is not reachable: {exc}",
                )

            if ping_ok is False:
                return (
                    False,
                    f"Host did not respond to ping and SSH port {connection.port} is not reachable: {exc}",
                )

            return False, f"SSH port {connection.port} is not reachable: {exc}. {ping_message}"

    @staticmethod
    def collect_ssh_debug_log(connection: SSHConnection, timeout_seconds: float = 4.0) -> str:
        """Collect debug output from an ssh -vvv attempt.

        Args:
            connection: SSHConnection to test
            timeout_seconds: Max execution time for the debug attempt

        Returns:
            Full debug log text (command, return code, and output)
        """
        ssh_bin = shutil.which("ssh")
        if not ssh_bin:
            return "ssh command not found in PATH."

        cmd = [
            ssh_bin,
            "-vvv",
            "-p",
            str(connection.port),
            "-o",
            f"ConnectTimeout={max(1, int(timeout_seconds))}",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "BatchMode=yes",
        ]

        if connection.key_path:
            key_path = str(Path(connection.key_path).expanduser())
            cmd.extend(["-i", key_path])

        cmd.append(f"{connection.user}@{connection.host}")
        cmd.append("exit")

        header = [
            f"Connection: {connection.name} ({connection.user}@{connection.host}:{connection.port})",
            f"Command: {' '.join(cmd)}",
            "",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
            body = [f"Return code: {result.returncode}", "", result.stderr or result.stdout or ""]
            return "\n".join(header + body)
        except subprocess.TimeoutExpired as exc:
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            body = [
                f"Timed out after {timeout_seconds:.1f}s",
                "",
                stderr or stdout or "No output captured before timeout.",
            ]
            return "\n".join(header + body)
        except Exception as exc:
            body = ["Failed to collect debug log.", "", str(exc)]
            return "\n".join(header + body)

    @staticmethod
    def check_credentials(connection: SSHConnection) -> tuple[bool, str | None]:
        """Perform a background authentication check.

        Args:
            connection: SSHConnection to check

        Returns:
            Tuple of (Success Status, Error Message)
        """
        if not connection.password and not connection.key_path:
            return True, None

        temp_key = None
        try:
            base_ssh_args = [
                "-o",
                "ConnectTimeout=1",
                "-o",
                "StrictHostKeyChecking=accept-new",
            ]

            # Use BatchMode if no password to avoid hanging on passphrase prompts
            if not connection.password:
                base_ssh_args.extend(["-o", "BatchMode=yes"])
            else:
                base_ssh_args.extend(["-o", "BatchMode=no"])

            env = os.environ.copy()
            if sys.platform != "win32":
                key_path = connection.key_path
                if key_path and key_path.endswith(".ppk"):
                    # On Linux/macOS, convert PPK to OpenSSH for the check
                    puttygen = shutil.which("puttygen")
                    if puttygen:
                        import tempfile

                        handle, temp_key = tempfile.mkstemp(prefix="sshive_key_")
                        os.close(handle)
                        try:
                            subprocess.run(
                                [puttygen, key_path, "-O", "private-openssh", "-o", temp_key],
                                check=True,
                                capture_output=True,
                            )
                            key_path = temp_key
                        except subprocess.CalledProcessError:
                            os.unlink(temp_key)
                            return False, "Failed to convert PPK key for authentication check."

                cmd = ["ssh", "-p", str(connection.port)]
                cmd.extend(base_ssh_args)
                if key_path:
                    cmd.extend(["-i", os.path.expanduser(key_path)])

                if connection.password:
                    sshpass = shutil.which("sshpass")
                    if not sshpass:
                        return False, "sshpass not found (required for password check)"
                    cmd = [sshpass, "-e"] + cmd
                    # Force password auth by disabling pubkey if we have a password
                    cmd.extend(["-o", "PubkeyAuthentication=no"])
                    env["SSHPASS"] = connection.password

                cmd.append(f"{connection.user}@{connection.host}")
                cmd.append("true")
            else:
                # Windows - use plink or klink
                prog = shutil.which("plink.exe") or shutil.which("klink.exe")
                if not prog:
                    return False, "plink.exe or klink.exe not found"

                cmd = [prog, "-P", str(connection.port), "-batch"]
                if connection.key_path:
                    cmd.extend(["-i", os.path.expanduser(connection.key_path)])
                if connection.password:
                    cmd.extend(["-pw", connection.password])

                cmd.append(f"{connection.user}@{connection.host}")
                cmd.append("true")

            # Run the check
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=2)

            if result.returncode == 0:
                return True, None

            error_msg = (
                result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
            )

            if "Permission denied" in error_msg:
                return (
                    False,
                    "Authentication failed: Permission denied (Check password/key or server config).",
                )
            if "Timeout" in error_msg or result.returncode == 255:
                return False, f"Connection timed out or failed:\n{error_msg}"

            return False, f"Authentication check failed:\n{error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Authentication check timed out."
        except Exception as e:
            return False, f"Error during authentication check: {str(e)}"
        finally:
            if temp_key and os.path.exists(temp_key):
                try:
                    os.unlink(temp_key)
                except Exception:
                    pass
