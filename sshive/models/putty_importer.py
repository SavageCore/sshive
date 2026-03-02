"""PuTTY and KiTTY session importer.

Handles parsing of PuTTY and KiTTY configuration files and converting them
to SSHConnection objects.
"""

import re
from pathlib import Path

from sshive.models.connection import SSHConnection


class PuTTYImporter:
    """Import sessions from PuTTY and KiTTY configuration files."""

    @staticmethod
    def parse_putty_registry_export(content: str) -> list[dict]:
        """Parse PuTTY registry export format (.reg file).

        Args:
            content: Content of a Windows registry export file

        Returns:
            List of session dictionaries
        """
        sessions = {}
        current_session = None

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Match registry path for a session
            # [HKEY_CURRENT_USER\Software\SimonTatham\PuTTY\Sessions\SessionName]
            match = re.match(r"\[.*\\Sessions\\([^\]]+)\]", line)
            if match:
                current_session = match.group(1)
                sessions[current_session] = {}
                continue

            if current_session is None:
                continue

            # Parse registry values
            # "HostName"="example.com"
            value_match = re.match(r'"([^"]+)"="([^"]*)"', line)
            if value_match:
                key, value = value_match.groups()
                sessions[current_session][key] = value
                continue

            # Parse DWORD values
            # "PortNumber"=dword:00000016
            dword_match = re.match(r'"([^"]+)"=dword:([0-9a-f]+)', line, re.IGNORECASE)
            if dword_match:
                key, value = dword_match.groups()
                sessions[current_session][key] = int(value, 16)

        return list(sessions.values())

    @staticmethod
    def parse_putty_ini(content: str) -> list[dict]:
        """Parse PuTTY INI format configuration.

        Args:
            content: Content of a PuTTY INI file

        Returns:
            List of session dictionaries
        """
        sessions = {}
        current_section = None

        for line in content.split("\n"):
            line = line.rstrip()
            if not line or line.startswith(";"):
                continue

            # Match section header [SessionName]
            section_match = re.match(r"\[([^\]]+)\]", line)
            if section_match:
                current_section = section_match.group(1)
                sessions[current_section] = {}
                continue

            if current_section is None:
                continue

            # Parse key=value pairs
            kv_match = re.match(r"([^=]+)=(.*)$", line)
            if kv_match:
                key, value = kv_match.groups()
                key = key.strip()
                value = value.strip()

                # Try to convert to int if it looks like a number
                if value.isdigit():
                    value = int(value)

                sessions[current_section][key] = value

        return list(sessions.values())

    @staticmethod
    def parse_kitty_ini(content: str) -> list[dict]:
        """Parse KiTTY INI format configuration.

        KiTTY uses a similar format to PuTTY.

        Args:
            content: Content of a KiTTY INI file

        Returns:
            List of session dictionaries
        """
        return PuTTYImporter.parse_putty_ini(content)

    @staticmethod
    def _normalize_session(session: dict) -> dict | None:
        """Normalize a session dict to common format.

        Args:
            session: Raw session dictionary from PuTTY/KiTTY

        Returns:
            Normalized session dict or None if invalid
        """
        # Required fields
        host = session.get("HostName") or session.get("hostname")
        if not host:
            return None

        user = session.get("UserName") or session.get("username") or "root"
        port = session.get("PortNumber") or session.get("portnumber") or 22

        # Convert port to int if it's a string
        if isinstance(port, str):
            try:
                port = int(port)
            except ValueError:
                port = 22

        # Get key path if present
        key_path = session.get("PublicKeyFile") or session.get("publickeyfile")

        normalized = {
            "host": host,
            "user": user,
            "port": port,
        }

        if key_path:
            # Expand ~ for home directory
            if isinstance(key_path, str):
                path = Path(key_path).expanduser()
                # Check if file exists before including
                if path.exists():
                    normalized["key_path"] = str(path)

        return normalized

    @staticmethod
    def import_from_putty_registry(reg_content: str) -> list[SSHConnection]:
        """Convert PuTTY registry export to SSHConnection objects.

        Args:
            reg_content: Content of Windows registry export file

        Returns:
            List of SSHConnection objects
        """
        sessions = PuTTYImporter.parse_putty_registry_export(reg_content)
        connections = []

        for i, session in enumerate(sessions):
            normalized = PuTTYImporter._normalize_session(session)
            if normalized:
                name = session.get("name", f"PuTTY Session {i + 1}")
                group = "Imported from PuTTY"

                conn = SSHConnection(
                    name=name,
                    host=normalized["host"],
                    user=normalized["user"],
                    port=normalized["port"],
                    key_path=normalized.get("key_path"),
                    group=group,
                )
                connections.append(conn)

        return connections

    @staticmethod
    def import_from_putty_ini(ini_content: str) -> list[SSHConnection]:
        """Convert PuTTY INI format to SSHConnection objects.

        Args:
            ini_content: Content of PuTTY INI file

        Returns:
            List of SSHConnection objects
        """
        sessions = PuTTYImporter.parse_putty_ini(ini_content)
        connections = []

        for session in sessions:
            normalized = PuTTYImporter._normalize_session(session)
            if normalized:
                # Get session name from the original session dict or use a default
                name = next(
                    (k for k, v in {"Sessions": session}.items() if v == session),
                    "Unnamed Session",
                )

                # Try to find the name from common fields
                for key in ["name", "SessionName", "sessionname"]:
                    if key in session:
                        name = session[key]
                        break

                group = "Imported from PuTTY"

                conn = SSHConnection(
                    name=name,
                    host=normalized["host"],
                    user=normalized["user"],
                    port=normalized["port"],
                    key_path=normalized.get("key_path"),
                    group=group,
                )
                connections.append(conn)

        return connections

    @staticmethod
    def import_from_putty_sessions_dir(dir_path: Path) -> list[SSHConnection]:
        """Import sessions from Linux PuTTY sessions directory (~/.putty/sessions).

        Each session is stored as a separate file with key=value format.

        Args:
            dir_path: Path to PuTTY sessions directory

        Returns:
            List of SSHConnection objects
        """
        connections = []

        if not dir_path.is_dir():
            return connections

        # Read all session files from the directory
        for session_file in dir_path.glob("*"):
            if session_file.is_file() and not session_file.name.startswith("."):
                try:
                    with open(session_file, encoding="utf-8") as f:
                        content = f.read()

                    # Parse as key=value format (similar to INI but no sections)
                    session_data = {}
                    for line in content.split("\n"):
                        line = line.strip()
                        if not line or "=" not in line:
                            continue

                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Try to convert to int if it looks like a number
                        if value.isdigit():
                            value = int(value)

                        session_data[key] = value

                    normalized = PuTTYImporter._normalize_session(session_data)
                    if normalized:
                        # Use filename as session name
                        name = session_file.name
                        group = "Imported from PuTTY"

                        conn = SSHConnection(
                            name=name,
                            host=normalized["host"],
                            user=normalized["user"],
                            port=normalized["port"],
                            key_path=normalized.get("key_path"),
                            group=group,
                        )
                        connections.append(conn)

                except (OSError, UnicodeDecodeError, ValueError):
                    continue

        return connections

    @staticmethod
    def import_from_file(file_path: Path) -> list[SSHConnection]:
        """Auto-detect format and import sessions from file or directory.

        Supports:
        - PuTTY registry export (.reg)
        - PuTTY INI format (putty.ini, kitty.ini)
        - KiTTY portable config
        - Linux PuTTY sessions directory (~/.putty/sessions)

        Args:
            file_path: Path to configuration file or directory

        Returns:
            List of SSHConnection objects
        """
        # Check if it's a directory (Linux PuTTY sessions)
        if file_path.is_dir():
            return PuTTYImporter.import_from_putty_sessions_dir(file_path)

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        # Detect format
        # Windows registry export contains [HKEY_...] entries
        if "[HKEY_" in content and "\\Software\\SimonTatham\\PuTTY" in content:
            # Windows registry export format
            return PuTTYImporter.import_from_putty_registry(content)
        elif "[" in content and "]" in content:
            # INI format (PuTTY or KiTTY)
            return PuTTYImporter.import_from_putty_ini(content)

        # Linux PuTTY single session file format (key=value, no section header)
        session_data = {}
        for line in content.split("\n"):
            line = line.strip()
            if not line or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if value.isdigit():
                value = int(value)

            session_data[key] = value

        normalized = PuTTYImporter._normalize_session(session_data)
        if normalized:
            return [
                SSHConnection(
                    name=file_path.name,
                    host=normalized["host"],
                    user=normalized["user"],
                    port=normalized["port"],
                    key_path=normalized.get("key_path"),
                    group="Imported from PuTTY",
                )
            ]

        return []
