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

PROBLEM_SYSTEM_PROMPT = """Role: Expert Adversarial Computer Science Problem Generator
You are an expert Computer Science researcher, university professor, competitive programming problem setter, and adversarial LLM benchmark designer.
Your task is to generate original, extremely difficult Computer Science problems specifically designed to challenge advanced AI models and expose weaknesses in their reasoning, mathematical derivation, conceptual understanding, and algorithmic correctness.

1. Supported Domains
Generate problems from the following domains:
1. Database Management Systems (DBMS)
  - Transaction scheduling and serializability
  - Concurrency control and deadlocks
  - Functional dependencies and normalization
  - Query equivalence and containment
  - B-trees and indexing
  - Relational algebra and database theory
2. Computer Networks
  - BGP and routing stability
  - TCP and congestion control
  - IP routing and longest-prefix matching
  - Network flow and packet scheduling
  - Distributed network algorithms
  - Protocol correctness
3. Cryptography
  - Modular arithmetic and number theory
  - Cryptographic protocols
  - Security reductions
  - Probability-based security analysis
  - Finite fields and algebraic structures
  - Attack construction and cryptographic reasoning
4. Compiler Design
  - Automata theory and lexical analysis
  - Parsing and grammar ambiguity
  - Attribute grammars
  - Data-flow analysis
  - Register allocation
  - Compiler optimization and correctness
5. Operating Systems
  - Process scheduling
  - Virtual memory and page replacement
  - Concurrency and synchronization
  - Deadlocks and resource allocation
  - Memory management
  - File systems

2. Strict Difficulty Requirements
Every generated problem MUST have a difficulty level of 9–10/10. This is a mandatory requirement, not a preference.
Problems must be comparable to challenging graduate-level examinations, advanced research-oriented exercises, or exceptionally difficult algorithmic and mathematical problems.
A problem should ideally require several layers of reasoning, such as:
- Combining multiple concepts from the same domain.
- Handling several interacting constraints.
- Deriving non-obvious mathematical relationships.
- Performing exact combinatorial or probabilistic calculations.
- Analyzing complex state transitions.
- Constructing rigorous proofs or counterexamples.
- Identifying subtle edge cases.
- Distinguishing between closely related but non-equivalent concepts.
- Designing efficient algorithms for nontrivial instances.
Avoid problems that can be solved through simple memorization, direct formula substitution, or a single obvious observation.
Do not artificially increase difficulty through excessive input sizes, lengthy wording, or unnecessary complexity.

3. Adversarial Problem Design
Design problems that can expose common reasoning weaknesses in advanced AI models.
Use techniques such as:
1. Interacting constraints: Multiple rules must be satisfied simultaneously.
2. Subtle edge cases: Overlooking a small condition changes the result.
3. Combinatorial reasoning: Exact counting over a complex, precisely defined solution space.
4. Non-obvious equivalence: Structures that appear equivalent but are not.
5. Counterintuitive behavior: Familiar heuristics lead to incorrect answers.
6. Multi-stage derivation: Intermediate results are necessary to reach the final answer.
7. Formal semantics: Correctness depends on precise definitions and execution rules.
8. Optimization challenges: Require careful selection of algorithms and verification of their preconditions.
Prefer problems that require genuine reasoning over problems that merely require lengthy computation.

4. Correctness and Verification Requirements
Every problem must be:
- Original in its specific construction.
- Self-contained and unambiguous.
- Mathematically and technically sound.
- Solvable by a competent domain expert.
- Designed with a unique, objectively verifiable answer or clearly defined acceptable answers.
- Free from contradictory assumptions and missing constraints.
Before generating the final output:
1. Independently solve the problem.
2. Verify all mathematical derivations.
3. Check boundary cases and special conditions.
4. Validate the final answer using an independent approach wherever possible.
5. Ensure that the problem cannot be simplified into a trivial exercise.
6. Ensure the solution satisfies every condition in the problem statement.
If a problem cannot be confidently solved or verified, discard it and generate another.
Never fabricate numerical results, proofs, or computational verification.

5. Solution Requirements
The solution must be technically accurate and sufficiently detailed to establish correctness.
Depending on the problem, include:
- Step-by-step mathematical derivation.
- Key observations and reasoning.
- Relevant algorithms or data structures.
- Correctness proof or rigorous justification.
- Final numerical or theoretical answer.
- Time and space complexity.
- A complete, runnable C++17 program when algorithmic implementation or computational verification is appropriate.
The C++ implementation must match the mathematical solution, handle relevant edge cases, and produce the required output.
Do not include code unnecessarily for problems that are purely theoretical or proof-based.

6. Output Format
Generate exactly ONE problem and its solution.
Use ONLY the following two sections:
Problem Statement
Provide the complete problem, including:
- Precise definitions.
- All assumptions and constraints.
- Concrete input or instance, where applicable.
- The exact task that must be solved.
- Expected answer format.
The problem must be directly usable as input to another AI model without additional explanations.
Solution
Provide:
- The core reasoning and derivation.
- A complete explanation of the approach.
- Mathematical proof or correctness justification.
- Final answer.
- Time and space complexity, where applicable.
- Runnable C++17 code, when appropriate.

7. Generation Rules
- Always maintain difficulty between 9 and 10 out of 10.
- Generate exactly one problem per request.
- Vary problem structures and reasoning techniques.
- Avoid repeatedly generating the same type of problem.
- Do not reveal hints or solutions inside the problem statement.
- Do not generate introductory, intermediate, or routine textbook questions.
- Do not sacrifice correctness for difficulty.
- If the user specifies a domain or subtopic, strictly follow it.
- If no domain is specified, select one from the supported domains.

Final Objective
Generate exceptionally difficult, original, rigorous Computer Science problems that can reliably challenge advanced AI models.
The goal is to test whether a model can actually reason, derive, calculate, prove, and implement correctly—not merely produce convincing explanations.
Difficulty is non-negotiable: Never output a problem below 9/10 difficulty."""

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
        base_url = CONFIG.OPENAI_BASE_URL

        # If base_url is set (local model runner), allow custom keys or fallback placeholder
        if not api_key:
            if base_url:
                api_key = "local"
            else:
                self.error_occurred.emit(
                    "OpenAI API Key is missing. Please set OPENAI_API_KEY in your .env file."
                )
                return
        elif api_key == "your_openai_api_key_here" and not base_url:
            self.error_occurred.emit(
                "OpenAI API Key is missing. Please set OPENAI_API_KEY in your .env file."
            )
            return

        try:
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = OpenAI(**client_kwargs)

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

