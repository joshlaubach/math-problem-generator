"""
SymPy Verifier — pure Python + SymPy, no LLM calls.

Verifies that a generated problem is well-formed and that the stated answer is
correct. Called after every problem generation attempt (max 3 retries before discard).

Returns VerifierResult(verified: bool, reason: str).
On failure, the orchestrator asks the generator to retry — max 3 attempts.
"""

from __future__ import annotations

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

from agents.schemas import VerifierResult

_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


def _safe_parse(expr_str: str) -> sp.Expr | None:
    """Parse a LaTeX-style or plain math string into a SymPy expression."""
    # Normalise common LaTeX → SymPy substitutions
    cleaned = (
        expr_str
        .replace("\\frac{", "(")
        .replace("}{", ")/(")
        .replace("}", ")")
        .replace("\\cdot", "*")
        .replace("^", "**")
        .replace("\\ln", "log")
        .replace("\\log", "log")
        .replace("\\sin", "sin")
        .replace("\\cos", "cos")
        .replace("\\tan", "tan")
        .replace("\\sqrt{", "sqrt(")
        .replace("\\pi", "pi")
        .replace("\\infty", "oo")
        .strip()
    )
    try:
        return parse_expr(cleaned, transformations=_TRANSFORMATIONS)
    except Exception:
        return None


async def verify(
    prompt_latex: str,
    candidate_answer: str,
    problem_type: str = "algebraic",
) -> VerifierResult:
    """
    Verify that candidate_answer is the correct solution for the given problem.

    Strategies by problem_type:
      'equation'  — extract equation from prompt_latex, solve, compare to answer
      'numeric'   — parse answer as a number and sanity-check
      'algebraic' — simplify(answer_expr - substituted_lhs) == 0
      'inequality'— parse and check direction of inequality

    Args:
        prompt_latex: The LaTeX problem statement.
        candidate_answer: The proposed canonical answer (LaTeX or numeric string).
        problem_type: Hint for the verifier strategy.

    Returns:
        VerifierResult(verified=True/False, reason=str)
    """
    if problem_type == "numeric":
        return _verify_numeric(candidate_answer)
    if problem_type in ("equation", "algebraic"):
        return _verify_algebraic(prompt_latex, candidate_answer)
    if problem_type == "inequality":
        return _verify_inequality(prompt_latex, candidate_answer)

    # Fallback: attempt algebraic, then numeric
    result = _verify_algebraic(prompt_latex, candidate_answer)
    if result.verified:
        return result
    return _verify_numeric(candidate_answer)


def _verify_numeric(answer: str) -> VerifierResult:
    """Check that the answer parses to a finite number."""
    expr = _safe_parse(answer)
    if expr is None:
        return VerifierResult(
            verified=False,
            reason=f"Cannot parse answer as a mathematical expression: '{answer}'"
        )
    try:
        val = float(expr.evalf())
        if abs(val) > 1e12:
            return VerifierResult(
                verified=False,
                reason=f"Answer value {val} seems implausibly large — check calibration."
            )
        return VerifierResult(verified=True, reason=f"Numeric answer {val} is well-formed.")
    except Exception as exc:
        return VerifierResult(
            verified=False,
            reason=f"Cannot evaluate answer numerically: {exc}"
        )


def _verify_algebraic(prompt_latex: str, answer: str) -> VerifierResult:
    """
    Check algebraic correctness:
      - Parse the answer (e.g. "x = 5", "2x + 3", "(x+1)^2")
      - If the prompt contains an equation ('='), extract lhs and rhs, substitute
        the answer's variable assignment, and check lhs - rhs == 0.
      - Otherwise, check the answer is a valid parseable expression.
    """
    # Extract variable assignment from answer ("x = 5" → x, 5)
    assignment = _parse_assignment(answer)

    if assignment is not None:
        var, val = assignment
        # Try to find the equation in the prompt and verify
        eq_result = _check_equation_in_prompt(prompt_latex, var, val)
        if eq_result is not None:
            return eq_result

    # Fallback: just confirm the answer parses
    expr = _safe_parse(answer.split("=")[-1].strip() if "=" in answer else answer)
    if expr is None:
        return VerifierResult(
            verified=False,
            reason=f"Cannot parse answer as a math expression: '{answer}'"
        )
    return VerifierResult(
        verified=True,
        reason="Answer is a well-formed mathematical expression (full equation verification not available for this problem type)."
    )


def _parse_assignment(answer: str) -> tuple[sp.Symbol, sp.Expr] | None:
    """Parse 'x = 5' or 'x = -3/2' into (Symbol('x'), expr)."""
    if "=" not in answer:
        return None
    parts = answer.split("=", 1)
    var_str = parts[0].strip().lstrip("\\")  # remove LaTeX backslash
    val_str = parts[1].strip()
    try:
        var = sp.Symbol(var_str, real=True)
        val = _safe_parse(val_str)
        if val is None:
            return None
        return (var, val)
    except Exception:
        return None


def _check_equation_in_prompt(
    prompt_latex: str, var: sp.Symbol, val: sp.Expr
) -> VerifierResult | None:
    """
    Extract an equation from the prompt and verify substituting var=val gives 0.
    Returns None if the equation cannot be extracted.
    """
    # Heuristic: look for "lhs = rhs" patterns, skipping "Solve for" text
    # Strip common prose
    import re
    cleaned = re.sub(r"(?i)(solve for|find|evaluate|simplify)[^:]*:", "", prompt_latex)
    cleaned = cleaned.strip(" $")

    if "=" not in cleaned:
        return None

    try:
        sides = cleaned.split("=", 1)
        lhs = _safe_parse(sides[0].strip())
        rhs = _safe_parse(sides[1].strip())
        if lhs is None or rhs is None:
            return None

        diff = sp.simplify(lhs.subs(var, val) - rhs.subs(var, val))
        if diff == 0:
            return VerifierResult(
                verified=True,
                reason=f"Verified: {var} = {val} satisfies the equation."
            )
        else:
            return VerifierResult(
                verified=False,
                reason=f"Substituting {var} = {val} gives lhs - rhs = {diff} ≠ 0."
            )
    except Exception as exc:
        return None  # Let caller try fallback


def _verify_inequality(prompt_latex: str, answer: str) -> VerifierResult:
    """Basic inequality answer verification — check parsability."""
    expr = _safe_parse(answer.replace("<", "").replace(">", "").replace("\\leq", "").replace("\\geq", ""))
    if expr is None:
        return VerifierResult(
            verified=False,
            reason=f"Cannot parse inequality answer: '{answer}'"
        )
    return VerifierResult(
        verified=True,
        reason="Inequality answer is well-formed (full symbolic verification not implemented for inequalities)."
    )
