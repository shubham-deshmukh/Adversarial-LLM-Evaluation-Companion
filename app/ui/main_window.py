"""
Main Floating Companion Window (Always-on-Top).
Provides a Human-in-the-Loop (HITL) interface for evaluating adversarial LLM edge cases.
Wires all state machine transitions, worker threads, and emergency stops.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
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
from app.workers.llm_worker import LLMWorker
from app.workers.typing_worker import TypingWorker

logger = logging.getLogger(__name__)


class CompanionWindow(QWidget):
    """
    Floating, Always-On-Top companion window implementing the HITL state machine.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Thread synchronization primitives & state
        self.abort_event = threading.Event()
        self.active_problem_text = ""
        self.active_solution_text = ""
        self.current_state = AppState.IDLE_READY

        # Active Worker references
        self._llm_worker: Optional[LLMWorker] = None
        self._typing_worker: Optional[TypingWorker] = None

        # Configure window flags: Always on top, normal utility window
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

        # Initialize UI widgets & wire event signals
        self._init_ui()
        self._wire_signals()

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

        self.btn_type_problem = QPushButton(
            f"2. Type Problem ({CONFIG.FOCUS_DELAY_SECONDS}s Focus Delay)", self
        )
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

        self.btn_type_solution = QPushButton(
            f"4. Type Solution ({CONFIG.FOCUS_DELAY_SECONDS}s Focus Delay)", self
        )
        self.btn_type_solution.setObjectName("btn_type_solution")
        self.btn_type_solution.setEnabled(False)
        main_layout.addWidget(self.btn_type_solution)

        # -------------------------------------------------------------
        # Emergency Stop Control (High Priority)
        # -------------------------------------------------------------
        self.btn_emergency_stop = QPushButton(
            f"STOP TYPING ({CONFIG.EMERGENCY_STOP_KEY_NAME.upper()})", self
        )
        self.btn_emergency_stop.setObjectName("btn_emergency_stop")
        self.btn_emergency_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        main_layout.addWidget(self.btn_emergency_stop)

    def _wire_signals(self) -> None:
        """Connects UI button events to state machine handlers."""
        self.btn_gen_problem.clicked.connect(self._on_gen_problem_clicked)
        self.btn_type_problem.clicked.connect(self._on_type_problem_clicked)
        self.btn_model_defeated.clicked.connect(self._on_model_defeated_clicked)
        self.btn_model_succeeded.clicked.connect(self._on_model_succeeded_clicked)
        self.btn_type_solution.clicked.connect(self._on_type_solution_clicked)
        self.btn_emergency_stop.clicked.connect(self._on_emergency_stop_clicked)
        self.preview_box.textChanged.connect(self._on_preview_text_changed)

    # -----------------------------------------------------------------
    # State Banner & UI Helpers
    # -----------------------------------------------------------------
    def set_status(self, text: str, highlight_mode: Optional[str] = None) -> None:
        """
        Updates the prominent top status banner with dynamic color themes.
        highlight_mode: 'active' (green), 'warning' (yellow/orange), 'error' (red), or None.
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
        elif (
            highlight_mode == "error"
            or "Emergency" in text
            or "aborted" in text.lower()
            or "error" in text.lower()
        ):
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

    # -----------------------------------------------------------------
    # Phase 1: Problem Generation & Typing Handlers
    # -----------------------------------------------------------------
    def _on_preview_text_changed(self) -> None:
        """Handles manual pasting or typing directly into the preview area."""
        # Do not alter button states if an active background worker is running
        if (self._typing_worker and self._typing_worker.isRunning()) or (
            self._llm_worker and self._llm_worker.isRunning()
        ):
            return

        text = self.preview_box.toPlainText().strip()
        current_status = self.status_banner.text()

        # If in Idle or Manual Input state:
        if current_status in (AppState.IDLE_READY.value, AppState.PROBLEM_READY_MANUAL.value):
            if text:
                self.btn_type_problem.setEnabled(True)
                if current_status == AppState.IDLE_READY.value:
                    self.set_status(AppState.PROBLEM_READY_MANUAL.value)
            else:
                self.btn_type_problem.setEnabled(False)
                if current_status == AppState.PROBLEM_READY_MANUAL.value:
                    self.set_status(AppState.IDLE_READY.value)

        # If in LLM-generated Problem Ready state:
        elif current_status == AppState.PROBLEM_READY.value:
            self.btn_type_problem.setEnabled(bool(text))

        # If in Solution Ready state:
        elif current_status == AppState.SOLUTION_READY.value:
            self.btn_type_solution.setEnabled(bool(text))

    def _on_gen_problem_clicked(self) -> None:
        """Initiates problem generation via LLMWorker."""
        self.set_status(AppState.GENERATING_PROBLEM.value)

        # Disable action buttons while generation is active
        self.btn_gen_problem.setEnabled(False)
        self.btn_type_problem.setEnabled(False)
        self.btn_model_defeated.setEnabled(False)
        self.btn_model_succeeded.setEnabled(False)
        self.btn_type_solution.setEnabled(False)

        self._llm_worker = LLMWorker(mode="problem", parent=self)
        self._llm_worker.result_ready.connect(self._on_llm_result_ready)
        self._llm_worker.error_occurred.connect(self._on_llm_error_occurred)
        self._llm_worker.start()

    def _on_type_problem_clicked(self) -> None:
        """Reads preview box text and starts TypingWorker for the problem."""
        problem_text = self.preview_box.toPlainText().strip()
        if not problem_text:
            self.set_status("Preview text is empty. Generate or enter text first.", highlight_mode="warning")
            return

        # Store latest edited text as active problem context
        self.active_problem_text = problem_text

        # Disable controls during typing
        self.btn_gen_problem.setEnabled(False)
        self.btn_type_problem.setEnabled(False)
        self.btn_model_defeated.setEnabled(False)
        self.btn_model_succeeded.setEnabled(False)
        self.btn_type_solution.setEnabled(False)

        self._start_typing_worker(text=problem_text, mode="problem")

    # -----------------------------------------------------------------
    # Phase 2: Human Evaluation Gate Handlers
    # -----------------------------------------------------------------
    def _on_model_defeated_clicked(self) -> None:
        """Operator verified model failed: generates verified ground-truth solution."""
        self.set_status(AppState.GENERATING_SOLUTION.value)

        # Context is either active problem text or current preview text
        context = self.active_problem_text or self.preview_box.toPlainText().strip()
        if not context:
            self.set_status("Problem context missing. Cannot generate solution.", highlight_mode="error")
            return

        self.btn_gen_problem.setEnabled(False)
        self.btn_type_problem.setEnabled(False)
        self.btn_model_defeated.setEnabled(False)
        self.btn_model_succeeded.setEnabled(False)
        self.btn_type_solution.setEnabled(False)

        self._llm_worker = LLMWorker(mode="solution", problem_context=context, parent=self)
        self._llm_worker.result_ready.connect(self._on_llm_result_ready)
        self._llm_worker.error_occurred.connect(self._on_llm_error_occurred)
        self._llm_worker.start()

    def _on_model_succeeded_clicked(self) -> None:
        """Operator verified model succeeded: resets workflow to clean state."""
        self.active_problem_text = ""
        self.active_solution_text = ""
        self.preview_box.clear()
        self.set_status(AppState.IDLE_READY.value)

        # Reset button states
        self.btn_gen_problem.setEnabled(True)
        self.btn_type_problem.setEnabled(False)
        self.btn_model_defeated.setEnabled(False)
        self.btn_model_succeeded.setEnabled(False)
        self.btn_type_solution.setEnabled(False)

    # -----------------------------------------------------------------
    # Phase 3: Solution Typing Handlers
    # -----------------------------------------------------------------
    def _on_type_solution_clicked(self) -> None:
        """Reads preview box text and starts TypingWorker for the solution."""
        solution_text = self.preview_box.toPlainText().strip()
        if not solution_text:
            self.set_status("Solution preview text is empty.", highlight_mode="warning")
            return

        self.active_solution_text = solution_text

        self.btn_gen_problem.setEnabled(False)
        self.btn_type_problem.setEnabled(False)
        self.btn_model_defeated.setEnabled(False)
        self.btn_model_succeeded.setEnabled(False)
        self.btn_type_solution.setEnabled(False)

        self._start_typing_worker(text=solution_text, mode="solution")

    # -----------------------------------------------------------------
    # LLM Callback Handlers
    # -----------------------------------------------------------------
    def _on_llm_result_ready(self, mode: str, generated_text: str) -> None:
        """Populates preview box and transitions states upon LLM completion."""
        self.preview_box.setPlainText(generated_text)

        if mode == "problem":
            self.active_problem_text = generated_text
            self.set_status(AppState.PROBLEM_READY.value)
            self.btn_gen_problem.setEnabled(True)
            self.btn_type_problem.setEnabled(True)
        elif mode == "solution":
            self.active_solution_text = generated_text
            self.set_status(AppState.SOLUTION_READY.value)
            self.btn_type_solution.setEnabled(True)
            self.btn_model_defeated.setEnabled(True)  # Allow re-gen if needed
            self.btn_model_succeeded.setEnabled(True)

    def _on_llm_error_occurred(self, error_message: str) -> None:
        """Displays error message and re-enables problem generation."""
        logger.error("LLMWorker error: %s", error_message)
        self.set_status(f"Error: {error_message}", highlight_mode="error")
        self.btn_gen_problem.setEnabled(True)
        if self.active_problem_text:
            self.btn_type_problem.setEnabled(True)
            self.btn_model_defeated.setEnabled(True)
            self.btn_model_succeeded.setEnabled(True)

    # -----------------------------------------------------------------
    # Typing Worker Execution & Callbacks
    # -----------------------------------------------------------------
    def _start_typing_worker(self, text: str, mode: str) -> None:
        """Instantiates and launches TypingWorker thread."""
        self.abort_event.clear()
        self._typing_worker = TypingWorker(
            text_to_type=text,
            mode=mode,
            abort_event=self.abort_event,
            parent=self,
        )
        self._typing_worker.status_update.connect(self._on_typing_status_update)
        self._typing_worker.typing_finished.connect(self._on_typing_finished)
        self._typing_worker.start()

    def _on_typing_status_update(self, status: str) -> None:
        """Updates the status banner as countdown and typing progress."""
        self.set_status(status)

    def _on_typing_finished(self, completed_normally: bool, mode: str) -> None:
        """Handles completion or cancellation of TypingWorker."""
        if completed_normally:
            self.set_status(AppState.TYPING_COMPLETED.value)

            if mode == "problem":
                # 1-second pause on "Typing completed" before transitioning to human eval
                QTimer.singleShot(1000, self._transition_to_human_eval)
            elif mode == "solution":
                # 1-second pause after solution typing completes, then return to ready
                QTimer.singleShot(1000, self._on_cycle_completed)
        else:
            # Typing was aborted or interrupted
            logger.info("Typing finished abnormally (Aborted / Stopped) for mode '%s'", mode)
            # Re-enable the corresponding type button so operator can refocus and retry without regenerating
            if mode == "problem":
                self.btn_gen_problem.setEnabled(True)
                self.btn_type_problem.setEnabled(True)
            elif mode == "solution":
                self.btn_type_solution.setEnabled(True)
                self.btn_model_defeated.setEnabled(True)
                self.btn_model_succeeded.setEnabled(True)

    def _transition_to_human_eval(self) -> None:
        """Transitions state to waiting for human evaluation gate."""
        self.set_status(AppState.WAITING_HUMAN_EVAL.value)
        self.btn_model_defeated.setEnabled(True)
        self.btn_model_succeeded.setEnabled(True)
        self.btn_gen_problem.setEnabled(True)
        self.btn_type_problem.setEnabled(True)

    def _on_cycle_completed(self) -> None:
        """Resets status after solution has been successfully delivered."""
        self.set_status("Evaluation Cycle Completed — Ready for next problem")
        self.btn_gen_problem.setEnabled(True)
        self.btn_model_succeeded.setEnabled(True)

    # -----------------------------------------------------------------
    # Emergency Stop Handlers
    # -----------------------------------------------------------------
    def _on_emergency_stop_clicked(self) -> None:
        """Triggered via GUI Emergency Stop button click."""
        logger.info("Emergency Stop button clicked.")
        self.abort_event.set()
        self._handle_emergency_stop_triggered()

    def _on_emergency_hotkey_pressed(self) -> None:
        """Thread-safe notification invoked when global Esc is pressed."""
        logger.info("Emergency Stop key detected by global listener.")
        QTimer.singleShot(0, self._handle_emergency_stop_triggered)

    def _handle_emergency_stop_triggered(self) -> None:
        """Called on main UI thread when emergency stop is triggered."""
        self.set_status(AppState.EMERGENCY_STOP_TRIGGERED.value, highlight_mode="error")

    # -----------------------------------------------------------------
    # Lifecycle Cleanup
    # -----------------------------------------------------------------
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
