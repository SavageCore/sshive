"""Tests for UI components."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytestqt.qtbot import QtBot

from sshive.models.connection import SSHConnection
from sshive.models.storage import ConnectionStorage
from sshive.ui.add_dialog import AddConnectionDialog
from sshive.ui.main_window import MainWindow
from sshive.ui.settings_dialog import SettingsDialog, _get_available_languages


class TestMainWindow:
    """Test cases for MainWindow."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)

        storage = ConnectionStorage(temp_path)

        yield storage

        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def window(self, qtbot: QtBot, temp_storage, monkeypatch):
        """Create main window with temporary storage."""
        # Monkey patch storage to use temp storage
        monkeypatch.setattr("sshive.ui.main_window.ConnectionStorage", lambda: temp_storage)

        win = MainWindow()
        win.storage = temp_storage
        qtbot.addWidget(win)
        return win

    def test_window_initialization(self, window):
        """Test that window initializes correctly."""
        assert window.windowTitle() == "SSHive - SSH Connection Manager"
        assert window.tree is not None
        assert window.add_btn is not None
        assert window.edit_btn is not None
        assert window.delete_btn is not None
        assert window.connect_btn is not None

    def test_buttons_disabled_on_start(self, window):
        """Test that edit/delete/connect buttons are disabled initially."""
        assert window.edit_btn.isEnabled() is False
        assert window.delete_btn.isEnabled() is False
        assert window.connect_btn.isEnabled() is False

    def test_load_connections_empty(self, window):
        """Test loading connections when none exist."""
        window._load_connections()

        assert window.tree.topLevelItemCount() == 0

    def test_load_connections_with_data(self, window, temp_storage):
        """Test loading connections from storage."""
        # Add test connections
        conn1 = SSHConnection(
            name="Server1", host="host1.com", user="user1", group="Work", icon="proxmox"
        )
        conn2 = SSHConnection(name="Server2", host="host2.com", user="user2", group="Work")

        temp_storage.add_connection(conn1)
        temp_storage.add_connection(conn2)

        window._load_connections()

        # Should have one group
        assert window.tree.topLevelItemCount() == 1

        # Group should have two children
        group_item = window.tree.topLevelItem(0)
        assert group_item.childCount() == 2

    def test_selection_enables_buttons(self, window, temp_storage, qtbot: QtBot):
        """Test that selecting a connection enables buttons."""
        # Add connection
        conn = SSHConnection(name="Test", host="example.com", user="testuser")
        temp_storage.add_connection(conn)
        window._load_connections()

        # Select the connection
        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)
        window.tree.setCurrentItem(conn_item)

        # Buttons should be enabled
        assert window.edit_btn.isEnabled() is True
        assert window.delete_btn.isEnabled() is True
        assert window.connect_btn.isEnabled() is True

    def test_selecting_group_disables_buttons(self, window, temp_storage, qtbot: QtBot):
        """Test that selecting a group keeps buttons disabled."""
        # Add connection
        conn = SSHConnection(name="Test", host="example.com", user="testuser")
        temp_storage.add_connection(conn)
        window._load_connections()

        # Select the group (not connection)
        group_item = window.tree.topLevelItem(0)
        window.tree.setCurrentItem(group_item)

        # Buttons should be disabled
        assert window.edit_btn.isEnabled() is False
        assert window.delete_btn.isEnabled() is False
        assert window.connect_btn.isEnabled() is False

    def test_cloning_generates_unique_id(self, window, temp_storage, qtbot: QtBot, monkeypatch):
        """Test that cloning a connection generates a new unique ID."""
        # Add connection
        conn = SSHConnection(name="Original", host="example.com", user="testuser")
        temp_storage.add_connection(conn)
        window._load_connections()

        # Select the connection
        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)
        window.tree.setCurrentItem(conn_item)

        # Mock AddConnectionDialog to capture cloned connection
        cloned_conn_captured = [None]

        class MockDialog:
            def __init__(self, parent=None, connection=None, existing_groups=None):
                cloned_conn_captured[0] = connection

            def exec(self):
                return True

            def get_connection(self):
                return cloned_conn_captured[0]

        monkeypatch.setattr("sshive.ui.main_window.AddConnectionDialog", MockDialog)

        # Trigger clone
        window._clone_connection()

        # Check results
        assert cloned_conn_captured[0] is not None
        assert cloned_conn_captured[0].id != conn.id
        assert cloned_conn_captured[0].name == "Original (Copy)"

        # Verify both are in storage
        all_conns = temp_storage.load_connections()
        assert len(all_conns) == 2
        ids = [c.id for c in all_conns]
        assert conn.id in ids
        assert cloned_conn_captured[0].id in ids
        assert len(set(ids)) == 2

    def test_incognito_mode_obfuscation(self, window, temp_storage, qtbot: QtBot):
        """Test that incognito mode swaps entire connections list with fake data."""
        # Add connection
        conn = SSHConnection(
            name="Real Server", host="real-host.com", user="realuser", group="Real Group"
        )
        temp_storage.add_connection(conn)
        window._load_connections()

        # Select the connection
        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)

        # Initially real data
        assert group_item.text(0) == "Real Group"
        assert conn_item.text(0) == "Real Server"

        # Toggle incognito mode
        window._toggle_incognito_mode()

        # Re-fetch invalidated tree items
        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)

        # Now fake data
        assert group_item.text(0) != "Real Group"
        assert conn_item.text(0) != "Real Server"
        assert any(
            s in conn_item.text(0)
            for s in [
                "Plex",
                "Nextcloud",
                "Home Assistant",
                "Pi-hole",
                "Portainer",
                "Uptime",
                "Jellyfin",
                "AdGuard",
                "Nginx",
                "Vaultwarden",
                "Paperless",
                "Transmission",
                "qBittorrent",
                "Grafana",
                "Prometheus",
            ]
        )
        assert conn_item.toolTip(0) == "Incognito mode active"

        # Toggle back
        window._toggle_incognito_mode()

        # Re-fetch again
        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)

        # Real data again
        assert group_item.text(0) == "Real Group"
        assert conn_item.text(0) == "Real Server"

    def test_incognito_mode_port_randomization(self, window, temp_storage, qtbot: QtBot):
        """Test that incognito mode randomizes ports."""
        # Add connection with standard SSH port
        conn = SSHConnection(name="Test Server", host="example.com", user="testuser", port=22)
        temp_storage.add_connection(conn)
        window._load_connections()

        # Toggle incognito mode
        window._toggle_incognito_mode()

        # Re-fetch item from tree
        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)

        # Port should be randomized (not 22)
        randomized_port = int(conn_item.text(3))
        assert randomized_port != 22
        assert 1024 <= randomized_port <= 65535

        # Toggle off and back on to check determinism
        window._toggle_incognito_mode()
        window._toggle_incognito_mode()

        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)
        assert int(conn_item.text(3)) == randomized_port


