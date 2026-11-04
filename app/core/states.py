"""
State definitions for the Adversarial LLM Evaluation Companion.
"""

from __future__ import annotations
from enum import Enum


class AppState(str, Enum):
    """Granular operational states for the application."""

    IDLE_READY = "Idle — Ready"
    GENERATING_PROBLEM = "Generating problem..."
    PROBLEM_READY = "Problem ready (Review preview below)"
    WAITING_FOCUS_2S = "Waiting for focus — 2 seconds"
    WAITING_FOCUS_1S = "Waiting for focus — 1 second"
    TYPING = "Typing..."
    TYPING_COMPLETED = "Typing completed"
    WAITING_HUMAN_EVAL = "Waiting for human evaluation"
    GENERATING_SOLUTION = "Generating solution..."
    SOLUTION_READY = "Solution ready (Review preview below)"
    EMERGENCY_STOP_TRIGGERED = "Emergency Stop triggered — Typing cancelled"
    TYPING_ABORTED = "Typing aborted by user"
    ERROR = "Error"

