"""
LLM Worker Thread for asynchronous OpenAI API interactions.
Runs non-blocking API calls for adversarial problem and solution generation.
"""

from __future__ import annotations

import logging
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI, OpenAIError

from app.config import CONFIG

logger = logging.getLogger(__name__)

PROBLEM_SYSTEM_PROMPT = (
    "You are an elite AI safety red-teamer and adversarial evaluation specialist. "
    "Your objective is to generate a novel, deceptive logic puzzle, counter-intuitive "
    "math edge-case, semantic garden-path question, or spatial reasoning trap designed "
    "to cause advanced frontier LLMs to fail due to superficial pattern-matching, cognitive shortcuts, "
    "or misread constraints.\n\n"
    "Rules:\n"
    "1. Keep the output strictly self-contained and concise (1-3 paragraphs maximum).\n"
    "2. Do NOT provide the answer, hints, spoiler tags, or meta-commentary.\n"
    "3. Output ONLY the raw puzzle text ready to be tested on the target model."
)

SOLUTION_SYSTEM_PROMPT = (
    "You are a master mathematical logic verifier and truth-engine. "
    "Provide a rigorous, definitive, step-by-step ground-truth solution for the given adversarial puzzle.\n\n"
    "Structure your response:\n"
    "1. Deconstruct the trap or deceptive premise that trips up standard models.\n"
    "2. Walk through the correct analytical reasoning step-by-step.\n"
    "3. Conclude with a clear, unambiguous final answer statement."
)


class LLMWorker(QThread):
    """
    Dedicated QThread worker for executing OpenAI Chat Completion calls
    without blocking the PyQt6 GUI event loop.
    """

    # Signals
    result_ready = pyqtSignal(str, str)  # (mode: "problem"|"solution", text: str)
    error_occurred = pyqtSignal(str)     # (error_message: str)

    def __init__(
        self,
        mode: str,
        problem_context: str = "",
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode.strip().lower()
        self.problem_context = problem_context.strip()

    def run(self) -> None:
        """Executes the Chat Completion call in a background thread."""
        api_key = CONFIG.OPENAI_API_KEY.strip()
        if not api_key or api_key == "your_openai_api_key_here":
            self.error_occurred.emit(
                "OpenAI API Key is missing. Please set OPENAI_API_KEY in your .env file."
            )
            return

        try:
            client = OpenAI(api_key=api_key)

            if self.mode == "problem":
                messages = [
                    {"role": "system", "content": PROBLEM_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": "Generate a novel adversarial evaluation puzzle now.",
                    },
                ]
            elif self.mode == "solution":
                if not self.problem_context:
                    self.error_occurred.emit("Problem context is empty. Cannot generate solution.")
                    return
                messages = [
                    {"role": "system", "content": SOLUTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Analyze and solve this problem definitively:\n\n{self.problem_context}",
                    },
                ]
            else:
                self.error_occurred.emit(f"Unknown LLMWorker mode: '{self.mode}'")
                return

            response = client.chat.completions.create(
                model=CONFIG.MODEL_NAME,
                messages=messages,
                temperature=0.7 if self.mode == "problem" else 0.2,
            )

            generated_text = response.choices[0].message.content or ""
            generated_text = generated_text.strip()

            if not generated_text:
                self.error_occurred.emit("Received empty response from OpenAI model.")
                return

            self.result_ready.emit(self.mode, generated_text)

        except OpenAIError as exc:
            logger.exception("OpenAI API error occurred during LLMWorker run")
            self.error_occurred.emit(f"OpenAI API Error: {exc}")
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error occurred during LLMWorker run")
            self.error_occurred.emit(f"Unexpected Error: {exc}")

