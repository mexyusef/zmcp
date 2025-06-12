"""
ZMCP Main Window

Main window implementation for ZMCP application.
"""
import sys
import logging
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QDockWidget,
    QMenuBar, QStatusBar, QMessageBox, QSplitter, QVBoxLayout, QWidget, QTextEdit
)

from zmcp.core.config import config
from zmcp.ui.server_panel import ServerPanel
from zmcp.ui.client_panel import ClientPanel
from zmcp.ui.a2a_tab import A2ATab
from zmcp.ui.tools_panel import ToolsPanel
from zmcp.ui.session_panel import SessionPanel
from zmcp.ui.server_config_dialog import ServerConfigDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window for ZMCP application."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.setWindowTitle("ZMCP - MCP Client/Server")
        self.resize(1200, 800)

        self._init_ui()
        self._setup_menu()
        self._connect_signals()
        self._restore_settings()

    def _init_ui(self):
        """Initialize UI components."""
        # Central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create panels
        self.server_panel = ServerPanel()
        self.client_panel = ClientPanel()
        self.a2a_panel = A2ATab(None, self)  # Pass None for parent as it's added to tabs

        # Add tabs
        self.tabs.addTab(self.server_panel, "Server")
        self.tabs.addTab(self.client_panel, "Client")
        self.tabs.addTab(self.a2a_panel, "A2A")

        # Create dock widgets
        self.tools_dock = QDockWidget("Tools", self)
        self.tools_dock.setObjectName("ToolsDockWidget")
        self.tools_panel = ToolsPanel()
        self.tools_dock.setWidget(self.tools_panel)
        self.tools_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea |
                                        Qt.DockWidgetArea.RightDockWidgetArea)

        self.session_dock = QDockWidget("Session", self)
        self.session_dock.setObjectName("SessionDockWidget")
        self.session_panel = SessionPanel()
        self.session_dock.setWidget(self.session_panel)
        self.session_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea |
                                         Qt.DockWidgetArea.TopDockWidgetArea)

        # Add dock widgets
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.tools_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.session_dock)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _connect_signals(self):
        """Connect signals between components."""
        # Server signals
        self.server_panel.server_started.connect(self._on_server_started)
        self.server_panel.server_stopped.connect(self._on_server_stopped)

        # Client signals
        self.client_panel.client_connected.connect(self._on_client_connected)
        self.client_panel.client_disconnected.connect(self._on_client_disconnected)

        # Session signals
        self.session_panel.session_message.connect(self._on_session_message)

    def _setup_menu(self):
        """Set up menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Session", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_session)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Session", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_session)
        file_menu.addAction(open_action)

        save_action = QAction("&Save Session", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_session)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        preferences_action = QAction("&Preferences", self)
        preferences_action.triggered.connect(self._edit_preferences)
        file_menu.addAction(preferences_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        toggle_tools_action = QAction("&Tools Panel", self)
        toggle_tools_action.setCheckable(True)
        toggle_tools_action.setChecked(True)
        toggle_tools_action.triggered.connect(
            lambda checked: self.tools_dock.setVisible(checked)
        )
        view_menu.addAction(toggle_tools_action)

        toggle_session_action = QAction("&Session Panel", self)
        toggle_session_action.setCheckable(True)
        toggle_session_action.setChecked(True)
        toggle_session_action.triggered.connect(
            lambda checked: self.session_dock.setVisible(checked)
        )
        view_menu.addAction(toggle_session_action)

        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")

        light_theme_action = QAction("&Light", self)
        light_theme_action.setCheckable(True)
        light_theme_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(light_theme_action)

        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(dark_theme_action)

        deep_blue_theme_action = QAction("Deep &Blue", self)
        deep_blue_theme_action.setCheckable(True)
        deep_blue_theme_action.triggered.connect(lambda: self._set_theme("deep_blue"))
        theme_menu.addAction(deep_blue_theme_action)

        # Server menu
        server_menu = menu_bar.addMenu("&Server")

        config_server_action = QAction("&Configure Server", self)
        config_server_action.triggered.connect(self._configure_server)
        server_menu.addAction(config_server_action)

        server_menu.addSeparator()

        start_server_action = QAction("&Start Server", self)
        start_server_action.triggered.connect(self._start_server)
        server_menu.addAction(start_server_action)

        stop_server_action = QAction("S&top Server", self)
        stop_server_action.triggered.connect(self._stop_server)
        server_menu.addAction(stop_server_action)

        # Client menu
        client_menu = menu_bar.addMenu("&Client")

        connect_action = QAction("&Connect to Server", self)
        connect_action.triggered.connect(self._connect_to_server)
        client_menu.addAction(connect_action)

        disconnect_action = QAction("&Disconnect", self)
        disconnect_action.triggered.connect(self._disconnect_from_server)
        client_menu.addAction(disconnect_action)

        # A2A menu
        a2a_menu = menu_bar.addMenu("&A2A")

        start_a2a_server_action = QAction("Start A2A &Server", self)
        start_a2a_server_action.triggered.connect(self._start_a2a_server)
        a2a_menu.addAction(start_a2a_server_action)

        stop_a2a_server_action = QAction("Stop A2A S&erver", self)
        stop_a2a_server_action.triggered.connect(self._stop_a2a_server)
        a2a_menu.addAction(stop_a2a_server_action)

        a2a_menu.addSeparator()

        connect_a2a_action = QAction("&Connect to A2A Agent", self)
        connect_a2a_action.triggered.connect(self._connect_to_a2a_agent)
        a2a_menu.addAction(connect_a2a_action)

        disconnect_a2a_action = QAction("&Disconnect from A2A Agent", self)
        disconnect_a2a_action.triggered.connect(self._disconnect_from_a2a_agent)
        a2a_menu.addAction(disconnect_a2a_action)

        a2a_menu.addSeparator()

        import_card_action = QAction("&Import Agent Card", self)
        import_card_action.triggered.connect(self._import_agent_card)
        a2a_menu.addAction(import_card_action)

        export_card_action = QAction("&Export Agent Card", self)
        export_card_action.triggered.connect(self._export_agent_card)
        a2a_menu.addAction(export_card_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        # Set initial theme based on settings
        theme = config.get("ui.theme", "light")
        if theme == "light":
            light_theme_action.setChecked(True)
        elif theme == "dark":
            dark_theme_action.setChecked(True)
        elif theme == "deep_blue":
            deep_blue_theme_action.setChecked(True)
        self._set_theme(theme)

    def _restore_settings(self):
        """Restore window settings."""
        settings = QSettings("ZMCP", "ZMCP")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = settings.value("windowState")
        if state:
            self.restoreState(state)

    def _save_settings(self):
        """Save window settings."""
        settings = QSettings("ZMCP", "ZMCP")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def closeEvent(self, event):
        """Handle window close event."""
        self._save_settings()

        # Check if server is running
        if hasattr(self.server_panel, "server_running") and self.server_panel.server_running:
            reply = QMessageBox.question(
                self, "Exit Confirmation",
                "The server is still running. Do you want to stop it before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self._stop_server()

        # Check if A2A server is running
        if hasattr(self.a2a_panel, "server_tab") and hasattr(self.a2a_panel.server_tab, "status_label") and self.a2a_panel.server_tab.status_label.text() == "Running":
            reply = QMessageBox.question(
                self, "Exit Confirmation",
                "The A2A server is still running. Do you want to stop it before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self._stop_a2a_server()

        # Make sure A2A dock widgets are properly closed
        if hasattr(self.a2a_panel, "log_dock"):
            self.a2a_panel.log_dock.close()

        if hasattr(self.a2a_panel, "task_dock"):
            self.a2a_panel.task_dock.close()

        event.accept()

    def _set_theme(self, theme):
        """Set application theme."""
        config.set("ui.theme", theme)

        if theme == "dark":
            self._apply_dark_theme()
        elif theme == "deep_blue":
            self._apply_deep_blue_theme()
        else:
            self._apply_light_theme()

    def _apply_light_theme(self):
        """Apply light theme to application."""
        self.setStyleSheet("")  # Reset to default

    def _apply_dark_theme(self):
        """Apply dark theme to application."""
        # A simple dark theme
        self.setStyleSheet("""
            QMainWindow, QDialog, QWidget {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
            }
            QTabBar::tab {
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #555555;
                padding: 5px 10px;
            }
            QTabBar::tab:selected {
                background-color: #454545;
            }
            QGroupBox {
                border: 1px solid #555555;
                margin-top: 2.5ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #e0e0e0;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                margin-top: 0.5ex;
                background-color: #2d2d2d;
            }
            QTableWidget {
                background-color: #252525;
                alternate-background-color: #2a2a2a;
                color: #e0e0e0;
                gridline-color: #555555;
            }
            QTableWidget QHeaderView::section {
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #555555;
            }
            QLineEdit, QTextEdit {
                background-color: #252525;
                color: #e0e0e0;
                border: 1px solid #555555;
            }
            QPushButton {
                background-color: #454545;
                color: #e0e0e0;
                border: 1px solid #555555;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #353535;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QMenu::item:selected {
                background-color: #454545;
            }
            QStatusBar {
                background-color: #353535;
                color: #e0e0e0;
            }
        """)

    def _apply_deep_blue_theme(self):
        """Apply deep blue theme with neon yellow text."""
        self.setStyleSheet("""
            QMainWindow, QDialog, QWidget {
                background-color: #0a1929;
                color: #eeff00;
            }
            QTabWidget::pane {
                border: 1px solid #1e3a5f;
            }
            QTabBar::tab {
                background-color: #0f2744;
                color: #eeff00;
                border: 1px solid #1e3a5f;
                padding: 5px 10px;
            }
            QTabBar::tab:selected {
                background-color: #1e3a5f;
            }
            QGroupBox {
                border: 1px solid #1e3a5f;
                margin-top: 2.5ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #eeff00;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                margin-top: 0.5ex;
                background-color: #0a1929;
            }
            QTableWidget {
                background-color: #0f2744;
                alternate-background-color: #132f52;
                color: #eeff00;
                gridline-color: #1e3a5f;
            }
            QTableWidget QHeaderView::section {
                background-color: #1e3a5f;
                color: #eeff00;
                border: 1px solid #1e3a5f;
            }
            QLineEdit, QTextEdit {
                background-color: #0f2744;
                color: #eeff00;
                border: 1px solid #1e3a5f;
            }
            QPushButton {
                background-color: #1e3a5f;
                color: #eeff00;
                border: 1px solid #1e3a5f;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #2a4e7a;
            }
            QPushButton:pressed {
                background-color: #0f2744;
            }
            QMenu {
                background-color: #0a1929;
                color: #eeff00;
            }
            QMenu::item:selected {
                background-color: #1e3a5f;
            }
            QStatusBar {
                background-color: #0f2744;
                color: #eeff00;
            }
            QTreeWidget {
                background-color: #0f2744;
                color: #eeff00;
                alternate-background-color: #132f52;
                border: 1px solid #1e3a5f;
            }
            QTreeWidget::item:selected {
                background-color: #2a4e7a;
            }
            QHeaderView::section {
                background-color: #1e3a5f;
                color: #eeff00;
                border: 1px solid #1e3a5f;
            }
            QComboBox {
                background-color: #0f2744;
                color: #eeff00;
                border: 1px solid #1e3a5f;
            }
            QComboBox QAbstractItemView {
                background-color: #0f2744;
                color: #eeff00;
                selection-background-color: #1e3a5f;
            }
        """)

    def _edit_preferences(self):
        """Edit application preferences."""
        # A simple preferences dialog could be added here
        QMessageBox.information(self, "Preferences",
                               "Preferences dialog would be implemented here.")

    def _new_session(self):
        """Create new session."""
        self.session_panel.new_session()
        self.status_bar.showMessage("New session created")

    def _open_session(self):
        """Open existing session."""
        self.session_panel.open_session()
        self.status_bar.showMessage("Session opened")

    def _save_session(self):
        """Save current session."""
        self.session_panel.save_session()
        self.status_bar.showMessage("Session saved")

    def _configure_server(self):
        """Open server configuration dialog."""
        dialog = ServerConfigDialog(self)
        if dialog.exec():
            self.status_bar.showMessage("Server configuration updated")
            # Refresh server panel if needed
            self.server_panel._populate_ui_from_config()

    def _start_server(self):
        """Start MCP server."""
        self.tabs.setCurrentWidget(self.server_panel)
        self.server_panel._start_server()

    def _stop_server(self):
        """Stop MCP server."""
        self.server_panel._stop_server()

    def _connect_to_server(self):
        """Connect to MCP server."""
        self.tabs.setCurrentWidget(self.client_panel)
        self.client_panel._connect_to_server()

    def _disconnect_from_server(self):
        """Disconnect from MCP server."""
        self.client_panel._disconnect_from_server()

    def _start_a2a_server(self):
        """Start A2A server."""
        self.tabs.setCurrentWidget(self.a2a_panel)
        # Switch to server tab
        self.a2a_panel.notebook.setCurrentIndex(0)  # Select the first tab (Server)
        # Start the server
        self.a2a_panel.server_tab._start_server()

    def _stop_a2a_server(self):
        """Stop A2A server."""
        self.tabs.setCurrentWidget(self.a2a_panel)
        # Switch to server tab
        self.a2a_panel.notebook.setCurrentIndex(0)  # Select the first tab (Server)
        # Stop the server
        self.a2a_panel.server_tab._stop_server()

    def _connect_to_a2a_agent(self):
        """Connect to A2A agent."""
        self.tabs.setCurrentWidget(self.a2a_panel)
        # Switch to client tab
        self.a2a_panel.notebook.setCurrentIndex(1)  # Select the second tab (Client)
        # Connect to agent
        self.a2a_panel.client_tab._connect()

    def _disconnect_from_a2a_agent(self):
        """Disconnect from A2A agent."""
        self.tabs.setCurrentWidget(self.a2a_panel)
        # Switch to client tab
        self.a2a_panel.notebook.setCurrentIndex(1)  # Select the second tab (Client)
        # Disconnect from agent
        self.a2a_panel.client_tab._disconnect()

    def _import_agent_card(self):
        """Import agent card."""
        self.tabs.setCurrentWidget(self.a2a_panel)
        # Switch to client tab
        self.a2a_panel.notebook.setCurrentIndex(1)  # Select the second tab (Client)
        # Import agent card
        self.a2a_panel.client_tab._import_card()

    def _export_agent_card(self):
        """Export agent card."""
        self.tabs.setCurrentWidget(self.a2a_panel)
        # Open dialog to export the agent card
        QMessageBox.information(self, "Export Agent Card",
                               "This would open a dialog to export the agent card.")

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About ZMCP",
            """<h2>ZMCP - MCP Client/Server</h2>
            <p>Version 1.0</p>
            <p>A desktop application
            implementing the Model Context Protocol (MCP).</p>
            <p>Provides both server and client capabilities in a modern,
            modular interface.</p>
            <p>Now with Agent-to-Agent (A2A) protocol support!</p>"""
        )

    def _on_server_started(self):
        """Handle server started event."""
        self.status_bar.showMessage("Server started")
        if hasattr(self.client_panel, "url_edit"):
            # Pre-fill client URL with local server info
            if hasattr(self.server_panel, "server_config"):
                host = self.server_panel.server_config.get("host", "localhost")
                port = self.server_panel.server_config.get("port", 8000)
                self.client_panel.url_edit.setText(f"http://{host}:{port}")

    def _on_server_stopped(self):
        """Handle server stopped event."""
        self.status_bar.showMessage("Server stopped")

    def _on_client_connected(self, url):
        """Handle client connected event."""
        self.status_bar.showMessage(f"Connected to {url}")

        # Update tools panel with client's tools, resources, and prompts
        if hasattr(self.client_panel, "client") and self.client_panel.client:
            server_name = url.split("://")[-1]  # Extract server name from URL

            # Update tools
            if hasattr(self.client_panel.client, "tools"):
                self.tools_panel.update_server_tools(url, server_name, self.client_panel.client.tools)

            # Update resources
            if hasattr(self.client_panel.client, "resources"):
                self.tools_panel.update_server_resources(url, server_name, self.client_panel.client.resources)

            # Update prompts
            if hasattr(self.client_panel.client, "prompts"):
                self.tools_panel.update_server_prompts(url, server_name, self.client_panel.client.prompts)

    def _on_client_disconnected(self):
        """Handle client disconnected event."""
        self.status_bar.showMessage("Disconnected from server")

        # Remove server from tools panel
        if hasattr(self.client_panel, "server_url") and self.client_panel.server_url:
            self.tools_panel.remove_server(self.client_panel.server_url)

    def _on_session_message(self, message):
        """Handle session message event."""
        self.status_bar.showMessage(message)
