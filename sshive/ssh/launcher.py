"""SSH connection launcher with terminal detection."""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from sshive.models.connection import SSHConnection


class SSHLauncher:
    """Handles launching SSH connections in appropriate terminal emulators."""

    # Extra directories to search for binaries in frozen (PyInstaller) builds,
    # where the inherited PATH is typically minimal (e.g. /usr/bin:/bin).
    _EXTRA_PATHS = [
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]

    @staticmethod
    def _which(name: str) -> str | None:
        """Find an executable by name, augmenting PATH in frozen builds.

        When running inside a PyInstaller bundle the inherited PATH is often
        stripped down to the bare minimum, which causes ``shutil.which`` to
        miss executables installed in common locations such as
        ``/usr/local/bin`` (Homebrew on Intel) or ``/opt/homebrew/bin``
        (Homebrew on Apple Silicon).

        This helper first tries the normal ``shutil.which`` lookup and, if
        that fails *and* we are in a frozen build, retries with extra paths
        appended.
        """
        result = shutil.which(name)
        if result:
            return result

        if not getattr(sys, "frozen", False):
            return None

        current_path = os.environ.get("PATH", "")
        extra = os.pathsep.join(
            p for p in SSHLauncher._EXTRA_PATHS if p not in current_path.split(os.pathsep)
        )
        if extra:
            augmented = f"{current_path}{os.pathsep}{extra}" if current_path else extra
            return shutil.which(name, path=augmented)

        return None

    @staticmethod
    def get_terminals() -> dict:
        """
        Return a dictionary of all available terminal emulators for the current platform.
        The keys are terminal names, the values are command templates (list of args).
        """
        if sys.platform == "darwin":

            def _macos_app_exists(app_name):
                try:
                    subprocess.run(
                        ["open", "-Ra", app_name],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
                except Exception:
                    return False

            terminals = {}
            if _macos_app_exists("iTerm"):
                terminals["iTerm"] = ["open", "-a", "iTerm"]
            if _macos_app_exists("Terminal"):
                terminals["Terminal"] = ["open", "-a", "Terminal"]
            if SSHLauncher._which("alacritty"):
                terminals["alacritty"] = ["alacritty", "-e"]
            elif _macos_app_exists("Alacritty"):
                alacritty_bin = "/Applications/Alacritty.app/Contents/MacOS/alacritty"
                if Path(alacritty_bin).exists():
                    terminals["alacritty"] = [alacritty_bin, "-e"]
            return terminals
        elif sys.platform == "win32":
            return {
                "wt": ["wt.exe"],
                "cmd": ["cmd", "/c", "start"],
            }
        else:
            return {
                "konsole": ["konsole", "-e"],
                "gnome-terminal": ["gnome-terminal", "--"],
                "xfce4-terminal": ["xfce4-terminal", "-e"],
                "alacritty": ["alacritty", "-e"],
                "kitty": ["kitty"],
                "tilix": ["tilix", "-e"],
                "terminator": ["terminator", "-e"],
                "xterm": ["xterm", "-e"],
            }

    @staticmethod
    def _convert_ppk_key(key_path: str, prefix: str = "sshive_key_") -> str | None:
        """
        Convert a PuTTY PPK key file to OpenSSH format on Linux/macOS.

        Args:
            key_path: Path to the PPK key file.
            prefix: Prefix for the temporary output file name.

        Returns:
            Path to the converted key file as a string, or None if conversion failed or not needed.
            The caller is responsible for deleting the returned file after use.
        """
        # Only convert if the key is a PPK file and not on Windows
        if not key_path.lower().endswith(".ppk") or sys.platform == "win32":
            return None

        puttygen = SSHLauncher._which("puttygen")
        if not puttygen:
            return None

        # Create a temporary file for the converted key, then delete it so puttygen can write to it
        fd, temp_key_path = tempfile.mkstemp(prefix=prefix, suffix=".key")
        os.close(fd)
        os.unlink(temp_key_path)

        try:
            expanded_key_path = os.path.expanduser(key_path)
            # Run puttygen to convert the key
            result = subprocess.run(
                [puttygen, expanded_key_path, "-O", "private-openssh", "-o", temp_key_path],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            # If conversion failed or file not created, clean up and return None
            if result.returncode != 0 or not os.path.exists(temp_key_path):
                if os.path.exists(temp_key_path):
                    os.unlink(temp_key_path)
                return None

            # If file is empty, treat as failure
            if os.path.getsize(temp_key_path) == 0:
                os.unlink(temp_key_path)
                return None

            return temp_key_path
        except Exception as e:
            print(f"PPK conversion failed: {e}")
            if os.path.exists(temp_key_path):
                os.unlink(temp_key_path)
            return None

    @staticmethod
    def detect_terminal(preferred_terminal: str = "auto") -> tuple[str, list[str]]:
        """
        Detect the first available terminal emulator on the current platform, or return the user's preferred terminal if available.

        Args:
            preferred_terminal: The terminal name to prefer (e.g., "iTerm", "alacritty", "Terminal", etc.), or "auto" to auto-detect.

        Returns:
            Tuple of (terminal_name, command_template). The command_template is a list of command arguments to launch the terminal,
            with the SSH command appended as needed. If no preferred or detected terminal is found, defaults to xterm.
        """
        terminals = SSHLauncher.get_terminals()

        # If user has a preferred terminal, check if it's available
        if preferred_terminal and preferred_terminal != "auto":
            if preferred_terminal in terminals:
                cmd = terminals[preferred_terminal]
                # On macOS, "open" is always available; on other platforms, check if binary is in PATH
                if cmd[0] == "open":
                    return preferred_terminal, cmd
                elif SSHLauncher._which(cmd[0]):
                    return preferred_terminal, cmd

        # Otherwise, return the first available terminal in the list
        for term_name, cmd_template in terminals.items():
            if cmd_template[0] == "open" or SSHLauncher._which(cmd_template[0]):
                return term_name, cmd_template

        # Fallback to xterm if nothing else is found
        return "xterm", ["xterm", "-e"]

    @staticmethod
    def launch(connection: SSHConnection, preferred_terminal: str = "auto") -> bool:
        """
        Launch an SSH connection in the user's chosen or auto-detected terminal emulator.

        Args:
            connection: The SSHConnection object containing connection details.
            preferred_terminal: The terminal emulator to use (e.g., "iTerm", "Terminal", "alacritty", etc.), or "auto" to auto-detect.

        Returns:
            True if the terminal was successfully launched, False otherwise.

        Notes:
            - Handles PPK key conversion if needed.
            - Handles password authentication using sshpass (Linux/macOS) or plink (Windows).
            - Cleans up temporary key files after use.
            - Uses AppleScript (osascript) for Terminal/iTerm on macOS.
        """
        try:
            terminal_name, terminal_cmd = SSHLauncher.detect_terminal(preferred_terminal)

            ssh_cmd = connection.get_ssh_command()

            temp_key = None
            if connection.key_path:
                converted = SSHLauncher._convert_ppk_key(connection.key_path, prefix="sshive_key_")
                if converted:
                    temp_key = Path(converted)
                    for i, arg in enumerate(ssh_cmd):
                        if (
                            arg == "-i"
                            and i + 1 < len(ssh_cmd)
                            and ssh_cmd[i + 1] == connection.key_path
                        ):
                            ssh_cmd[i + 1] = converted
                            break

            env = os.environ.copy()

            if connection.password:
                if sys.platform != "win32":
                    if SSHLauncher._which("sshpass"):
                        env["SSHPASS"] = connection.password
                        ssh_cmd = ["sshpass", "-e"] + ssh_cmd
                else:
                    plink = SSHLauncher._which("plink.exe") or SSHLauncher._which("klink.exe")
                    if plink:
                        ssh_cmd = [plink, "-pw", connection.password]
                        if connection.key_path:
                            ssh_cmd.extend(["-i", connection.key_path])
                        if connection.port != 22:
                            ssh_cmd.extend(["-P", str(connection.port)])
                        ssh_cmd.append(f"{connection.user}@{connection.host}")

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
                cmd_str = " ".join([f'"{arg}"' if " " in arg else arg for arg in ssh_cmd])
                wrapped_cmd = f"{cmd_str} || {{ echo -v; echo '----------------------------------------'; echo 'Connection failed or closed.'; read -p 'Press Enter to close...'; }}"
                full_cmd = terminal_cmd + ["bash", "-c", wrapped_cmd]

            elif terminal_name in ["kitty"]:
                full_cmd = terminal_cmd + ssh_cmd

            elif terminal_name == "wt":
                full_cmd = terminal_cmd + ssh_cmd

            elif terminal_name == "iTerm":
                ssh_script = " ".join([f'"{arg}"' if " " in arg else arg for arg in ssh_cmd])
                osa_script = (
                    'tell application "iTerm"\n'
                    "    try\n"
                    f'        set newWindow to (create window with default profile command "{ssh_script}")\n'
                    "    on error\n"
                    f'        tell current window to create tab with default profile command "{ssh_script}"\n'
                    "    end try\n"
                    "    activate\n"
                    "end tell"
                )
                full_cmd = ["osascript", "-e", osa_script]

            elif terminal_name == "Terminal":
                ssh_script = " ".join([f'"{arg}"' if " " in arg else arg for arg in ssh_cmd])
                osa_script = (
                    'tell application "Terminal"\n'
                    f'    do script "{ssh_script}"\n'
                    "    activate\n"
                    "end tell"
                )
                full_cmd = ["osascript", "-e", osa_script]
            else:
                full_cmd = terminal_cmd + ssh_cmd

            if getattr(sys, "frozen", False):
                for var in ["LD_LIBRARY_PATH", "PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH"]:
                    orig_var = f"{var}_ORIG"
                    if orig_var in env:
                        env[var] = env[orig_var]
                    else:
                        env.pop(var, None)

            subprocess.Popen(
                full_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )

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

            return True

        except Exception as e:
            print(f"Failed to launch SSH connection: {e}")
            return False

    @staticmethod
    def launch_tunnel(connection: SSHConnection) -> tuple[bool, str | None]:
        """
        Launch an SSH tunnel in the background, forwarding all configured ports.

        Args:
            connection: The SSHConnection object with tunnel configuration (must have port_forwards).

        Returns:
            Tuple (success, error_message). success is True if the tunnel was launched, False otherwise. error_message is None on success, or a string describing the error.

        Notes:
            - Handles password authentication using sshpass (Linux/macOS).
            - Handles PPK key conversion if needed.
            - Cleans up temporary key files after use.
            - Not supported on Windows with password authentication.
        """
        if not connection.port_forwards:
            return False, "No port forwards configured for tunnel."

        try:
            tunnel_cmd = connection.get_tunnel_command()

            env = os.environ.copy()
            if connection.password:
                if sys.platform != "win32":
                    if SSHLauncher._which("sshpass"):
                        env["SSHPASS"] = connection.password
                        tunnel_cmd = ["sshpass", "-e"] + tunnel_cmd
                    else:
                        return False, "Password authentication requires 'sshpass' to be installed."
                else:
                    return (
                        False,
                        "Tunnel mode with password authentication is not supported on Windows.",
                    )

            temp_key = None
            if connection.key_path:
                converted = SSHLauncher._convert_ppk_key(
                    connection.key_path, prefix="sshive_tunnel_"
                )
                if converted:
                    temp_key = Path(converted)
                    for i, arg in enumerate(tunnel_cmd):
                        if (
                            arg == "-i"
                            and i + 1 < len(tunnel_cmd)
                            and tunnel_cmd[i + 1] == connection.key_path
                        ):
                            tunnel_cmd[i + 1] = converted
                            break
                elif connection.key_path.lower().endswith(".ppk") and sys.platform != "win32":
                    puttygen = SSHLauncher._which("puttygen")
                    if not puttygen:
                        return (
                            False,
                            "PPK key format requires 'puttygen' to be installed for conversion on Linux/macOS.",
                        )
                    return False, "Failed to convert PPK key. Check file permissions and format."

            if getattr(sys, "frozen", False):
                for var in ["LD_LIBRARY_PATH", "PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH"]:
                    orig_var = f"{var}_ORIG"
                    if orig_var in env:
                        env[var] = env[orig_var]
                    else:
                        env.pop(var, None)

            subprocess.Popen(
                tunnel_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )

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
        """
        Test if an SSH connection is possible (preflight check, does not actually connect).

        Args:
            connection: The SSHConnection object to test.

        Returns:
            Tuple (success, error_message). success is True if the connection is possible, False otherwise. error_message is None on success, or a string describing the error.
        """
        if not SSHLauncher._which("ssh"):
            return False, "SSH command ('ssh') not found in PATH."

        if connection.key_path:
            key_path = Path(connection.key_path).expanduser()
            if not key_path.exists():
                return False, f"SSH key file doesn't exist: {connection.key_path}"

            if (
                connection.key_path.lower().endswith(".ppk")
                and sys.platform != "win32"
                and not SSHLauncher._which("puttygen")
            ):
                return (
                    False,
                    "PPK key format requires 'puttygen' to be installed for conversion on Linux/macOS.",
                )

        if connection.password:
            if sys.platform != "win32":
                if not SSHLauncher._which("sshpass"):
                    return False, "Password authentication requires 'sshpass' to be installed."
            else:
                if not (SSHLauncher._which("plink.exe") or SSHLauncher._which("klink.exe")):
                    return (
                        False,
                        "Password authentication on Windows requires 'PuTTY' (plink.exe) or 'KiTTY' (klink.exe) in your PATH.",
                    )

        return True, None

    @staticmethod
    def test_full_connection(connection: SSHConnection) -> tuple[bool, str]:
        """
        Run a comprehensive connection test: preflight, network reachability, and authentication check.

        Args:
            connection: The SSHConnection object to test.

        Returns:
            Tuple (success, status_message). success is True if all checks pass, False otherwise. status_message contains details.
        """
        preflight_ok, preflight_err = SSHLauncher.test_connection(connection)
        if not preflight_ok:
            return False, f"Preflight check failed:\n{preflight_err}"

        reach_ok, reach_msg = SSHLauncher.test_connectivity(connection)
        if not reach_ok:
            return False, f"Network connectivity failed:\n{reach_msg}"

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
        """
        Check host reachability via ping and SSH port connectivity.

        Args:
            connection: The SSHConnection object to test.
            timeout_seconds: Timeout for ping and port checks.

        Returns:
            Tuple (success, status_message). success is True if the host is reachable and the port is open, False otherwise. status_message contains details.
        """
        host = connection.host.strip()
        if not host:
            return False, "Host is empty."

        ping_available = SSHLauncher._which("ping") is not None
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
        """
        Collect debug output from an ssh -vvv attempt for troubleshooting.

        Args:
            connection: The SSHConnection object to test.
            timeout_seconds: Maximum execution time for the debug attempt.

        Returns:
            Full debug log text (command, return code, and output).
        """
        ssh_bin = SSHLauncher._which("ssh")
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

        temp_key = None
        if connection.key_path:
            key_path = str(Path(connection.key_path).expanduser())

            converted = SSHLauncher._convert_ppk_key(connection.key_path, prefix="sshive_debug_")
            if converted:
                temp_key = Path(converted)
                key_path = converted

            cmd.extend(["-i", key_path])

        cmd.append(f"{connection.user}@{connection.host}")
        cmd.append("exit")

        header = [
            f"Connection: {connection.name} ({connection.user}@{connection.host}:{connection.port})",
            f"Command: {' '.join(cmd)}",
            "",
        ]

        try:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout_seconds
                )
                body = [
                    f"Return code: {result.returncode}",
                    "",
                    result.stderr or result.stdout or "",
                ]
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
        finally:
            if temp_key and temp_key.exists():
                try:
                    temp_key.unlink()
                except Exception:
                    pass

    @staticmethod
    def check_credentials(connection: SSHConnection) -> tuple[bool, str | None]:
        """
        Perform a background authentication check (password or key) for the given connection.

        Args:
            connection: The SSHConnection object to check.

        Returns:
            Tuple (success, error_message). success is True if authentication is successful, False otherwise. error_message is None on success, or a string describing the error.
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

            if not connection.password:
                base_ssh_args.extend(["-o", "BatchMode=yes"])
            else:
                base_ssh_args.extend(["-o", "BatchMode=no"])
            env = os.environ.copy()
            if sys.platform != "win32":
                key_path = connection.key_path
                if key_path:
                    converted = SSHLauncher._convert_ppk_key(key_path, prefix="sshive_key_")
                    if converted:
                        temp_key = converted
                        key_path = converted
                    elif key_path.lower().endswith(".ppk"):
                        puttygen = SSHLauncher._which("puttygen")
                        if not puttygen:
                            return (
                                False,
                                "PPK key format requires 'puttygen' to be installed for conversion on Linux/macOS.",
                            )
                        return (
                            False,
                            "Failed to convert PPK key. Check file permissions and format.",
                        )

                cmd = ["ssh", "-p", str(connection.port)]
                cmd.extend(base_ssh_args)
                if key_path:
                    cmd.extend(["-i", os.path.expanduser(key_path)])

                if connection.password:
                    sshpass = SSHLauncher._which("sshpass")
                    if not sshpass:
                        return False, "sshpass not found (required for password check)"
                    cmd = [sshpass, "-e"] + cmd
                    cmd.extend(["-o", "PubkeyAuthentication=no"])
                    env["SSHPASS"] = connection.password

                cmd.append(f"{connection.user}@{connection.host}")
                cmd.append("true")
            else:
                prog = SSHLauncher._which("plink.exe") or SSHLauncher._which("klink.exe")
                if not prog:
                    return False, "plink.exe or klink.exe not found"

                cmd = [prog, "-P", str(connection.port), "-batch"]
                if connection.key_path:
                    cmd.extend(["-i", os.path.expanduser(connection.key_path)])
                if connection.password:
                    cmd.extend(["-pw", connection.password])

                cmd.append(f"{connection.user}@{connection.host}")
                cmd.append("true")

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
