"""
A2A Tab UI Implementation

This module implements the UI for the A2A protocol tab in the ZMCP application.
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QCheckBox, QFormLayout, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QSplitter, QDockWidget, QFileDialog
)

from zmcp.a2a.types import AgentCard, AgentSkill
from zmcp.bridge.mcp_to_a2a import MCPToolToA2AAgent
from zmcp.bridge.a2a_to_mcp import A2AAgentToMCPTool

logger = logging.getLogger(__name__)


class A2ATab(QWidget):
    """
    A2A Protocol Tab for the ZMCP UI.

    This tab provides interfaces for both A2A Server and A2A Client functionality.
    """

    def __init__(self, parent, main_app):
        """
        Initialize the A2A tab.

        Args:
            parent: Parent widget
            main_app: Main application instance
        """
        super().__init__(parent)
        self.main_app = main_app

        # Create layout
        layout = QVBoxLayout(self)

        # Create notebook for server/client tabs
        self.notebook = QTabWidget()
        layout.addWidget(self.notebook)

        # Create server and client tabs
        self.server_tab = A2AServerTab(self)
        self.client_tab = A2AClientTab(self)

        # Add tabs to notebook
        self.notebook.addTab(self.server_tab, "A2A Server")
        self.notebook.addTab(self.client_tab, "A2A Client")

        # Create dock widgets only if we have a main_app
        if self.main_app:
            self.create_dock_widgets()

    def create_dock_widgets(self):
        """Create dock widgets for the A2A tab."""
        # Log dock widget
        self.log_dock = QDockWidget("A2A Log", self.main_app)
        self.log_dock.setObjectName("A2ALogDockWidget")
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_dock.setWidget(self.log_widget)

        # Task dock widget
        self.task_dock = QDockWidget("A2A Tasks", self.main_app)
        self.task_dock.setObjectName("A2ATaskDockWidget")
        self.task_widget = QTableWidget(0, 4)
        self.task_widget.setHorizontalHeaderLabels(["Task ID", "Status", "Created", "Updated"])
        self.task_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.task_dock.setWidget(self.task_widget)

        # Add dock widgets to main window
        # Add Log dock below the Tools dock
        self.main_app.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.log_dock)

        # Add Tasks dock below the Log dock
        self.main_app.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.task_dock)

        # Stack the Log and Tasks docks
        self.main_app.tabifyDockWidget(self.log_dock, self.task_dock)


class A2AServerTab(QWidget):
    """
    A2A Server tab implementation.

    Allows users to create and manage A2A agents.
    """

    def __init__(self, parent):
        """
        Initialize the A2A Server tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.parent = parent
        self.main_app = parent.main_app
        self.server_running = False

        # Main layout
        layout = QVBoxLayout(self)

        # Create sections
        self._create_agent_config_section(layout)
        self._create_skills_section(layout)
        self._create_capabilities_section(layout)
        self._create_bridge_section(layout)
        self._create_server_control_section(layout)

        # Add stretch at the bottom
        layout.addStretch()

    def _create_agent_config_section(self, parent_layout):
        """Create the agent configuration section."""
        config_group = QGroupBox("Agent Configuration")
        config_layout = QFormLayout()
        config_group.setLayout(config_layout)

        # Agent name
        self.agent_name_edit = QLineEdit("ZMCP A2A Agent")
        config_layout.addRow("Agent Name:", self.agent_name_edit)

        # Description
        self.description_edit = QLineEdit("AI assistant powered by ZMCP")
        config_layout.addRow("Description:", self.description_edit)

        # Version
        self.version_edit = QLineEdit("1.0.0")
        config_layout.addRow("Version:", self.version_edit)

        # URL
        self.agent_url_edit = QLineEdit("http://localhost:8000")
        config_layout.addRow("URL:", self.agent_url_edit)

        # Input modes
        self.input_modes_edit = QLineEdit("text/plain")
        config_layout.addRow("Input Modes:", self.input_modes_edit)

        # Output modes
        self.output_modes_edit = QLineEdit("text/plain")
        config_layout.addRow("Output Modes:", self.output_modes_edit)

        parent_layout.addWidget(config_group)

    def _create_skills_section(self, parent_layout):
        """Create the skills section."""
        skills_group = QGroupBox("Skills")
        skills_layout = QVBoxLayout()
        skills_group.setLayout(skills_layout)

        # Create treeview for skills
        self.skills_tree = QTreeWidget()
        self.skills_tree.setHeaderLabels(["ID", "Name", "Description", "Tags"])
        self.skills_tree.setColumnWidth(0, 100)
        self.skills_tree.setColumnWidth(1, 150)
        self.skills_tree.setColumnWidth(2, 300)
        self.skills_tree.setColumnWidth(3, 150)

        # Add some example skills
        self._add_example_skills()

        skills_layout.addWidget(self.skills_tree)

        # Add button layout
        button_layout = QHBoxLayout()

        # Add buttons
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_skill)
        button_layout.addWidget(add_button)

        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._remove_skill)
        button_layout.addWidget(remove_button)

        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._edit_skill)
        button_layout.addWidget(edit_button)

        skills_layout.addLayout(button_layout)
        parent_layout.addWidget(skills_group)

    def _add_example_skills(self):
        """Add example skills to the tree."""
        # Add general skill
        general_item = QTreeWidgetItem(["general", "Assistant", "General assistance", "assistant"])
        self.skills_tree.addTopLevelItem(general_item)

        # Add search skill
        search_item = QTreeWidgetItem(["search", "Search", "Web search", "web, search"])
        self.skills_tree.addTopLevelItem(search_item)

        # Add calculator skill
        calc_item = QTreeWidgetItem(["calc", "Calculator", "Math calculations", "math"])
        self.skills_tree.addTopLevelItem(calc_item)

    def _create_capabilities_section(self, parent_layout):
        """Create the capabilities section."""
        capabilities_group = QGroupBox("Capabilities")
        capabilities_layout = QVBoxLayout()
        capabilities_group.setLayout(capabilities_layout)

        # Streaming
        self.streaming_check = QCheckBox("Streaming")
        self.streaming_check.setChecked(True)
        capabilities_layout.addWidget(self.streaming_check)

        # Push notifications
        self.push_notifications_check = QCheckBox("Push Notifications")
        self.push_notifications_check.setChecked(False)
        capabilities_layout.addWidget(self.push_notifications_check)

        # State transition history
        self.state_history_check = QCheckBox("State Transition History")
        self.state_history_check.setChecked(True)
        capabilities_layout.addWidget(self.state_history_check)

        parent_layout.addWidget(capabilities_group)

    def _create_bridge_section(self, parent_layout):
        """Create the bridge configuration section."""
        bridge_group = QGroupBox("Bridge Configuration")
        bridge_layout = QVBoxLayout()
        bridge_group.setLayout(bridge_layout)

        # Expose as MCP Tools
        self.expose_mcp_check = QCheckBox("Expose as MCP Tools")
        self.expose_mcp_check.setChecked(True)
        bridge_layout.addWidget(self.expose_mcp_check)

        # Import MCP Tools as Skills
        self.import_mcp_check = QCheckBox("Import MCP Tools as Skills")
        self.import_mcp_check.setChecked(False)
        bridge_layout.addWidget(self.import_mcp_check)

        parent_layout.addWidget(bridge_group)

    def _create_server_control_section(self, parent_layout):
        """Create the server control section."""
        control_layout = QHBoxLayout()

        # Start/stop buttons
        start_button = QPushButton("Start Agent Server")
        start_button.clicked.connect(self._start_server)
        control_layout.addWidget(start_button)

        stop_button = QPushButton("Stop Agent Server")
        stop_button.clicked.connect(self._stop_server)
        control_layout.addWidget(stop_button)

        parent_layout.addLayout(control_layout)

        # Status layout
        status_layout = QHBoxLayout()

        # Status label
        status_layout.addWidget(QLabel("Server Status:"))
        self.status_label = QLabel("Stopped")
        status_layout.addWidget(self.status_label)

        # Port
        status_layout.addWidget(QLabel("Port:"))
        self.port_edit = QLineEdit("8080")
        self.port_edit.setMaximumWidth(80)
        status_layout.addWidget(self.port_edit)

        # Add stretch to push everything to the left
        status_layout.addStretch()

        parent_layout.addLayout(status_layout)

    def _add_skill(self):
        """Add a new skill."""
        # In a real implementation, this would open a dialog to add a skill
        QMessageBox.information(self, "Add Skill", "This would open a dialog to add a new skill.")

    def _remove_skill(self):
        """Remove the selected skill."""
        selected = self.skills_tree.selectedItems()
        if selected:
            for item in selected:
                index = self.skills_tree.indexOfTopLevelItem(item)
                self.skills_tree.takeTopLevelItem(index)
        else:
            QMessageBox.information(self, "Remove Skill", "Please select a skill to remove.")

    def _edit_skill(self):
        """Edit the selected skill."""
        selected = self.skills_tree.selectedItems()
        if selected:
            # In a real implementation, this would open a dialog to edit the skill
            QMessageBox.information(self, "Edit Skill", "This would open a dialog to edit the selected skill.")
        else:
            QMessageBox.information(self, "Edit Skill", "Please select a skill to edit.")

    def _start_server(self):
        """Start the A2A agent server."""
        # In a real implementation, this would start a FastAPI server
        self.status_label.setText("Running")
        QMessageBox.information(self, "Server Started", f"A2A agent server started on port {self.port_edit.text()}")

    def _stop_server(self):
        """Stop the A2A agent server."""
        # In a real implementation, this would stop the server
        self.status_label.setText("Stopped")
        QMessageBox.information(self, "Server Stopped", "A2A agent server stopped")