class TestAddConnectionDialog:
    """Test cases for AddConnectionDialog."""

    @pytest.fixture
    def dialog(self, qtbot: QtBot):
        """Create dialog for testing."""
        dlg = AddConnectionDialog()
        qtbot.addWidget(dlg)
        return dlg

    def test_dialog_initialization(self, dialog):
        """Test that dialog initializes correctly."""
        assert dialog.windowTitle() == "Add Connection"
        assert dialog.name_input is not None
        assert dialog.host_input is not None
        assert dialog.user_input is not None
        assert dialog.port_input is not None
        assert dialog.key_input is not None
        assert dialog.group_input is not None

    def test_default_port_is_22(self, dialog):
        """Test that default port is 22."""
        assert dialog.port_input.value() == 22

    def test_default_group_is_default(self, dialog):
        """Test that default group is 'Default'."""
        assert dialog.group_input.currentText() == "Default"

    def test_get_connection_with_valid_data(self, dialog, qtbot: QtBot):
        """Test getting connection with valid input."""
        dialog.name_input.setText("Test Server")
        dialog.host_input.setText("example.com")
        dialog.user_input.setText("testuser")
        dialog.port_input.setValue(2222)
        dialog.group_input.setCurrentText("Work")
        dialog.icon_input.setText("home-assistant")

        conn = dialog.get_connection()

        assert conn is not None
        assert conn.name == "Test Server"
        assert conn.host == "example.com"
        assert conn.user == "testuser"
        assert conn.port == 2222
        assert conn.group == "Work"
        assert conn.icon == "home-assistant"

    def test_get_connection_with_key(self, dialog):
        """Test getting connection with SSH key."""
        dialog.name_input.setText("Test")
        dialog.host_input.setText("example.com")
        dialog.user_input.setText("testuser")
        dialog.key_input.setText("~/.ssh/id_rsa")

        conn = dialog.get_connection()

        assert conn is not None
        assert conn.key_path is not None

    def test_get_connection_with_empty_name(self, dialog):
        """Test that empty name returns None."""
        dialog.name_input.setText("")
        dialog.host_input.setText("example.com")
        dialog.user_input.setText("testuser")

        conn = dialog.get_connection()

        assert conn is None

    def test_get_connection_with_empty_host(self, dialog):
        """Test that empty host returns None."""
        dialog.name_input.setText("Test")
        dialog.host_input.setText("")
        dialog.user_input.setText("testuser")

        conn = dialog.get_connection()

        assert conn is None

    def test_get_connection_with_empty_user(self, dialog):
        """Test that empty user returns None."""
        dialog.name_input.setText("Test")
        dialog.host_input.setText("example.com")
        dialog.user_input.setText("")

        conn = dialog.get_connection()

        assert conn is None

    def test_edit_mode_populates_fields(self, qtbot: QtBot):
        """Test that editing an existing connection populates fields."""
        conn = SSHConnection(
            name="Original",
            host="example.com",
            user="testuser",
            port=2222,
            key_path="~/.ssh/id_rsa",
            group="Work",
            icon="proxmox",
        )

        dialog = AddConnectionDialog(connection=conn)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Edit Connection"
        assert dialog.name_input.text() == "Original"
        assert dialog.host_input.text() == "example.com"
        assert dialog.user_input.text() == "testuser"
        assert dialog.port_input.value() == 2222
        assert dialog.group_input.currentText() == "Work"
        assert dialog.icon_input.text() == "proxmox"

    def test_existing_groups_populated(self, qtbot: QtBot):
        """Test that existing groups are populated in dropdown."""
        existing_groups = ["Work", "Personal", "Development"]

        dialog = AddConnectionDialog(existing_groups=existing_groups)
        qtbot.addWidget(dialog)

        # Check that groups are in the combobox
        items = [dialog.group_input.itemText(i) for i in range(dialog.group_input.count())]

        assert "Work" in items
        assert "Personal" in items
        assert "Development" in items


