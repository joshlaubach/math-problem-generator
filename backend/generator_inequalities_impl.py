"""
Linear inequality problem generator.

Generates one-variable linear inequality problems (e.g., 2x + 3 > 7)
with step-by-step solutions verified using SymPy.

Uses solution-first approach: choose target solution set, then construct
an inequality that has that solution.
"""

from dataclasses import dataclass
from typing import Literal
import random
import uuid
from sympy import symbols, solve_univariate_inequality, S, sympify, latex

from models import Problem, Solution, SolutionStep, CalculatorMode


@dataclass
class InequalityProblem:
    """Represents the mathematical structure of a linear inequality."""

    left_expr_str: str  # e.g., "2*x + 3"
    operator: Literal["<", "<=", ">", ">="]  # The inequality operator
    right_expr_str: str  # e.g., "7"


def _choose_target_solution(difficulty: int) -> Literal["<", "<=", ">", ">="]:
    """
    Choose a random inequality operator for the target solution set.

    Args:
        difficulty: 1-4 (not used, but kept for consistency)

    Returns:
        One of: <, <=, >, >=
    """
    return random.choice(["<", "<=", ">", ">="])


def _build_difficulty_1_inequality() -> InequalityProblem:
    """Difficulty 1: Simple one-step inequalities (e.g., x > 5)."""
    operator = _choose_target_solution(1)
    target = random.randint(-10, 10)
    # Simple: x op target
    return InequalityProblem(left_expr_str="x", operator=operator, right_expr_str=str(target))


def _build_difficulty_2_inequality() -> InequalityProblem:
    """Difficulty 2: Two-step inequalities (e.g., 2x > 10, or x + 3 < 8)."""
    operator = _choose_target_solution(2)

    if random.choice([True, False]):
        # Format: coeff * x op constant
        coeff = random.randint(2, 5)
        target = random.randint(-20, 20)
        return InequalityProblem(
            left_expr_str=f"{coeff}*x",
            operator=operator,
            right_expr_str=str(target),
        )
    else:
        # Format: x + const op target
        const = random.randint(-10, 10)
        target = random.randint(-10, 10)
        sign = "+" if const >= 0 else ""
        return InequalityProblem(
            left_expr_str=f"x {sign} {const}".replace("  ", " "),
            operator=operator,
            right_expr_str=str(target),
        )


def _build_difficulty_3_inequality() -> InequalityProblem:
    """Difficulty 3: Mixed inequalities (e.g., 3x + 4 > -5)."""
    operator = _choose_target_solution(3)
    coeff = random.randint(2, 7)
    const = random.randint(-10, 10)
    target = random.randint(-20, 20)

    sign = "+" if const >= 0 else ""
    return InequalityProblem(
        left_expr_str=f"{coeff}*x {sign} {const}".replace("  ", " "),
        operator=operator,
        right_expr_str=str(target),
    )


def _build_difficulty_4_inequality() -> InequalityProblem:
    """Difficulty 4: Complex with negative coefficients and constants."""
    operator = _choose_target_solution(4)
    coeff = random.randint(-10, -2) if random.choice([True, False]) else random.randint(2, 10)
    const = random.randint(-20, 20)
    target = random.randint(-30, 30)

    sign = "+" if const >= 0 else ""
    return InequalityProblem(
        left_expr_str=f"{coeff}*x {sign} {const}".replace("  ", " "),
        operator=operator,
        right_expr_str=str(target),
    )


def _verify_inequality(inequality: InequalityProblem) -> tuple[bool, str]:
    """
    Verify the inequality is valid using SymPy.

    Args:
        inequality: The InequalityProblem to verify

    Returns:
        (is_valid, explanation)
    """
    try:
        x = symbols("x")
        left = sympify(inequality.left_expr_str)
        right = sympify(inequality.right_expr_str)

        # Build the inequality expression
        if inequality.operator == "<":
            expr = left < right
        elif inequality.operator == "<=":
            expr = left <= right
        elif inequality.operator == ">":
            expr = left > right
        elif inequality.operator == ">=":
            expr = left >= right

        # Solve to verify it's solvable
        solution_set = solve_univariate_inequality(expr, x, relational=False)

        return (True, str(solution_set))
    except Exception as e:
        return (False, f"Error verifying inequality: {str(e)}")


