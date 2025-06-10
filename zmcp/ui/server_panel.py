"""
ZMCP Server Panel

Server configuration and control panel.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QGroupBox, QTextEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)

from zmcp.core.config import config
from zmcp.server.base import MCPServer
from zmcp.server.http_server import MCPHTTPServer, start_http_server
from zmcp.server.tools import AVAILABLE_TOOLS, TOOL_HANDLERS
from zmcp.ui.server_config_dialog import ServerConfigDialog

logger = logging.getLogger(__name__)


class ServerPanel(QWidget):
    """Server configuration and control panel."""

    server_started = pyqtSignal()
    server_stopped = pyqtSignal()

    def __init__(self):
        """Initialize server panel."""
        super().__init__()
        self.mcp_server = None
        self.http_server = None
        self.server_running = False
        self.server_config = self._load_server_config()
        self._init_ui()
        self._populate_ui_from_config()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Server configuration
        config_group = QGroupBox("Server Configuration")
        config_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setReadOnly(True)
        config_layout.addRow("Server Name:", self.name_edit)

        self.host_edit = QLineEdit()
        self.host_edit.setReadOnly(True)
        config_layout.addRow("Host:", self.host_edit)

        self.port_edit = QLineEdit()
        self.port_edit.setReadOnly(True)
        config_layout.addRow("Port:", self.port_edit)

        # Add configure button
        config_button_layout = QHBoxLayout()
        self.configure_btn = QPushButton("Configure Server")
        self.configure_btn.clicked.connect(self._open_config_dialog)
        config_button_layout.addWidget(self.configure_btn)
        config_layout.addRow("", config_button_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Enabled Tools
        tools_group = QGroupBox("Enabled Tools")
        tools_layout = QVBoxLayout()

        # Tools table
        self.tools_table = QTableWidget(0, 2)
        self.tools_table.setHorizontalHeaderLabels(["Tool Name", "Description"])
        self.tools_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tools_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tools_layout.addWidget(self.tools_table)

        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # Server controls
        controls_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self._start_server)
        controls_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.clicked.connect(self._stop_server)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)

        layout.addLayout(controls_layout)

        # Server log
        log_group = QGroupBox("Server Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        # Log controls
        log_controls = QHBoxLayout()
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self._clear_log)
        log_controls.addWidget(self.clear_log_btn)

        log_layout.addLayout(log_controls)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Server status
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Server Status:"))
        self.status_label = QLabel("Stopped")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        # Add monitoring info
        self.connections_label = QLabel("Connections: 0")
        status_layout.addWidget(self.connections_label)

        self.requests_label = QLabel("Requests: 0")
        status_layout.addWidget(self.requests_label)

        layout.addLayout(status_layout)

        self.setLayout(layout)

        # Setup timer for status updates
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second

    def _load_server_config(self) -> Dict[str, Any]:
        """Load server configuration."""
        server_config = config.get("servers.default", {})
        if not server_config:
            # Default configuration
            server_config = {
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
            config.set("servers.default", server_config)
        return server_config

    def _populate_ui_from_config(self):
        """Populate UI elements from configuration."""
        self.name_edit.setText(self.server_config.get("name", "ZMCP Server"))
        self.host_edit.setText(self.server_config.get("host", "localhost"))
        self.port_edit.setText(str(self.server_config.get("port", 8000)))

        # Clear and populate tools table
        self.tools_table.setRowCount(0)
        enabled_tools = self.server_config.get("tools", [])

        for tool_name in enabled_tools:
            for tool in AVAILABLE_TOOLS:
                if tool.name == tool_name:
                    row = self.tools_table.rowCount()
                    self.tools_table.insertRow(row)
                    self.tools_table.setItem(row, 0, QTableWidgetItem(tool.name))
                    self.tools_table.setItem(row, 1, QTableWidgetItem(tool.description))
                    break

    def _open_config_dialog(self):
        """Open server configuration dialog."""
        if self.server_running:
            QMessageBox.warning(self, "Server Running",
                                "Stop the server before changing configuration.")
            return

        dialog = ServerConfigDialog(self)
        dialog.config_updated.connect(self._config_updated)
        dialog.exec()

    def _config_updated(self, new_config: Dict[str, Any]):
        """Handle configuration update from dialog."""
        self.server_config = new_config
        self._populate_ui_from_config()
        self.log_text.append("Server configuration updated")

    def _clear_log(self):
        """Clear the server log."""
        self.log_text.clear()

    def _update_status(self):
        """Update server status display."""
        if not self.server_running:
            return

        # In a real implementation, we would get actual metrics
        # For now, just simulate some activity
        self.connections_label.setText(f"Connections: {self._get_connection_count()}")
        self.requests_label.setText(f"Requests: {self._get_request_count()}")

    def _get_connection_count(self) -> int:
        """Get current connection count (placeholder)."""
        # This would be implemented with actual server stats
        return 0

    def _get_request_count(self) -> int:
        """Get total request count (placeholder)."""
        # This would be implemented with actual server stats
        return 0

    async def _start_server_async(self):
        """Start the MCP server asynchronously."""
        try:
            # Create MCP server instance
            self.mcp_server = MCPServer(
                name=self.server_config.get("name", "ZMCP Server"),
                description=self.server_config.get("description", "MCP Server for ZMCP")
            )

            # Add enabled tools
            enabled_tools = self.server_config.get("tools", [])
            for tool in AVAILABLE_TOOLS:
                if tool.name in enabled_tools:
                    self.mcp_server.add_tool(tool)

            # Start HTTP server
            host = self.server_config.get("host", "localhost")
            port = self.server_config.get("port", 8000)

            self.http_server = await start_http_server(self.mcp_server, host, port)

            return True
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            return False

    def _start_server(self):
        """Start the MCP server."""
        self.log_text.append(f"Starting server at {self.host_edit.text()}:{self.port_edit.text()}...")

        # Use asyncio to start the server
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(self._start_server_async())

        if success:
            self.server_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.configure_btn.setEnabled(False)
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.server_started.emit()
            self.log_text.append("Server started successfully")
        else:
            self.log_text.append("Failed to start server")
            QMessageBox.critical(self, "Server Error", "Failed to start server. See log for details.")

    async def _stop_server_async(self):
        """Stop the MCP server asynchronously."""
        try:
            if self.http_server:
                # In a real implementation, we would gracefully shut down the server
                # This is a simplified version
                pass

            self.http_server = None
            self.mcp_server = None

            return True
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return False

    def _stop_server(self):
        """Stop the MCP server."""
        self.log_text.append("Stopping server...")

        # Use asyncio to stop the server
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(self._stop_server_async())

        if success:
            self.server_running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.configure_btn.setEnabled(True)
            self.status_label.setText("Stopped")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.server_stopped.emit()
            self.log_text.append("Server stopped successfully")
        else:
            self.log_text.append("Failed to stop server cleanly")
            QMessageBox.warning(self, "Server Warning", "Server did not stop cleanly. See log for details.")
