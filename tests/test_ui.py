"""Tests for UI components."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMessageBox
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
        monkeypatch.setattr(
            "sshive.ui.main_window.ConnectionStorage", lambda **kwargs: temp_storage
        )

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
        assert window.test_btn is not None
        assert window.connect_btn is not None

    def test_buttons_disabled_on_start(self, window):
        """Test that edit/delete/connect buttons are disabled initially."""
        assert window.edit_btn.isEnabled() is False
        assert window.delete_btn.isEnabled() is False
        assert window.test_btn.isEnabled() is False
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

    def test_load_connections_with_custom_icon_path(self, window, temp_storage):
        """Custom icon file paths are used directly without icon manager fetch."""
        icon_path = temp_storage.config_file.parent / "custom-icon.png"
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.red)
        assert pixmap.save(str(icon_path))

        conn = SSHConnection(
            name="Server1",
            host="host1.com",
            user="user1",
            group="Work",
            icon=str(icon_path),
        )
        temp_storage.add_connection(conn)

        original_get_icon = window.icon_manager.get_icon

        def fail_get_icon(_):
            raise AssertionError("Icon manager should not be called for custom icon path")

        window.icon_manager.get_icon = fail_get_icon
        try:
            window._load_connections()
        finally:
            window.icon_manager.get_icon = original_get_icon

        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)
        assert not conn_item.icon(0).isNull()

    def test_delete_connection_cleans_orphan_custom_icons(self, window, temp_storage, monkeypatch):
        """Deleting a connection removes unreferenced custom icon files."""
        custom_icons_dir = temp_storage.config_file.parent / "custom_icons"
        custom_icons_dir.mkdir(parents=True, exist_ok=True)

        keep_icon = custom_icons_dir / "keep.png"
        orphan_icon = custom_icons_dir / "orphan.png"

        keep_pixmap = QPixmap(16, 16)
        keep_pixmap.fill(Qt.GlobalColor.green)
        assert keep_pixmap.save(str(keep_icon), "PNG")

        orphan_pixmap = QPixmap(16, 16)
        orphan_pixmap.fill(Qt.GlobalColor.yellow)
        assert orphan_pixmap.save(str(orphan_icon), "PNG")

        keep_conn = SSHConnection(
            name="Keep Server",
            host="keep.example.com",
            user="keep",
            icon=str(keep_icon),
        )
        delete_conn = SSHConnection(
            name="Delete Server",
            host="delete.example.com",
            user="delete",
            icon=str(orphan_icon),
        )

        temp_storage.add_connection(keep_conn)
        temp_storage.add_connection(delete_conn)
        window._load_connections()

        monkeypatch.setattr(
            "sshive.ui.main_window.QMessageBox.question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )

        group_item = window.tree.topLevelItem(0)
        delete_item = None
        for i in range(group_item.childCount()):
            child = group_item.child(i)
            conn = child.data(0, Qt.ItemDataRole.UserRole)
            if conn and conn.id == delete_conn.id:
                delete_item = child
                break

        assert delete_item is not None
        window._delete_connection(delete_item)

        remaining_ids = [conn.id for conn in temp_storage.load_connections()]
        assert keep_conn.id in remaining_ids
        assert delete_conn.id not in remaining_ids
        assert keep_icon.exists()
        assert not orphan_icon.exists()

    def test_edit_connection_cleans_replaced_custom_icon(self, window, temp_storage, monkeypatch):
        """Editing a connection icon removes the previously referenced custom icon file."""
        custom_icons_dir = temp_storage.config_file.parent / "custom_icons"
        custom_icons_dir.mkdir(parents=True, exist_ok=True)

        old_icon = custom_icons_dir / "old.png"
        new_icon = custom_icons_dir / "new.png"

        old_pixmap = QPixmap(16, 16)
        old_pixmap.fill(Qt.GlobalColor.cyan)
        assert old_pixmap.save(str(old_icon), "PNG")

        new_pixmap = QPixmap(16, 16)
        new_pixmap.fill(Qt.GlobalColor.magenta)
        assert new_pixmap.save(str(new_icon), "PNG")

        conn = SSHConnection(
            name="Edit Server",
            host="edit.example.com",
            user="edit",
            icon=str(old_icon),
        )
        temp_storage.add_connection(conn)
        window._load_connections()

        class MockDialog:
            def __init__(self, parent=None, connection=None, existing_groups=None):
                self.connection = connection

            def exec(self):
                return True

            def get_connection(self):
                self.connection.icon = str(new_icon)
                return self.connection

        monkeypatch.setattr("sshive.ui.main_window.AddConnectionDialog", MockDialog)

        group_item = window.tree.topLevelItem(0)
        edit_item = None
        for i in range(group_item.childCount()):
            child = group_item.child(i)
            item_conn = child.data(0, Qt.ItemDataRole.UserRole)
            if item_conn and item_conn.id == conn.id:
                edit_item = child
                break

        assert edit_item is not None
        window._edit_connection(edit_item)

        updated_connections = temp_storage.load_connections()
        assert len(updated_connections) == 1
        assert updated_connections[0].icon == str(new_icon)
        assert not old_icon.exists()
        assert new_icon.exists()

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
        assert window.test_btn.isEnabled() is True
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
        assert window.test_btn.isEnabled() is False
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

    def test_connect_records_recent_history_on_success(self, window, temp_storage, monkeypatch):
        """Successful launches are persisted in recent connections history."""
        conn = SSHConnection(name="Prod", host="prod.example.com", user="root", port=2222)
        temp_storage.add_connection(conn)
        window._load_connections()

        monkeypatch.setattr(
            "sshive.ui.main_window.SSHLauncher.test_connection", lambda connection: (True, None)
        )
        monkeypatch.setattr(
            "sshive.ui.main_window.SSHLauncher.launch", lambda connection, **kwargs: True
        )

        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)
        window._connect_to_server(conn_item)

        recent = temp_storage.get_recent_connections()
        assert len(recent) == 1
        assert recent[0]["id"] == conn.id

    def test_connect_host_key_mismatch_prompts_and_retries(self, window, temp_storage, monkeypatch):
        """A host-key mismatch prompts trust flow, updates known_hosts, and retries auth."""
        conn = SSHConnection(
            name="Seedbox",
            host="seedbox.example.com",
            user="root",
            key_path="~/.ssh/id_rsa",
        )
        temp_storage.add_connection(conn)
        window._load_connections()

        attempts = {"count": 0}

        def fake_check_credentials(_connection):
            attempts["count"] += 1
            if attempts["count"] == 1:
                return False, "WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!"
            return True, None

        monkeypatch.setattr(
            "sshive.ui.main_window.SSHLauncher.test_connection", lambda connection: (True, None)
        )
        monkeypatch.setattr(
            "sshive.ui.main_window.SSHLauncher.check_credentials", fake_check_credentials
        )
        monkeypatch.setattr(
            "sshive.ui.main_window.SSHLauncher.resolve_host_key_mismatch",
            lambda connection: (True, None),
        )
        monkeypatch.setattr(
            "sshive.ui.main_window.QMessageBox.question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        monkeypatch.setattr(
            "sshive.ui.main_window.SSHLauncher.launch", lambda connection, **kwargs: True
        )

        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)
        window._connect_to_server(conn_item)

        assert attempts["count"] == 2

    def test_connect_skips_recent_history_when_disabled(self, window, temp_storage, monkeypatch):
        """History is not recorded when save_recent_history setting is disabled."""
        conn = SSHConnection(name="Prod", host="prod.example.com", user="root", port=2222)
        temp_storage.add_connection(conn)
        window._load_connections()
        window.settings.setValue("save_recent_history", "false")

        monkeypatch.setattr(
            "sshive.ui.main_window.SSHLauncher.test_connection", lambda connection: (True, None)
        )
        monkeypatch.setattr(
            "sshive.ui.main_window.SSHLauncher.launch", lambda connection, **kwargs: True
        )

        group_item = window.tree.topLevelItem(0)
        conn_item = group_item.child(0)
        window._connect_to_server(conn_item)

        recent = temp_storage.get_recent_connections()
        assert len(recent) == 0

    def test_recent_connections_menu_shows_saved_entries(self, window, temp_storage):
        """Recent menu is populated from persisted history and enables valid targets."""
        conn = SSHConnection(name="DB", host="db.example.com", user="admin", port=2200)
        temp_storage.add_connection(conn)
        temp_storage.record_connection_used(conn)
        window._load_connections()

        window._refresh_recent_connections_menu()

        actions = window.recent_menu.actions()
        assert len(actions) == 3
        assert actions[0].isEnabled() is True
        assert "DB" in actions[0].text()
        assert actions[2].text() == "Clear Recent History"
        assert actions[2].isEnabled() is True

    def test_recent_connections_menu_disables_clear_when_empty(self, window):
        """Clear Recent History action is disabled when there is no history."""
        window._refresh_recent_connections_menu()

        actions = window.recent_menu.actions()
        assert len(actions) == 3
        assert actions[0].text() == "No recent connections"
        assert actions[2].text() == "Clear Recent History"
        assert actions[2].isEnabled() is False

    def test_recent_connections_menu_shows_disabled_message_when_setting_off(
        self, window, temp_storage
    ):
        """Recent menu indicates when history is disabled in settings."""
        conn = SSHConnection(name="DB", host="db.example.com", user="admin", port=2200)
        temp_storage.add_connection(conn)
        temp_storage.record_connection_used(conn)
        window.settings.setValue("save_recent_history", "false")

        window._load_connections()
        window._refresh_recent_connections_menu()

        actions = window.recent_menu.actions()
        assert len(actions) == 1
        assert actions[0].isEnabled() is False
        assert actions[0].text() == "History is disabled in Settings"

    def test_recent_connections_menu_disables_stale_entries(self, window, temp_storage):
        """Recent menu entries are disabled when history points to missing connections."""
        with open(temp_storage.config_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "1.0",
                    "connections": [],
                    "recent_connections": [
                        {
                            "id": "missing-conn-id",
                            "name": "Legacy",
                            "host": "legacy.example.com",
                            "user": "legacy",
                            "port": 22,
                            "last_connected_at": "2026-01-01T00:00:00+00:00",
                        }
                    ],
                },
                f,
                indent=2,
            )

        window._load_connections()

        window._refresh_recent_connections_menu()

        actions = window.recent_menu.actions()
        assert len(actions) == 3
        assert actions[0].isEnabled() is False

    def test_clear_recent_history_action_empties_history(self, window, temp_storage, monkeypatch):
        """Clear action removes all recent history entries after confirmation."""
        conn = SSHConnection(name="DB", host="db.example.com", user="admin", port=2200)
        temp_storage.add_connection(conn)
        temp_storage.record_connection_used(conn)

        monkeypatch.setattr(
            "sshive.ui.main_window.QMessageBox.question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )

        window._clear_recent_connections_history()
        recent = temp_storage.get_recent_connections()
        assert recent == []

    def test_disabling_recent_history_prompts_and_clears_when_confirmed(
        self, window, temp_storage, monkeypatch
    ):
        """Disabling history asks to clear existing history and clears it on Yes."""
        conn = SSHConnection(name="DB", host="db.example.com", user="admin", port=2200)
        temp_storage.add_connection(conn)
        temp_storage.record_connection_used(conn)
        window.settings.setValue("save_recent_history", "true")

        class MockSettingsDialog:
            def __init__(self, *args, **kwargs):
                pass

            def exec(self):
                return True

            def get_settings(self):
                return {
                    "verify_credentials": True,
                    "check_updates_startup": True,
                    "connection_test_debug": False,
                    "close_to_tray": True,
                    "save_recent_history": False,
                    "max_backups": 10,
                    "theme_preference": "System",
                    "language": "system",
                    "column_visibility": {1: True, 2: True, 3: True},
                }

        monkeypatch.setattr("sshive.ui.main_window.SettingsDialog", MockSettingsDialog)
        monkeypatch.setattr(
            "sshive.ui.main_window.QMessageBox.question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )

        window._show_settings_dialog()

        assert temp_storage.get_recent_connections() == []


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
        assert dialog.test_btn is not None

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

    def test_edit_mode_with_no_icon_keeps_icon_empty(self, qtbot: QtBot):
        """Editing a connection without an icon should not auto-fill icon from name."""
        conn = SSHConnection(
            name="Original",
            host="example.com",
            user="testuser",
            port=2222,
            key_path="~/.ssh/id_rsa",
            group="Work",
            icon=None,
        )

        dialog = AddConnectionDialog(connection=conn)
        qtbot.addWidget(dialog)

        assert dialog.icon_input.text() == ""

    def test_get_connection_persists_custom_icon_to_config(self, dialog, tmp_path, monkeypatch):
        """Custom icon path is copied/resized into app config custom_icons directory."""
        monkeypatch.setattr(
            "sshive.ui.add_dialog.QStandardPaths.writableLocation", lambda *_: str(tmp_path)
        )

        source_icon = tmp_path / "source-large.png"
        source_pixmap = QPixmap(256, 128)
        source_pixmap.fill(Qt.GlobalColor.blue)
        assert source_pixmap.save(str(source_icon), "PNG")

        dialog.name_input.setText("Test Server")
        dialog.host_input.setText("example.com")
        dialog.user_input.setText("testuser")
        dialog.icon_input.setText(str(source_icon))

        conn = dialog.get_connection()

        assert conn is not None
        assert conn.icon is not None
        stored_icon = Path(conn.icon)
        assert stored_icon.exists()
        assert stored_icon.parent == tmp_path / "custom_icons"
        assert stored_icon.suffix.lower() == ".png"

        stored_pixmap = QPixmap(str(stored_icon))
        assert not stored_pixmap.isNull()
        assert stored_pixmap.width() <= 64
        assert stored_pixmap.height() <= 64

    def test_test_button_runs_connectivity_check(self, dialog, monkeypatch):
        """Test button runs full connection test and shows success dialog."""
        dialog.name_input.setText("Test Server")
        dialog.host_input.setText("example.com")
        dialog.user_input.setText("testuser")

        called = {"full_test": False, "info": False}

        def fake_full_test(connection):
            called["full_test"] = True
            assert connection.host == "example.com"
            return True, "Full connection test passed.\n\nSSH port is reachable."

        def fake_information(parent, title, text):
            called["info"] = True
            assert "Test Server" in text
            assert "Full connection test passed" in text
            return QMessageBox.StandardButton.Ok

        monkeypatch.setattr("sshive.ui.add_dialog.SSHLauncher.test_full_connection", fake_full_test)
        monkeypatch.setattr("sshive.ui.add_dialog.QMessageBox.information", fake_information)

        dialog.test_btn.click()

        assert called["full_test"] is True
        assert called["info"] is True

    def test_test_button_requires_name_host_user(self, dialog, monkeypatch):
        """Test button warns when required fields are missing."""
        called = {"warn": False}

        def fake_warning(parent, title, text):
            called["warn"] = True
            assert "Please fill in" in text
            return QMessageBox.StandardButton.Ok

        monkeypatch.setattr("sshive.ui.add_dialog.QMessageBox.warning", fake_warning)

        dialog.test_btn.click()

        assert called["warn"] is True

    def test_test_button_shows_debug_log_on_failure(self, dialog, monkeypatch):
        """Test button shows debug log dialog when connection test fails."""
        dialog.name_input.setText("Fedora Box")
        dialog.host_input.setText("fedora.local")
        dialog.user_input.setText("user")

        called = {"full_test": False, "debug_dialog": False}

        def fake_full_test(connection):
            called["full_test"] = True
            return False, "Authentication failed: Permission denied"

        def fake_debug_dialog(parent, title, conn, summary, log):
            called["debug_dialog"] = True

        monkeypatch.setattr("sshive.ui.add_dialog.SSHLauncher.test_full_connection", fake_full_test)
        monkeypatch.setattr(
            "sshive.ui.add_dialog.SSHLauncher.collect_ssh_debug_log",
            lambda c: "ssh -vvv output here",
        )
        monkeypatch.setattr(
            "sshive.ui.add_dialog.show_connection_test_debug_dialog",
            fake_debug_dialog,
        )

        dialog.test_btn.click()

        assert called["full_test"] is True
        assert called["debug_dialog"] is True

    def test_test_button_host_key_mismatch_prompts_and_retries(self, dialog, monkeypatch):
        """Host-key mismatch in test flow prompts trust and retries once."""
        dialog.name_input.setText("Seedbox")
        dialog.host_input.setText("seedbox.example.com")
        dialog.user_input.setText("root")
        dialog.key_input.setText("~/.ssh/id_rsa")

        attempts = {"count": 0}
        called = {"info": False}

        def fake_full_test(connection):
            attempts["count"] += 1
            if attempts["count"] == 1:
                return False, "WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!"
            return True, "Full connection test passed."

        def fake_information(parent, title, text):
            called["info"] = True
            return QMessageBox.StandardButton.Ok

        monkeypatch.setattr("sshive.ui.add_dialog.SSHLauncher.test_full_connection", fake_full_test)
        monkeypatch.setattr(
            "sshive.ui.add_dialog.SSHLauncher.resolve_host_key_mismatch",
            lambda connection: (True, None),
        )
        monkeypatch.setattr(
            "sshive.ui.add_dialog.QMessageBox.question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        monkeypatch.setattr("sshive.ui.add_dialog.QMessageBox.information", fake_information)

        dialog.test_btn.click()

        assert attempts["count"] == 2
        assert called["info"] is True

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

    def test_get_settings_includes_connection_test_debug(self, dialog):
        """get_settings() includes the debug toggle for connection testing."""
        result = dialog.get_settings()
        assert "connection_test_debug" in result
        assert result["connection_test_debug"] is False

    def test_get_settings_includes_close_to_tray(self, dialog):
        """get_settings() includes close-to-tray toggle and defaults to enabled."""
        result = dialog.get_settings()
        assert "close_to_tray" in result
        assert result["close_to_tray"] is True

    def test_get_settings_includes_save_recent_history(self, dialog):
        """get_settings() includes recent history persistence toggle and defaults to enabled."""
        result = dialog.get_settings()
        assert "save_recent_history" in result
        assert result["save_recent_history"] is True

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
