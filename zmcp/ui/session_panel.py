"""
ZMCP Session Panel

Panel for managing and viewing session history.
"""
import logging
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QSplitter, QComboBox
)

logger = logging.getLogger(__name__)


class SessionPanel(QWidget):
    """Panel for managing and viewing session history."""

    session_message = pyqtSignal(str)

    def __init__(self):
        """Initialize session panel."""
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Session controls
        controls_layout = QHBoxLayout()

        self.session_selector = QComboBox()
        self.session_selector.addItem("Current Session")
        self.session_selector.currentTextChanged.connect(self._session_selected)
        controls_layout.addWidget(QLabel("Session:"))
        controls_layout.addWidget(self.session_selector, 1)

        self.new_session_btn = QPushButton("New")
        self.new_session_btn.clicked.connect(self._new_session)
        controls_layout.addWidget(self.new_session_btn)

        self.save_session_btn = QPushButton("Save")
        self.save_session_btn.clicked.connect(self._save_session)
        controls_layout.addWidget(self.save_session_btn)

        self.export_session_btn = QPushButton("Export")
        self.export_session_btn.clicked.connect(self._export_session)
        controls_layout.addWidget(self.export_session_btn)

        layout.addLayout(controls_layout)

        # Session content
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Messages list
        self.messages_table = QTableWidget(0, 3)
        self.messages_table.setHorizontalHeaderLabels(["Time", "Type", "Content"])
        self.messages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.messages_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.messages_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.messages_table.verticalHeader().setVisible(False)
        self.messages_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.messages_table.itemSelectionChanged.connect(self._message_selected)
        content_splitter.addWidget(self.messages_table)

        # Message details
        self.message_details = QTextEdit()
        self.message_details.setReadOnly(True)
        content_splitter.addWidget(self.message_details)

        # Set initial splitter sizes
        content_splitter.setSizes([300, 500])

        layout.addWidget(content_splitter, 1)

        self.setLayout(layout)

        # Add sample data
        self._add_sample_data()

    def _add_sample_data(self):
        """Add sample session data."""
        sample_messages = [
            (QDateTime.currentDateTime().addSecs(-300), "Request", "Connect to server"),
            (QDateTime.currentDateTime().addSecs(-290), "Response", "Connected to http://localhost:8000"),
            (QDateTime.currentDateTime().addSecs(-280), "Request", "List tools"),
            (QDateTime.currentDateTime().addSecs(-270), "Response", "Tools: echo, calculator, weather"),
            (QDateTime.currentDateTime().addSecs(-260), "Request", "Execute echo tool"),
            (QDateTime.currentDateTime().addSecs(-250), "Response", "Echo response: Hello, world!")
        ]

        for time, msg_type, content in sample_messages:
            row = self.messages_table.rowCount()
            self.messages_table.insertRow(row)

            time_item = QTableWidgetItem(time.toString("hh:mm:ss"))
            time_item.setData(Qt.ItemDataRole.UserRole, time)
            self.messages_table.setItem(row, 0, time_item)

            self.messages_table.setItem(row, 1, QTableWidgetItem(msg_type))
            self.messages_table.setItem(row, 2, QTableWidgetItem(content))

    def _session_selected(self, session_name):
        """Handle session selection."""
        # TODO: Implement session loading
        logger.info(f"Selected session: {session_name}")
        self.session_message.emit(f"Selected session: {session_name}")

    def _new_session(self):
        """Create new session."""
        # TODO: Implement new session creation
        session_name = f"Session {self.session_selector.count() + 1}"
        self.session_selector.addItem(session_name)
        self.session_selector.setCurrentText(session_name)
        self.messages_table.setRowCount(0)
        self.message_details.clear()
        logger.info(f"Created new session: {session_name}")
        self.session_message.emit(f"Created new session: {session_name}")

    def _save_session(self):
        """Save current session."""
        # TODO: Implement session saving
        session_name = self.session_selector.currentText()
        logger.info(f"Saved session: {session_name}")
        self.session_message.emit(f"Saved session: {session_name}")

    def _export_session(self):
        """Export session to file."""
        # TODO: Implement session export
        session_name = self.session_selector.currentText()
        logger.info(f"Exported session: {session_name}")
        self.session_message.emit(f"Exported session: {session_name}")

    def _message_selected(self):
        """Handle message selection."""
        selected_items = self.messages_table.selectedItems()
        if not selected_items:
            self.message_details.clear()
            return

        row = selected_items[0].row()
        time = self.messages_table.item(row, 0).text()
        msg_type = self.messages_table.item(row, 1).text()
        content = self.messages_table.item(row, 2).text()

        details = f"Time: {time}\nType: {msg_type}\n\nContent:\n{content}"

        # Add sample detailed content based on type
        if msg_type == "Request":
            if "Execute" in content:
                details += "\n\nTool: echo\nInput: Hello, world!"
        elif msg_type == "Response":
            if "Tools:" in content:
                details += "\n\nAvailable Tools:\n- echo: Echo back the input text\n- calculator: Perform basic calculations\n- weather: Get weather information for a location"

        self.message_details.setText(details)

    def add_message(self, msg_type, content):
        """
        Add message to session history.

        Args:
            msg_type: Message type (Request/Response)
            content: Message content
        """
        time = QDateTime.currentDateTime()

        row = self.messages_table.rowCount()
        self.messages_table.insertRow(row)

        time_item = QTableWidgetItem(time.toString("hh:mm:ss"))
        time_item.setData(Qt.ItemDataRole.UserRole, time)
        self.messages_table.setItem(row, 0, time_item)

        self.messages_table.setItem(row, 1, QTableWidgetItem(msg_type))
        self.messages_table.setItem(row, 2, QTableWidgetItem(content))

        # Scroll to the new item
        self.messages_table.scrollToItem(self.messages_table.item(row, 0))

        # Emit message signal
        self.session_message.emit(f"New {msg_type.lower()}: {content[:30]}...")