def _construct_solution_steps(inequality: InequalityProblem) -> list[SolutionStep]:
    """
    Construct step-by-step solution for the inequality.

    Args:
        inequality: The InequalityProblem

    Returns:
        List of SolutionStep objects
    """
    steps = []
    step_index = 0

    # Step 1: State the problem
    step_index += 1
    steps.append(
        SolutionStep(
            index=step_index,
            description_latex="Given inequality",
            expression_latex=f"{inequality.left_expr_str} {inequality.operator} {inequality.right_expr_str}",
        )
    )

    # Step 2-N: Solve step by step
    x = symbols("x")
    left = sympify(inequality.left_expr_str)
    right = sympify(inequality.right_expr_str)

    # For simplicity, show the solving process
    if inequality.operator == "<":
        expr = left < right
    elif inequality.operator == "<=":
        expr = left <= right
    elif inequality.operator == ">":
        expr = left > right
    else:  # >=
        expr = left >= right

    solution_set = solve_univariate_inequality(expr, x, relational=False)

    step_index += 1
    steps.append(
        SolutionStep(
            index=step_index,
            description_latex="Solve for x",
            expression_latex=str(solution_set),
        )
    )

    return steps


def generate_linear_inequality_problem(
    difficulty: int, calculator_mode: CalculatorMode = "none"
) -> Problem:
    """
    Generate a linear inequality problem.

    Uses solution-first approach: build the inequality, verify it, then
    create step-by-step solution.

    Args:
        difficulty: 1-4 for different complexities
        calculator_mode: "none", "scientific", or "graphing"

    Returns:
        A Problem instance with complete solution

    Raises:
        ValueError: If difficulty is not in range 1-4
    """
    if not (1 <= difficulty <= 4):
        raise ValueError(f"Difficulty must be 1-4, got {difficulty}")

    # Step 1: Generate inequality based on difficulty
    if difficulty == 1:
        inequality = _build_difficulty_1_inequality()
    elif difficulty == 2:
        inequality = _build_difficulty_2_inequality()
    elif difficulty == 3:
        inequality = _build_difficulty_3_inequality()
    else:  # difficulty == 4
        inequality = _build_difficulty_4_inequality()

    # Step 2: Verify using SymPy
    is_valid, verification_details = _verify_inequality(inequality)
    if not is_valid:
        raise ValueError(f"Generated invalid inequality: {verification_details}")

    # Step 3: Solve to get the solution set
    x = symbols("x")
    left = sympify(inequality.left_expr_str)
    right = sympify(inequality.right_expr_str)

    if inequality.operator == "<":
        expr = left < right
    elif inequality.operator == "<=":
        expr = left <= right
    elif inequality.operator == ">":
        expr = left > right
    else:  # >=
        expr = left >= right

    solution_set = solve_univariate_inequality(expr, x, relational=False)

    # Step 4: Build the problem
    problem_id = f"ineq_{uuid.uuid4().hex[:8]}"

    prompt_latex = f"{inequality.left_expr_str} {inequality.operator} {inequality.right_expr_str}"

    # Step 5: Construct solution
    solution_steps = _construct_solution_steps(inequality)

    # Full solution LaTeX
    full_solution_latex = "\\begin{align*}\n"
    for step in solution_steps:
        full_solution_latex += f"  {step.expression_latex} & \\quad \\text{{{step.description_latex}}} \\\\\n"
    full_solution_latex += "\\end{align*}"

    final_answer_latex = str(solution_set)

    solution = Solution(
        full_solution_latex=full_solution_latex,
        steps=solution_steps,
        final_answer_latex=final_answer_latex,
        sympy_verified=is_valid,
        verification_details=verification_details,
    )

    # Step 6: Map difficulty to primary concept
    concept_map = {
        1: "alg1.linear_ineq.one_step_int",
        2: "alg1.linear_ineq.two_step_int",
        3: "alg1.linear_ineq.negative_coeff_reverse",
        4: "alg1.linear_ineq.rational_coeffs"
    }

    return Problem(
        id=problem_id,
        course_id="alg1",
        unit_id="alg1_linear_eqs",
        topic_id="alg1_linear_inequalities_one_var",
        difficulty=difficulty,
        calculator_mode=calculator_mode,
        prompt_latex=prompt_latex,
        answer_type="expression",  # Solution is an interval or union
        final_answer=str(solution_set),
        metadata={"solution": solution},
        primary_concept_id=concept_map[difficulty],
        concept_ids=[concept_map[difficulty]]  # For now, primary is the only concept tagged
    )
