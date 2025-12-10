"""
Base class for problem generators.

Defines the ProblemGenerator interface that all topic-specific generators
must implement.
"""

from abc import ABC, abstractmethod

from models import Problem, CalculatorMode


class ProblemGenerator(ABC):
    """Abstract base class for problem generators."""

    course_id: str
    unit_id: str
    topic_id: str

    @abstractmethod
    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "none"
    ) -> Problem:
        """
        Generate a problem for the given difficulty and calculator mode.

        Args:
            difficulty: Problem difficulty level (typically 1-4)
            calculator_mode: Calculator mode allowed for the problem

        Returns:
            A Problem instance with embedded Solution

        Raises:
            ValueError: If difficulty is out of valid range
        """
        ...
