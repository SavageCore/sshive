"""Dialog for adding and editing SSH connections."""

from pathlib import Path

import qtawesome as qta
from nanoid import generate
from PySide6.QtCore import QStandardPaths, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
)

from sshive.models.connection import PortForward, SSHConnection
from sshive.ssh.launcher import SSHLauncher
from sshive.ui.icon_manager import IconManager
from sshive.ui.theme import ThemeManager
from sshive.ui.utils import show_connection_test_debug_dialog


class PortForwardDialog(QDialog):
    """Dialog for adding or editing a single port forward rule."""

    def __init__(
        self,
        parent=None,
        port_forward: PortForward | None = None,
    ):
        """Initialize port forward dialog.

        Args:
            parent: Parent widget
            port_forward: Existing port forward to edit (None for new)
        """
        super().__init__(parent)
        self.port_forward = port_forward

        self.setWindowTitle(
            self.tr("Edit Port Forward") if port_forward else self.tr("Add Port Forward")
        )
        self.setMinimumWidth(500)
        self._setup_ui()

        if port_forward:
            self._populate_fields()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()

        form_layout = QFormLayout()

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.tr("e.g., Database, Redis, SOCKS Proxy"))
        form_layout.addRow(self.tr("Name:"), self.name_input)

        # Forward Type with icons and hints
        type_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(
            [
                self.tr("Local Forward (-L)"),
                self.tr("Remote Forward (-R)"),
                self.tr("Dynamic Proxy (-D)"),
            ]
        )
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)

        # Add help icon
        self.type_help_btn = QToolButton()
        self.type_help_btn.setIcon(qta.icon("fa5s.question", color="steelblue"))
        self.type_help_btn.setToolTip(
            self.tr(
                "<b>Local (-L):</b> Access remote service locally<br>"
                "localhost:8000 → database.internal:5432<br><br>"
                "<b>Remote (-R):</b> Share your local service<br>"
                "9000 ← localhost:8000<br><br>"
                "<b>Dynamic (-D):</b> SOCKS proxy for all traffic<br>"
                "localhost:1080 (proxy)"
            )
        )
        self.type_help_btn.setStyleSheet("border: none; padding: 4px;")
        self.type_help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        type_layout.addWidget(self.type_help_btn)
        form_layout.addRow(self.tr("Type:"), type_layout)

        # Hint label that changes based on type
        self.hint_label = QLabel()
        self.hint_label.setStyleSheet("color: steelblue; font-style: italic; font-size: 10px;")
        self.hint_label.setWordWrap(True)
        form_layout.addRow(self.hint_label)

        # Local Port
        self.local_port_input = QSpinBox()
        self.local_port_input.setRange(1, 65535)
        self.local_port_input.setValue(8000)
        local_port_layout = QHBoxLayout()
        local_port_layout.addWidget(self.local_port_input)
        self.local_port_info = QLabel()
        self.local_port_info.setStyleSheet("color: gray; font-size: 9px;")
        local_port_layout.addWidget(self.local_port_info)
        form_layout.addRow(self.tr("Local Port:"), local_port_layout)

        # Remote Port (hidden for dynamic)
        self.remote_port_label = QLabel(self.tr("Remote Port:"))
        self.remote_port_input = QSpinBox()
        self.remote_port_input.setRange(1, 65535)
        self.remote_port_input.setValue(8000)
        remote_port_layout = QHBoxLayout()
        remote_port_layout.addWidget(self.remote_port_input)
        self.remote_port_info = QLabel()
        self.remote_port_info.setStyleSheet("color: gray; font-size: 9px;")
        remote_port_layout.addWidget(self.remote_port_info)
        form_layout.addRow(self.remote_port_label, remote_port_layout)

        # Remote Bind Address
        self.remote_bind_label = QLabel(self.tr("Remote Address:"))
        self.remote_bind_input = QLineEdit()
        self.remote_bind_input.setPlaceholderText(self.tr("e.g., localhost or db.internal"))
        self.remote_bind_input.setText("localhost")
        remote_bind_layout = QHBoxLayout()
        remote_bind_layout.addWidget(self.remote_bind_input)
        self.remote_bind_info = QLabel()
        self.remote_bind_info.setStyleSheet("color: gray; font-size: 9px;")
        remote_bind_layout.addWidget(self.remote_bind_info)
        form_layout.addRow(self.remote_bind_label, remote_bind_layout)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self._on_type_changed()

    def _on_type_changed(self):
        """Update UI based on selected forward type."""
        forward_type = self.type_combo.currentText()
        is_dynamic = "Dynamic" in forward_type
        is_local = "Local" in forward_type
        is_remote = "Remote" in forward_type

        # Update visibility
        self.remote_port_label.setVisible(not is_dynamic)
        self.remote_port_input.setVisible(not is_dynamic)
        self.remote_bind_label.setVisible(not is_dynamic)
        self.remote_bind_input.setVisible(not is_dynamic)

        # Update hints and labels
        if is_local:
            self.hint_label.setText(
                self.tr("💻 Access a remote service as if it were local on your machine")
            )
            self.local_port_info.setText(self.tr("(your computer)"))
            self.remote_port_info.setText(self.tr("(via bastion)"))
            self.remote_bind_info.setText(self.tr("(network accessible from bastion)"))
        elif is_remote:
            self.hint_label.setText(self.tr("🌐 Share your local service with the remote server"))
            self.local_port_info.setText(self.tr("(your computer)"))
            self.remote_port_info.setText(self.tr("(appears on bastion)"))
            self.remote_bind_info.setText(self.tr("(usually localhost)"))
        else:  # dynamic
            self.hint_label.setText(
                self.tr("🔒 Route all traffic through remote server as a SOCKS proxy")
            )
            self.local_port_info.setText(self.tr("(SOCKS proxy port)"))
            self.remote_port_info.setText("")
            self.remote_bind_info.setText("")

    def _populate_fields(self):
        """Populate fields with existing port forward data."""
        if not self.port_forward:
            return

        self.name_input.setText(self.port_forward.name)

        type_map = {"local": 0, "remote": 1, "dynamic": 2}
        self.type_combo.setCurrentIndex(type_map.get(self.port_forward.forward_type, 0))

        self.local_port_input.setValue(self.port_forward.local_port)
        self.remote_port_input.setValue(self.port_forward.remote_port or 8000)
        self.remote_bind_input.setText(self.port_forward.remote_bind_address)

    def get_port_forward(self) -> PortForward | None:
        """Get port forward from form data.

        Returns:
            PortForward object or None if validation fails
        """
        name = self.name_input.text().strip()
        if not name:
            return None

        type_map = {0: "local", 1: "remote", 2: "dynamic"}
        forward_type = type_map.get(self.type_combo.currentIndex(), "local")

        try:
            return PortForward(
                name=name,
                forward_type=forward_type,
                local_port=self.local_port_input.value(),
                remote_port=self.remote_port_input.value() if forward_type != "dynamic" else 0,
                remote_bind_address=self.remote_bind_input.text().strip() or "localhost",
            )
        except ValueError:
            return None


