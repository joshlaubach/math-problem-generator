"""
Generator for one-variable linear equations.

Implements solution-first generation: choose a target solution x0,
construct an equation with that solution, verify it with SymPy,
and generate a step-by-step solution.
"""

import random
import uuid
from typing import Optional

import sympy as sp
from sympy import symbols, Eq, solve, latex, Rational

from models import Problem, Solution, SolutionStep, CalculatorMode


x = symbols('x', real=True)


def _choose_target_solution(difficulty: int) -> int:
    """
    Choose a "nice" integer target solution based on difficulty.
    
    Difficulty 1-2: Small integers (-10 to 10)
    Difficulty 3-4: Slightly larger range (-20 to 20)
    """
    if difficulty in (1, 2):
        return random.randint(-10, 10)
    elif difficulty in (3, 4):
        return random.randint(-20, 20)
    else:
        raise ValueError(f"Invalid difficulty: {difficulty}. Must be 1-4.")


def _build_difficulty_1_equation(x0: int) -> tuple[sp.Expr, sp.Expr]:
    """
    Build a difficulty 1 equation: x + b = c or x - b = c.
    Returns (lhs, rhs) to form Eq(lhs, rhs).
    """
    b = random.randint(1, 10)
    if random.choice([True, False]):
        # x + b = c
        c = x0 + b
        lhs = x + b
    else:
        # x - b = c
        c = x0 - b
        lhs = x - b
    return lhs, c


def _build_difficulty_2_equation(x0: int) -> tuple[sp.Expr, sp.Expr]:
    """
    Build a difficulty 2 equation: a*x + b = c.
    Returns (lhs, rhs) to form Eq(lhs, rhs).
    """
    a = random.randint(-5, 5)
    while a == 0 or a == 1:  # Ensure a is nonzero and not trivial
        a = random.randint(-5, 5)
    
    b = random.randint(-10, 10)
    c = a * x0 + b
    lhs = a * x + b
    return lhs, c


def _build_difficulty_3_equation(x0: int) -> tuple[sp.Expr, sp.Expr]:
    """
    Build a difficulty 3 equation: a*x + b = c*x + d.
    Variables on both sides, integer coefficients.
    Returns (lhs, rhs) to form Eq(lhs, rhs).
    """
    a = random.randint(-5, 5)
    while a == 0:
        a = random.randint(-5, 5)
    
    c = random.randint(-5, 5)
    while c == 0 or c == a:  # Ensure c != 0 and c != a (otherwise no solution or infinite solutions)
        c = random.randint(-5, 5)
    
    b = random.randint(-10, 10)
    d = random.randint(-10, 10)
    
    # Adjust d so that a*x0 + b = c*x0 + d
    # => d = a*x0 + b - c*x0 = (a - c)*x0 + b
    d = (a - c) * x0 + b
    
    lhs = a * x + b
    rhs = c * x + d
    return lhs, rhs


def _build_difficulty_4_equation(x0: int) -> tuple[sp.Expr, sp.Expr]:
    """
    Build a difficulty 4 equation with fractional coefficients: (p/q)*x + b = (r/s)*x + d.
    Returns (lhs, rhs) to form Eq(lhs, rhs).
    """
    # Generate small rational coefficients
    p = random.randint(1, 5)
    q = random.randint(1, 3)
    a = Rational(p, q)
    if random.choice([True, False]):
        a = -a
    
    r = random.randint(1, 5)
    s = random.randint(1, 3)
    c = Rational(r, s)
    if random.choice([True, False]):
        c = -c
    
    # Ensure a != c
    while a == c:
        r = random.randint(1, 5)
        s = random.randint(1, 3)
        c = Rational(r, s)
        if random.choice([True, False]):
            c = -c
    
    b = random.randint(-10, 10)
    
    # d = (a - c)*x0 + b
    d = (a - c) * x0 + b
    
    lhs = a * x + b
    rhs = c * x + d
    return lhs, rhs


def _build_equation_for_difficulty(difficulty: int, x0: int) -> tuple[sp.Expr, sp.Expr]:
    """
    Build an equation (lhs, rhs) for a given difficulty level and target solution x0.
    """
    if difficulty == 1:
        return _build_difficulty_1_equation(x0)
    elif difficulty == 2:
        return _build_difficulty_2_equation(x0)
    elif difficulty == 3:
        return _build_difficulty_3_equation(x0)
    elif difficulty == 4:
        return _build_difficulty_4_equation(x0)
    else:
        raise ValueError(f"Invalid difficulty: {difficulty}. Must be 1-4.")