class TestSettingsDialog:
    """Test cases for SettingsDialog language selection."""

    @pytest.fixture
    def mock_i18n_dir(self, tmp_path):
        """Create a temp i18n directory with mock .qm files."""
        i18n_dir = tmp_path / "i18n"
        i18n_dir.mkdir()
        (i18n_dir / "en.qm").touch()
        (i18n_dir / "nl.qm").touch()
        return i18n_dir

    @pytest.fixture
    def mock_settings(self):
        """Create a mock QSettings object."""
        settings = MagicMock()
        settings.value.side_effect = lambda key, default=None: default
        return settings

    @pytest.fixture
    def dialog(self, qtbot: QtBot, mock_settings, mock_i18n_dir):
        """Create a SettingsDialog for testing."""
        dlg = SettingsDialog(
            settings=mock_settings,
            column_names=["Name", "Host", "User", "Port"],
            hidden_columns=[],
            i18n_dir=mock_i18n_dir,
        )
        qtbot.addWidget(dlg)
        return dlg

    def test_get_available_languages_includes_system(self, mock_i18n_dir):
        """'system' entry is always first in the language list."""
        langs = _get_available_languages(i18n_dir=mock_i18n_dir)
        assert langs[0][0] == "system"
        assert "System" in langs[0][1]

    def test_get_available_languages_includes_qm_files(self, mock_i18n_dir):
        """Available languages include entries for each .qm file present."""
        langs = _get_available_languages(i18n_dir=mock_i18n_dir)
        codes = [code for code, _ in langs]
        assert "en" in codes
        assert "nl" in codes

    def test_lang_combo_exists(self, dialog):
        """Language combo box is present in the settings dialog."""
        assert dialog.lang_combo is not None

    def test_default_language_is_system(self, dialog):
        """When no language is saved, 'system' is selected."""
        assert dialog.lang_combo.currentData() == "system"

    def test_saved_language_is_pre_selected(self, qtbot: QtBot, mock_settings, mock_i18n_dir):
        """When a language is already saved it is pre-selected in the combo."""
        mock_settings.value.side_effect = lambda key, default=None: (
            "nl" if key == "language" else default
        )
        dlg = SettingsDialog(
            settings=mock_settings,
            column_names=["Name"],
            hidden_columns=[],
            i18n_dir=mock_i18n_dir,
        )
        qtbot.addWidget(dlg)
        assert dlg.lang_combo.currentData() == "nl"

    def test_get_settings_returns_language_code(self, dialog):
        """get_settings() includes the selected language code."""
        result = dialog.get_settings()
        assert "language" in result
        assert result["language"] == "system"

    def test_restart_label_hidden_by_default(self, dialog):
        """Restart warning label is hidden when dialog opens."""
        assert dialog.lang_restart_label.isHidden()

    def test_restart_label_shown_on_change(self, dialog):
        """Restart warning appears when a different language is selected."""
        # Find an index that is NOT the current one
        current_index = dialog.lang_combo.currentIndex()
        other_index = 0 if current_index != 0 else 1
        if dialog.lang_combo.count() > 1:
            dialog.lang_combo.setCurrentIndex(other_index)
            assert not dialog.lang_restart_label.isHidden()

    def test_restart_label_hidden_when_reverted(self, dialog):
        """Restart warning hides again if user selects the originally saved language."""
        if dialog.lang_combo.count() > 1:
            original_index = dialog.lang_combo.currentIndex()
            # Change to another language
            dialog.lang_combo.setCurrentIndex(1 if original_index == 0 else 0)
            assert not dialog.lang_restart_label.isHidden()
            # Revert
            dialog.lang_combo.setCurrentIndex(original_index)
            assert dialog.lang_restart_label.isHidden()