class IconDropLabel(QLabel):
    """Clickable, droppable icon preview label."""

    clicked = Signal()
    file_dropped = Signal(str)
    drag_active_changed = Signal(bool)
    drag_preview_changed = Signal(str)

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".gif", ".ico"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def _extract_image_path(self, event) -> str | None:
        mime_data = event.mimeData()
        if not mime_data or not mime_data.hasUrls():
            return None

        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            file_path = Path(url.toLocalFile())
            if file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                return str(file_path)
        return None

    def dragEnterEvent(self, event):
        preview_path = self._extract_image_path(event)
        if preview_path:
            self.drag_active_changed.emit(True)
            self.drag_preview_changed.emit(preview_path)
            event.acceptProposedAction()
        else:
            self.drag_active_changed.emit(False)
            event.ignore()

    def dragMoveEvent(self, event):
        preview_path = self._extract_image_path(event)
        if preview_path:
            self.drag_active_changed.emit(True)
            self.drag_preview_changed.emit(preview_path)
            event.acceptProposedAction()
        else:
            self.drag_active_changed.emit(False)
            event.ignore()

    def dropEvent(self, event):
        file_path = self._extract_image_path(event)
        self.drag_active_changed.emit(False)
        if file_path:
            self.file_dropped.emit(file_path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.drag_active_changed.emit(False)
        super().dragLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class AddConnectionDialog(QDialog):
    """Dialog for adding or editing SSH connections."""

    CUSTOM_ICON_ID_LENGTH = 5

    def __init__(
        self,
        parent=None,
        connection: SSHConnection | None = None,
        existing_groups: list[str] | None = None,
    ):
        """Initialize dialog.

        Args:
            parent: Parent widget
            connection: Existing connection to edit (None for new connection)
            existing_groups: List of existing group names for autocomplete
        """
        super().__init__(parent)
        self.connection = connection
        self.existing_groups = existing_groups or []

        self.setWindowTitle(self.tr("Edit Connection") if connection else self.tr("Add Connection"))
        self.setMinimumWidth(500)

        self._setup_ui()

        # Populate if editing existing connection
        if connection:
            self._populate_fields()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()

        # Form fields
        form_layout = QFormLayout()

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.tr("e.g., Production Server"))
        form_layout.addRow(self.tr("Name:"), self.name_input)

        # Host
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText(self.tr("e.g., example.com or 192.168.1.1"))
        form_layout.addRow(self.tr("Host:"), self.host_input)

        # User
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText(self.tr("e.g., root or ubuntu"))
        form_layout.addRow(self.tr("User:"), self.user_input)

        # Port
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        form_layout.addRow(self.tr("Port:"), self.port_input)

        # SSH Key
        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText(self.tr("Optional - path to private key"))
        self.key_browse_btn = QPushButton(self.tr("Browse..."))
        self.key_browse_btn.clicked.connect(self._browse_key)
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.key_browse_btn)
        form_layout.addRow(self.tr("SSH Key:"), key_layout)

        # Password
        password_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(self.tr("Optional - SSH password"))

        self.toggle_password_btn = QToolButton()

        icon_color = "white" if ThemeManager.is_system_dark_mode() else "black"

        self.toggle_password_btn.setIcon(qta.icon("fa5s.eye", color=icon_color))
        self.toggle_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_password_btn.clicked.connect(self._toggle_password_visibility)
        self.toggle_password_btn.setStyleSheet("border: none; padding: 4px;")

        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.toggle_password_btn)
        form_layout.addRow(self.tr("Password:"), password_layout)

        # Group (combobox with editable text)
        self.group_input = QComboBox()
        self.group_input.setEditable(True)
        self.group_input.addItems(self.existing_groups)
        self.group_input.setCurrentText(self.tr("Default"))
        form_layout.addRow(self.tr("Group:"), self.group_input)

        # Connection Type
        self.connection_type_combo = QComboBox()
        self.connection_type_combo.addItems(
            [
                self.tr("Shell (Terminal)"),
                self.tr("Tunnel (Background)"),
            ]
        )
        self.connection_type_combo.currentIndexChanged.connect(self._on_connection_type_changed)
        form_layout.addRow(self.tr("Connection Type:"), self.connection_type_combo)

        # Icon
        icon_layout = QHBoxLayout()
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText(self.tr("e.g. proxmox, home-assistant"))
        self.icon_input.textChanged.connect(self._update_icon_preview_from_text)

        self.icon_preview = IconDropLabel()
        self.icon_preview.setFixedSize(32, 32)
        self._drag_is_active = False
        self._drag_restore_tooltip = ""
        self._drag_restore_pixmap = None
        self._apply_icon_preview_style(False)
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_preview.setToolTip(self.tr("No Icon (click or drop an image)"))
        self.icon_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_preview.setPixmap(qta.icon("fa5s.image", color="gray").pixmap(20, 20))
        self.icon_preview.clicked.connect(self._browse_icon)
        self.icon_preview.file_dropped.connect(self._set_custom_icon)
        self.icon_preview.drag_active_changed.connect(self._apply_icon_preview_style)
        self.icon_preview.drag_preview_changed.connect(self._apply_drag_preview)

        icon_layout.addWidget(self.icon_input)
        icon_layout.addWidget(self.icon_preview)
        form_layout.addRow(self.tr("Icon:"), icon_layout)

        # Connect name change to auto-fill icon (only if icon is empty)
        self.name_input.textChanged.connect(self._auto_fill_icon)

        layout.addLayout(form_layout)

        # Port Forwards Section (only visible in tunnel mode)
        self.port_forwards_widget = QVBoxLayout()

        self.port_forwards_title = QLabel(self.tr("<b>Port Forwarding Rules</b>"))
        self.port_forwards_title.setStyleSheet("margin-top: 10px;")
        self.port_forwards_widget.addWidget(self.port_forwards_title)

        # Port forwards list
        self.port_forwards_list = QListWidget()
        self.port_forwards_list.setMaximumHeight(150)
        self.port_forwards_widget.addWidget(self.port_forwards_list)

        # Port forwards buttons
        self.pf_buttons_layout = QHBoxLayout()
        self.add_pf_btn = QPushButton(self.tr("Add Forward"))
        self.add_pf_btn.setIcon(qta.icon("fa5s.plus", color="white"))
        self.add_pf_btn.clicked.connect(self._add_port_forward)
        self.edit_pf_btn = QPushButton(self.tr("✎ Edit"))
        self.edit_pf_btn.clicked.connect(self._edit_port_forward)
        self.edit_pf_btn.setEnabled(False)
        self.delete_pf_btn = QPushButton(self.tr("✕ Delete"))
        self.delete_pf_btn.clicked.connect(self._delete_port_forward)
        self.delete_pf_btn.setEnabled(False)

        self.port_forwards_list.itemSelectionChanged.connect(self._on_pf_selection_changed)

        self.pf_buttons_layout.addWidget(self.add_pf_btn)
        self.pf_buttons_layout.addWidget(self.edit_pf_btn)
        self.pf_buttons_layout.addWidget(self.delete_pf_btn)
        self.port_forwards_widget.addLayout(self.pf_buttons_layout)

        # Store references to port forwards
        self.port_forwards: list[PortForward] = []

        # Add port forwards section to main layout
        layout.addLayout(self.port_forwards_widget)

        # Initially hide port forwards section
        self._on_connection_type_changed()

        # Initialize icon manager

        self.icon_manager = IconManager.instance()
        self.icon_manager.icon_loaded.connect(self._on_icon_loaded)
        self.icon_manager.icon_failed.connect(self._on_icon_failed)

        # Info label
        info_layout = QHBoxLayout()
        self.tip_icon = QLabel()
        self.tip_icon.setPixmap(qta.icon("fa5s.lightbulb", color="#FFD700").pixmap(14, 14))
        self.tip_icon.setContentsMargins(0, 1, 5, 0)
        self.tip_icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        tip_text = QLabel(
            self.tr(
                "Tip: SSH keys should be in ~/.ssh/ directory. Use ssh-keygen to create one if needed."
            )
        )
        tip_text.setWordWrap(True)
        tip_text.setStyleSheet("color: gray; font-size: 10px;")
        info_layout.addWidget(self.tip_icon, 0)
        info_layout.addWidget(tip_text, 1)
        info_layout.setAlignment(tip_text, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(info_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.test_btn = button_box.addButton(
            self.tr("Test"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.test_btn.setIcon(qta.icon("fa5s.flask", color="white"))
        self.test_btn.clicked.connect(self._test_connection)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

        # Focus on name field
        self.name_input.setFocus()

    def _browse_key(self):
        """Open file browser for SSH key selection."""
        ssh_dir = Path.home() / ".ssh"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select SSH Private Key"),
            str(ssh_dir),
            self.tr("SSH Private Keys (*.key *.pem *.ppk id_*);;All Files (*)"),
        )

        if file_path:
            self.key_input.setText(file_path)

    def _populate_fields(self):
        """Populate fields with existing connection data."""
        if not self.connection:
            return

        self.name_input.setText(self.connection.name)
        self.host_input.setText(self.connection.host)
        self.user_input.setText(self.connection.user)
        self.port_input.setValue(self.connection.port)

        if self.connection.key_path:
            self.key_input.setText(self.connection.key_path)

        if self.connection.password:
            self.password_input.setText(self.connection.password)

        if self.connection.group:
            self.group_input.setCurrentText(self.connection.group)

        if self.connection.icon:
            self.icon_input.setText(self.connection.icon)
            self._update_icon_preview(self.connection.icon)

        # Set connection type
        type_index = 1 if self.connection.connection_type == "tunnel" else 0
        self.connection_type_combo.setCurrentIndex(type_index)

        # Load port forwards if tunnel
        if self.connection.port_forwards:
            self.port_forwards = self.connection.port_forwards.copy()
            self._refresh_port_forwards_list()

    @staticmethod
    def _is_custom_icon_path(value: str) -> bool:
        """Check if the icon value should be treated as a file path."""
        icon_value = value.strip()
        if not icon_value:
            return False

        suffix = Path(icon_value).suffix.lower()
        if suffix in IconDropLabel.IMAGE_EXTENSIONS:
            return True

        if icon_value.startswith(("/", "./", "../", "~")):
            return True

        return "/" in icon_value or "\\" in icon_value

    def _apply_icon_preview_style(self, drag_active: bool):
        """Apply icon preview border style, highlighting on drag-over."""
        if drag_active:
            if not self._drag_is_active:
                self._drag_restore_tooltip = self.icon_preview.toolTip()
                self._drag_restore_pixmap = self.icon_preview.pixmap()
                self._drag_is_active = True

            color = self.palette().highlight().color().name()
            self.icon_preview.setStyleSheet(
                "border: 1px solid gray; border-radius: 4px; background-color: rgba(88, 166, 255, 0.14);"
            )
            self.icon_preview.setCursor(Qt.CursorShape.DragCopyCursor)
            self.icon_preview.setToolTip(self.tr("Drop image here"))
            if not self.icon_input.text().strip() and not self.icon_preview.pixmap():
                self.icon_preview.setPixmap(qta.icon("fa5s.upload", color=color).pixmap(20, 20))
            return

        self._drag_is_active = False
        self.icon_preview.setStyleSheet("border: 1px solid gray; border-radius: 4px;")
        self.icon_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._drag_restore_tooltip:
            self.icon_preview.setToolTip(self._drag_restore_tooltip)
        if self._drag_restore_pixmap is not None:
            self.icon_preview.setPixmap(self._drag_restore_pixmap)

    def _apply_drag_preview(self, file_path: str):
        """Show a live preview of the dragged icon while hovering."""
        if not self._drag_is_active:
            return

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            return

        self.icon_preview.setPixmap(
            pixmap.scaled(
                32,
                32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _custom_icons_dir(self) -> Path:
        """Get custom icon storage directory under app config."""
        config_dir = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        )
        icon_dir = config_dir / "custom_icons"
        icon_dir.mkdir(parents=True, exist_ok=True)
        return icon_dir

    def _persist_custom_icon(self, file_path: str) -> str | None:
        """Copy and resize custom icon into app config storage."""
        source_path = Path(file_path).expanduser()
        if not source_path.exists() or not source_path.is_file():
            return None

        icon_dir = self._custom_icons_dir()
        if source_path.parent == icon_dir:
            return str(source_path)

        pixmap = QPixmap(str(source_path))
        if pixmap.isNull():
            return None

        scaled_pixmap = pixmap.scaled(
            64,
            64,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        target_path = None
        for _ in range(10):
            random_id = generate(size=self.CUSTOM_ICON_ID_LENGTH)
            candidate = icon_dir / f"{random_id}.png"
            if not candidate.exists():
                target_path = candidate
                break

        if target_path is None:
            return None

        if not scaled_pixmap.save(str(target_path), "PNG"):
            return None

        return str(target_path)

    def _browse_icon(self):
        """Open file browser for custom icon selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select Custom Icon"),
            str(Path.home()),
            self.tr(
                "Image Files (*.png *.jpg *.jpeg *.webp *.svg *.bmp *.gif *.ico);;All Files (*)"
            ),
        )

        if file_path:
            self._set_custom_icon(file_path)

    def _set_custom_icon(self, file_path: str):
        """Set and persist a custom icon file path."""
        persisted_path = self._persist_custom_icon(file_path)
        if persisted_path:
            self.icon_input.setText(persisted_path)
        else:
            self.icon_input.setText(str(Path(file_path).expanduser()))

    def _update_icon_preview_from_text(self, text):
        """Update icon preview based on text input."""
        if text and not self._is_custom_icon_path(text):
            lower_text = text.lower()
        else:
            lower_text = text

        if text != lower_text:
            self.icon_input.setText(lower_text)
            return  # setText will re-trigger textChanged
        self._update_icon_preview(text)

    def _update_icon_preview(self, icon_name):
        """Update the icon preview label."""
        if not icon_name:
            self.icon_preview.clear()
            self.icon_preview.setToolTip(self.tr("No Icon (click or drop an image)"))
            self.icon_preview.setPixmap(qta.icon("fa5s.image", color="gray").pixmap(20, 20))
            return

        if self._is_custom_icon_path(icon_name):
            custom_path = Path(icon_name).expanduser()
            if custom_path.exists() and custom_path.is_file():
                pixmap = QPixmap(str(custom_path))
                if not pixmap.isNull():
                    self.icon_preview.setPixmap(
                        pixmap.scaled(
                            32,
                            32,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    self.icon_preview.setToolTip(str(custom_path))
                    return

            self.icon_preview.setPixmap(
                qta.icon("fa5s.exclamation-circle", color="#e05252").pixmap(20, 20)
            )
            self.icon_preview.setToolTip(self.tr("Custom icon file not found or invalid"))
            return

        manager = IconManager.instance()

        # Try to get cached icon
        icon_path = manager.get_icon_path(icon_name)
        if icon_path and Path(icon_path).exists():
            pixmap = QPixmap(str(icon_path))
            self.icon_preview.setPixmap(
                pixmap.scaled(
                    32,
                    32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            # Trigger fetch if not cached
            manager.fetch_icon(icon_name)
            self.icon_preview.setPixmap(
                qta.icon(
                    "fa5s.spinner", color="gray", animation=qta.Spin(self.icon_preview)
                ).pixmap(20, 20)
            )

    def _on_icon_loaded(self, name, path):
        """Handle icon loaded signal."""
        if self.icon_input.text() == name:
            self._update_icon_preview(name)

    def _on_icon_failed(self, name):
        if self.icon_input.text() == name:
            self.icon_preview.setPixmap(
                qta.icon("fa5s.exclamation-circle", color="#e05252").pixmap(20, 20)
            )
            self.icon_preview.setToolTip(self.tr("Icon '{}' not found").format(name))

    def _auto_fill_icon(self, name):
        """Auto-fill icon field based on connection name."""
        if self.connection is not None:
            return

        if not self.icon_input.text():
            # Convert name to kebab-case-ish (simplified)
            icon_name = name.lower().replace(" ", "-")
            self.icon_input.setText(icon_name)
            self._update_icon_preview(icon_name)

    def _toggle_password_visibility(self):
        """Toggle the echo mode of the password input."""
        current_mode = self.password_input.echoMode()
        from sshive.ui.theme import ThemeManager

        icon_color = "white" if ThemeManager.is_system_dark_mode() else "black"
        import qtawesome as qta

        if current_mode == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_btn.setIcon(qta.icon("fa5s.eye-slash", color=icon_color))
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_btn.setIcon(qta.icon("fa5s.eye", color=icon_color))

    def _build_connection_for_test(self) -> SSHConnection | None:
        """Build a temporary connection object from current form values."""
        name = self.name_input.text().strip()
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()

        if not name or not host or not user:
            return None

        key_path = self.key_input.text().strip() or None
        password = self.password_input.text() or None
        group = self.group_input.currentText().strip() or self.tr("Default")
        icon = self.icon_input.text().strip() or None

        try:
            return SSHConnection(
                name=name,
                host=host,
                user=user,
                port=self.port_input.value(),
                key_path=key_path,
                password=password,
                group=group,
                icon=icon,
            )
        except ValueError:
            return None

    def _on_connection_type_changed(self):
        """Show/hide port forwards section based on connection type."""
        is_tunnel = self.connection_type_combo.currentIndex() == 1

        # Hide/show all port forward related widgets
        self.port_forwards_title.setVisible(is_tunnel)
        self.port_forwards_list.setVisible(is_tunnel)
        self.add_pf_btn.setVisible(is_tunnel)
        self.edit_pf_btn.setVisible(is_tunnel)
        self.delete_pf_btn.setVisible(is_tunnel)

    def _add_port_forward(self):
        """Open dialog to add a new port forward."""
        dialog = PortForwardDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            pf = dialog.get_port_forward()
            if pf:
                self.port_forwards.append(pf)
                self._refresh_port_forwards_list()

    def _edit_port_forward(self):
        """Edit the selected port forward."""
        current_item = self.port_forwards_list.currentItem()
        if not current_item:
            return

        index = self.port_forwards_list.row(current_item)
        if 0 <= index < len(self.port_forwards):
            dialog = PortForwardDialog(self, self.port_forwards[index])
            if dialog.exec() == QDialog.DialogCode.Accepted:
                pf = dialog.get_port_forward()
                if pf:
                    self.port_forwards[index] = pf
                    self._refresh_port_forwards_list()

    def _delete_port_forward(self):
        """Delete the selected port forward."""
        current_item = self.port_forwards_list.currentItem()
        if not current_item:
            return

        index = self.port_forwards_list.row(current_item)
        if 0 <= index < len(self.port_forwards):
            self.port_forwards.pop(index)
            self._refresh_port_forwards_list()

    def _on_pf_selection_changed(self):
        """Update button states based on port forward selection."""
        has_selection = self.port_forwards_list.currentItem() is not None
        self.edit_pf_btn.setEnabled(has_selection)
        self.delete_pf_btn.setEnabled(has_selection)

    def _refresh_port_forwards_list(self):
        """Refresh the port forwards list widget."""
        self.port_forwards_list.clear()
        for pf in self.port_forwards:
            # Create descriptive text for each forward
            if pf.forward_type == "local":
                text = f"🔗 {pf.name}: localhost:{pf.local_port} ← {pf.remote_bind_address}:{pf.remote_port}"
            elif pf.forward_type == "remote":
                text = f"🔗 {pf.name}: {pf.remote_port} ← localhost:{pf.local_port}"
            else:  # dynamic
                text = f"🔗 {pf.name}: SOCKS localhost:{pf.local_port}"

            item = QListWidgetItem(text)
            self.port_forwards_list.addItem(item)

    def _test_connection(self):
        """Run full connection test (preflight + network + auth) for dialog form values."""
        connection = self._build_connection_for_test()
        if connection is None:
            QMessageBox.warning(
                self,
                self.tr("Connection Test"),
                self.tr("Please fill in Name, Host, and User before testing."),
            )
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            QApplication.processEvents()
            success, message = SSHLauncher.test_full_connection(connection)
        finally:
            QApplication.restoreOverrideCursor()

        if success:
            QMessageBox.information(
                self,
                self.tr("Connection Test"),
                self.tr("{}\n\n{}").format(connection.name, message),
            )
        else:
            # On failure, collect and show debug log
            debug_log = SSHLauncher.collect_ssh_debug_log(connection)
            title = self.tr("Connection Test Failed")
            show_connection_test_debug_dialog(self, title, connection, message, debug_log)

    def get_connection(self) -> SSHConnection | None:
        """Get connection from form data.

        Returns:
            SSHConnection object or None if validation fails
        """
        # Validate required fields
        name = self.name_input.text().strip()
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()

        if not name or not host or not user:
            return None

        key_path = self.key_input.text().strip() or None
        password = self.password_input.text() or None
        group = self.group_input.currentText().strip() or self.tr("Default")
        icon = self.icon_input.text().strip() or None

        if icon and self._is_custom_icon_path(icon):
            persisted_path = self._persist_custom_icon(icon)
            if persisted_path:
                icon = persisted_path

        # Get connection type and port forwards
        connection_type = "tunnel" if self.connection_type_combo.currentIndex() == 1 else "shell"
        port_forwards = self.port_forwards if connection_type == "tunnel" else []

        try:
            if self.connection:
                # Update the existing object
                self.connection.name = name
                self.connection.host = host
                self.connection.user = user
                self.connection.port = self.port_input.value()
                self.connection.key_path = key_path
                self.connection.password = password
                self.connection.group = group
                self.connection.icon = icon
                self.connection.connection_type = connection_type
                self.connection.port_forwards = port_forwards
                return self.connection
            else:
                # Create new connection
                return SSHConnection(
                    name=name,
                    host=host,
                    user=user,
                    port=self.port_input.value(),
                    key_path=key_path,
                    password=password,
                    group=group,
                    icon=icon,
                    connection_type=connection_type,
                    port_forwards=port_forwards,
                )
        except ValueError as e:
            print(f"Validation error: {e}")
            return None
