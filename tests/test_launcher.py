"""Tests for SSH launcher."""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from sshive.models.connection import SSHConnection
from sshive.ssh.launcher import SSHLauncher


class TestSSHLauncher:
    """Test cases for SSHLauncher class."""

    def test_detect_terminal_finds_available(self):
        """Test terminal detection finds available terminal."""
        terminal_name, cmd_template = SSHLauncher.detect_terminal()

        assert terminal_name is not None
        assert isinstance(cmd_template, list)
        assert len(cmd_template) > 0

    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_detect_terminal_konsole(self, mock_which):
        """Test detection of konsole terminal."""

        def which_side_effect(cmd):
            return "/usr/bin/konsole" if cmd == "konsole" else None

        mock_which.side_effect = which_side_effect

        with patch("sys.platform", "linux"):
            terminal_name, cmd_template = SSHLauncher.detect_terminal()

        assert terminal_name == "konsole"
        assert cmd_template[0] == "konsole"

    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_detect_terminal_fallback(self, mock_which):
        """Test fallback to xterm when no terminal found."""
        mock_which.return_value = None

        with patch("sys.platform", "linux"):
            terminal_name, cmd_template = SSHLauncher.detect_terminal()

        # Should fallback to xterm
        assert terminal_name == "xterm"

    @patch("subprocess.Popen")
    @patch("sshive.ssh.launcher.SSHLauncher.detect_terminal")
    def test_launch_basic_connection(self, mock_detect, mock_popen):
        """Test launching a basic SSH connection."""
        mock_detect.return_value = ("konsole", ["konsole", "-e"])
        mock_popen.return_value = MagicMock()

        conn = SSHConnection(name="Test", host="example.com", user="testuser")

        result = SSHLauncher.launch(conn)

        assert result is True
        mock_popen.assert_called_once()

        # Check command includes ssh
        call_args = mock_popen.call_args[0][0]
        assert any("ssh" in arg for arg in call_args)

    @patch("subprocess.Popen")
    @patch("sshive.ssh.launcher.SSHLauncher.detect_terminal")
    def test_launch_with_key(self, mock_detect, mock_popen):
        """Test launching connection with SSH key."""
        mock_detect.return_value = ("konsole", ["konsole", "-e"])
        mock_popen.return_value = MagicMock()

        conn = SSHConnection(
            name="Test", host="example.com", user="testuser", key_path="~/.ssh/id_rsa"
        )

        result = SSHLauncher.launch(conn)

        assert result is True

        # Check command includes -i flag
        call_args = mock_popen.call_args[0][0]
        assert any("-i" in arg for arg in call_args)

    @patch("subprocess.Popen")
    @patch("sshive.ssh.launcher.SSHLauncher.detect_terminal")
    def test_launch_with_custom_port(self, mock_detect, mock_popen):
        """Test launching connection with custom port."""
        mock_detect.return_value = ("konsole", ["konsole", "-e"])
        mock_popen.return_value = MagicMock()

        conn = SSHConnection(name="Test", host="example.com", user="testuser", port=2222)

        result = SSHLauncher.launch(conn)

        assert result is True

        # Check command includes -p flag
        call_args = mock_popen.call_args[0][0]
        assert any("-p" in arg for arg in call_args)
        assert any("2222" in arg for arg in call_args)

    @patch("subprocess.Popen")
    @patch("sshive.ssh.launcher.SSHLauncher.detect_terminal")
    def test_launch_failure(self, mock_detect, mock_popen):
        """Test handling of launch failure."""
        mock_detect.return_value = ("konsole", ["konsole", "-e"])
        mock_popen.side_effect = Exception("Launch failed")

        conn = SSHConnection(name="Test", host="example.com", user="testuser")

        result = SSHLauncher.launch(conn)

        assert result is False

    def test_test_connection_ssh_exists(self):
        """Test connection test when ssh command exists."""
        conn = SSHConnection(name="Test", host="example.com", user="testuser")

        # Only passes if ssh is actually installed
        result, msg = SSHLauncher.test_connection(conn)

        if shutil.which("ssh"):
            assert result is True
            assert msg is None
        else:
            assert result is False
            assert msg is not None

    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_test_connection_no_ssh(self, mock_which):
        """Test connection test when ssh command doesn't exist."""
        mock_which.return_value = None

        conn = SSHConnection(name="Test", host="example.com", user="testuser")
        result, msg = SSHLauncher.test_connection(conn)

        assert result is False
        assert "not found" in msg.lower()

    def test_test_connection_invalid_key(self):
        """Test connection test with non-existent key file."""
        conn = SSHConnection(
            name="Test", host="example.com", user="testuser", key_path="/nonexistent/key/file"
        )
        result, msg = SSHLauncher.test_connection(conn)

        assert result is False
        assert "doesn't exist" in msg.lower()

    def test_test_connection_valid_key(self):
        """Test connection test with valid key file."""
        # Create temporary key file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            key_path = f.name

        try:
            conn = SSHConnection(
                name="Test", host="example.com", user="testuser", key_path=key_path
            )

            # Only passes if ssh is installed
            result, msg = SSHLauncher.test_connection(conn)

            if shutil.which("ssh"):
                assert result is True
                assert msg is None
            else:
                assert result is False
                assert msg is not None

        finally:
            Path(key_path).unlink()

    @patch("sshive.ssh.launcher.socket.create_connection")
    @patch("subprocess.run")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_test_connectivity_success_with_ping(
        self, mock_which, mock_run, mock_create_connection
    ):
        """Connectivity check succeeds when ping and port connectivity both work."""
        mock_which.return_value = "/usr/bin/ping"
        mock_run.return_value = MagicMock(returncode=0)

        mock_socket = MagicMock()
        mock_socket.__enter__.return_value = mock_socket
        mock_socket.__exit__.return_value = False
        mock_create_connection.return_value = mock_socket

        conn = SSHConnection(name="Test", host="example.com", user="testuser", port=22)
        success, message = SSHLauncher.test_connectivity(conn)

        assert success is True
        assert "reachable" in message.lower()

    @patch("sshive.ssh.launcher.socket.create_connection")
    @patch("subprocess.run")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_test_connectivity_port_open_ping_blocked(
        self, mock_which, mock_run, mock_create_connection
    ):
        """Connectivity check still succeeds when ping fails but SSH port is reachable."""
        mock_which.return_value = "/usr/bin/ping"
        mock_run.return_value = MagicMock(returncode=1)

        mock_socket = MagicMock()
        mock_socket.__enter__.return_value = mock_socket
        mock_socket.__exit__.return_value = False
        mock_create_connection.return_value = mock_socket

        conn = SSHConnection(name="Test", host="example.com", user="testuser", port=22)
        success, message = SSHLauncher.test_connectivity(conn)

        assert success is True
        assert "ping failed" in message.lower() or "icmp" in message.lower()

    @patch("sshive.ssh.launcher.socket.create_connection")
    @patch("subprocess.run")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_test_connectivity_port_unreachable(self, mock_which, mock_run, mock_create_connection):
        """Connectivity check fails when SSH port is unreachable."""
        mock_which.return_value = "/usr/bin/ping"
        mock_run.return_value = MagicMock(returncode=0)
        mock_create_connection.side_effect = OSError("Connection refused")

        conn = SSHConnection(name="Test", host="example.com", user="testuser", port=22)
        success, message = SSHLauncher.test_connectivity(conn)

        assert success is False
        assert "not reachable" in message.lower()

    @patch("subprocess.Popen")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    @patch("sshive.ssh.launcher.SSHLauncher.detect_terminal")
    def test_launch_with_password_linux(self, mock_detect, mock_which, mock_popen):
        """Test launching connection with password on Linux."""
        mock_detect.return_value = ("konsole", ["konsole", "-e"])
        mock_popen.return_value = MagicMock()

        # Mock sshpass exists
        mock_which.side_effect = lambda cmd: (
            "/usr/bin/sshpass" if cmd == "sshpass" else "/usr/bin/ssh"
        )

        with patch("sys.platform", "linux"):
            conn = SSHConnection(
                name="Test", host="example.com", user="testuser", password="secretpassword"
            )
            result = SSHLauncher.launch(conn)

            assert result is True
            call_args = mock_popen.call_args[0][0]
            assert any("sshpass" in arg for arg in call_args)
            assert "-e" in call_args

            # Check environment variable
            env = mock_popen.call_args[1].get("env", {})
            assert env.get("SSHPASS") == "secretpassword"

    @patch("subprocess.Popen")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    @patch("sshive.ssh.launcher.SSHLauncher.detect_terminal")
    def test_launch_with_password_windows(self, mock_detect, mock_which, mock_popen):
        """Test launching connection with password on Windows using plink."""
        mock_detect.return_value = ("wt", ["wt.exe"])
        mock_popen.return_value = MagicMock()

        # Mock plink exists
        mock_which.side_effect = lambda cmd: "C:\\bin\\plink.exe" if cmd == "plink.exe" else None

        with patch("sys.platform", "win32"):
            conn = SSHConnection(
                name="Test", host="example.com", user="testuser", password="secretpassword"
            )
            result = SSHLauncher.launch(conn)

            assert result is True
            call_args = mock_popen.call_args[0][0]
            # Check if any part of the command contains plink.exe
            assert any("plink.exe" in arg for arg in call_args)
            assert "-pw" in call_args
            assert "secretpassword" in call_args

    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_test_connection_password_provider(self, mock_which):
        """Test connection test checks for password providers."""
        conn = SSHConnection(name="Test", host="example.com", user="testuser", password="pass")

        # Linux - sshpass missing
        with patch("sys.platform", "linux"):
            mock_which.side_effect = lambda cmd: "/usr/bin/ssh" if cmd == "ssh" else None
            result, msg = SSHLauncher.test_connection(conn)
            assert result is False
            assert "sshpass" in msg.lower()

            # sshpass exists
            mock_which.side_effect = lambda cmd: (
                "/usr/bin/sshpass" if cmd == "sshpass" else "/usr/bin/ssh"
            )
            result, msg = SSHLauncher.test_connection(conn)
            assert result is True
            assert msg is None

        # Windows - plink missing
        with patch("sys.platform", "win32"):
            mock_which.side_effect = lambda cmd: "ssh" if cmd == "ssh" else None
            result, msg = SSHLauncher.test_connection(conn)
            assert result is False
            assert "putty" in msg.lower() or "kitty" in msg.lower()

            # plink exists
            mock_which.side_effect = lambda cmd: "plink.exe" if "plink" in cmd else "ssh"
            result, msg = SSHLauncher.test_connection(conn)
            assert result is True
            assert msg is None

    @patch("subprocess.run")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_check_credentials_success(self, mock_which, mock_run):
        """Test authentication check success."""
        mock_which.side_effect = lambda cmd: (
            "/usr/bin/sshpass" if cmd == "sshpass" else "/usr/bin/ssh"
        )
        mock_run.return_value = MagicMock(returncode=0)

        with patch("sys.platform", "linux"):
            conn = SSHConnection(
                name="Test", host="example.com", user="testuser", password="secretpassword"
            )
            result, msg = SSHLauncher.check_credentials(conn)

            assert result is True
            assert msg is None

            # Verify subprocess.run was called with correct args
            args = mock_run.call_args[0][0]
            assert any("sshpass" in arg for arg in args)
            assert any("StrictHostKeyChecking=accept-new" in arg for arg in args)
            assert any("PubkeyAuthentication=no" in arg for arg in args)

    @patch("subprocess.run")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_check_credentials_failure(self, mock_which, mock_run):
        """Test authentication check failure (permission denied)."""
        mock_which.side_effect = lambda cmd: (
            "/usr/bin/sshpass" if cmd == "sshpass" else "/usr/bin/ssh"
        )
        mock_run.return_value = MagicMock(returncode=5, stderr="Permission denied", stdout="")

        with patch("sys.platform", "linux"):
            conn = SSHConnection(
                name="Test", host="example.com", user="testuser", password="wrongpassword"
            )
            result, msg = SSHLauncher.check_credentials(conn)

            assert result is False
            assert "Permission denied" in msg

    @patch("subprocess.Popen")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    @patch("sshive.ssh.launcher.SSHLauncher.detect_terminal")
    def test_launch_terminal_wrapping_linux(self, mock_detect, mock_which, mock_popen):
        """Test that terminal command is wrapped with bash and pause on Linux."""
        mock_detect.return_value = ("konsole", ["konsole", "-e"])
        mock_popen.return_value = MagicMock()
        mock_which.side_effect = lambda cmd: "/usr/bin/ssh"

        with patch("sys.platform", "linux"):
            conn = SSHConnection(name="Test", host="example.com", user="testuser")
            SSHLauncher.launch(conn)

            call_args = mock_popen.call_args[0][0]
            assert "bash" in call_args
            assert "-c" in call_args
            # Verify command string contains ssh command and pause logic
            cmd_str = call_args[-1]
            assert "ssh" in cmd_str
            assert "read -p" in cmd_str
            assert "Connection failed" in cmd_str

    @patch("subprocess.run")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_check_credentials_key_success(self, mock_which, mock_run):
        """Test credential check success with SSH key."""
        mock_which.return_value = "/usr/bin/ssh"
        mock_run.return_value = MagicMock(returncode=0)

        conn = SSHConnection(
            name="Test", host="example.com", user="testuser", key_path="~/.ssh/test_key"
        )

        success, error = SSHLauncher.check_credentials(conn)

        assert success is True
        assert error is None

        # Verify subprocess.run was called with correct args
        args = mock_run.call_args[0][0]
        assert "ssh" in args
        assert any("-i" in arg for arg in args)
        assert any("test_key" in arg for arg in args)
        assert any("BatchMode=yes" in arg for arg in args)

    @patch("subprocess.run")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_check_credentials_key_failure(self, mock_which, mock_run):
        """Test credential check failure with SSH key."""
        mock_which.return_value = "/usr/bin/ssh"
        mock_run.return_value = MagicMock(returncode=255, stderr="Permission denied (publickey).")

        conn = SSHConnection(
            name="Test", host="example.com", user="testuser", key_path="~/.ssh/test_key"
        )

        success, error = SSHLauncher.check_credentials(conn)

        assert success is False
        assert "Permission denied" in error

    @patch("subprocess.run")
    @patch("sshive.ssh.launcher.SSHLauncher._which")
    def test_collect_ssh_debug_log(self, mock_which, mock_run):
        """Debug log collection includes return code and output."""
        mock_which.return_value = "/usr/bin/ssh"
        mock_run.return_value = MagicMock(returncode=255, stderr="debug line", stdout="")

        conn = SSHConnection(name="Test", host="example.com", user="testuser", port=22)
        output = SSHLauncher.collect_ssh_debug_log(conn)

        assert "Return code" in output
        assert "debug line" in output

    @patch("sshive.ssh.launcher.SSHLauncher.check_credentials")
    @patch("sshive.ssh.launcher.SSHLauncher.test_connectivity")
    @patch("sshive.ssh.launcher.SSHLauncher.test_connection")
    def test_test_full_connection_success(self, mock_test_conn, mock_test_reach, mock_check_auth):
        """Full test chains preflight, reachability, and auth checks."""
        mock_test_conn.return_value = (True, None)
        mock_test_reach.return_value = (True, "SSH port is reachable")
        mock_check_auth.return_value = (True, None)

        conn = SSHConnection(
            name="Test", host="example.com", user="testuser", key_path="~/.ssh/id_rsa"
        )
        success, message = SSHLauncher.test_full_connection(conn)

        assert success is True
        assert "Full connection test passed" in message
        mock_test_conn.assert_called_once_with(conn)
        mock_test_reach.assert_called_once_with(conn)
        mock_check_auth.assert_called_once_with(conn)

    @patch("sshive.ssh.launcher.SSHLauncher.test_connection")
    def test_test_full_connection_preflight_failure(self, mock_test_conn):
        """Full test stops at preflight if check fails."""
        mock_test_conn.return_value = (False, "SSH not found")

        conn = SSHConnection(name="Test", host="example.com", user="testuser")
        success, message = SSHLauncher.test_full_connection(conn)

        assert success is False
        assert "Preflight check failed" in message
        assert "SSH not found" in message

    @patch("sshive.ssh.launcher.SSHLauncher.test_connectivity")
    @patch("sshive.ssh.launcher.SSHLauncher.test_connection")
    def test_test_full_connection_reachability_failure(self, mock_test_conn, mock_test_reach):
        """Full test stops at reachability if check fails."""
        mock_test_conn.return_value = (True, None)
        mock_test_reach.return_value = (False, "Target not reachable")

        conn = SSHConnection(name="Test", host="example.com", user="testuser")
        success, message = SSHLauncher.test_full_connection(conn)

        assert success is False
        assert "Network connectivity failed" in message
        assert "Target not reachable" in message

    @patch("sshive.ssh.launcher.SSHLauncher.check_credentials")
    @patch("sshive.ssh.launcher.SSHLauncher.test_connectivity")
    @patch("sshive.ssh.launcher.SSHLauncher.test_connection")
    def test_test_full_connection_auth_failure(
        self, mock_test_conn, mock_test_reach, mock_check_auth
    ):
        """Full test stops at auth if credentials fail."""
        mock_test_conn.return_value = (True, None)
        mock_test_reach.return_value = (True, "SSH port is reachable")
        mock_check_auth.return_value = (
            False,
            "Permission denied (publickey)",
        )

        conn = SSHConnection(
            name="Test", host="example.com", user="testuser", key_path="~/.ssh/id_rsa"
        )
        success, message = SSHLauncher.test_full_connection(conn)

        assert success is False
        assert "Authentication check failed" in message
        assert "Permission denied" in message


