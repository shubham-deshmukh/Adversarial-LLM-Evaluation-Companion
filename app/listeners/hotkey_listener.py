"""
Global Emergency Stop Hotkey Listener.
Listens for OS-level keyboard events across all windows using pynput.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional
from pynput.keyboard import Key, KeyCode, Listener

from app.config import CONFIG

logger = logging.getLogger(__name__)


class GlobalHotkeyListener:
    """
    Background hook capturing global keyboard events across the OS.
    When the configured emergency stop key (default: Esc) is pressed,
    the shared abort_event is immediately set.
    """

    def __init__(
        self,
        abort_event: threading.Event,
        on_stop_triggered: Optional[Callable[[], None]] = None,
    ) -> None:
        self.abort_event = abort_event
        self.on_stop_triggered = on_stop_triggered
        self._listener: Optional[Listener] = None
        self._is_running = False

    def _on_press(self, key: Optional[Key | KeyCode]) -> None:
        """Callback executed on any OS key press event."""
        try:
            # Check for Esc key
            if key == CONFIG.EMERGENCY_STOP_KEY or key == Key.esc:
                logger.info("Global emergency stop hotkey [ESC] intercepted.")
                self.abort_event.set()
                if self.on_stop_triggered:
                    self.on_stop_triggered()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error in hotkey listener callback: %s", exc)

    def start(self) -> None:
        """Starts the low-level OS keyboard listener in a daemon thread."""
        if self._listener is not None and self._listener.is_alive():
            logger.debug("Hotkey listener already active.")
            return

        self._listener = Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()
        self._is_running = True
        logger.info("Global emergency stop listener started (Monitoring: %s).", CONFIG.EMERGENCY_STOP_KEY_NAME)

    def stop(self) -> None:
        """Stops the low-level keyboard listener safely."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._is_running = False
        logger.info("Global emergency stop listener stopped.")

    @property
    def is_running(self) -> bool:
        """Returns True if the hook is active."""
        return self._is_running and self._listener is not None and self._listener.is_alive()
