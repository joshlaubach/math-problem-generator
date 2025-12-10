"""
SAT Math problem generator wrapper.

Implements ProblemGenerator interface for SAT Math topics.
"""

from models import Problem, CalculatorMode
from generators.base import ProblemGenerator
import generator_sat_math_impl


class SATLinearEquationGenerator(ProblemGenerator):
    """Generator for SAT linear equation problems."""
    
    course_id = "sat_math"
    unit_id = "sat_algebra"
    topic_id = "sat_linear"

    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "none",
    ) -> Problem:
        """Generate a SAT linear equation problem."""
        return generator_sat_math_impl.generate_sat_linear_equation_problem(
            difficulty, calculator_mode
        )


class SATQuadraticGenerator(ProblemGenerator):
    """Generator for SAT quadratic equation problems."""
    
    course_id = "sat_math"
    unit_id = "sat_algebra"
    topic_id = "sat_quadratic"

    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "scientific",
    ) -> Problem:
        """Generate a SAT quadratic equation problem."""
        return generator_sat_math_impl.generate_sat_quadratic_problem(
            difficulty, calculator_mode
        )


class SATDataStatsGenerator(ProblemGenerator):
    """Generator for SAT data analysis and statistics problems."""
    
    course_id = "sat_math"
    unit_id = "sat_data"
    topic_id = "sat_statistics"

    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "scientific",
    ) -> Problem:
        """Generate a SAT data analysis problem."""
        return generator_sat_math_impl.generate_sat_data_stats_problem(
            difficulty, calculator_mode
        )
