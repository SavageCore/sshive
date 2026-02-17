"""Main application window."""

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sshive.models.connection import SSHConnection
from sshive.models.storage import ConnectionStorage
from sshive.ssh.launcher import SSHLauncher
from sshive.ui.add_dialog import AddConnectionDialog
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

        self._setup_ui()
        self._load_connections()

        self.setWindowTitle("SSHive - SSH Connection Manager")
        self.resize(800, 600)

    def _setup_ui(self):
        """Setup the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Add connection action
        add_icon = qta.icon("fa5s.plus", color=self.icon_color)

        add_action = QAction(add_icon, "Add Connection", self)
        add_action.triggered.connect(self._add_connection)
        toolbar.addAction(add_action)

        toolbar.addSeparator()

        # Refresh action
        refresh_icon = qta.icon("fa5s.sync-alt", color=self.icon_color)
        refresh_action = QAction(refresh_icon, "Refresh", self)
        refresh_action.triggered.connect(self._load_connections)
        toolbar.addAction(refresh_action)

        # Connection tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Host", "User", "Port"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 150)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._connect_to_server)

        layout.addWidget(self.tree)

        # Bottom buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Connection")
        self.add_btn.setIcon(add_icon)
        self.add_btn.clicked.connect(self._add_connection)
        button_layout.addWidget(self.add_btn)

        edit_icon = qta.icon("fa5s.edit", color=self.icon_color)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setIcon(edit_icon)
        self.edit_btn.clicked.connect(self._edit_connection)
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)

        delete_icon = qta.icon("fa5s.trash", color=self.icon_color)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setIcon(delete_icon)
        self.delete_btn.clicked.connect(self._delete_connection)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        connect_icon = qta.icon("fa5s.rocket", color=self.icon_color)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setIcon(connect_icon)
        self.connect_btn.clicked.connect(lambda: self._connect_to_server(None))
        self.connect_btn.setEnabled(False)
        self.connect_btn.setDefault(True)
        button_layout.addWidget(self.connect_btn)

        layout.addLayout(button_layout)

        # Connect selection change
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_connections(self):
        """Load connections from storage and populate tree."""
        self.connections = self.storage.load_connections()
        self._populate_tree()

    def _populate_tree(self):
        """Populate tree widget with connections grouped by category."""
        self.tree.clear()

        # Group connections by group name
        groups: dict[str, list[SSHConnection]] = {}
        for conn in self.connections:
            group_name = conn.group or "Default"
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(conn)

        # Define icons for tree
        folder_icon = qta.icon("fa5s.folder", color=self.icon_color)

        # Create tree structure
        for group_name in sorted(groups.keys()):
            # Group item
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, f"{group_name}")
            group_item.setIcon(0, folder_icon)
            group_item.setExpanded(True)
            group_item.setData(0, Qt.ItemDataRole.UserRole, None)  # No connection data

            # Add connections to group
            for conn in sorted(groups[group_name], key=lambda c: c.name):
                conn_item = QTreeWidgetItem(group_item)
                conn_item.setText(0, conn.name)
                conn_item.setText(1, conn.host)
                conn_item.setText(2, conn.user)
                conn_item.setText(3, str(conn.port))
                conn_item.setData(0, Qt.ItemDataRole.UserRole, conn)

                # Add tooltip
                conn_item.setToolTip(0, str(conn))

    def _on_selection_changed(self):
        """Handle tree selection changes."""
        selected_items = self.tree.selectedItems()

        if not selected_items:
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.connect_btn.setEnabled(False)
            return

        item = selected_items[0]
        connection = item.data(0, Qt.ItemDataRole.UserRole)

        # Enable buttons only if a connection is selected (not a group)
        is_connection = connection is not None
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

    def _edit_connection(self):
        """Show edit connection dialog for selected connection."""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        connection = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
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

    def _delete_connection(self):
        """Delete selected connection after confirmation."""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        connection = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
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

        # Test connection validity
        if not SSHLauncher.test_connection(connection):
            QMessageBox.warning(
                self,
                "Connection Error",
                f"Cannot connect to {connection.name}.\n\n"
                f"Possible issues:\n"
                f"• SSH command not found\n"
                f"• SSH key file doesn't exist: {connection.key_path or 'N/A'}",
            )
            return

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

        edit_action = menu.addAction(qta.icon("fa5s.edit", color=self.icon_color), "Edit")
        edit_action.triggered.connect(self._edit_connection)

        delete_action = menu.addAction(qta.icon("fa5s.trash", color=self.icon_color), "Delete")
        delete_action.triggered.connect(self._delete_connection)

        menu.exec(self.tree.viewport().mapToGlobal(position))
