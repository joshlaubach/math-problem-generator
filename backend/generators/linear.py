"""
Linear equation problem generator implementation.

Wraps the generate_linear_equation_problem function in a ProblemGenerator class.
"""

from models import Problem, CalculatorMode
from generators.base import ProblemGenerator
import generator_linear_impl


class LinearEquationGenerator(ProblemGenerator):
    """
    Problem generator for one-variable linear equations.
    
    Implements the ProblemGenerator interface for the Algebra I topic:
    "Solving one-variable linear equations".
    """

    course_id = "algebra_1"
    unit_id = "alg1_unit_linear_equations"
    topic_id = "alg1_linear_solve_one_var"

    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "none"
    ) -> Problem:
        """
        Generate a linear equation problem.

        Args:
            difficulty: Problem difficulty (1-4)
            calculator_mode: Calculator mode allowed ("none", "scientific", "graphing")

        Returns:
            A Problem instance with embedded Solution

        Raises:
            ValueError: If difficulty is not in range 1-4
        """
        return generator_linear_impl.generate_linear_equation_problem(
            difficulty, calculator_mode
        )