class TestWhichHelper:
    """Test cases for SSHLauncher._which PATH augmentation."""

    def test_which_finds_existing_binary(self):
        """_which finds a binary that exists on the normal PATH."""
        # 'ls' should exist on all platforms
        result = SSHLauncher._which("ls")
        assert result is not None
        assert "ls" in result

    def test_which_returns_none_for_missing_binary(self):
        """_which returns None for a nonexistent binary."""
        result = SSHLauncher._which("definitely_not_a_real_binary_12345")
        assert result is None

    @patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=False)
    def test_which_augments_path_in_frozen_build(self):
        """In a frozen build with a restricted PATH, _which searches extra dirs."""
        with patch("shutil.which") as mock_which:
            # First call (normal PATH) returns None, second call (augmented) finds it
            mock_which.side_effect = [None, "/usr/local/bin/puttygen"]

            with patch.object(sys, "frozen", True, create=True):
                result = SSHLauncher._which("puttygen")

            assert result == "/usr/local/bin/puttygen"
            assert mock_which.call_count == 2
            # Second call should include augmented path
            _, kwargs = mock_which.call_args
            assert "/usr/local/bin" in kwargs["path"]
            assert "/opt/homebrew/bin" in kwargs["path"]

    def test_which_does_not_augment_when_not_frozen(self):
        """When not in a frozen build, _which does not augment PATH."""
        with patch("shutil.which", return_value=None) as mock_which:
            result = SSHLauncher._which("puttygen")

            assert result is None
            # Should only be called once - no augmented retry
            mock_which.assert_called_once_with("puttygen")

    @patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=False)
    def test_which_frozen_still_returns_none_if_not_found(self):
        """In a frozen build, _which returns None if binary not in extra paths either."""
        with patch("shutil.which", return_value=None) as mock_which:
            with patch.object(sys, "frozen", True, create=True):
                result = SSHLauncher._which("definitely_not_a_real_binary_12345")

            assert result is None
            assert mock_which.call_count == 2

    @patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}, clear=False)
    def test_which_frozen_skips_already_present_paths(self):
        """In a frozen build, _which doesn't duplicate paths already in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = [None, None]

            with patch.object(sys, "frozen", True, create=True):
                SSHLauncher._which("something")

            _, kwargs = mock_which.call_args
            augmented = kwargs["path"]
            parts = augmented.split(os.pathsep)
            # /usr/bin and /bin are already in PATH, should not be duplicated
            assert parts.count("/usr/bin") == 1
            assert parts.count("/bin") == 1
