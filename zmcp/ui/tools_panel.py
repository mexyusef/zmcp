"""
ZMCP Tools Panel

Panel displaying available tools and resources.
"""
import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSettings
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QMenu, QMessageBox,
    QHeaderView, QSplitter
)
from PyQt6.QtGui import QIcon, QAction, QFont

from zmcp.core.mcp import Tool, Resource, Prompt

logger = logging.getLogger(__name__)


class ToolsPanel(QWidget):
    """Panel displaying available tools and resources."""

    tool_selected = pyqtSignal(str, str)  # Tool name, server URL

    def __init__(self):
        """Initialize tools panel."""
        super().__init__()
        self.servers = {}  # Dict of server_url -> {"tools": [...], "resources": [...], "prompts": [...]}
        self.favorites = []  # List of favorite tools
        self._init_ui()
        self._load_favorites()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Create tabs for different types of capabilities
        self.tabs = QTabWidget()

        # Tools tab
        self.tools_tab = QWidget()
        tools_layout = QVBoxLayout()
        tools_layout.setContentsMargins(0, 0, 0, 0)

        self.tools_tree = QTreeWidget()
        self.tools_tree.setHeaderLabels(["Name", "Description"])
        self.tools_tree.setColumnCount(2)
        self.tools_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tools_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tools_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tools_tree.customContextMenuRequested.connect(self._show_tools_context_menu)
        self.tools_tree.itemDoubleClicked.connect(self._tool_double_clicked)

        tools_layout.addWidget(self.tools_tree)
        self.tools_tab.setLayout(tools_layout)

        # Resources tab
        self.resources_tab = QWidget()
        resources_layout = QVBoxLayout()
        resources_layout.setContentsMargins(0, 0, 0, 0)

        self.resources_tree = QTreeWidget()
        self.resources_tree.setHeaderLabels(["Name", "Description"])
        self.resources_tree.setColumnCount(2)
        self.resources_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.resources_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.resources_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.resources_tree.customContextMenuRequested.connect(self._show_resources_context_menu)
        self.resources_tree.itemDoubleClicked.connect(self._resource_double_clicked)

        resources_layout.addWidget(self.resources_tree)
        self.resources_tab.setLayout(resources_layout)

        # Prompts tab
        self.prompts_tab = QWidget()
        prompts_layout = QVBoxLayout()
        prompts_layout.setContentsMargins(0, 0, 0, 0)

        self.prompts_tree = QTreeWidget()
        self.prompts_tree.setHeaderLabels(["Name", "Description"])
        self.prompts_tree.setColumnCount(2)
        self.prompts_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.prompts_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.prompts_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.prompts_tree.customContextMenuRequested.connect(self._show_prompts_context_menu)
        self.prompts_tree.itemDoubleClicked.connect(self._prompt_double_clicked)

        prompts_layout.addWidget(self.prompts_tree)
        self.prompts_tab.setLayout(prompts_layout)

        # Add tabs
        self.tabs.addTab(self.tools_tab, "Tools")
        self.tabs.addTab(self.resources_tab, "Resources")
        self.tabs.addTab(self.prompts_tab, "Prompts")

        layout.addWidget(self.tabs)

        # Control buttons
        controls_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_tools)
        controls_layout.addWidget(self.refresh_btn)

        self.favorite_btn = QPushButton("Add to Favorites")
        self.favorite_btn.clicked.connect(self._add_to_favorites)
        controls_layout.addWidget(self.favorite_btn)

        layout.addLayout(controls_layout)

        self.setLayout(layout)

    def _load_favorites(self):
        """Load favorites from settings."""
        settings = QSettings("ZMCP", "ZMCP")
        self.favorites = settings.value("favorites", []) or []

    def _save_favorites(self):
        """Save favorites to settings."""
        settings = QSettings("ZMCP", "ZMCP")
        settings.setValue("favorites", self.favorites)

    def _show_tools_context_menu(self, position):
        """Show context menu for tools tree."""
        item = self.tools_tree.itemAt(position)
        if not item:
            return

        # Get tool data
        tool_name = item.text(0)
        server_url = item.data(0, Qt.ItemDataRole.UserRole)

        # Create menu
        menu = QMenu()

        # Execute action
        execute_action = QAction("Execute", self)
        execute_action.triggered.connect(lambda: self._execute_tool(tool_name, server_url))
        menu.addAction(execute_action)

        menu.addSeparator()

        # Favorite actions
        if f"{tool_name}|{server_url}" in self.favorites:
            remove_favorite_action = QAction("Remove from Favorites", self)
            remove_favorite_action.triggered.connect(lambda: self._remove_from_favorites(tool_name, server_url))
            menu.addAction(remove_favorite_action)
        else:
            add_favorite_action = QAction("Add to Favorites", self)
            add_favorite_action.triggered.connect(lambda: self._add_to_favorites(tool_name, server_url))
            menu.addAction(add_favorite_action)

        # Show menu
        menu.exec(self.tools_tree.viewport().mapToGlobal(position))

    def _show_resources_context_menu(self, position):
        """Show context menu for resources tree."""
        item = self.resources_tree.itemAt(position)
        if not item:
            return

        # Get resource data
        resource_name = item.text(0)
        server_url = item.data(0, Qt.ItemDataRole.UserRole)

        # Create menu
        menu = QMenu()

        # Execute action
        execute_action = QAction("Execute", self)
        execute_action.triggered.connect(lambda: self._execute_resource(resource_name, server_url))
        menu.addAction(execute_action)

        menu.addSeparator()

        # Favorite actions
        if f"{resource_name}|{server_url}" in self.favorites:
            remove_favorite_action = QAction("Remove from Favorites", self)
            remove_favorite_action.triggered.connect(lambda: self._remove_from_favorites(resource_name, server_url))
            menu.addAction(remove_favorite_action)
        else:
            add_favorite_action = QAction("Add to Favorites", self)
            add_favorite_action.triggered.connect(lambda: self._add_to_favorites(resource_name, server_url))
            menu.addAction(add_favorite_action)

        # Show menu
        menu.exec(self.resources_tree.viewport().mapToGlobal(position))

    def _show_prompts_context_menu(self, position):
        """Show context menu for prompts tree."""
        item = self.prompts_tree.itemAt(position)
        if not item:
            return

        # Get prompt data
        prompt_name = item.text(0)
        server_url = item.data(0, Qt.ItemDataRole.UserRole)

        # Create menu
        menu = QMenu()

        # Execute action
        execute_action = QAction("Execute", self)
        execute_action.triggered.connect(lambda: self._execute_prompt(prompt_name, server_url))
        menu.addAction(execute_action)

        menu.addSeparator()

        # Favorite actions
        if f"{prompt_name}|{server_url}" in self.favorites:
            remove_favorite_action = QAction("Remove from Favorites", self)
            remove_favorite_action.triggered.connect(lambda: self._remove_from_favorites(prompt_name, server_url))
            menu.addAction(remove_favorite_action)
        else:
            add_favorite_action = QAction("Add to Favorites", self)
            add_favorite_action.triggered.connect(lambda: self._add_to_favorites(prompt_name, server_url))
            menu.addAction(add_favorite_action)

        # Show menu
        menu.exec(self.prompts_tree.viewport().mapToGlobal(position))

    def _execute_tool(self, tool_name, server_url):
        """Execute a tool."""
        self.tool_selected.emit(tool_name, server_url)

    def _execute_resource(self, resource_name, server_url):
        """Execute a resource."""
        self.tool_selected.emit(resource_name, server_url)

    def _execute_prompt(self, prompt_name, server_url):
        """Execute a prompt."""
        self.tool_selected.emit(prompt_name, server_url)

    def _add_to_favorites(self, name, server_url):
        """Add a tool, resource, or prompt to favorites."""
        favorite_id = f"{name}|{server_url}"
        if favorite_id not in self.favorites:
            self.favorites.append(favorite_id)
            self._save_favorites()
            self._refresh_trees()

    def _remove_from_favorites(self, name, server_url):
        """Remove a tool, resource, or prompt from favorites."""
        favorite_id = f"{name}|{server_url}"
        if favorite_id in self.favorites:
            self.favorites.remove(favorite_id)
            self._save_favorites()
            self._refresh_trees()

    def _tool_double_clicked(self, item, column):
        """Handle double-click on a tool."""
        tool_name = item.text(0)
        server_url = item.data(0, Qt.ItemDataRole.UserRole)
        self._execute_tool(tool_name, server_url)

    def _resource_double_clicked(self, item, column):
        """Handle double-click on a resource."""
        resource_name = item.text(0)
        server_url = item.data(0, Qt.ItemDataRole.UserRole)
        self._execute_resource(resource_name, server_url)

    def _prompt_double_clicked(self, item, column):
        """Handle double-click on a prompt."""
        prompt_name = item.text(0)
        server_url = item.data(0, Qt.ItemDataRole.UserRole)
        self._execute_prompt(prompt_name, server_url)

    def _refresh_tools(self):
        """Refresh tools list."""
        # This will be triggered by the main window when servers change
        self._refresh_trees()

    def _refresh_trees(self):
        """Refresh all tree widgets."""
        self._refresh_tools_tree()
        self._refresh_resources_tree()
        self._refresh_prompts_tree()

    def _refresh_tools_tree(self):
        """Refresh tools tree widget."""
        # Clear tree
        self.tools_tree.clear()

        # Add favorites group
        favorites_item = QTreeWidgetItem(["Favorites"])
        favorites_item.setExpanded(True)
        bold_font = QFont()
        bold_font.setBold(True)
        favorites_item.setFont(0, bold_font)
        self.tools_tree.addTopLevelItem(favorites_item)

        # Add favorites
        for favorite in self.favorites:
            name, server_url = favorite.split("|")

            # Check if server exists
            if server_url not in self.servers:
                continue

            # Check if tool exists in server
            server_data = self.servers[server_url]
            tool_exists = False
            for tool in server_data.get("tools", []):
                # Handle both Tool objects and dictionaries
                if hasattr(tool, "name"):
                    tool_name = tool.name
                    tool_description = tool.description
                else:
                    tool_name = tool.get("name", "")
                    tool_description = tool.get("description", "")

                if tool_name == name:
                    tool_exists = True

                    # Add favorite item
                    item = QTreeWidgetItem([name, tool_description])
                    item.setData(0, Qt.ItemDataRole.UserRole, server_url)
                    favorites_item.addChild(item)
                    break

        # Add servers
        for server_url, server_data in self.servers.items():
            server_item = QTreeWidgetItem([server_data["name"]])
            server_item.setExpanded(True)
            bold_font = QFont()
            bold_font.setBold(True)
            server_item.setFont(0, bold_font)
            self.tools_tree.addTopLevelItem(server_item)

            # Add tools
            for tool in server_data.get("tools", []):
                # Handle both Tool objects and dictionaries
                if hasattr(tool, "name"):
                    name = tool.name
                    description = tool.description
                else:
                    name = tool.get("name", "")
                    description = tool.get("description", "")

                item = QTreeWidgetItem([name, description])
                item.setData(0, Qt.ItemDataRole.UserRole, server_url)
                server_item.addChild(item)

    def _refresh_resources_tree(self):
        """Refresh resources tree widget."""
        # Clear tree
        self.resources_tree.clear()

        # Add favorites group
        favorites_item = QTreeWidgetItem(["Favorites"])
        favorites_item.setExpanded(True)
        bold_font = QFont()
        bold_font.setBold(True)
        favorites_item.setFont(0, bold_font)
        self.resources_tree.addTopLevelItem(favorites_item)

        # Add favorites
        for favorite in self.favorites:
            name, server_url = favorite.split("|")

            # Check if server exists
            if server_url not in self.servers:
                continue

            # Check if resource exists in server
            server_data = self.servers[server_url]
            resource_exists = False
            for resource in server_data.get("resources", []):
                # Handle both Resource objects and dictionaries
                if hasattr(resource, "uri_template"):
                    resource_name = resource.uri_template
                    resource_description = resource.description
                else:
                    resource_name = resource.get("name", "")
                    resource_description = resource.get("description", "")

                if resource_name == name:
                    resource_exists = True

                    # Add favorite item
                    item = QTreeWidgetItem([name, resource_description])
                    item.setData(0, Qt.ItemDataRole.UserRole, server_url)
                    favorites_item.addChild(item)
                    break

        # Add servers
        for server_url, server_data in self.servers.items():
            server_item = QTreeWidgetItem([server_data["name"]])
            server_item.setExpanded(True)
            bold_font = QFont()
            bold_font.setBold(True)
            server_item.setFont(0, bold_font)
            self.resources_tree.addTopLevelItem(server_item)

            # Add resources
            for resource in server_data.get("resources", []):
                # Handle both Resource objects and dictionaries
                if hasattr(resource, "uri_template"):
                    name = resource.uri_template
                    description = resource.description
                else:
                    name = resource.get("name", "")
                    description = resource.get("description", "")

                item = QTreeWidgetItem([name, description])
                item.setData(0, Qt.ItemDataRole.UserRole, server_url)
                server_item.addChild(item)

    def _refresh_prompts_tree(self):
        """Refresh prompts tree widget."""
        # Clear tree
        self.prompts_tree.clear()

        # Add favorites group
        favorites_item = QTreeWidgetItem(["Favorites"])
        favorites_item.setExpanded(True)
        bold_font = QFont()
        bold_font.setBold(True)
        favorites_item.setFont(0, bold_font)
        self.prompts_tree.addTopLevelItem(favorites_item)

        # Add favorites
        for favorite in self.favorites:
            name, server_url = favorite.split("|")

            # Check if server exists
            if server_url not in self.servers:
                continue

            # Check if prompt exists in server
            server_data = self.servers[server_url]
            prompt_exists = False
            for prompt in server_data.get("prompts", []):
                # Handle both Prompt objects and dictionaries
                if hasattr(prompt, "name"):
                    prompt_name = prompt.name
                    prompt_description = prompt.description
                else:
                    prompt_name = prompt.get("name", "")
                    prompt_description = prompt.get("description", "")

                if prompt_name == name:
                    prompt_exists = True

                    # Add favorite item
                    item = QTreeWidgetItem([name, prompt_description])
                    item.setData(0, Qt.ItemDataRole.UserRole, server_url)
                    favorites_item.addChild(item)
                    break

        # Add servers
        for server_url, server_data in self.servers.items():
            server_item = QTreeWidgetItem([server_data["name"]])
            server_item.setExpanded(True)
            bold_font = QFont()
            bold_font.setBold(True)
            server_item.setFont(0, bold_font)
            self.prompts_tree.addTopLevelItem(server_item)

            # Add prompts
            for prompt in server_data.get("prompts", []):
                # Handle both Prompt objects and dictionaries
                if hasattr(prompt, "name"):
                    name = prompt.name
                    description = prompt.description
                else:
                    name = prompt.get("name", "")
                    description = prompt.get("description", "")

                item = QTreeWidgetItem([name, description])
                item.setData(0, Qt.ItemDataRole.UserRole, server_url)
                server_item.addChild(item)

    @pyqtSlot(str, str, list)
    def update_server_tools(self, server_url: str, server_name: str, tools: List[Tool]):
        """
        Update tools for a server.

        Args:
            server_url: Server URL
            server_name: Server name
            tools: List of tools
        """
        if server_url not in self.servers:
            self.servers[server_url] = {"name": server_name}

        self.servers[server_url]["tools"] = tools
        self._refresh_trees()

    @pyqtSlot(str, str, list)
    def update_server_resources(self, server_url: str, server_name: str, resources: List[Resource]):
        """
        Update resources for a server.

        Args:
            server_url: Server URL
            server_name: Server name
            resources: List of resources
        """
        if server_url not in self.servers:
            self.servers[server_url] = {"name": server_name}

        self.servers[server_url]["resources"] = resources
        self._refresh_trees()

    @pyqtSlot(str, str, list)
    def update_server_prompts(self, server_url: str, server_name: str, prompts: List[Prompt]):
        """
        Update prompts for a server.

        Args:
            server_url: Server URL
            server_name: Server name
            prompts: List of prompts
        """
        if server_url not in self.servers:
            self.servers[server_url] = {"name": server_name}

        self.servers[server_url]["prompts"] = prompts
        self._refresh_trees()

    @pyqtSlot(str)
    def remove_server(self, server_url: str):
        """
        Remove a server.

        Args:
            server_url: Server URL
        """
        if server_url in self.servers:
            del self.servers[server_url]
            self._refresh_trees()
