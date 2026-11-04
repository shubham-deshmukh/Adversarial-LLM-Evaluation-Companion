"""
Interruptible Keystroke Emulation Engine.
Executes non-blocking, character-by-character native OS keystrokes with
sub-10ms emergency abort responsiveness.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal
from pynput.keyboard import Controller, Key

from app.config import CONFIG
from app.core.states import AppState

logger = logging.getLogger(__name__)


class TypingWorker(QThread):
    """
    Dedicated QThread worker for typing text into target applications.
    Implements a responsive focus countdown and fine-grained character typing
    with instantaneous abort capabilities via a threading.Event flag.
    """

    status_update = pyqtSignal(str)          # Emits human-readable operational states
    typing_finished = pyqtSignal(bool, str)   # (completed_normally: bool, mode: str)

    def __init__(
        self,
        text_to_type: str,
        mode: str,
        abort_event: threading.Event,
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.text_to_type = text_to_type
        self.mode = mode.strip().lower()
        self.abort_event = abort_event
        self.controller = Controller()

    def run(self) -> None:
        """Executes the countdown and keystroke emulation loop."""
        # Ensure abort flag is cleared before commencing
        self.abort_event.clear()

        # Handle empty text case
        if not self.text_to_type.strip():
            logger.warning("TypingWorker invoked with empty text.")
            self.status_update.emit(AppState.IDLE_READY.value)
            self.typing_finished.emit(False, self.mode)
            return

        # -------------------------------------------------------------
        # Phase 1: Focus Countdown (sliced into small intervals)
        # -------------------------------------------------------------
        total_seconds = CONFIG.FOCUS_DELAY_SECONDS
        tick_interval = CONFIG.COUNTDOWN_TICK_SECONDS  # 0.1 seconds
        ticks_per_second = int(1.0 / tick_interval)

        for remaining in range(total_seconds, 0, -1):
            if remaining == 2:
                self.status_update.emit(AppState.WAITING_FOCUS_2S.value)
            elif remaining == 1:
                self.status_update.emit(AppState.WAITING_FOCUS_1S.value)
            else:
                self.status_update.emit(f"Waiting for focus — {remaining} seconds")

            for _ in range(ticks_per_second):
                if self.abort_event.is_set():
                    logger.info("Typing countdown aborted by user via emergency stop.")
                    self.status_update.emit(AppState.TYPING_ABORTED.value)
                    self.typing_finished.emit(False, self.mode)
                    return
                time.sleep(tick_interval)

        # Final check after countdown ends before typing starts
        if self.abort_event.is_set():
            self.status_update.emit(AppState.TYPING_ABORTED.value)
            self.typing_finished.emit(False, self.mode)
            return

        # -------------------------------------------------------------
        # Phase 2: Keystroke Emulation Loop
        # -------------------------------------------------------------
        self.status_update.emit(AppState.TYPING.value)
        logger.info("Starting typing emulation for mode '%s' (%d chars).", self.mode, len(self.text_to_type))

        try:
            # Normalize line endings to avoid double-spaced lines
            normalized_text = self.text_to_type.replace("\r\n", "\n").replace("\r", "\n")

            for char in normalized_text:
                # Ultra-low latency check before every single keystroke (<10ms)
                if self.abort_event.is_set():
                    logger.info("Emergency Stop triggered during active typing.")
                    self.status_update.emit(AppState.EMERGENCY_STOP_TRIGGERED.value)
                    self.typing_finished.emit(False, self.mode)
                    return

                if char == "\n":
                    # Shift+Enter cleanly inputs a newline in web chat boxes without submitting
                    with self.controller.pressed(Key.shift):
                        self.controller.press(Key.enter)
                        self.controller.release(Key.enter)
                else:
                    self.controller.type(char)

                # Randomized human-like typing jitter delay (default: 3ms to 10ms)
                delay = random.uniform(CONFIG.MIN_TYPE_DELAY, CONFIG.MAX_TYPE_DELAY)
                time.sleep(delay)

            # -------------------------------------------------------------
            # Phase 3: Successful Completion
            # -------------------------------------------------------------
            logger.info("Typing completed successfully for mode '%s'.", self.mode)
            self.status_update.emit(AppState.TYPING_COMPLETED.value)
            self.typing_finished.emit(True, self.mode)

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Error occurred in TypingWorker keystroke loop")
            self.status_update.emit(f"Typing Error: {exc}")
            self.typing_finished.emit(False, self.mode)

