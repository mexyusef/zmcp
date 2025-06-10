"""
ZMCP Client Panel

Client connection and interaction panel.
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QGroupBox, QTextEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QMessageBox, QDialog, QVBoxLayout, QDialogButtonBox, QTabWidget,
    QProgressBar
)
from PyQt6.QtGui import QFont

from zmcp.core.config import config
from zmcp.client.base import MCPClient
from zmcp.core.mcp import Tool, Content, TextContent

logger = logging.getLogger(__name__)


class ToolInputDialog(QDialog):
    """Dialog for entering tool input parameters."""

    def __init__(self, tool: Tool, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.tool = tool
        self.setWindowTitle(f"Tool Input: {tool.name}")
        self.resize(500, 400)
        self.input_fields = {}
        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Tool info
        layout.addWidget(QLabel(f"<b>{self.tool.name}</b>"))
        layout.addWidget(QLabel(self.tool.description))
        layout.addWidget(QLabel("Parameters:"))

        # Input fields
        form_layout = QFormLayout()

        if self.tool.input_schema and "properties" in self.tool.input_schema:
            properties = self.tool.input_schema["properties"]
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "string")
                param_description = param_info.get("description", "")

                if param_type in ["string", "number", "integer"]:
                    field = QLineEdit()
                    if param_description:
                        field.setPlaceholderText(param_description)
                    self.input_fields[param_name] = field
                    form_layout.addRow(f"{param_name}:", field)

                elif param_type == "boolean":
                    from PyQt6.QtWidgets import QCheckBox
                    field = QCheckBox()
                    field.setChecked(False)
                    self.input_fields[param_name] = field
                    form_layout.addRow(f"{param_name}:", field)

                # Could extend with support for arrays, objects, etc.

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_input_values(self) -> Dict[str, Any]:
        """Get input values from dialog fields."""
        values = {}
        for param_name, field in self.input_fields.items():
            from PyQt6.QtWidgets import QCheckBox
            if isinstance(field, QCheckBox):
                values[param_name] = field.isChecked()
            else:
                value = field.text()
                # Try to convert to appropriate type
                if self.tool.input_schema and "properties" in self.tool.input_schema:
                    param_info = self.tool.input_schema["properties"].get(param_name, {})
                    param_type = param_info.get("type", "string")

                    if param_type == "number":
                        try:
                            values[param_name] = float(value)
                        except ValueError:
                            values[param_name] = value
                    elif param_type == "integer":
                        try:
                            values[param_name] = int(value)
                        except ValueError:
                            values[param_name] = value
                    else:
                        values[param_name] = value
                else:
                    values[param_name] = value
        return values


class ClientPanel(QWidget):
    """Client connection and interaction panel."""

    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal()
    tool_selected = pyqtSignal(str, str)  # Tool name, server URL

    def __init__(self):
        """Initialize client panel."""
        super().__init__()
        self.client = None
        self.current_tool = None
        self.server_url = ""
        self.current_resource = None
        self.current_prompt = None
        self.recent_connections = self._load_recent_connections()
        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Connection configuration
        config_group = QGroupBox("Server Connection")
        config_layout = QFormLayout()

        self.url_edit = QLineEdit("http://localhost:8000")
        config_layout.addRow("Server URL:", self.url_edit)

        self.recent_servers = QComboBox()
        self.recent_servers.setEditable(False)
        for url in self.recent_connections:
            self.recent_servers.addItem(url)
        self.recent_servers.currentTextChanged.connect(self._server_selected)
        config_layout.addRow("Recent Servers:", self.recent_servers)

        # Connection controls
        controls_layout = QHBoxLayout()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect_to_server)
        controls_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._disconnect_from_server)
        self.disconnect_btn.setEnabled(False)
        controls_layout.addWidget(self.disconnect_btn)

        config_layout.addRow("", controls_layout)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Server capabilities
        capabilities_widget = QTabWidget()

        # Tools tab
        tools_tab = QWidget()
        tools_layout = QVBoxLayout()

        self.tools_table = QTableWidget(0, 3)
        self.tools_table.setHorizontalHeaderLabels(["Name", "Description", "Parameters"])
        self.tools_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tools_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tools_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tools_table.verticalHeader().setVisible(False)
        self.tools_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tools_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tools_table.setAlternatingRowColors(True)
        self.tools_table.itemClicked.connect(self._tool_clicked)
        tools_layout.addWidget(self.tools_table)

        tools_tab.setLayout(tools_layout)
        capabilities_widget.addTab(tools_tab, "Tools")

        # Resources tab
        resources_tab = QWidget()
        resources_layout = QVBoxLayout()

        self.resources_table = QTableWidget(0, 2)
        self.resources_table.setHorizontalHeaderLabels(["Name", "Description"])
        self.resources_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.resources_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.resources_table.verticalHeader().setVisible(False)
        self.resources_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.resources_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.resources_table.setAlternatingRowColors(True)
        self.resources_table.itemClicked.connect(self._resource_clicked)
        resources_layout.addWidget(self.resources_table)

        resources_tab.setLayout(resources_layout)
        capabilities_widget.addTab(resources_tab, "Resources")

        # Prompts tab
        prompts_tab = QWidget()
        prompts_layout = QVBoxLayout()

        self.prompts_table = QTableWidget(0, 2)
        self.prompts_table.setHorizontalHeaderLabels(["Name", "Description"])
        self.prompts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.prompts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.prompts_table.verticalHeader().setVisible(False)
        self.prompts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.prompts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.prompts_table.setAlternatingRowColors(True)
        self.prompts_table.itemClicked.connect(self._prompt_clicked)
        prompts_layout.addWidget(self.prompts_table)

        prompts_tab.setLayout(prompts_layout)
        capabilities_widget.addTab(prompts_tab, "Prompts")

        layout.addWidget(capabilities_widget)

        # Interaction area
        interaction_group = QGroupBox("Interaction")
        interaction_layout = QVBoxLayout()

        # Tool info
        self.tool_info = QLabel("No tool selected")
        interaction_layout.addWidget(self.tool_info)

        # Input and response in splitter - horizontal layout
        interaction_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Input panel
        input_group = QWidget()
        input_layout = QVBoxLayout()
        input_layout.addWidget(QLabel("Input:"))

        self.input_text = QTextEdit()
        input_layout.addWidget(self.input_text)

        input_buttons = QHBoxLayout()
        self.clear_input_btn = QPushButton("Clear")
        self.clear_input_btn.clicked.connect(lambda: self.input_text.clear())
        input_buttons.addWidget(self.clear_input_btn)

        self.execute_btn = QPushButton("Execute")
        self.execute_btn.clicked.connect(self._execute)
        self.execute_btn.setEnabled(False)
        input_buttons.addWidget(self.execute_btn)

        input_layout.addLayout(input_buttons)
        input_group.setLayout(input_layout)
        interaction_splitter.addWidget(input_group)

        # Response panel
        response_group = QWidget()
        response_layout = QVBoxLayout()
        response_layout.addWidget(QLabel("Response:"))

        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        response_layout.addWidget(self.response_text)

        response_buttons = QHBoxLayout()
        self.clear_response_btn = QPushButton("Clear")
        self.clear_response_btn.clicked.connect(lambda: self.response_text.clear())
        response_buttons.addWidget(self.clear_response_btn)

        response_layout.addLayout(response_buttons)
        response_group.setLayout(response_layout)
        interaction_splitter.addWidget(response_group)

        # Set equal sizes for the splitter
        interaction_splitter.setSizes([1000, 1000])

        interaction_layout.addWidget(interaction_splitter)
        interaction_group.setLayout(interaction_layout)
        layout.addWidget(interaction_group)
        self.setLayout(layout)

    def _load_recent_connections(self) -> List[str]:
        """Load recent server connections."""
        return config.get("client.recent_connections", ["http://localhost:8000"])

    def _save_recent_connection(self, url: str):
        """Save a recent server connection."""
        recent = config.get("client.recent_connections", [])
        if url in recent:
            recent.remove(url)
        recent.insert(0, url)  # Add to the beginning
        if len(recent) > 10:  # Limit to 10 recent connections
            recent = recent[:10]
        config.set("client.recent_connections", recent)

    def _server_selected(self, url):
        """Handle server selection from dropdown."""
        if url:
            self.url_edit.setText(url)

    async def _connect_async(self, url: str) -> bool:
        """Connect to MCP server asynchronously."""
        try:
            self.client = MCPClient(url)
            await self.client.connect()
            return True
        except Exception as e:
            logger.error(f"Error connecting to server: {e}")
            return False

    def _connect_to_server(self):
        """Connect to MCP server."""
        url = self.url_edit.text()
        if not url:
            QMessageBox.warning(self, "Connection Error", "Please enter a server URL")
            return

        self.response_text.clear()
        self.response_text.append(f"Connecting to {url}...")

        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(self._connect_async(url))

        if success:
            # Add to recent connections
            self._save_recent_connection(url)
            self.server_url = url

            # Update UI
            if self.recent_servers.findText(url) == -1:
                self.recent_servers.addItem(url)

            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)

            # Fetch server capabilities
            self._fetch_capabilities()

            self.client_connected.emit(url)
            self.response_text.append("Connected successfully")
        else:
            self.response_text.append("Failed to connect to server")
            QMessageBox.critical(self, "Connection Error",
                                 "Failed to connect to server. See log for details.")

    def _fetch_capabilities(self):
        """Fetch server capabilities."""
        if not self.client:
            return

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._fetch_capabilities_async())

    async def _fetch_capabilities_async(self):
        """Fetch server capabilities asynchronously."""
        if not self.client:
            return

        try:
            # Fetch and display tools
            await self.client.fetch_tools()
            self.tools_table.setRowCount(0)
            for tool in self.client.tools:
                row = self.tools_table.rowCount()
                self.tools_table.insertRow(row)
                self.tools_table.setItem(row, 0, QTableWidgetItem(tool.name))
                self.tools_table.setItem(row, 1, QTableWidgetItem(tool.description))

            # Fetch and display resources
            await self.client.fetch_resources()
            self.resources_table.setRowCount(0)
            for resource in self.client.resources:
                row = self.resources_table.rowCount()
                self.resources_table.insertRow(row)
                self.resources_table.setItem(row, 0, QTableWidgetItem(resource.uri_template))
                self.resources_table.setItem(row, 1, QTableWidgetItem(resource.description))

            # Fetch and display prompts
            await self.client.fetch_prompts()
            self.prompts_table.setRowCount(0)
            for prompt in self.client.prompts:
                row = self.prompts_table.rowCount()
                self.prompts_table.insertRow(row)
                self.prompts_table.setItem(row, 0, QTableWidgetItem(prompt.name))
                self.prompts_table.setItem(row, 1, QTableWidgetItem(prompt.description))

        except Exception as e:
            logger.error(f"Error fetching capabilities: {e}")
            self.response_text.append(f"Error fetching server capabilities: {str(e)}")

    async def _disconnect_async(self) -> bool:
        """Disconnect from MCP server asynchronously."""
        try:
            if self.client:
                await self.client.disconnect()
                self.client = None
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from server: {e}")
            return False

    def _disconnect_from_server(self):
        """Disconnect from MCP server."""
        self.response_text.append("Disconnecting from server...")

        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(self._disconnect_async())

        # Update UI
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
        self.tool_info.setText("No tool selected")
        self.current_tool = None
        self.current_resource = None
        self.current_prompt = None

        # Clear tables
        self.tools_table.setRowCount(0)
        self.resources_table.setRowCount(0)
        self.prompts_table.setRowCount(0)

        self.client_disconnected.emit()
        self.response_text.append("Disconnected successfully")

    def _tool_clicked(self, item):
        """Handle tool click from table (enables Execute button)."""
        if not self.client:
            return

        row = item.row()
        tool_name = self.tools_table.item(row, 0).text()

        # Find tool in client
        for tool in self.client.tools:
            if tool.name == tool_name:
                self.current_tool = tool
                self.tool_info.setText(f"<b>Tool:</b> {tool.name} - {tool.description}")
                self.execute_btn.setEnabled(True)

                # Create a placeholder for input based on schema
                if tool.input_schema and "properties" in tool.input_schema:
                    placeholder = "{\n"
                    for param_name, param_info in tool.input_schema["properties"].items():
                        desc = param_info.get("description", "")
                        placeholder += f'    "{param_name}": "", // {desc}\n'
                    placeholder += "}"
                    self.input_text.setPlaceholderText(placeholder)
                else:
                    self.input_text.setPlaceholderText("")

                # Emit tool selected signal
                self.tool_selected.emit(tool.name, self.server_url)
                break

    def _resource_clicked(self, item):
        """Handle resource click from table."""
        if not self.client:
            return

        row = item.row()
        uri_template = self.resources_table.item(row, 0).text()
        description = self.resources_table.item(row, 1).text()

        self.tool_info.setText(f"<b>Resource:</b> {uri_template} - {description}")
        self.execute_btn.setEnabled(True)
        self.input_text.clear()
        self.input_text.setPlaceholderText("Enter the resource URI")
        self.input_text.setFocus()
        self.current_tool = None

    def _prompt_clicked(self, item):
        """Handle prompt click from table."""
        if not self.client:
            return

        row = item.row()
        prompt_name = self.prompts_table.item(row, 0).text()
        description = self.prompts_table.item(row, 1).text()

        self.tool_info.setText(f"<b>Prompt:</b> {prompt_name} - {description}")
        self.execute_btn.setEnabled(True)
        self.input_text.clear()
        self.input_text.setPlaceholderText("Enter your prompt text")
        self.input_text.setFocus()
        self.current_tool = None

    async def _execute_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> List[Content]:
        """Execute tool asynchronously."""
        try:
            return await self.client.call_tool(tool_name, **arguments)
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return [TextContent(f"Error: {str(e)}")]

    async def _request_resource_async(self, uri: str) -> List[Content]:
        """Request resource asynchronously."""
        try:
            return await self.client.request_resource(uri)
        except Exception as e:
            logger.error(f"Error requesting resource: {e}")
            return [TextContent(f"Error: {str(e)}")]

    async def _send_prompt_async(self, prompt_name: str, text: str) -> List[Content]:
        """Send prompt asynchronously."""
        try:
            return await self.client.send_prompt(prompt_name, text)
        except Exception as e:
            logger.error(f"Error sending prompt: {e}")
            return [TextContent(f"Error: {str(e)}")]

    def _execute(self):
        """Execute selected tool, resource, or prompt."""
        if not self.client:
            QMessageBox.warning(self, "Not Connected", "Please connect to a server first")
            return

        info_text = self.tool_info.text()

        if info_text.startswith("<b>Tool:</b>"):
            self._execute_selected_tool()
        elif info_text.startswith("<b>Resource:</b>"):
            self._execute_selected_resource()
        elif info_text.startswith("<b>Prompt:</b>"):
            self._execute_selected_prompt()
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a tool, resource, or prompt first")

    def _execute_selected_tool(self):
        """Execute the selected tool."""
        if not self.current_tool:
            return

        # Get input parameters
        tool_dialog = ToolInputDialog(self.current_tool, self)
        if tool_dialog.exec():
            arguments = tool_dialog.get_input_values()

            # Display the request
            self.response_text.append(f"Executing tool '{self.current_tool.name}' with arguments:")
            self.response_text.append(json.dumps(arguments, indent=2))

            # Execute tool
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                self._execute_tool_async(self.current_tool.name, arguments)
            )

            # Display response
            self.response_text.append("\nResponse:")
            for content in result:
                if hasattr(content, "text"):
                    self.response_text.append(content.text)
                else:
                    self.response_text.append(str(content.to_dict()))

    def _execute_selected_resource(self):
        """Execute the selected resource."""
        uri = self.input_text.toPlainText().strip()
        if not uri:
            QMessageBox.warning(self, "Input Error", "Please enter a resource URI")
            return

        # Display the request
        self.response_text.append(f"Requesting resource: {uri}")

        # Execute request
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self._request_resource_async(uri))

        # Display response
        self.response_text.append("\nResponse:")
        for content in result:
            if hasattr(content, "text"):
                self.response_text.append(content.text)
            else:
                self.response_text.append(str(content.to_dict()))

    def _execute_selected_prompt(self):
        """Execute the selected prompt."""
        prompt_name = self.tool_info.text().split("<b>Prompt:</b> ")[1].split(" - ")[0]
        text = self.input_text.toPlainText().strip()

        if not text:
            QMessageBox.warning(self, "Input Error", "Please enter prompt text")
            return

        # Display the request
        self.response_text.append(f"Sending prompt '{prompt_name}' with text:\n{text}")

        # Execute prompt
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self._send_prompt_async(prompt_name, text))

        # Display response
        self.response_text.append("\nResponse:")
        for content in result:
            if hasattr(content, "text"):
                self.response_text.append(content.text)
            else:
                self.response_text.append(str(content.to_dict()))