def _verify_equation(lhs: sp.Expr, rhs: sp.Expr, expected_solution: int) -> tuple[bool, str]:
    """
    Verify that the equation lhs = rhs has exactly [expected_solution] as its solution set.
    Returns (verified: bool, details: str).
    """
    equation = Eq(lhs, rhs)
    try:
        solutions = solve(equation, x)
        if solutions == [expected_solution]:
            return True, f"Verified: {latex(equation)} has solution x = {expected_solution}"
        else:
            return False, f"Solution mismatch: expected [{expected_solution}], got {solutions}"
    except Exception as e:
        return False, f"Solver error: {str(e)}"


def _construct_solution_steps(
    difficulty: int,
    lhs: sp.Expr,
    rhs: sp.Expr,
    x0: int
) -> list[SolutionStep]:
    """
    Construct step-by-step solution for the given equation and difficulty.
    """
    steps = []
    step_index = 0
    
    # Helper function to extract constant term from an expression
    def get_constant_term(expr: sp.Expr) -> Optional[sp.Expr]:
        """Extract the constant term from an expression."""
        if isinstance(expr, sp.Add):
            for arg in expr.args:
                if arg.is_constant():
                    return arg
        elif expr.is_constant():
            return expr
        return None
    
    if difficulty == 1:
        # Forms: x + b = c or x - b = c
        # Step 1: Subtract the constant from both sides
        const_term = get_constant_term(lhs)
        if const_term is not None and const_term != 0:
            new_rhs = rhs - const_term
            steps.append(SolutionStep(
                index=step_index,
                description_latex=f"Subtract ${latex(const_term)}$ from both sides",
                expression_latex=latex(Eq(x, new_rhs))
            ))
            step_index += 1
        
        # Step 2: Simplify (showing final answer)
        steps.append(SolutionStep(
            index=step_index,
            description_latex="Simplify",
            expression_latex=latex(Eq(x, x0))
        ))
    
    elif difficulty == 2:
        # Form: a*x + b = c
        current_lhs = lhs
        current_rhs = rhs
        
        # Step 1: Subtract constant from both sides
        const_term = get_constant_term(current_lhs)
        if const_term is not None and const_term != 0:
            current_rhs = current_rhs - const_term
            current_lhs = current_lhs - const_term
            steps.append(SolutionStep(
                index=step_index,
                description_latex=f"Subtract ${latex(const_term)}$ from both sides",
                expression_latex=latex(Eq(current_lhs, current_rhs))
            ))
            step_index += 1
        
        # Step 2: Get coefficient of x and divide
        coeff_x = sp.Poly(current_lhs, x).nth(1) if current_lhs != x else 1
        if coeff_x and coeff_x != 1:
            new_lhs = current_lhs / coeff_x
            new_rhs = current_rhs / coeff_x
            steps.append(SolutionStep(
                index=step_index,
                description_latex=f"Divide both sides by ${latex(coeff_x)}$",
                expression_latex=latex(Eq(new_lhs, new_rhs))
            ))
            step_index += 1
        
        # Step 3: Simplify
        steps.append(SolutionStep(
            index=step_index,
            description_latex="Simplify",
            expression_latex=latex(Eq(x, x0))
        ))
    
    elif difficulty == 3:
        # Form: a*x + b = c*x + d
        current_lhs = lhs
        current_rhs = rhs
        
        # Step 1: Collect variable terms on left side
        rhs_coeff = sp.Poly(current_rhs, x).nth(1)
        rhs_const = get_constant_term(current_rhs) or 0
        
        new_lhs = current_lhs - rhs_coeff * x
        new_rhs = rhs_const
        steps.append(SolutionStep(
            index=step_index,
            description_latex=f"Subtract ${latex(rhs_coeff * x)}$ from both sides",
            expression_latex=latex(Eq(new_lhs, new_rhs))
        ))
        step_index += 1
        current_lhs = new_lhs
        current_rhs = new_rhs
        
        # Step 2: Collect constants on right side
        lhs_const = get_constant_term(current_lhs) or 0
        if lhs_const != 0:
            new_lhs = current_lhs - lhs_const
            new_rhs = current_rhs - lhs_const
            steps.append(SolutionStep(
                index=step_index,
                description_latex=f"Subtract ${latex(lhs_const)}$ from both sides",
                expression_latex=latex(Eq(new_lhs, new_rhs))
            ))
            step_index += 1
            current_lhs = new_lhs
            current_rhs = new_rhs
        
        # Step 3: Divide by coefficient of x
        coeff_x = sp.Poly(current_lhs, x).nth(1)
        if coeff_x and coeff_x != 1:
            steps.append(SolutionStep(
                index=step_index,
                description_latex=f"Divide both sides by ${latex(coeff_x)}$",
                expression_latex=latex(Eq(x, current_rhs / coeff_x))
            ))
            step_index += 1
        
        # Final: show answer
        steps.append(SolutionStep(
            index=step_index,
            description_latex="Simplify",
            expression_latex=latex(Eq(x, x0))
        ))
    
    else:  # difficulty == 4
        # Form: (p/q)*x + b = (r/s)*x + d (similar to difficulty 3)
        current_lhs = lhs
        current_rhs = rhs
        
        # Step 1: Collect variable terms on left side
        rhs_coeff = sp.Poly(current_rhs, x).nth(1)
        rhs_const = get_constant_term(current_rhs) or 0
        
        new_lhs = sp.expand(current_lhs - rhs_coeff * x)
        new_rhs = rhs_const
        steps.append(SolutionStep(
            index=step_index,
            description_latex=f"Subtract ${latex(rhs_coeff * x)}$ from both sides",
            expression_latex=latex(Eq(new_lhs, new_rhs))
        ))
        step_index += 1
        current_lhs = new_lhs
        current_rhs = new_rhs
        
        # Step 2: Collect constants on right side
        lhs_const = get_constant_term(current_lhs) or 0
        if lhs_const != 0:
            new_lhs = current_lhs - lhs_const
            new_rhs = current_rhs - lhs_const
            steps.append(SolutionStep(
                index=step_index,
                description_latex=f"Subtract ${latex(lhs_const)}$ from both sides",
                expression_latex=latex(Eq(new_lhs, new_rhs))
            ))
            step_index += 1
            current_lhs = new_lhs
            current_rhs = new_rhs
        
        # Step 3: Divide by coefficient of x
        coeff_x = sp.Poly(current_lhs, x).nth(1)
        if coeff_x and coeff_x != 1:
            steps.append(SolutionStep(
                index=step_index,
                description_latex=f"Divide both sides by ${latex(coeff_x)}$",
                expression_latex=latex(Eq(x, current_rhs / coeff_x))
            ))
            step_index += 1
        
        # Final: show answer
        steps.append(SolutionStep(
            index=step_index,
            description_latex="Simplify",
            expression_latex=latex(Eq(x, x0))
        ))
    
    return steps


