"""
Main Floating Companion Window (Always-on-Top).
Provides a Human-in-the-Loop (HITL) interface for evaluating adversarial LLM edge cases.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import CONFIG
from app.core.states import AppState
from app.listeners.hotkey_listener import GlobalHotkeyListener
from app.ui.styles import DARK_THEME_QSS

logger = logging.getLogger(__name__)


class CompanionWindow(QWidget):
    """
    Floating, Always-On-Top companion window implementing the HITL state machine.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Thread synchronization primitives
        self.abort_event = threading.Event()
        self.active_problem_text = ""
        self.active_solution_text = ""

        # Workers references
        self._llm_worker = None
        self._typing_worker = None

        # Configure window flags: Always on top, normal dialog style
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setWindowTitle(CONFIG.WINDOW_TITLE)
        self.resize(CONFIG.WINDOW_WIDTH, CONFIG.WINDOW_HEIGHT)
        self.setMinimumSize(400, 520)

        # Apply dark modern stylesheet
        self.setStyleSheet(DARK_THEME_QSS)

        # Initialize UI widgets
        self._init_ui()

        # Initialize and start global background OS keyboard listener
        self.hotkey_listener = GlobalHotkeyListener(
            abort_event=self.abort_event,
            on_stop_triggered=self._on_emergency_hotkey_pressed,
        )
        self.hotkey_listener.start()

    def _init_ui(self) -> None:
        """Constructs and arranges all UI widgets in the window."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # Status Banner
        # -------------------------------------------------------------
        self.status_banner = QLabel(AppState.IDLE_READY.value, self)
        self.status_banner.setObjectName("status_banner")
        self.status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_banner.setWordWrap(True)
        main_layout.addWidget(self.status_banner)

        # -------------------------------------------------------------
        # Preview & Manual Edit Box
        # -------------------------------------------------------------
        preview_label = QLabel("Preview & Edit Area (Editable before typing)", self)
        preview_label.setProperty("class", "section-header")
        main_layout.addWidget(preview_label)

        self.preview_box = QPlainTextEdit(self)
        self.preview_box.setObjectName("preview_box")
        self.preview_box.setPlaceholderText(
            "Generated problem or solution will appear here.\n"
            "You can review, format, or manually edit this text before clicking 'Type'."
        )
        main_layout.addWidget(self.preview_box, stretch=1)

        # -------------------------------------------------------------
        # Phase 1 Controls: Adversarial Problem Generation & Typing
        # -------------------------------------------------------------
        phase1_label = QLabel("Phase 1: Adversarial Problem", self)
        phase1_label.setProperty("class", "section-header")
        main_layout.addWidget(phase1_label)

        phase1_layout = QHBoxLayout()
        phase1_layout.setSpacing(8)

        self.btn_gen_problem = QPushButton("1. Generate Problem", self)
        self.btn_gen_problem.setObjectName("btn_gen_problem")
        phase1_layout.addWidget(self.btn_gen_problem)

        self.btn_type_problem = QPushButton(f"2. Type Problem ({CONFIG.FOCUS_DELAY_SECONDS}s Focus Delay)", self)
        self.btn_type_problem.setObjectName("btn_type_problem")
        self.btn_type_problem.setEnabled(False)
        phase1_layout.addWidget(self.btn_type_problem)

        main_layout.addLayout(phase1_layout)

        # -------------------------------------------------------------
        # Phase 2 Controls: Human Evaluation Gate
        # -------------------------------------------------------------
        phase2_label = QLabel("Phase 2: Human Evaluation Gate", self)
        phase2_label.setProperty("class", "section-header")
        main_layout.addWidget(phase2_label)

        phase2_layout = QHBoxLayout()
        phase2_layout.setSpacing(8)

        self.btn_model_defeated = QPushButton("3a. Target Defeated -> Gen Solution", self)
        self.btn_model_defeated.setObjectName("btn_model_defeated")
        self.btn_model_defeated.setEnabled(False)
        phase2_layout.addWidget(self.btn_model_defeated)

        self.btn_model_succeeded = QPushButton("3b. Model Succeeded -> Reset", self)
        self.btn_model_succeeded.setObjectName("btn_model_succeeded")
        self.btn_model_succeeded.setEnabled(False)
        phase2_layout.addWidget(self.btn_model_succeeded)

        main_layout.addLayout(phase2_layout)

        # -------------------------------------------------------------
        # Phase 3 Controls: Ground Truth Solution Typing
        # -------------------------------------------------------------
        phase3_label = QLabel("Phase 3: Ground Truth Solution", self)
        phase3_label.setProperty("class", "section-header")
        main_layout.addWidget(phase3_label)

        self.btn_type_solution = QPushButton(f"4. Type Solution ({CONFIG.FOCUS_DELAY_SECONDS}s Focus Delay)", self)
        self.btn_type_solution.setObjectName("btn_type_solution")
        self.btn_type_solution.setEnabled(False)
        main_layout.addWidget(self.btn_type_solution)

        # -------------------------------------------------------------
        # Emergency Stop Control (High Priority)
        # -------------------------------------------------------------
        self.btn_emergency_stop = QPushButton(f"STOP TYPING ({CONFIG.EMERGENCY_STOP_KEY_NAME.upper()})", self)
        self.btn_emergency_stop.setObjectName("btn_emergency_stop")
        self.btn_emergency_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        main_layout.addWidget(self.btn_emergency_stop)

    def set_status(self, text: str, highlight_mode: Optional[str] = None) -> None:
        """
        Updates the prominent top status banner with dynamic color themes.
        highlight_mode: 'active' (green), 'warning' (yellow/orange), 'error' (red), or None (blue default).
        """
        self.status_banner.setText(text)

        base_style = "border-radius: 8px; padding: 10px 14px; font-weight: 600; font-size: 13px;"
        if highlight_mode == "active" or "Typing..." in text:
            self.status_banner.setStyleSheet(
                f"{base_style} background-color: #064e3b; color: #34d399; border: 1px solid #10b981;"
            )
        elif highlight_mode == "warning" or "Waiting" in text:
            self.status_banner.setStyleSheet(
                f"{base_style} background-color: #451a03; color: #fbbf24; border: 1px solid #f59e0b;"
            )
        elif highlight_mode == "error" or "Emergency" in text or "aborted" in text.lower() or "Error" in text:
            self.status_banner.setStyleSheet(
                f"{base_style} background-color: #450a0a; color: #f87171; border: 1px solid #ef4444;"
            )
        elif "completed" in text.lower() or "ready" in text.lower():
            self.status_banner.setStyleSheet(
                f"{base_style} background-color: #1e1b4b; color: #818cf8; border: 1px solid #6366f1;"
            )
        else:
            self.status_banner.setStyleSheet(
                f"{base_style} background-color: #1e2025; color: #38bdf8; border: 1px solid #334155;"
            )

    def _on_emergency_hotkey_pressed(self) -> None:
        """Thread-safe notification invoked when global Esc is pressed."""
        logger.info("Emergency Stop key detected by global listener.")
        # Trigger UI update safely on Qt main thread via QTimer
        QTimer.singleShot(0, self._handle_emergency_stop_triggered)

    def _handle_emergency_stop_triggered(self) -> None:
        """Called on main UI thread when emergency stop is triggered."""
        self.set_status(AppState.EMERGENCY_STOP_TRIGGERED.value, highlight_mode="error")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Gracefully terminates background threads when window is closed."""
        logger.info("Shutting down application window and background listeners...")
        self.abort_event.set()

        # Stop global keyboard hook
        if hasattr(self, "hotkey_listener") and self.hotkey_listener is not None:
            self.hotkey_listener.stop()

        # Safely terminate workers if active
        if self._typing_worker is not None and self._typing_worker.isRunning():
            self._typing_worker.wait(1000)

        if self._llm_worker is not None and self._llm_worker.isRunning():
            self._llm_worker.wait(1000)

        super().closeEvent(event)
