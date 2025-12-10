"""
SAT Math problem generator implementation.

Generates SAT-aligned math problems with concept tagging.
Currently provides placeholder implementations that will be extended with
actual SAT problem generation logic.
"""

from uuid import uuid4
from models import Problem, CalculatorMode, Solution, SolutionStep
from concepts import get_concept


def generate_sat_linear_equation_problem(
    difficulty: int,
    calculator_mode: CalculatorMode = "none",
) -> Problem:
    """
    Generate an SAT linear equation problem.

    Args:
        difficulty: Problem difficulty (1-4, where 1 is easiest)
        calculator_mode: Calculator mode allowed ("none", "scientific", "graphing")

    Returns:
        A Problem instance with SAT concept tagging

    Raises:
        ValueError: If difficulty is not in range 1-4
    """
    if not 1 <= difficulty <= 4:
        raise ValueError(f"Difficulty must be 1-4, got {difficulty}")

    # Placeholder: in production, this would generate actual SAT linear problems
    # based on difficulty level
    prompt = f"Solve: 2x + 3 = 7"
    final_answer = 2
    
    # Determine primary concept based on difficulty
    if difficulty <= 2:
        primary_concept_id = "sat.algebra.linear_basics"
    else:
        primary_concept_id = "sat.algebra.linear_basics"
    
    # Verify concept exists in registry
    get_concept(primary_concept_id)  # raises KeyError if not found
    
    solution = Solution(
        full_solution_latex=r"$2x + 3 = 7 \implies 2x = 4 \implies x = 2$",
        steps=[
            SolutionStep(1, "Subtract 3 from both sides", r"$2x = 4$"),
            SolutionStep(2, "Divide both sides by 2", r"$x = 2$"),
        ],
        final_answer_latex="$2$",
        sympy_verified=True,
        verification_details="Direct substitution: 2(2) + 3 = 7 ✓",
    )

    return Problem(
        id=str(uuid4()),
        course_id="sat_math",
        unit_id="sat_algebra",
        topic_id="sat_linear",
        difficulty=difficulty,
        calculator_mode=calculator_mode,
        prompt_latex=prompt,
        answer_type="numeric",
        final_answer=final_answer,
        metadata={
            "generator": "sat_math",
            "problem_type": "linear_equation",
        },
        concept_ids=[
            primary_concept_id,
            "alg1.linear_eq.both_sides",  # underlying curriculum concept
        ],
        primary_concept_id=primary_concept_id,
    )


def generate_sat_quadratic_problem(
    difficulty: int,
    calculator_mode: CalculatorMode = "scientific",
) -> Problem:
    """
    Generate an SAT quadratic equation problem.

    Args:
        difficulty: Problem difficulty (1-4)
        calculator_mode: Calculator mode allowed

    Returns:
        A Problem instance with SAT concept tagging
    """
    if not 1 <= difficulty <= 4:
        raise ValueError(f"Difficulty must be 1-4, got {difficulty}")

    prompt = r"Solve: $x^2 - 5x + 6 = 0$"
    final_answer_1 = 2
    final_answer_2 = 3

    primary_concept_id = "sat.algebra.quadratic_solving"
    get_concept(primary_concept_id)

    solution = Solution(
        full_solution_latex=r"$x^2 - 5x + 6 = 0 \implies (x-2)(x-3) = 0 \implies x = 2 \text{ or } x = 3$",
        steps=[
            SolutionStep(1, "Factor the quadratic", r"$(x-2)(x-3) = 0$"),
            SolutionStep(2, "Apply zero product property", r"$x - 2 = 0$ or $x - 3 = 0$"),
            SolutionStep(3, "Solve each equation", r"$x = 2$ or $x = 3$"),
        ],
        final_answer_latex=r"$x = 2$ or $x = 3$",
        sympy_verified=True,
    )

    return Problem(
        id=str(uuid4()),
        course_id="sat_math",
        unit_id="sat_algebra",
        topic_id="sat_quadratic",
        difficulty=difficulty,
        calculator_mode=calculator_mode,
        prompt_latex=prompt,
        answer_type="expression",
        final_answer=(final_answer_1, final_answer_2),
        metadata={
            "generator": "sat_math",
            "problem_type": "quadratic_solving",
        },
        concept_ids=[
            primary_concept_id,
            "alg2.quadratic.solving_methods",  # underlying curriculum concept
        ],
        primary_concept_id=primary_concept_id,
    )


def generate_sat_data_stats_problem(
    difficulty: int,
    calculator_mode: CalculatorMode = "scientific",
) -> Problem:
    """
    Generate an SAT statistics/data analysis problem.

    Args:
        difficulty: Problem difficulty (1-4)
        calculator_mode: Calculator mode allowed

    Returns:
        A Problem instance with SAT concept tagging
    """
    if not 1 <= difficulty <= 4:
        raise ValueError(f"Difficulty must be 1-4, got {difficulty}")

    prompt = "The mean of a dataset is 50 and the median is 48. Which is likely true?"
    final_answer = "The dataset has a few high outliers"

    primary_concept_id = "sat.data.statistics"
    get_concept(primary_concept_id)

    solution = Solution(
        full_solution_latex="When mean > median, the distribution is right-skewed (high outliers pull the mean up)",
        steps=[
            SolutionStep(1, "Recall relationship between mean and median", "Mean > Median suggests right skew"),
            SolutionStep(2, "Identify cause of right skew", "High outliers increase mean more than median"),
        ],
        final_answer_latex="The dataset has a few high outliers",
        sympy_verified=False,
    )

    return Problem(
        id=str(uuid4()),
        course_id="sat_math",
        unit_id="sat_data",
        topic_id="sat_statistics",
        difficulty=difficulty,
        calculator_mode=calculator_mode,
        prompt_latex=prompt,
        answer_type="expression",
        final_answer=final_answer,
        metadata={
            "generator": "sat_math",
            "problem_type": "data_analysis",
        },
        concept_ids=[
            primary_concept_id,
            "probstat.distributions.normal",
        ],
        primary_concept_id=primary_concept_id,
    )
