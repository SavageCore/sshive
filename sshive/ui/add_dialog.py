"""Dialog for adding and editing SSH connections."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
)

from sshive.models.connection import SSHConnection
from sshive.ui.icon_manager import IconManager


class AddConnectionDialog(QDialog):
    """Dialog for adding or editing SSH connections."""

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

        self.setWindowTitle("Edit Connection" if connection else "Add Connection")
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
        self.name_input.setPlaceholderText("e.g., Production Server")
        form_layout.addRow("Name:", self.name_input)

        # Host
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("e.g., example.com or 192.168.1.1")
        form_layout.addRow("Host:", self.host_input)

        # User
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("e.g., root or ubuntu")
        form_layout.addRow("User:", self.user_input)

        # Port
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        form_layout.addRow("Port:", self.port_input)

        # SSH Key
        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Optional - path to private key")
        self.key_browse_btn = QPushButton("Browse...")
        self.key_browse_btn.clicked.connect(self._browse_key)
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.key_browse_btn)
        form_layout.addRow("SSH Key:", key_layout)

        # Password
        password_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Optional - SSH password")

        self.toggle_password_btn = QToolButton()
        from sshive.ui.theme import ThemeManager

        icon_color = "white" if ThemeManager.is_system_dark_mode() else "black"
        import qtawesome as qta

        self.toggle_password_btn.setIcon(qta.icon("fa5s.eye", color=icon_color))
        self.toggle_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_password_btn.clicked.connect(self._toggle_password_visibility)
        self.toggle_password_btn.setStyleSheet("border: none; padding: 4px;")

        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.toggle_password_btn)
        form_layout.addRow("Password:", password_layout)

        # Group (combobox with editable text)
        self.group_input = QComboBox()
        self.group_input.setEditable(True)
        self.group_input.addItems(self.existing_groups)
        self.group_input.setCurrentText("Default")
        form_layout.addRow("Group:", self.group_input)

        # Icon
        icon_layout = QHBoxLayout()
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("e.g. proxmox, home-assistant")
        self.icon_input.textChanged.connect(self._update_icon_preview_from_text)

        self.icon_preview = QLabel("No Icon")
        self.icon_preview.setFixedSize(32, 32)
        self.icon_preview.setStyleSheet("border: 1px solid gray; border-radius: 4px;")
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_layout.addWidget(self.icon_input)
        icon_layout.addWidget(self.icon_preview)
        form_layout.addRow("Icon:", icon_layout)

        # Connect name change to auto-fill icon (only if icon is empty)
        self.name_input.textChanged.connect(self._auto_fill_icon)

        layout.addLayout(form_layout)

        # Initialize icon manager

        self.icon_manager = IconManager.instance()
        self.icon_manager.icon_loaded.connect(self._on_icon_loaded)

        # Info label
        info_label = QLabel(
            "💡 Tip: SSH keys should be in ~/.ssh/ directory. "
            "Use ssh-keygen to create one if needed."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
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
            "Select SSH Private Key",
            str(ssh_dir),
            "SSH Private Keys (*.key *.pem *.ppk id_*);;All Files (*)",
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

        if self.connection.icon:
            self.icon_input.setText(self.connection.icon)
            self._update_icon_preview(self.connection.icon)

    def _update_icon_preview_from_text(self, text):
        """Update icon preview based on text input."""
        lower_text = text.lower()
        if text != lower_text:
            self.icon_input.setText(lower_text)
            return  # setText will re-trigger textChanged
        self._update_icon_preview(text)

    def _update_icon_preview(self, icon_name):
        """Update the icon preview label."""
        if not icon_name:
            self.icon_preview.clear()
            self.icon_preview.setText("No Icon")
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
            self.icon_preview.setText("Loading...")

    def _on_icon_loaded(self, name, path):
        """Handle icon loaded signal."""
        if self.icon_input.text() == name:
            self._update_icon_preview(name)

    def _auto_fill_icon(self, name):
        """Auto-fill icon field based on connection name."""
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
        group = self.group_input.currentText().strip() or "Default"
        icon = self.icon_input.text().strip() or None

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
                )
        except ValueError as e:
            print(f"Validation error: {e}")
            return None
