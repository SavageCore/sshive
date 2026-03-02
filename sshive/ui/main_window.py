"""Main application window."""

import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSettings, QStandardPaths, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from sshive import __version__
from sshive.models.connection import SSHConnection
from sshive.models.storage import ConnectionStorage
from sshive.ssh.launcher import SSHLauncher
from sshive.ui.about_dialog import AboutDialog
from sshive.ui.add_dialog import AddConnectionDialog
from sshive.ui.icon_manager import IconManager
from sshive.ui.settings_dialog import SettingsDialog
from sshive.ui.theme import ThemeManager
from sshive.ui.update_dialog import UpdateDialog
from sshive.ui.utils import show_connection_test_debug_dialog
from sshive.updater import UpdateChecker


class MainWindow(QMainWindow):
    """Main application window with connection tree."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Load settings first to get backup configuration
        self.settings = QSettings("sshive", "sshive")
        max_backups = int(self.settings.value("max_backups", "10"))

        self.storage = ConnectionStorage(max_backups=max_backups)
        self.connections: list[SSHConnection] = []
        self._is_quitting = False
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_toggle_action: QAction | None = None

        # Determine icon color based on theme preference
        self._apply_theme()

        self.incognito_mode = False
        self._setup_ui()
        self._setup_shortcuts()

        self.icon_manager = IconManager.instance()
        self.icon_manager.icon_loaded.connect(self._on_icon_loaded)

        self._load_connections()

        self.setWindowTitle(self.tr("SSHive - SSH Connection Manager"))
        self._setup_system_tray()

        # Restore window state and geometry (Wayland may only restore size)
        if not self.restoreGeometry(self.settings.value("geometry", b"")):
            self.resize(800, 600)

        self.restoreState(self.settings.value("windowState", b""))

        header_state = self.settings.value("columnState")
        if header_state:
            self.tree.header().restoreState(header_state)

        # Force the last visible section to stretch to avoid empty viewport space
        # which breaks full-width hover highlighting across themes.
        self._update_column_stretch()

        # Update Checker
        self.updater = UpdateChecker(__version__, self)
        self.updater.update_available.connect(self._on_update_available)

        # Start background check if enabled
        if self.settings.value("check_updates_startup", "true") == "true":
            self.updater.check_for_updates()

    def _setup_system_tray(self):
        """Create and show the system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        QApplication.setQuitOnLastWindowClosed(False)

        tray_icon = self.windowIcon()
        if tray_icon.isNull():
            tray_icon = qta.icon("fa5s.server", color=self.icon_color)

        self.tray_icon = QSystemTrayIcon(tray_icon, self)
        self.tray_icon.setToolTip(self.tr("SSHive"))

        tray_menu = QMenu(self)
        self.tray_toggle_action = QAction(self.tr("Hide"), self)
        self.tray_toggle_action.triggered.connect(self._toggle_window_visibility)
        tray_menu.addAction(self.tray_toggle_action)

        tray_menu.addSeparator()

        quit_action = QAction(self.tr("Quit"), self)
        quit_action.triggered.connect(self._quit_from_tray)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        self._update_tray_toggle_action()

    @staticmethod
    def _setting_to_bool(value, default: bool = False) -> bool:
        """Convert QSettings-style values to bool."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() == "true"

    @staticmethod
    def _is_test_mode() -> bool:
        """Check if running in test environment."""
        return "PYTEST_CURRENT_TEST" in os.environ or "CI" in os.environ

    def _update_tray_toggle_action(self):
        """Update tray menu label based on window visibility."""
        if not self.tray_toggle_action:
            return

        is_window_visible = self.isVisible() and not self.isMinimized()
        self.tray_toggle_action.setText(self.tr("Hide") if is_window_visible else self.tr("Show"))

    def _toggle_window_visibility(self):
        """Toggle main window visibility from the tray menu."""
        is_window_visible = self.isVisible() and not self.isMinimized()
        if is_window_visible:
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

        self._update_tray_toggle_action()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handle tray icon click interactions."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._toggle_window_visibility()

    def _quit_from_tray(self):
        """Exit the application from tray menu."""
        self._is_quitting = True
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def _show_first_tray_close_hint(self):
        """Show a one-time notification that the app is still running in tray."""
        if not self.tray_icon or not QSystemTrayIcon.supportsMessages() or self._is_test_mode():
            return

        hint_seen = self._setting_to_bool(
            self.settings.value("tray_close_hint_shown", "false"), default=False
        )
        if hint_seen:
            return

        self.tray_icon.showMessage(
            self.tr("SSHive is still running"),
            self.tr("SSHive was minimized to the system tray. Use the tray icon to reopen it."),
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )
        self.settings.setValue("tray_close_hint_shown", "true")

    def handle_ipc_command(self, args: list[str]):
        """Handle commands received via IPC from other instances.

        Args:
            args: List of command flags (e.g., ['--show', '--quick-connect']).
        """
        for arg in args:
            if arg == "--show":
                self._show_window()
            elif arg == "--quick-connect":
                self._show_quick_connect_dialog()
            elif arg == "--recent":
                self._show_recent_connections_menu()

    def _show_window(self):
        """Show and focus the main window."""
        if self.isVisible() and not self.isMinimized():
            # Already visible, minimize/hide it instead
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

        self._update_tray_toggle_action()

    def _create_connection_popup_dialog(
        self,
        title: str,
        populate_callback,
        select_callback,
        has_search: bool = False,
        header_widget=None,
    ):
        """Create a reusable popup dialog for showing connections.

        Args:
            title: Dialog window title
            populate_callback: Function(list_widget, search_text) that populates the list
            select_callback: Function(connection_id) called when a connection is selected
            has_search: Whether to show a search input field
            header_widget: Optional widget to display at the top (e.g., QLabel, QLineEdit)
        """
        from PySide6.QtCore import QEvent, QObject, Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QVBoxLayout

        # Ensure main window is activated (required for Wayland grabbing popup)
        self.raise_()
        self.activateWindow()

        # Create popup dialog with proper parent for Wayland compatibility
        dialog = QDialog(self, Qt.WindowType.Popup | Qt.WindowType.Tool)
        dialog.setWindowTitle(title)
        dialog.setFixedSize(750, 640)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Add header widget if provided (search input or label)
        focus_widget = None
        if header_widget:
            layout.addWidget(header_widget)
            focus_widget = header_widget

        # Connection list
        connection_list = QListWidget(self)
        layout.addWidget(connection_list)
        if not focus_widget:
            focus_widget = connection_list

        # Bottom button bar
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)

        show_main_btn = QPushButton(
            qta.icon("fa5s.window-restore", color=self.icon_color),
            self.tr("Show Main Window"),
            self,
        )
        show_main_btn.clicked.connect(
            lambda: (dialog.close(), self.show(), self.raise_(), self.activateWindow())
        )
        button_layout.addWidget(show_main_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Setup connection selection handler
        def on_connection_selected():
            if connection_list.currentItem():
                conn_id = connection_list.currentItem().data(Qt.ItemDataRole.UserRole)
                if conn_id:
                    dialog.close()
                    select_callback(conn_id)

        connection_list.itemDoubleClicked.connect(on_connection_selected)

        # Install event filter for keyboard navigation
        class KeyboardNavigationFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
                    if event.key() == Qt.Key.Key_Down:
                        if connection_list.count() > 0:
                            connection_list.setCurrentRow(
                                min(connection_list.currentRow() + 1, connection_list.count() - 1)
                            )
                        return True
                    elif event.key() == Qt.Key.Key_Up:
                        if connection_list.count() > 0:
                            connection_list.setCurrentRow(max(connection_list.currentRow() - 1, 0))
                        return True
                    elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        on_connection_selected()
                        return True
                return False

        # Keep reference to prevent garbage collection
        event_filter = KeyboardNavigationFilter()
        dialog._event_filter = event_filter
        if header_widget:
            header_widget.installEventFilter(event_filter)
        else:
            connection_list.installEventFilter(event_filter)

        # Connect search input to update list if it's a QLineEdit
        if has_search and header_widget:
            header_widget.textChanged.connect(
                lambda: populate_callback(connection_list, header_widget.text())
            )

        # Initial population
        populate_callback(connection_list, "")

        # Position dialog at top center of screen
        screen_geometry = self.screen().geometry()
        x = screen_geometry.left() + (screen_geometry.width() - 750) // 2
        y = screen_geometry.top() + 50
        dialog.setGeometry(x, y, 750, 640)

        dialog.show()
        if focus_widget:
            focus_widget.setFocus()

    def _show_quick_connect_dialog(self):
        """Show a quick connection search popup at the top center of the screen."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem

        # Create search input
        search_input = QLineEdit(self)
        search_input.setPlaceholderText(self.tr("Type to filter connections..."))

        def populate_quick_connect(list_widget, filter_text):
            """Populate list with filtered connections."""
            list_widget.clear()

            # Group connections by group name
            grouped_conns: dict[str, list[SSHConnection]] = {}
            for conn in self.connections:
                if not isinstance(conn, SSHConnection):
                    continue
                group_name = conn.group or self.tr("Default")
                if group_name not in grouped_conns:
                    grouped_conns[group_name] = []
                grouped_conns[group_name].append(conn)

            # Add items in sorted order
            for group_name in sorted(grouped_conns.keys()):
                for conn in sorted(grouped_conns[group_name], key=lambda c: c.name):
                    display_text = f"{conn.name} ({conn.user}@{conn.host}:{conn.port})"
                    if filter_text.lower() in display_text.lower():
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.ItemDataRole.UserRole, conn.id)
                        list_widget.addItem(item)

            # Auto-select first item
            if list_widget.count() > 0:
                list_widget.setCurrentRow(0)

        def on_select(conn_id):
            """Launch the selected connection."""
            for conn in self.connections:
                if isinstance(conn, SSHConnection) and conn.id == conn_id:
                    self._connect_with_connection(conn)
                    break

        # Create the dialog
        self._create_connection_popup_dialog(
            self.tr("SSHive - Quick Connect"),
            populate_quick_connect,
            on_select,
            has_search=True,
            header_widget=search_input,
        )

    def _show_recent_connections_menu(self):
        """Show a recent connections popup dialog."""
        import random
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel, QListWidgetItem

        # Create info label
        info_label = QLabel(self.tr("Your most recently used connections:"))

        def populate_recent(list_widget, _filter_text):
            """Populate list with recent connections."""
            list_widget.clear()

            # Handle incognito mode - show 3-6 fake recent connections
            if self.incognito_mode:
                # Use a deterministic seed based on the mode toggle to keep it consistent
                rng = random.Random(42)
                num_fake = rng.randint(3, 6)

                for i in range(num_fake):
                    fake_id = f"fake-recent-{i}"
                    name, host, user, _, _, port = self._get_fake_data(fake_id, service_index=i)

                    display_text = f"{name} ({user}@{host}:{port})"
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, fake_id)
                    list_widget.addItem(item)

                # Auto-select first item
                if list_widget.count() > 0:
                    list_widget.setCurrentRow(0)
                return

            if not self._setting_to_bool(self.settings.value("save_recent_history", "true"), True):
                item = QListWidgetItem(self.tr("History is disabled in Settings"))
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                list_widget.addItem(item)
                return

            recent_entries = self.storage.get_recent_connections(limit=10)

            if not recent_entries:
                item = QListWidgetItem(self.tr("No recent connections"))
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                list_widget.addItem(item)
                return

            for entry in recent_entries:
                display_name = entry["name"] or self.tr("Unnamed")
                details = self.tr("{}@{}:{}").format(entry["user"], entry["host"], entry["port"])
                display_text = f"{display_name} ({details})"

                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, entry["id"])

                # Check if connection still exists
                is_available = self._find_connection_by_id(entry["id"]) is not None
                if not is_available:
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    item.setToolTip(self.tr("Connection no longer exists."))

                list_widget.addItem(item)

            # Auto-select first available item
            for i in range(list_widget.count()):
                if list_widget.item(i).flags() & Qt.ItemFlag.ItemIsEnabled:
                    list_widget.setCurrentRow(i)
                    break

        def on_select(conn_id):
            """Launch the selected recent connection."""
            # In incognito mode, don't try to launch fake connections
            if not self.incognito_mode:
                self._connect_recent_by_id(conn_id)

        self._create_connection_popup_dialog(
            self.tr("SSHive - Recent Connections"),
            populate_recent,
            on_select,
            has_search=False,
            header_widget=info_label,
        )

    def _prompt_close_behavior(self) -> tuple[bool | None, bool]:
        """Ask user what to do when the window is closed for the first time.

        Returns:
            Tuple of (close_to_tray, remember_choice).
            close_to_tray is None when the dialog is cancelled.
        """
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Close Behavior"))
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText(self.tr("When closing SSHive, what should happen?"))
        msg.setInformativeText(self.tr("You can change this later in Settings."))

        tray_button = msg.addButton(self.tr("Close to Tray"), QMessageBox.ButtonRole.AcceptRole)
        quit_button = msg.addButton(self.tr("Quit App"), QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)

        remember_check = QCheckBox(self.tr("Remember my choice"), msg)
        remember_check.setChecked(True)
        msg.setCheckBox(remember_check)

        msg.exec()

        clicked = msg.clickedButton()
        if clicked == tray_button:
            return True, remember_check.isChecked()
        if clicked == quit_button:
            return False, remember_check.isChecked()
        return None, remember_check.isChecked()

    def _update_column_stretch(self):
        """Update the stretch mode of the last visible column."""
        header = self.tree.header()
        header.setStretchLastSection(False)

        last_visible = -1
        # Find the last visible logical column
        for i in range(header.count()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            if not self.tree.isColumnHidden(i):
                last_visible = i

        if last_visible >= 0:
            header.setSectionResizeMode(last_visible, QHeaderView.ResizeMode.Stretch)

    @staticmethod
    def _custom_icon_path(icon_value: str) -> Path | None:
        """Resolve a custom icon path if icon value points to a local file."""
        if not icon_value:
            return None

        candidate = Path(icon_value).expanduser()
        if candidate.exists() and candidate.is_file():
            return candidate
        return None

    def _custom_icons_dir(self) -> Path:
        """Return directory where persisted custom icons are stored."""
        return self.storage.config_file.parent / "custom_icons"

    def _cleanup_orphan_custom_icons(self):
        """Delete persisted custom icons no longer referenced by any connection."""
        icon_dir = self._custom_icons_dir()
        if not icon_dir.exists() or not icon_dir.is_dir():
            return

        referenced_files: set[Path] = set()
        for conn in self.storage.load_connections():
            if not conn.icon:
                continue
            icon_path = self._custom_icon_path(conn.icon)
            if not icon_path:
                continue
            try:
                resolved_path = icon_path.resolve()
                if resolved_path.parent == icon_dir.resolve():
                    referenced_files.add(resolved_path)
            except OSError:
                continue

        for candidate in icon_dir.iterdir():
            if not candidate.is_file():
                continue
            try:
                resolved_candidate = candidate.resolve()
                if resolved_candidate not in referenced_files:
                    candidate.unlink()
            except OSError:
                continue

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
        self.search_bar.setPlaceholderText(self.tr("Search connections..."))
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setFixedWidth(300)
        search_icon = qta.icon("fa5s.search", color=self.icon_color)
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        top_layout.addWidget(self.search_bar)

        top_layout.addStretch()

        # Update button (hidden by default)
        self.update_btn = QToolButton()
        self.update_btn.setText(self.tr("Update Available!"))
        self.update_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.update_btn.setToolTip(self.tr("A new version is available! Click to update."))

        self.update_icon_default = qta.icon("fa5s.arrow-alt-circle-up", color="#3498db")
        self.update_icon_hover = qta.icon("fa5s.arrow-alt-circle-up", color="white")
        self.update_btn.setIcon(self.update_icon_default)

        self.update_btn.setStyleSheet("""
            QToolButton {
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 4px 8px;
                color: #3498db;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #3498db;
                color: white;
            }
        """)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setVisible(False)
        self.update_btn.installEventFilter(self)
        top_layout.addWidget(self.update_btn)

        # Settings button (bars/burger) - Now a menu
        settings_icon = qta.icon("fa5s.bars", color=self.icon_color)
        self.settings_btn = QToolButton()
        self.settings_btn.setIcon(settings_icon)
        self.settings_btn.setToolTip(self.tr("Options"))
        self.settings_btn.setStyleSheet("border: none; padding: 4px;")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.settings_menu = QMenu(self)

        # Check for Updates action
        check_updates_icon = qta.icon("fa5s.arrow-alt-circle-up", color=self.icon_color)
        self.check_updates_action = QAction(check_updates_icon, self.tr("Check for Updates"), self)
        self.check_updates_action.setToolTip(self.tr("Check for new SSHive updates."))
        self.check_updates_action.triggered.connect(
            lambda: self.updater.check_for_updates(force=True)
        )
        self.settings_menu.addAction(self.check_updates_action)

        self.recent_menu = self.settings_menu.addMenu(self.tr("Recent Connections"))
        self.recent_menu.aboutToShow.connect(self._refresh_recent_connections_menu)

        self.clear_recent_action = QAction(self.tr("Clear Recent History"), self)
        self.clear_recent_action.triggered.connect(self._clear_recent_connections_history)

        self.settings_menu.addSeparator()

        # Export/Import submenu
        backup_menu = self.settings_menu.addMenu(self.tr("Backup and Restore"))

        export_icon = qta.icon("fa5s.file-export", color=self.icon_color)
        export_action = QAction(export_icon, self.tr("Export Connections"), self)
        export_action.setToolTip(self.tr("Save connections to a file."))
        export_action.triggered.connect(self._export_connections)
        backup_menu.addAction(export_action)

        import_icon = qta.icon("fa5s.file-import", color=self.icon_color)
        import_action = QAction(import_icon, self.tr("Import Connections"), self)
        import_action.setToolTip(self.tr("Load connections from a file."))
        import_action.triggered.connect(self._import_connections)
        backup_menu.addAction(import_action)

        putty_icon = qta.icon("fa5s.download", color=self.icon_color)
        putty_action = QAction(putty_icon, self.tr("Import from PuTTY/KiTTY"), self)
        putty_action.setToolTip(self.tr("Import sessions from PuTTY or KiTTY configuration files."))
        putty_action.triggered.connect(self._import_putty_sessions)
        backup_menu.addAction(putty_action)

        backup_menu.addSeparator()

        open_folder_icon = qta.icon("fa5s.folder-open", color=self.icon_color)
        open_folder_action = QAction(open_folder_icon, self.tr("Open Config Folder"), self)
        open_folder_action.setToolTip(self.tr("Open config folder in file manager."))
        open_folder_action.triggered.connect(self._open_config_folder)
        backup_menu.addAction(open_folder_action)

        self.settings_menu.addSeparator()

        # Settings action
        settings_icon = qta.icon("fa5s.cog", color=self.icon_color)
        settings_action = QAction(settings_icon, self.tr("Settings"), self)
        settings_action.setToolTip(self.tr("Configure SSHive settings."))
        settings_action.triggered.connect(self._show_settings_dialog)
        self.settings_menu.addAction(settings_action)

        # About action
        about_icon = qta.icon("fa5s.info-circle", color=self.icon_color)
        about_action = QAction(about_icon, self.tr("About"), self)
        about_action.setToolTip(self.tr("About SSHive."))
        about_action.triggered.connect(self._show_about_dialog)
        self.settings_menu.addAction(about_action)

        self.settings_menu.addSeparator()

        # Quit action
        quit_icon = qta.icon("fa5s.times", color=self.icon_color)
        quit_action = QAction(quit_icon, self.tr("Quit"), self)
        quit_action.setToolTip(self.tr("Exit SSHive."))
        quit_action.triggered.connect(QApplication.quit)
        self.settings_menu.addAction(quit_action)

        self.settings_btn.setMenu(self.settings_menu)

        top_layout.addWidget(self.settings_btn)
        layout.addLayout(top_layout)

        # Icons for later use
        add_icon = qta.icon("fa5s.plus", color=self.icon_color)

        # Connection tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            [self.tr("Name"), self.tr("Host"), self.tr("User"), self.tr("Port")]
        )
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 150)
        self.tree.setAlternatingRowColors(False)
        self.tree.setAllColumnsShowFocus(True)
        self.tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(20)
        self.tree.setMouseTracking(True)
        self.tree.itemEntered.connect(self._on_item_entered)
        self.tree.itemClicked.connect(self._on_item_clicked)
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

        self.add_btn = QPushButton(self.tr("Add Connection"))
        self.add_btn.setIcon(add_icon)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_connection)
        button_layout.addWidget(self.add_btn)

        clone_icon = qta.icon("fa5s.clone", color=self.icon_color)
        self.clone_btn = QPushButton(self.tr("Clone"))
        self.clone_btn.setIcon(clone_icon)
        self.clone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clone_btn.clicked.connect(self._clone_connection)
        self.clone_btn.setEnabled(False)
        button_layout.addWidget(self.clone_btn)

        edit_icon = qta.icon("fa5s.edit", color=self.icon_color)
        self.edit_btn = QPushButton(self.tr("Edit"))
        self.edit_btn.setIcon(edit_icon)
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(lambda: self._edit_connection())
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)

        delete_icon = qta.icon("fa5s.trash", color=self.icon_color)
        self.delete_btn = QPushButton(self.tr("Delete"))
        self.delete_btn.setIcon(delete_icon)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._delete_connection)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        test_icon = qta.icon("fa5s.flask", color=self.icon_color)
        self.test_btn = QPushButton(self.tr("Test"))
        self.test_btn.setIcon(test_icon)
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(lambda: self._test_connection(None))
        self.test_btn.setEnabled(False)
        button_layout.addWidget(self.test_btn)

        connect_icon = qta.icon("fa5s.rocket", color=self.icon_color)
        self.connect_btn = QPushButton(self.tr("Connect"))
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
        self.incognito_action = QAction(self.tr("Toggle Incognito Mode"), self)
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

    INCOGNITO_VERSION = 4

    INCOGNITO_SERVICES = [
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
        ("Sonarr", "Downloads/Arr", "sonarr"),
        ("Radarr", "Downloads/Arr", "radarr"),
        ("Prowlarr", "Downloads/Arr", "prowlarr"),
        ("Overseerr", "Downloads/Arr", "overseerr"),
        ("Bazarr", "Downloads/Arr", "bazarr"),
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
        ("Gitea", "Web", "gitea"),
        ("Wiki.js", "Web", "wikijs"),
        ("Heimdall", "Web", "heimdall"),
        ("Flame", "Web", "flame"),
        ("Organizr", "Web", "organizr"),
    ]

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

        # Fallback: generate deterministically from full service catalog
        fake_conns = []
        used_identities = set()

        for i, (_, _, icon_name) in enumerate(self.INCOGNITO_SERVICES):
            fake_id = f"incognito-{icon_name}-{i}"

            # Ensure we cycle through services correctly
            name, host, user, group, icon, _ = self._get_fake_data(fake_id, service_index=i)

            # Handle potential identity collisions
            counter = 1
            while (name, host) in used_identities and counter < 10:
                name, host, user, group, icon, _ = self._get_fake_data(
                    f"{fake_id}-{counter}", service_index=i + counter
                )
                counter += 1

            used_identities.add((name, host))

            # Use deterministic port
            _, _, _, _, _, fake_port = self._get_fake_data(fake_id, service_index=i)

            fake_conn = SSHConnection(
                name=name,
                host=host,
                user=user,
                port=fake_port,
                group=group,
                icon=icon,
                id=fake_id,
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

        users = ["admin", "root", "pi", "user", "manager", "maintainer", "sysop", "dev"]

        # Use service_index if provided to ensure distribution, otherwise fallback to seed
        idx = service_index if service_index is not None else seed
        service_info = self.INCOGNITO_SERVICES[idx % len(self.INCOGNITO_SERVICES)]

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
        """Handle window close event to save settings and support tray mode."""
        self._save_settings()

        if self.tray_icon and not self._is_quitting:
            close_pref = self.settings.value("close_to_tray")
            close_to_tray: bool | None

            if close_pref is None:
                # Skip prompt in test mode; default to close-to-tray
                if self._is_test_mode():
                    close_to_tray = True
                else:
                    close_to_tray, remember_choice = self._prompt_close_behavior()

                    if close_to_tray is None:
                        event.ignore()
                        return

                    if remember_choice:
                        self.settings.setValue("close_to_tray", str(close_to_tray).lower())
            else:
                close_to_tray = self._setting_to_bool(close_pref, default=True)

            if close_to_tray:
                event.ignore()
                self.hide()
                self._update_tray_toggle_action()
                self._show_first_tray_close_hint()
                return

            self._is_quitting = True
            self.tray_icon.hide()
            event.accept()
            QApplication.quit()
            return

        if self.tray_icon:
            self.tray_icon.hide()

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

    def _find_connection_by_id(self, connection_id: str) -> SSHConnection | None:
        """Find a loaded connection by ID."""
        for connection in self.connections:
            if connection.id == connection_id:
                return connection
        return None

    def _refresh_recent_connections_menu(self):
        """Rebuild the recent connections submenu from persisted history."""
        self.recent_menu.clear()

        if not self._setting_to_bool(self.settings.value("save_recent_history", "true"), True):
            disabled_action = self.recent_menu.addAction(self.tr("History is disabled in Settings"))
            disabled_action.setEnabled(False)
            return

        recent_entries = self.storage.get_recent_connections(limit=10)

        if not recent_entries:
            empty_action = self.recent_menu.addAction(self.tr("No recent connections"))
            empty_action.setEnabled(False)
            self.recent_menu.addSeparator()
            self.clear_recent_action.setEnabled(False)
            self.recent_menu.addAction(self.clear_recent_action)
            return

        for entry in recent_entries:
            display_name = entry["name"] or self.tr("Unnamed")
            details = self.tr("{}@{}:{}").format(entry["user"], entry["host"], entry["port"])
            action = self.recent_menu.addAction(f"{display_name} ({details})")

            is_available = self._find_connection_by_id(entry["id"]) is not None
            action.setEnabled(is_available)
            if not is_available:
                action.setToolTip(self.tr("Connection no longer exists."))
                continue

            action.triggered.connect(
                lambda _checked=False, connection_id=entry["id"]: self._connect_recent_by_id(
                    connection_id
                )
            )

        self.recent_menu.addSeparator()
        self.clear_recent_action.setEnabled(True)
        self.recent_menu.addAction(self.clear_recent_action)

    def _clear_recent_connections_history(self):
        """Clear persisted recent connection history after confirmation."""
        reply = QMessageBox.question(
            self,
            self.tr("Clear Recent History"),
            self.tr("Clear all recent connection history?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.storage.clear_recent_connections()
        self._refresh_recent_connections_menu()

    def _connect_recent_by_id(self, connection_id: str):
        """Connect to a recent connection by its ID."""
        connection = self._find_connection_by_id(connection_id)
        if connection is None:
            QMessageBox.warning(
                self,
                self.tr("Connection Not Found"),
                self.tr("The selected connection no longer exists."),
            )
            self._refresh_recent_connections_menu()
            return

        self._connect_with_connection(connection)

    def _populate_tree(self):
        """Populate tree widget with connections grouped by category."""
        self.tree.clear()

        # Group connections by group name
        grouped_conns: dict[str, list[SSHConnection]] = {}
        for conn in self.connections:
            group_name = conn.group or self.tr("Default")
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
                    custom_icon_path = self._custom_icon_path(conn.icon)
                    if custom_icon_path:
                        conn_item.setIcon(0, QIcon(str(custom_icon_path)))
                    else:
                        icon = self.icon_manager.get_icon(conn.icon)
                        if icon:
                            conn_item.setIcon(0, icon)
                        else:
                            conn_item.setIcon(0, server_icon)
                else:
                    conn_item.setIcon(0, server_icon)

                conn_item.setData(0, Qt.ItemDataRole.UserRole, conn)
                if self.incognito_mode:
                    conn_item.setToolTip(0, self.tr("Incognito mode active"))
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
            self.test_btn.setEnabled(False)
            self.connect_btn.setEnabled(False)
            return

        item = selected_items[0]
        connection = item.data(0, Qt.ItemDataRole.UserRole)

        # Enable buttons only if a connection is selected (not a group)
        is_connection = connection is not None
        self.clone_btn.setEnabled(is_connection)
        self.edit_btn.setEnabled(is_connection)
        self.delete_btn.setEnabled(is_connection)
        self.test_btn.setEnabled(is_connection)
        self.connect_btn.setEnabled(is_connection)

    def _test_connection(self, item: QTreeWidgetItem | None = None):
        """Run full connection test (preflight + network + auth) for selected connection."""
        if not item:
            selected_items = self.tree.selectedItems()
            if not selected_items:
                return
            item = selected_items[0]

        connection = item.data(0, Qt.ItemDataRole.UserRole)
        if not connection:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            QApplication.processEvents()
            success, message = SSHLauncher.test_full_connection(connection)
        finally:
            QApplication.restoreOverrideCursor()

        if success:
            title = self.tr("Connection Test")
        else:
            title = self.tr("Connection Test Failed")

        if self.settings.value("connection_test_debug", "false") in ["true", True]:
            debug_log = SSHLauncher.collect_ssh_debug_log(connection)
            show_connection_test_debug_dialog(self, title, connection, message, debug_log)
            return

        if success:
            QMessageBox.information(
                self, title, self.tr("{}\n\n{}").format(connection.name, message)
            )
        else:
            QMessageBox.warning(self, title, self.tr("{}\n\n{}").format(connection.name, message))

    def _add_connection(self):
        """Show add connection dialog."""
        dialog = AddConnectionDialog(self, existing_groups=self.storage.get_groups())

        if dialog.exec():
            connection = dialog.get_connection()
            if connection:
                self.storage.add_connection(connection)
                self._cleanup_orphan_custom_icons()
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
                self._cleanup_orphan_custom_icons()
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
                self._cleanup_orphan_custom_icons()
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
            self.tr("Confirm Delete"),
            self.tr("Are you sure you want to delete '{}'?").format(connection.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.storage.delete_connection(connection.id)
            self._cleanup_orphan_custom_icons()
            self._load_connections()

    def _connect_to_selected_server(self):
        """Launch SSH connection for the currently selected server."""
        self._connect_to_server(None)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Toggle expansion when a group item is clicked.

        Args:
            item: Clicked item
            column: Clicked column index
        """
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())

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

        self._connect_with_connection(connection)

    def _connect_with_connection(self, connection: SSHConnection):
        """Launch SSH connection for a specific connection object."""

        # Test connection validity (dependency/path checks)
        success, error_msg = SSHLauncher.test_connection(connection)
        if not success:
            QMessageBox.warning(
                self,
                self.tr("Connection Error"),
                self.tr("Cannot connect to '{}'.\n\n{}'").format(connection.name, error_msg),
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
                        self.tr("Authentication Failed"),
                        self.tr("Failed to authenticate for {}.\n\n{}'").format(
                            connection.name, auth_error
                        ),
                    )
                    return
            finally:
                QApplication.restoreOverrideCursor()

        # Launch connection (shell or tunnel)
        if connection.connection_type == "tunnel":
            # Launch tunnel in background
            success, error = SSHLauncher.launch_tunnel(connection)
            if not success:
                QMessageBox.warning(
                    self,
                    self.tr("Tunnel Error"),
                    self.tr("Failed to launch tunnel for {}.\n\n{}").format(connection.name, error),
                )
                return

            # Show success message with tunnel details
            tunnel_info = "\n".join(
                [
                    f"• {pf.name}: "
                    + (
                        f"localhost:{pf.local_port} → {pf.remote_bind_address}:{pf.remote_port}"
                        if pf.forward_type == "local"
                        else f"{pf.remote_port} ← localhost:{pf.local_port}"
                        if pf.forward_type == "remote"
                        else f"SOCKS localhost:{pf.local_port}"
                    )
                    for pf in connection.port_forwards
                ]
            )
            QMessageBox.information(
                self,
                self.tr("Tunnel Started"),
                self.tr("Tunnel for {} is now running in the background.\n\n{}").format(
                    connection.name, tunnel_info
                ),
            )
        else:
            # Launch terminal shell connection
            success = SSHLauncher.launch(connection)

            if not success:
                QMessageBox.warning(
                    self,
                    self.tr("Launch Error"),
                    self.tr(
                        "Failed to launch terminal for {}.\n\n"
                        "Check that you have a terminal emulator installed."
                    ).format(connection.name),
                )
                return

        if self._setting_to_bool(self.settings.value("save_recent_history", "true"), True):
            self.storage.record_connection_used(connection)

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

        connect_action = menu.addAction(
            qta.icon("fa5s.rocket", color=self.icon_color), self.tr("Connect")
        )
        connect_action.triggered.connect(lambda: self._connect_to_server(item))

        test_action = menu.addAction(
            qta.icon("fa5s.flask", color=self.icon_color), self.tr("Test Connection")
        )
        test_action.triggered.connect(lambda: self._test_connection(item))

        menu.addSeparator()

        clone_action = menu.addAction(
            qta.icon("fa5s.clone", color=self.icon_color), self.tr("Clone")
        )
        clone_action.triggered.connect(lambda: self._clone_connection(item))

        edit_action = menu.addAction(qta.icon("fa5s.edit", color=self.icon_color), self.tr("Edit"))
        edit_action.triggered.connect(lambda: self._edit_connection(item))

        delete_action = menu.addAction(
            qta.icon("fa5s.trash", color=self.icon_color), self.tr("Delete")
        )
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
        hide_action = menu.addAction(self.tr("Hide {}").format(column_name))
        hide_action.triggered.connect(lambda: self._hide_column(column))

        menu.exec(self.tree.header().mapToGlobal(position))

    def _hide_column(self, column: int):
        """Hide a column and update stretch behavior."""
        self.tree.setColumnHidden(column, True)
        self._update_column_stretch()
        self.settings.setValue("columnState", self.tree.header().saveState())

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
            previous_save_recent_history = self._setting_to_bool(
                self.settings.value("save_recent_history", "true"), True
            )

            # Update verification setting
            self.settings.setValue(
                "verify_credentials", str(settings["verify_credentials"]).lower()
            )

            # Update updater setting
            self.settings.setValue(
                "check_updates_startup", str(settings["check_updates_startup"]).lower()
            )

            # Update connection test debug setting
            self.settings.setValue(
                "connection_test_debug", str(settings["connection_test_debug"]).lower()
            )

            # Update close behavior setting
            self.settings.setValue("close_to_tray", str(settings["close_to_tray"]).lower())

            # Update recent history persistence setting
            self.settings.setValue(
                "save_recent_history", str(settings["save_recent_history"]).lower()
            )

            # Update automatic backups setting
            self.settings.setValue("max_backups", int(settings["max_backups"]))
            self.storage.max_backups = settings["max_backups"]

            if previous_save_recent_history and not settings["save_recent_history"]:
                has_recent_history = bool(self.storage.get_recent_connections(limit=1))
                if has_recent_history:
                    clear_reply = QMessageBox.question(
                        self,
                        self.tr("Clear Recent History"),
                        self.tr("Recent connection history exists. Do you want to clear it now?"),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if clear_reply == QMessageBox.StandardButton.Yes:
                        self.storage.clear_recent_connections()

            # Update column visibility
            for idx, visible in settings["column_visibility"].items():
                self.tree.setColumnHidden(idx, not visible)

            # Save theme preference and apply
            theme_val = settings.get("theme_preference", "System")
            self.settings.setValue("theme_preference", theme_val)
            self._apply_theme()

            # Save language preference (takes effect on next launch)
            lang_val = settings.get("language", "system")
            self.settings.setValue("language", lang_val)

            self._update_column_stretch()

            # Save column state
            self.settings.setValue("columnState", self.tree.header().saveState())

    def _apply_theme(self):
        """Apply the theme based on user settings and update icons appropriately."""
        theme_val = self.settings.value("theme_preference", "System")

        if theme_val == "Dark":
            ThemeManager.apply_dark_theme(QApplication.instance())
            self.icon_color = "white"
        elif theme_val == "Light":
            ThemeManager.apply_light_theme(QApplication.instance())
            self.icon_color = "black"
        else:  # System or fallback
            ThemeManager.apply_theme(QApplication.instance())
            self.icon_color = "white" if ThemeManager.is_system_dark_mode() else "black"

        # Update icons in UI if they already exist
        if hasattr(self, "search_bar"):
            search_action = self.search_bar.actions()[0]
            search_action.setIcon(qta.icon("fa5s.search", color=self.icon_color))

            self.settings_btn.setIcon(qta.icon("fa5s.bars", color=self.icon_color))
            self.add_btn.setIcon(qta.icon("fa5s.plus", color=self.icon_color))
            self.clone_btn.setIcon(qta.icon("fa5s.clone", color=self.icon_color))
            self.edit_btn.setIcon(qta.icon("fa5s.edit", color=self.icon_color))
            self.delete_btn.setIcon(qta.icon("fa5s.trash", color=self.icon_color))
            self.connect_btn.setIcon(qta.icon("fa5s.rocket", color=self.icon_color))

            # Repopulate tree to refresh folder/server icons
            self._populate_tree()

    def _on_update_available(self, version, url, notes):
        """Handle update available signal."""
        self.check_updates_action.setText(self.tr("Update Available! ({})").format(version))
        # Ensure it's prominent or we can just keep it in menu
        # Maybe show the dialog automatically if it's the first time?
        # For now, just updating the menu item is what was implied.

        # Reconnect triggered to show dialog instead of checking again
        try:
            self.check_updates_action.triggered.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.check_updates_action.triggered.connect(
            lambda: self._show_update_dialog(version, url, notes)
        )

    def _export_connections(self) -> None:
        """Export connections to user-chosen location."""
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Connections"),
            str(downloads_dir / "connections-backup.json"),
            self.tr("JSON Files (*.json);;All Files (*)"),
        )

        if not path:
            return

        if self.storage.export_connections(Path(path)):
            QMessageBox.information(
                self,
                self.tr("Export Successful"),
                self.tr("Connections exported to:") + f"\n{path}",
            )
        else:
            QMessageBox.warning(
                self,
                self.tr("Export Failed"),
                self.tr("Failed to export connections. Please check permissions."),
            )

    def _import_connections(self) -> None:
        """Import connections from a file."""
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Import Connections"),
            str(downloads_dir),
            self.tr("JSON Files (*.json);;All Files (*)"),
        )

        if not path:
            return

        # Ask user if they want to merge or replace
        reply = QMessageBox.question(
            self,
            self.tr("Import Mode"),
            self.tr(
                "Do you want to merge with existing connections?\n\nYes = Merge\nNo = Replace all"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        merge = reply == QMessageBox.StandardButton.Yes

        if self.storage.import_connections(Path(path), merge=merge):
            self.load_connections()
            if merge:
                msg = self.tr(
                    "Connections imported (merged).\nChanges will be saved automatically."
                )
            else:
                msg = self.tr(
                    "Connections imported (replaced).\nChanges will be saved automatically."
                )
            QMessageBox.information(self, self.tr("Import Successful"), msg)
        else:
            QMessageBox.warning(
                self,
                self.tr("Import Failed"),
                self.tr(
                    "Failed to import connections. Please ensure the file is a valid SSHive backup."
                ),
            )

    def _import_putty_sessions(self) -> None:
        """Import sessions from PuTTY or KiTTY configuration files or directory."""
        home_dir = Path.home()
        putty_dir = home_dir / ".putty"

        # Ask how user wants to select source
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Select Import Source"))
        msg.setText(self.tr("How would you like to import PuTTY sessions?"))
        msg.setStandardButtons(QMessageBox.StandardButton.NoButton)

        select_files = msg.addButton(self.tr("Select Files"), QMessageBox.ButtonRole.ActionRole)
        browse_folder = msg.addButton(self.tr("Browse Folder"), QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton(QMessageBox.StandardButton.Cancel)
        select_files.setIcon(qta.icon("fa5s.file", color=self.icon_color))
        browse_folder.setIcon(qta.icon("fa5s.folder-open", color=self.icon_color))
        msg.setDefaultButton(cancel_btn)

        msg.exec()
        clicked = msg.clickedButton()

        paths = []
        if clicked == select_files:
            # File selection for .reg, .ini files
            config_dir = putty_dir
            if not config_dir.exists():
                config_dir = home_dir / ".config" / "KiTTY"
            if not config_dir.exists():
                config_dir = home_dir / ".config"
            if not config_dir.exists():
                config_dir = home_dir

            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                self.tr("Select PuTTY/KiTTY Configuration Files"),
                str(config_dir),
                self.tr(
                    "All Files (*);;Registry Exports (*.reg);;INI Files (*.ini);;Config Files (*.conf)"
                ),
            )
            paths = file_paths
        elif clicked == browse_folder:
            # Directory selection for sessions directory
            dir_path = QFileDialog.getExistingDirectory(
                self,
                self.tr("Select PuTTY Sessions Directory"),
                str(putty_dir if putty_dir.exists() else home_dir),
                QFileDialog.Option.ShowDirsOnly,
            )
            if dir_path:
                paths = [dir_path]
        else:
            # Cancel was clicked or X was pressed
            return

        if not paths:
            return

        # Ask user how to handle existing connections
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Import Mode"))
        msg.setText(self.tr("How should these sessions be added?"))
        msg.setStandardButtons(QMessageBox.StandardButton.NoButton)

        add_new = msg.addButton(self.tr("Add to Existing"), QMessageBox.ButtonRole.ActionRole)
        replace_all = msg.addButton(self.tr("Replace All"), QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton(QMessageBox.StandardButton.Cancel)
        add_new.setIcon(qta.icon("fa5s.plus", color=self.icon_color))
        replace_all.setIcon(qta.icon("fa5s.exclamation-triangle", color="#f0ad4e"))
        msg.setDefaultButton(cancel_btn)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == add_new:
            merge = True
        elif clicked == replace_all:
            confirm = QMessageBox.warning(
                self,
                self.tr("Confirm Replace All"),
                self.tr(
                    "This will remove ALL existing saved connections.\n\n"
                    "After this action, only the imported PuTTY/KiTTY entries will remain.\n\n"
                    "Do you want to continue?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            merge = False
        else:
            # Cancel was clicked or X was pressed - ALWAYS cancel, never default to replace
            return

        success, count = self.storage.import_putty_connections(
            [Path(p) for p in paths], merge=merge
        )

        if success and count > 0:
            self._load_connections()
            if merge:
                msg = self.tr(
                    "Successfully imported {} sessions from PuTTY/KiTTY.\n"
                    "All sessions have been added to the 'Imported from PuTTY' group.\n"
                    "Changes will be saved automatically."
                ).format(count)
            else:
                msg = self.tr(
                    "Successfully imported {} sessions from PuTTY/KiTTY (replaced all existing).\n"
                    "All sessions have been added to the 'Imported from PuTTY' group.\n"
                    "Changes will be saved automatically."
                ).format(count)
            QMessageBox.information(
                self,
                self.tr("Import Successful"),
                msg,
            )
        elif count == 0:
            QMessageBox.warning(
                self,
                self.tr("Import Failed"),
                self.tr(
                    "No valid sessions found in the selected file(s).\n\n"
                    "Supported formats:\n"
                    "- PuTTY registry export (.reg)\n"
                    "- PuTTY portable (putty.ini)\n"
                    "- KiTTY portable (kitty.ini)"
                ),
            )
        else:
            QMessageBox.warning(
                self,
                self.tr("Import Failed"),
                self.tr("Failed to import from PuTTY/KiTTY. Please check the file format."),
            )

    def _open_config_folder(self) -> None:
        """Open config folder in the system file manager."""
        config_dir = self.storage.config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        try:
            if os.name == "nt":  # Windows
                os.startfile(config_dir)  # type: ignore
            elif os.name == "posix":  # Linux/macOS
                # Try xdg-open first (Linux), then open (macOS)
                try:
                    subprocess.Popen(["xdg-open", str(config_dir)])
                except FileNotFoundError:
                    subprocess.Popen(["open", str(config_dir)])
        except (OSError, subprocess.SubprocessError) as e:
            print(f"Error opening folder: {e}")
            QMessageBox.warning(
                self,
                self.tr("Could Not Open Folder"),
                self.tr("Failed to open config folder.") + f"\nPath: {config_dir}",
            )

    def eventFilter(self, obj, event):
        """Swap update button icon on hover for visibility against blue background."""
        if obj is self.update_btn:
            if event.type() == event.Type.Enter:
                self.update_btn.setIcon(self.update_icon_hover)
            elif event.type() == event.Type.Leave:
                self.update_btn.setIcon(self.update_icon_default)
        return super().eventFilter(obj, event)

    def _show_update_dialog(self, version, url, notes):
        """Show the update information dialog."""
        dialog = UpdateDialog(version, notes, url, self.updater, self)
        dialog.exec()

    def _show_about_dialog(self):
        """Show the about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
