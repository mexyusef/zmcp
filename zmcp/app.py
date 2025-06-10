"""
ZMCP Application

Main application entry point.
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication

from zmcp.ui.main_window import MainWindow


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def main():
    """Main application entry point."""
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("ZMCP")
    app.setOrganizationName("ZMCP")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
