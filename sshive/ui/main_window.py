"""Main application window."""

import hashlib
import json
import uuid
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSettings, QStandardPaths, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from sshive.models.connection import SSHConnection
from sshive.models.storage import ConnectionStorage
from sshive.ssh.launcher import SSHLauncher
from sshive.ui.add_dialog import AddConnectionDialog
from sshive.ui.icon_manager import IconManager
from sshive.ui.settings_dialog import SettingsDialog
from sshive.ui.theme import ThemeManager


class MainWindow(QMainWindow):
    """Main application window with connection tree."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        self.storage = ConnectionStorage()
        self.connections: list[SSHConnection] = []

        # Determine icon color based on theme
        self.icon_color = "white" if ThemeManager.is_system_dark_mode() else "black"

        self.incognito_mode = False
        self._setup_ui()
        self._setup_shortcuts()

        self.icon_manager = IconManager.instance()
        self.icon_manager.icon_loaded.connect(self._on_icon_loaded)

        self._load_connections()

        self.setWindowTitle("SSHive - SSH Connection Manager")

        # Restore window state and geometry
        self.settings = QSettings("sshive", "sshive")

        # Restore window state and geometry (Wayland may only restore size)
        if not self.restoreGeometry(self.settings.value("geometry", b"")):
            self.resize(800, 600)

        self.restoreState(self.settings.value("windowState", b""))

        header_state = self.settings.value("columnState")
        if header_state:
            self.tree.header().restoreState(header_state)

    def _setup_ui(self):
        """Setup the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Top options layout
        top_layout = QHBoxLayout()

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search connections...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setFixedWidth(300)
        search_icon = qta.icon("fa5s.search", color=self.icon_color)
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        top_layout.addWidget(self.search_bar)

        top_layout.addStretch()

        # Settings button (cog)
        settings_icon = qta.icon("fa5s.cog", color=self.icon_color)
        self.settings_btn = QToolButton()
        self.settings_btn.setIcon(settings_icon)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setStyleSheet("border: none; padding: 4px;")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._show_settings_dialog)

        top_layout.addWidget(self.settings_btn)
        layout.addLayout(top_layout)

        # Icons for later use
        add_icon = qta.icon("fa5s.plus", color=self.icon_color)

        # Connection tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Host", "User", "Port"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 150)
        self.tree.setAlternatingRowColors(False)
        self.tree.setAllColumnsShowFocus(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(20)
        self.tree.setMouseTracking(True)
        self.tree.itemEntered.connect(self._on_item_entered)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._connect_to_server)

        # Header context menu
        header = self.tree.header()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_context_menu)

        layout.addWidget(self.tree)

        # Bottom buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Connection")
        self.add_btn.setIcon(add_icon)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_connection)
        button_layout.addWidget(self.add_btn)

        clone_icon = qta.icon("fa5s.clone", color=self.icon_color)
        self.clone_btn = QPushButton("Clone")
        self.clone_btn.setIcon(clone_icon)
        self.clone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clone_btn.clicked.connect(self._clone_connection)
        self.clone_btn.setEnabled(False)
        button_layout.addWidget(self.clone_btn)

        edit_icon = qta.icon("fa5s.edit", color=self.icon_color)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setIcon(edit_icon)
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(lambda: self._edit_connection())
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)

        delete_icon = qta.icon("fa5s.trash", color=self.icon_color)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setIcon(delete_icon)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._delete_connection)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        connect_icon = qta.icon("fa5s.rocket", color=self.icon_color)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setIcon(connect_icon)
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.clicked.connect(lambda: self._connect_to_server(None))
        self.connect_btn.setEnabled(False)
        self.connect_btn.setDefault(True)
        button_layout.addWidget(self.connect_btn)

        layout.addLayout(button_layout)

        # Connect selection change
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)

        # Enable column reordering
        self.tree.header().setSectionsMovable(True)

        # Status overlay for long actions
        self._status_msg = None

    def _show_status(self, message: str):
        """Show a temporary status message."""
        print(f"Status: {message}")

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        self.incognito_action = QAction("Toggle Incognito Mode", self)
        self.incognito_action.setShortcut("Ctrl+I")
        self.incognito_action.triggered.connect(self._toggle_incognito_mode)
        self.addAction(self.incognito_action)

    def _toggle_incognito_mode(self):
        """Toggle obfuscation of server list by swapping connection sets."""
        self.incognito_mode = not self.incognito_mode

        if self.incognito_mode:
            # Backup real connections
            self._real_connections = self.connections.copy()

            # Load or generate fake connections
            self.connections = self._load_or_generate_incognito_connections()
        else:
            # Restore real connections
            if hasattr(self, "_real_connections"):
                self.connections = self._real_connections

        self._populate_tree()

    INCOGNITO_VERSION = 3

    def _load_or_generate_incognito_connections(self) -> list[SSHConnection]:
        """Load fake connections from file or generate them deterministically."""

        # Try to load from incognito-connections.json in the same dir as the app config
        config_dir = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        )
        incognito_path = config_dir / "incognito-connections.json"

        if incognito_path.exists():
            try:
                with open(incognito_path) as f:
                    data = json.load(f)

                    if isinstance(data, dict) and data.get("version") == self.INCOGNITO_VERSION:
                        return [SSHConnection.from_dict(conn) for conn in data["connections"]]
            except Exception as e:
                print(f"Failed to load incognito connections: {e}")

        # Fallback: generate deterministically from real connections
        fake_conns = []
        used_identities = set()

        for i, conn in enumerate(self.connections):
            # Ensure we cycle through services correctly
            name, host, user, group, icon, _ = self._get_fake_data(conn.id, service_index=i)

            # Handle potential identity collisions
            counter = 1
            while (name, host) in used_identities and counter < 10:
                name, host, user, group, icon, _ = self._get_fake_data(
                    f"{conn.id}-{counter}", service_index=i + counter
                )
                counter += 1

            used_identities.add((name, host))

            # Use deterministic port
            _, _, _, _, _, fake_port = self._get_fake_data(conn.id, service_index=i)

            fake_conn = SSHConnection(
                name=name,
                host=host,
                user=user,
                port=fake_port,
                group=group,
                icon=icon,
                id=conn.id,
            )
            fake_conns.append(fake_conn)

        # Save generated connections for consistency
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            output_data = {
                "version": self.INCOGNITO_VERSION,
                "connections": [c.to_dict() for c in fake_conns],
            }
            with open(incognito_path, "w") as f:
                json.dump(output_data, f, indent=4)
        except Exception as e:
            print(f"Failed to save incognito connections: {e}")

        return fake_conns

    def _get_fake_data(
        self, connection_id: str, service_index: int | None = None
    ) -> tuple[str, str, str, str, str, int]:
        """Generate deterministic fake data based on connection ID.

        Args:
            connection_id: Unique identifier for the connection
            service_index: Optional index to force a specific service selection

        Returns:
            Tuple of (name, host, user, group, icon, port)
        """

        seed = int(hashlib.md5(connection_id.encode()).hexdigest(), 16)

        services = [
            ("Plex", "Media", "plex"),
            ("Nextcloud", "Storage", "nextcloud"),
            ("Home Assistant", "Automation", "home-assistant"),
            ("Pi-hole", "Network", "pi-hole"),
            ("Portainer", "Docker", "portainer"),
            ("Uptime Kuma", "Monitoring", "uptime-kuma"),
            ("Jellyfin", "Media", "jellyfin"),
            ("AdGuard Home", "Network", "adguard-home"),
            ("Nginx Proxy Manager", "Network", "nginx-proxy-manager"),
            ("Vaultwarden", "Security", "bitwarden"),
            ("Paperless-ngx", "Storage", "paperless-ngx"),
            ("deluge", "Downloads", "deluge"),
            ("rtorrent", "Downloads", "rtorrent"),
            ("Transmission", "Downloads", "transmission"),
            ("qBittorrent", "Downloads", "qbittorrent"),
            ("Grafana", "Monitoring", "grafana"),
            ("Prometheus", "Monitoring", "prometheus"),
            ("Homebridge", "Automation", "homebridge"),
            ("FreshRSS", "Media", "freshrss"),
            ("Mealie", "Storage", "mealie"),
            ("Ghost", "Web", "ghost"),
            ("WordPress", "Web", "wordpress"),
            ("Node-RED", "Automation", "node-red"),
            ("Mosquitto", "Automation", "mosquitto"),
            ("TrueNAS Core", "Storage", "truenas"),
            ("Unraid OS", "Storage", "unraid"),
            ("Bitwarden", "Security", "bitwarden"),
            ("Logsnag", "Monitoring", "logsnag"),
            ("Netdata", "Monitoring", "netdata"),
            ("Checkmk", "Monitoring", "checkmk"),
            ("Guacamole", "Network", "guacamole"),
            ("Tailscale", "Network", "tailscale"),
            ("WireGuard", "Network", "wireguard"),
            ("Dozzle", "Docker", "dozzle"),
            ("Statping", "Monitoring", "statping"),
            ("Audiobookshelf", "Media", "audiobookshelf"),
            ("Navidrome", "Media", "navidrome"),
            ("Sonarr", "Downloads", "sonarr"),
            ("Radarr", "Downloads", "radarr"),
            ("Prowlarr", "Downloads", "prowlarr"),
            ("Overseerr", "Downloads", "overseerr"),
            ("Bazarr", "Downloads", "bazarr"),
            ("Gitea", "Web", "gitea"),
            ("Wiki.js", "Web", "wikijs"),
            ("Heimdall", "Web", "heimdall"),
            ("Flame", "Web", "flame"),
            ("Organizr", "Web", "organizr"),
        ]

        users = ["admin", "root", "pi", "user", "manager", "maintainer", "sysop", "dev"]

        # Use service_index if provided to ensure distribution, otherwise fallback to seed
        idx = service_index if service_index is not None else seed
        service_info = services[idx % len(services)]

        name = service_info[0]
        group = service_info[1]
        icon = service_info[2]

        # Generate deterministic local IP
        host_byte = (seed >> 16) % 254 + 1

        # Assign subnet based on seed
        ip_prefix = seed % 3
        if ip_prefix == 0:
            subnet = (seed >> 12) % 10  # More variety in subnets
            host = f"192.168.{subnet}.{host_byte}"
        elif ip_prefix == 1:
            subnet = (seed >> 12) % 50
            host = f"10.0.{subnet}.{host_byte}"
        else:
            subnet = (seed >> 12) % 32
            host = f"172.16.{subnet}.{host_byte}"

        user = users[seed % len(users)]

        # Generate deterministic port
        port = 1024 + (seed % (65535 - 1024 + 1))

        return name, host, user, group, icon, port

    def closeEvent(self, event):
        """Handle window close event to save settings."""
        self._save_settings()
        super().closeEvent(event)

    def _save_settings(self):
        """Save window state and geometry."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("columnState", self.tree.header().saveState())

    def _load_connections(self):
        """Load connections from storage and populate tree."""
        self.connections = self.storage.load_connections()
        self._populate_tree()

    def _populate_tree(self):
        """Populate tree widget with connections grouped by category."""
        self.tree.clear()

        # Group connections by group name
        grouped_conns: dict[str, list[SSHConnection]] = {}
        for conn in self.connections:
            group_name = conn.group or "Default"
            if group_name not in grouped_conns:
                grouped_conns[group_name] = []
            grouped_conns[group_name].append(conn)

        # Define standard icons
        folder_icon = qta.icon("fa5s.folder", color=self.icon_color)
        server_icon = qta.icon("fa5s.server", color=self.icon_color)

        # Map path -> QTreeWidgetItem
        group_items: dict[str, QTreeWidgetItem] = {}

        for group_name in sorted(grouped_conns.keys()):
            parts = group_name.split("/")
            current_path = ""

            for part in parts:
                prev_path = current_path
                current_path = f"{current_path}/{part}" if current_path else part

                if current_path not in group_items:
                    # Create item
                    parent_item = group_items[prev_path] if prev_path else self.tree

                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, part)
                    item.setIcon(0, folder_icon)
                    item.setExpanded(True)
                    item.setData(0, Qt.ItemDataRole.UserRole, None)
                    group_items[current_path] = item

            # Add connections to this group
            group_item = group_items[group_name]
            for conn in sorted(grouped_conns[group_name], key=lambda c: c.name):
                conn_item = QTreeWidgetItem(group_item)

                conn_item.setText(0, conn.name)
                conn_item.setText(1, conn.host)
                conn_item.setText(2, conn.user)
                conn_item.setText(3, str(conn.port))

                # Set icon
                if conn.icon:
                    icon = self.icon_manager.get_icon(conn.icon)
                    if icon:
                        conn_item.setIcon(0, icon)
                    else:
                        conn_item.setIcon(0, server_icon)
                else:
                    conn_item.setIcon(0, server_icon)

                conn_item.setData(0, Qt.ItemDataRole.UserRole, conn)
                if self.incognito_mode:
                    conn_item.setToolTip(0, "Incognito mode active")
                else:
                    conn_item.setToolTip(0, str(conn))

    def _on_icon_loaded(self, name: str, path: str):
        """Handle icon loaded signal and update tree items."""
        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            conn = item.data(0, Qt.ItemDataRole.UserRole)
            if conn and conn.icon == name:
                item.setIcon(0, QIcon(path))
            it += 1

    def _on_item_entered(self, item: QTreeWidgetItem, column: int):
        """Update cursor based on item type."""
        connection = item.data(0, Qt.ItemDataRole.UserRole)
        if connection is None:  # It's a group
            self.tree.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.tree.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_search_text_changed(self, text: str):
        """Filter tree items based on search text."""
        text = text.lower()
        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            connection = item.data(0, Qt.ItemDataRole.UserRole)

            if connection:
                # It's a connection item
                matches = text in connection.name.lower() or text in connection.host.lower()
                item.setHidden(not matches)

                # If matches, we need to make sure all parents are visible
                if matches:
                    parent = item.parent()
                    while parent:
                        parent.setHidden(False)
                        parent = parent.parent()
            else:
                # Handle group items visibility
                if not text:
                    item.setHidden(False)
                else:
                    item.setHidden(True)

            it += 1

    def _on_selection_changed(self):
        """Handle tree selection changes."""
        selected_items = self.tree.selectedItems()

        if not selected_items:
            self.clone_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.connect_btn.setEnabled(False)
            return

        item = selected_items[0]
        connection = item.data(0, Qt.ItemDataRole.UserRole)

        # Enable buttons only if a connection is selected (not a group)
        is_connection = connection is not None
        self.clone_btn.setEnabled(is_connection)
        self.edit_btn.setEnabled(is_connection)
        self.delete_btn.setEnabled(is_connection)
        self.connect_btn.setEnabled(is_connection)

    def _add_connection(self):
        """Show add connection dialog."""
        dialog = AddConnectionDialog(self, existing_groups=self.storage.get_groups())

        if dialog.exec():
            connection = dialog.get_connection()
            if connection:
                self.storage.add_connection(connection)
                self._load_connections()

    def _clone_connection(self, item: QTreeWidgetItem | None = None):
        """Show clone connection dialog for selected connection.

        Args:
            item: Tree item to clone (optional, uses selection if None)
        """
        if not item:
            selected_items = self.tree.selectedItems()
            if not selected_items:
                return
            item = selected_items[0]

        connection = item.data(0, Qt.ItemDataRole.UserRole)
        if not connection:
            return

        # Clone with fresh ID to prevent duplicates
        new_connection = SSHConnection(
            name=f"{connection.name} (Copy)",
            host=connection.host,
            user=connection.user,
            port=connection.port,
            key_path=connection.key_path,
            group=connection.group,
            id=uuid.uuid4().hex,
        )

        dialog = AddConnectionDialog(
            self, connection=new_connection, existing_groups=self.storage.get_groups()
        )

        if dialog.exec():
            cloned_connection = dialog.get_connection()
            if cloned_connection:
                self.storage.add_connection(cloned_connection)
                self._load_connections()

    def _edit_connection(self, item: QTreeWidgetItem | None = None):
        """Show edit connection dialog for selected connection.

        Args:
            item: Tree item to edit (optional, uses selection if None)
        """
        if not item:
            selected_items = self.tree.selectedItems()
            if not selected_items:
                return
            item = selected_items[0]

        connection = item.data(0, Qt.ItemDataRole.UserRole)
        if not connection:
            return

        dialog = AddConnectionDialog(
            self, connection=connection, existing_groups=self.storage.get_groups()
        )

        if dialog.exec():
            updated_connection = dialog.get_connection()
            if updated_connection:
                self.storage.update_connection(updated_connection)
                self._load_connections()

    def _delete_connection(self, item: QTreeWidgetItem | None = None):
        """Delete selected connection after confirmation.

        Args:
            item: Tree item to delete (optional, uses selection if None)
        """
        if not item:
            selected_items = self.tree.selectedItems()
            if not selected_items:
                return
            item = selected_items[0]

        connection = item.data(0, Qt.ItemDataRole.UserRole)
        if not connection:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{connection.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.storage.delete_connection(connection.id)
            self._load_connections()

    def _connect_to_server(self, item: QTreeWidgetItem | None):
        """Launch SSH connection for selected server.

        Args:
            item: Tree item that was double-clicked (or None if button clicked)
        """
        # Get connection from item or selected item
        if item:
            connection = item.data(0, Qt.ItemDataRole.UserRole)
        else:
            selected_items = self.tree.selectedItems()
            if not selected_items:
                return
            connection = selected_items[0].data(0, Qt.ItemDataRole.UserRole)

        if not connection:
            return  # Clicked on group, not connection

        # Test connection validity (dependency/path checks)
        success, error_msg = SSHLauncher.test_connection(connection)
        if not success:
            QMessageBox.warning(
                self,
                "Connection Error",
                f"Cannot connect to {connection.name}.\n\n{error_msg}",
            )
            return

        # Background credential check if password/key provided
        verify_credentials = self.settings.value("verify_credentials", "true") == "true"
        if verify_credentials and (connection.password or connection.key_path):
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                # Force a UI update to show the cursor
                QApplication.processEvents()

                auth_success, auth_error = SSHLauncher.check_credentials(connection)
                if not auth_success:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(
                        self,
                        "Authentication Failed",
                        f"Failed to authenticate for {connection.name}.\n\n{auth_error}",
                    )
                    return
            finally:
                QApplication.restoreOverrideCursor()

        # Launch connection
        success = SSHLauncher.launch(connection)

        if not success:
            QMessageBox.warning(
                self,
                "Launch Error",
                f"Failed to launch terminal for {connection.name}.\n\n"
                f"Check that you have a terminal emulator installed.",
            )

    def _show_context_menu(self, position):
        """Show context menu for tree items.

        Args:
            position: Position where right-click occurred
        """
        item = self.tree.itemAt(position)
        if not item:
            return

        connection = item.data(0, Qt.ItemDataRole.UserRole)
        if not connection:
            return  # Don't show menu for groups

        menu = QMenu()

        connect_action = menu.addAction(qta.icon("fa5s.rocket", color=self.icon_color), "Connect")
        connect_action.triggered.connect(lambda: self._connect_to_server(item))

        menu.addSeparator()

        clone_action = menu.addAction(qta.icon("fa5s.clone", color=self.icon_color), "Clone")
        clone_action.triggered.connect(lambda: self._clone_connection(item))

        edit_action = menu.addAction(qta.icon("fa5s.edit", color=self.icon_color), "Edit")
        edit_action.triggered.connect(lambda: self._edit_connection(item))

        delete_action = menu.addAction(qta.icon("fa5s.trash", color=self.icon_color), "Delete")
        delete_action.triggered.connect(lambda: self._delete_connection(item))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _show_header_context_menu(self, position):
        """Show context menu for tree header to hide columns.

        Args:
            position: Position where right-click occurred
        """
        column = self.tree.header().logicalIndexAt(position)
        if column <= 0:  # Don't hide the "Name" column
            return

        menu = QMenu()
        column_name = self.tree.headerItem().text(column)
        hide_action = menu.addAction(f"Hide {column_name}")
        hide_action.triggered.connect(lambda: self.tree.setColumnHidden(column, True))

        menu.exec(self.tree.header().mapToGlobal(position))

    def _show_settings_dialog(self):
        """Show the settings dialog."""
        header_item = self.tree.headerItem()
        column_names = [header_item.text(i) for i in range(self.tree.columnCount())]
        hidden_columns = [
            i for i in range(1, self.tree.columnCount()) if self.tree.isColumnHidden(i)
        ]

        dialog = SettingsDialog(self, self.settings, column_names, hidden_columns)
        if dialog.exec():
            settings = dialog.get_settings()

            # Update verification setting
            self.settings.setValue(
                "verify_credentials", str(settings["verify_credentials"]).lower()
            )

            # Update column visibility
            for idx, visible in settings["column_visibility"].items():
                self.tree.setColumnHidden(idx, not visible)

            # Save column state
            self.settings.setValue("columnState", self.tree.header().saveState())
