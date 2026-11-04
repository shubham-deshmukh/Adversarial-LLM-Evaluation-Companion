"""
Application Entrypoint for Adversarial LLM Evaluation Companion.
Initializes the Qt Application, applies high-DPI configurations, and displays
the floating companion window.
"""

from __future__ import annotations

import logging
import sys
from PyQt6.QtWidgets import QApplication

from app.config import CONFIG
from app.ui.main_window import CompanionWindow

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(threadName)s) %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app.main")


def main() -> int:
    """Initializes and runs the companion desktop application."""
    logger.info("Starting %s...", CONFIG.WINDOW_TITLE)

    # Initialize Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(CONFIG.WINDOW_TITLE)
    app.setOrganizationName("AI-RedTeam")

    # Instantiate and display the companion window
    window = CompanionWindow()
    window.show()

    logger.info("Application event loop started.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

