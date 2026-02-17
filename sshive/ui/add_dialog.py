"""Dialog for adding and editing SSH connections."""

from pathlib import Path

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
    QVBoxLayout,
)

from sshive.models.connection import SSHConnection


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

        # Group (combobox with editable text)
        self.group_input = QComboBox()
        self.group_input.setEditable(True)
        self.group_input.addItems(self.existing_groups)
        self.group_input.setCurrentText("Default")
        form_layout.addRow("Group:", self.group_input)

        layout.addLayout(form_layout)

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
            self, "Select SSH Private Key", str(ssh_dir), "All Files (*)"
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

        if self.connection.group:
            self.group_input.setCurrentText(self.connection.group)

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
        group = self.group_input.currentText().strip() or "Default"

        try:
            # Create new connection or update existing
            if self.connection:
                # Update existing connection
                self.connection.name = name
                self.connection.host = host
                self.connection.user = user
                self.connection.port = self.port_input.value()
                self.connection.key_path = key_path
                self.connection.group = group
                return self.connection
            else:
                # Create new connection
                return SSHConnection(
                    name=name,
                    host=host,
                    user=user,
                    port=self.port_input.value(),
                    key_path=key_path,
                    group=group,
                )
        except ValueError as e:
            print(f"Validation error: {e}")
            return None
