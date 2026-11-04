"""
Configuration Module for Adversarial LLM Evaluation Companion.
Loads settings from environment variables and defines operational constants.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pynput.keyboard import Key

# Find and load .env file from workspace root or current directory
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    """Application-wide configuration parameters."""

    # API Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", "").strip() or None
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")

    # Keystroke Engine Timings
    FOCUS_DELAY_SECONDS: int = int(os.getenv("FOCUS_DELAY_SECONDS", "2"))
    MIN_TYPE_DELAY: float = float(os.getenv("MIN_TYPE_DELAY", "0.003"))
    MAX_TYPE_DELAY: float = float(os.getenv("MAX_TYPE_DELAY", "0.010"))

    # Global Emergency Stop
    EMERGENCY_STOP_KEY_NAME: str = os.getenv("EMERGENCY_STOP_KEY", "<esc>")
    EMERGENCY_STOP_KEY: Key = Key.esc

    # Sliced countdown increment in seconds for responsive abortion
    COUNTDOWN_TICK_SECONDS: float = 0.1

    # UI Window Specifications
    WINDOW_TITLE: str = "Adversarial LLM Evaluation Companion"
    WINDOW_WIDTH: int = 440
    WINDOW_HEIGHT: int = 560


# Singleton configuration instance
CONFIG = AppConfig()