def generate_linear_equation_problem(
    difficulty: int,
    calculator_mode: CalculatorMode = "none"
) -> Problem:
    """
    Generate a linear equation problem using solution-first approach.
    
    Args:
        difficulty: Problem difficulty (1-4)
        calculator_mode: Calculator mode allowed ("none", "scientific", "graphing")
    
    Returns:
        A Problem instance with generated equation and solution.
    
    Raises:
        ValueError: If difficulty is not in range 1-4.
    """
    if difficulty not in (1, 2, 3, 4):
        raise ValueError(f"Invalid difficulty: {difficulty}. Must be 1-4.")
    
    # Step 1: Choose target solution
    x0 = _choose_target_solution(difficulty)
    
    # Step 2: Build equation
    lhs, rhs = _build_equation_for_difficulty(difficulty, x0)
    
    # Step 3: Verify with SymPy
    verified, verification_details = _verify_equation(lhs, rhs, x0)
    
    if not verified:
        # In case of verification failure, raise an error
        raise RuntimeError(f"Equation verification failed: {verification_details}")
    
    # Step 4: Create solution steps
    steps = _construct_solution_steps(difficulty, lhs, rhs, x0)
    
    # Step 5: Build full solution LaTeX
    full_solution_lines = []
    for step in steps:
        full_solution_lines.append(f"{step.description_latex} \\\\ {step.expression_latex}")
    full_solution_latex = " \\\\ ".join(full_solution_lines)
    
    # Step 6: Create Solution object
    solution = Solution(
        full_solution_latex=full_solution_latex,
        steps=steps,
        final_answer_latex=latex(x0),
        sympy_verified=verified,
        verification_details=verification_details
    )
    
    # Step 7: Create Problem object
    prompt_latex = latex(Eq(lhs, rhs))
    
    # Step 8: Map difficulty to primary concept
    concept_map = {
        1: "alg1.linear_eq.one_step_int",
        2: "alg1.linear_eq.two_step_int",
        3: "alg1.linear_eq.multistep_one_side",
        4: "alg1.linear_eq.both_sides"
    }
    
    problem = Problem(
        id=str(uuid.uuid4()),
        course_id="algebra_1",
        unit_id="alg1_unit_linear_equations",
        topic_id="alg1_linear_solve_one_var",
        difficulty=difficulty,
        calculator_mode=calculator_mode,
        prompt_latex=f"Solve for $x$: {prompt_latex}",
        answer_type="numeric",
        final_answer=x0,
        metadata={"solution": solution},
        primary_concept_id=concept_map[difficulty],
        concept_ids=[concept_map[difficulty]]  # For now, primary is the only concept tagged
    )
    
    return problem

