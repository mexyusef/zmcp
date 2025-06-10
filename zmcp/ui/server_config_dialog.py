"""
ZMCP Server Configuration Dialog

Dialog for configuring MCP server settings.
"""
import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QPushButton, QCheckBox, QTabWidget, QWidget, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QComboBox, QMessageBox, QTextEdit, QDialogButtonBox
)

from zmcp.core.config import config
from zmcp.server.tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


class ServerConfigDialog(QDialog):
    """Dialog for configuring MCP server settings."""

    config_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.setWindowTitle("Server Configuration")
        self.resize(600, 500)

        self.server_config = self._load_server_config()

        self._init_ui()
        self._populate_fields()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Server settings tab widget
        self.tab_widget = QTabWidget()

        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout()

        self.server_name_edit = QLineEdit()
        general_layout.addRow("Server Name:", self.server_name_edit)

        self.server_description_edit = QTextEdit()
        self.server_description_edit.setMaximumHeight(100)
        general_layout.addRow("Description:", self.server_description_edit)

        self.host_edit = QLineEdit()
        general_layout.addRow("Host:", self.host_edit)

        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1024, 65535)
        self.port_spinbox.setValue(8000)
        general_layout.addRow("Port:", self.port_spinbox)

        general_tab.setLayout(general_layout)

        # Tools tab
        tools_tab = QWidget()
        tools_layout = QVBoxLayout()

        self.tools_list = QListWidget()
        for tool in AVAILABLE_TOOLS:
            item = QListWidgetItem(f"{tool.name} - {tool.description}")
            item.setData(Qt.ItemDataRole.UserRole, tool.name)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.tools_list.addItem(item)

        tools_layout.addWidget(QLabel("Available Tools:"))
        tools_layout.addWidget(self.tools_list)

        tools_button_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self._select_all_tools)
        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.clicked.connect(self._clear_all_tools)

        tools_button_layout.addWidget(self.select_all_button)
        tools_button_layout.addWidget(self.clear_all_button)
        tools_layout.addLayout(tools_button_layout)

        tools_tab.setLayout(tools_layout)

        # Security tab
        security_tab = QWidget()
        security_layout = QFormLayout()

        self.auth_enabled_checkbox = QCheckBox()
        security_layout.addRow("Enable Authentication:", self.auth_enabled_checkbox)

        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems(["Basic", "API Key", "None"])
        security_layout.addRow("Authentication Type:", self.auth_type_combo)

        self.auth_key_edit = QLineEdit()
        security_layout.addRow("API Key/Password:", self.auth_key_edit)

        security_tab.setLayout(security_layout)

        # Add tabs to tab widget
        self.tab_widget.addTab(general_tab, "General")
        self.tab_widget.addTab(tools_tab, "Tools")
        self.tab_widget.addTab(security_tab, "Security")

        layout.addWidget(self.tab_widget)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._save_config)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def _load_server_config(self) -> dict:
        """Load server configuration."""
        server_config = config.get("servers", {})
        if not server_config:
            # Default configuration
            server_config = {
                "default": {
                    "name": "ZMCP Server",
                    "description": "MCP Server for ZMCP",
                    "host": "localhost",
                    "port": 8000,
                    "tools": [tool.name for tool in AVAILABLE_TOOLS],
                    "auth": {
                        "enabled": False,
                        "type": "None",
                        "key": ""
                    }
                }
            }
        return server_config

    def _populate_fields(self):
        """Populate fields with current configuration."""
        # Use the first server config (or default if none)
        server_id = next(iter(self.server_config.keys()), "default")
        server = self.server_config.get(server_id, {})

        # General tab
        self.server_name_edit.setText(server.get("name", "ZMCP Server"))
        self.server_description_edit.setText(server.get("description", "MCP Server for ZMCP"))
        self.host_edit.setText(server.get("host", "localhost"))
        self.port_spinbox.setValue(server.get("port", 8000))

        # Tools tab
        enabled_tools = server.get("tools", [])
        for i in range(self.tools_list.count()):
            item = self.tools_list.item(i)
            tool_name = item.data(Qt.ItemDataRole.UserRole)
            item.setCheckState(
                Qt.CheckState.Checked if tool_name in enabled_tools else Qt.CheckState.Unchecked
            )

        # Security tab
        auth = server.get("auth", {})
        self.auth_enabled_checkbox.setChecked(auth.get("enabled", False))

        auth_type = auth.get("type", "None")
        index = self.auth_type_combo.findText(auth_type)
        if index >= 0:
            self.auth_type_combo.setCurrentIndex(index)

        self.auth_key_edit.setText(auth.get("key", ""))

    def _select_all_tools(self):
        """Select all tools."""
        for i in range(self.tools_list.count()):
            self.tools_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _clear_all_tools(self):
        """Clear all tool selections."""
        for i in range(self.tools_list.count()):
            self.tools_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _save_config(self):
        """Save configuration."""
        # Get enabled tools
        enabled_tools = []
        for i in range(self.tools_list.count()):
            item = self.tools_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                enabled_tools.append(item.data(Qt.ItemDataRole.UserRole))

        # Create configuration
        server_config = {
            "name": self.server_name_edit.text(),
            "description": self.server_description_edit.toPlainText(),
            "host": self.host_edit.text(),
            "port": self.port_spinbox.value(),
            "tools": enabled_tools,
            "auth": {
                "enabled": self.auth_enabled_checkbox.isChecked(),
                "type": self.auth_type_combo.currentText(),
                "key": self.auth_key_edit.text()
            }
        }

        # Update global config
        config.set("servers.default", server_config)

        # Emit signal with new config
        self.config_updated.emit(server_config)

        self.accept()
