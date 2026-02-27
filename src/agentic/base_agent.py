"""
Base agent class for Agentic GraphRAG.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from ..embeddings import OllamaLLM
from .state import AgenticRAGState


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Each agent is responsible for one step in the Agentic RAG pipeline.
    """

    def __init__(
        self,
        llm: OllamaLLM,
        config: dict[str, Any],
        verbose: bool = False,
    ) -> None:
        self.llm = llm
        self.config = config
        self.verbose = verbose

    @abstractmethod
    def execute(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        Execute agent logic and update state.

        Args:
            state: Current pipeline state

        Returns:
            Updated state
        """
        raise NotImplementedError

    def log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[{self.__class__.__name__}] {message}")

    def _call_llm(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.0,
    ) -> str:
        """
        Call LLM with error handling.

        Args:
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            LLM response
        """
        try:
            response = self.llm.generate(
                prompt,
                system=system,
                temperature=temperature,
            )
            return response.strip()
        except Exception as e:
            self.log(f"LLM call failed: {e}")
            raise

    def _extract_score(self, response: str) -> float:
        """
        Extract numeric score from LLM response.

        Expects format like "Score: 0.85" or just "0.85"

        Returns:
            Score between 0.0 and 1.0, or 0.0 if parsing fails
        """
        import re

        # Try patterns: "Score: 0.85", "0.85", "85%"
        patterns = [
            r"(?:score|relevance|confidence)[:\s]+([0-9.]+)",
            r"^([0-9.]+)$",
            r"([0-9]+)%",
        ]

        for pattern in patterns:
            match = re.search(pattern, response.lower().strip())
            if match:
                value = float(match.group(1))
                # Normalize percentage to 0-1
                if value > 1.0:
                    value /= 100.0
                return max(0.0, min(1.0, value))

        return 0.0

    def _extract_yes_no(self, response: str) -> bool:
        """
        Extract yes/no decision from LLM response.

        Returns:
            True if response contains affirmative signal, False otherwise
        """
        response_lower = response.lower().strip()

        # Affirmative signals
        if any(
            word in response_lower
            for word in ["yes", "true", "correct", "valid", "relevant", "예", "맞", "관련"]
        ):
            return True

        # Negative signals
        if any(
            word in response_lower
            for word in ["no", "false", "incorrect", "invalid", "irrelevant", "아니", "틀", "무관"]
        ):
            return False

        # Default to False if ambiguous
        return False