class A2AClientTab(QWidget):
    """
    A2A Client tab implementation.

    Allows users to connect to and interact with A2A agents.
    """

    def __init__(self, parent):
        """
        Initialize the A2A Client tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.parent = parent
        self.main_app = parent.main_app
        self.connected = False

        # Main layout
        layout = QVBoxLayout(self)

        # Create sections
        self._create_connection_section(layout)
        self._create_agent_info_section(layout)
        self._create_skills_section(layout)
        self._create_conversation_section(layout)

    def _create_connection_section(self, parent_layout):
        """Create the agent connection section."""
        connection_group = QGroupBox("Agent Connection")
        connection_layout = QVBoxLayout()
        connection_group.setLayout(connection_layout)

        # URL field layout
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Agent URL:"))
        self.url_edit = QLineEdit("https://agent.example.com/agent")
        url_layout.addWidget(self.url_edit)
        connection_layout.addLayout(url_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self._connect)
        buttons_layout.addWidget(connect_button)

        disconnect_button = QPushButton("Disconnect")
        disconnect_button.clicked.connect(self._disconnect)
        buttons_layout.addWidget(disconnect_button)

        import_button = QPushButton("Import Agent Card")
        import_button.clicked.connect(self._import_card)
        buttons_layout.addWidget(import_button)

        connection_layout.addLayout(buttons_layout)
        parent_layout.addWidget(connection_group)

    def _create_agent_info_section(self, parent_layout):
        """Create the agent information section."""
        info_group = QGroupBox("Agent Information")
        info_layout = QFormLayout()
        info_group.setLayout(info_layout)

        # Name
        self.agent_name_label = QLabel("")
        info_layout.addRow("Name:", self.agent_name_label)

        # Description
        self.description_label = QLabel("")
        info_layout.addRow("Description:", self.description_label)

        # Provider
        self.provider_label = QLabel("")
        info_layout.addRow("Provider:", self.provider_label)

        parent_layout.addWidget(info_group)

    def _create_skills_section(self, parent_layout):
        """Create the skills section."""
        skills_group = QGroupBox("Available Skills")
        skills_layout = QVBoxLayout()
        skills_group.setLayout(skills_layout)

        # Create treeview for skills
        self.skills_tree = QTreeWidget()
        self.skills_tree.setHeaderLabels(["ID", "Name", "Description"])
        self.skills_tree.setColumnWidth(0, 100)
        self.skills_tree.setColumnWidth(1, 150)
        self.skills_tree.setColumnWidth(2, 400)

        skills_layout.addWidget(self.skills_tree)

        # Import as MCP Tools checkbox
        checkbox_layout = QHBoxLayout()

        self.import_as_mcp_check = QCheckBox("Import as MCP Tools")
        self.import_as_mcp_check.setChecked(True)
        checkbox_layout.addWidget(self.import_as_mcp_check)

        import_button = QPushButton("Import Selected")
        import_button.clicked.connect(self._import_selected)
        checkbox_layout.addWidget(import_button)

        # Add stretch to push everything to the left
        checkbox_layout.addStretch()

        skills_layout.addLayout(checkbox_layout)
        parent_layout.addWidget(skills_group)

    def _create_conversation_section(self, parent_layout):
        """Create the conversation section."""
        conversation_group = QGroupBox("Conversation")
        conversation_layout = QVBoxLayout()
        conversation_group.setLayout(conversation_layout)

        # Message history
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        conversation_layout.addWidget(self.history_text)

        # Message input layout
        input_layout = QHBoxLayout()

        self.message_edit = QLineEdit()
        self.message_edit.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.message_edit)

        send_button = QPushButton("Send")
        send_button.clicked.connect(self._send_message)
        input_layout.addWidget(send_button)

        conversation_layout.addLayout(input_layout)
        parent_layout.addWidget(conversation_group)

    def _connect(self):
        """Connect to the A2A agent."""
        url = self.url_edit.text()

        # In a real implementation, this would connect to the agent and retrieve the agent card
        self.agent_name_label.setText("Example Agent")
        self.description_label.setText("AI assistant for various tasks")
        self.provider_label.setText("Example AI")

        # Add example skills
        self.skills_tree.clear()
        general_item = QTreeWidgetItem(["general", "Assistant", "General assistance capabilities"])
        self.skills_tree.addTopLevelItem(general_item)

        search_item = QTreeWidgetItem(["search", "Search", "Web search functionality"])
        self.skills_tree.addTopLevelItem(search_item)

        calc_item = QTreeWidgetItem(["calc", "Calculator", "Mathematical calculations"])
        self.skills_tree.addTopLevelItem(calc_item)

        # Add connection message to history
        self._add_to_history(f"Connected to agent at {url}")

    def _disconnect(self):
        """Disconnect from the A2A agent."""
        # In a real implementation, this would close the connection
        self.agent_name_label.setText("")
        self.description_label.setText("")
        self.provider_label.setText("")

        # Clear skills
        self.skills_tree.clear()

        # Add disconnection message to history
        self._add_to_history("Disconnected from agent")

    def _import_card(self):
        """Import an agent card from a file."""
        # In a real implementation, this would open a file dialog
        QMessageBox.information(self, "Import Agent Card", "This would open a file dialog to import an agent card.")

    def _import_selected(self):
        """Import selected skills as MCP tools."""
        selected = self.skills_tree.selectedItems()
        if selected:
            skill_ids = [item.text(0) for item in selected]

            # In a real implementation, this would import the skills as MCP tools
            QMessageBox.information(self, "Import Skills", f"Importing skills as MCP tools: {', '.join(skill_ids)}")
        else:
            QMessageBox.information(self, "Import Skills", "Please select skills to import.")

    def _send_message(self):
        """Send a message to the A2A agent."""
        message = self.message_edit.text()
        if not message:
            return

        # Add user message to history
        self._add_to_history(f"User: {message}")

        # In a real implementation, this would send the message to the agent and get a response
        response = f"Agent: I received your message: {message}"
        self._add_to_history(response)

        # Clear message input
        self.message_edit.clear()

    def _add_to_history(self, text):
        """Add text to the conversation history."""
        self.history_text.append(text)
