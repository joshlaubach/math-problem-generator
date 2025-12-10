"""
AP Calculus problem generator wrapper.

Implements ProblemGenerator interface for AP Calculus AB and BC topics.
"""

from models import Problem, CalculatorMode
from generators.base import ProblemGenerator
import generator_ap_calculus_impl


class APCalcDerivativePowerRuleGenerator(ProblemGenerator):
    """Generator for AP Calculus power rule derivative problems."""
    
    course_id = "ap_calculus"
    unit_id = "ap_derivatives"
    topic_id = "ap_deriv_rules"

    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "none",
    ) -> Problem:
        """Generate an AP Calculus power rule derivative problem."""
        return generator_ap_calculus_impl.generate_ap_calc_derivative_power_rule_problem(
            difficulty, calculator_mode
        )


class APCalcChainRuleGenerator(ProblemGenerator):
    """Generator for AP Calculus chain rule problems."""
    
    course_id = "ap_calculus"
    unit_id = "ap_derivatives"
    topic_id = "ap_deriv_chain"

    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "none",
    ) -> Problem:
        """Generate an AP Calculus chain rule problem."""
        return generator_ap_calculus_impl.generate_ap_calc_chain_rule_problem(
            difficulty, calculator_mode
        )


class APCalcIntegralFTCGenerator(ProblemGenerator):
    """Generator for AP Calculus Fundamental Theorem of Calculus problems."""
    
    course_id = "ap_calculus"
    unit_id = "ap_integrals"
    topic_id = "ap_int_ftc"

    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "none",
    ) -> Problem:
        """Generate an AP Calculus FTC problem."""
        return generator_ap_calculus_impl.generate_ap_calc_integral_ftc_problem(
            difficulty, calculator_mode
        )


class APCalcBCSeriesGenerator(ProblemGenerator):
    """Generator for AP Calculus BC series convergence problems."""
    
    course_id = "ap_calculus"
    unit_id = "ap_series"
    topic_id = "ap_series_conv"

    def generate(
        self,
        difficulty: int,
        calculator_mode: CalculatorMode = "none",
    ) -> Problem:
        """Generate an AP Calculus BC series problem."""
        return generator_ap_calculus_impl.generate_ap_calc_bc_series_convergence_problem(
            difficulty, calculator_mode
        )
