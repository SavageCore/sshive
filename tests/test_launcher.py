"""Tests for SSH launcher."""

import shutil
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

    @patch("shutil.which")
    def test_detect_terminal_konsole(self, mock_which):
        """Test detection of konsole terminal."""

        def which_side_effect(cmd):
            return "/usr/bin/konsole" if cmd == "konsole" else None

        mock_which.side_effect = which_side_effect

        terminal_name, cmd_template = SSHLauncher.detect_terminal()

        assert terminal_name == "konsole"
        assert cmd_template[0] == "konsole"

    @patch("shutil.which")
    def test_detect_terminal_fallback(self, mock_which):
        """Test fallback to xterm when no terminal found."""
        mock_which.return_value = None

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
        assert "ssh" in call_args

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
        assert "-i" in call_args

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
        assert "-p" in call_args
        assert "2222" in call_args

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
        result = SSHLauncher.test_connection(conn)

        if shutil.which("ssh"):
            assert result is True
        else:
            assert result is False

    @patch("shutil.which")
    def test_test_connection_no_ssh(self, mock_which):
        """Test connection test when ssh command doesn't exist."""
        mock_which.return_value = None

        conn = SSHConnection(name="Test", host="example.com", user="testuser")

        result = SSHLauncher.test_connection(conn)

        assert result is False

    def test_test_connection_invalid_key(self):
        """Test connection test with non-existent key file."""
        conn = SSHConnection(
            name="Test", host="example.com", user="testuser", key_path="/nonexistent/key/file"
        )

        result = SSHLauncher.test_connection(conn)

        assert result is False

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
            result = SSHLauncher.test_connection(conn)

            if shutil.which("ssh"):
                assert result is True
            else:
                assert result is False

        finally:
            Path(key_path).unlink()
