"""
Linear Inequality Problem Generator using the abstraction.

Concrete implementation of ProblemGenerator for linear inequalities.
"""

from generators.base import ProblemGenerator
from generator_inequalities_impl import generate_linear_inequality_problem
from models import Problem, CalculatorMode


class InequalityProblemGenerator(ProblemGenerator):
    """
    Generates linear one-variable inequality problems.

    Example: 2x + 3 > 7
    """

    course_id: str = "alg1"
    unit_id: str = "alg1_linear_eqs"
    topic_id: str = "alg1_linear_inequalities_one_var"

    def __init__(self):
        """Initialize the inequality problem generator."""
        pass

    def generate(
        self, difficulty: int, calculator_mode: CalculatorMode = "none"
    ) -> Problem:
        """
        Generate a linear inequality problem.

        Args:
            difficulty: 1-4 for increasing complexity
            calculator_mode: "none", "scientific", or "graphing"

        Returns:
            A Problem instance
        """
        return generate_linear_inequality_problem(difficulty, calculator_mode)
