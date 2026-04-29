"""
Answer Checker — pure Python + SymPy, no LLM calls.

Uses symbolic equivalence to check student answers against the canonical answer.
Handles algebraic forms, simplified expressions, and floating-point tolerances.

Correct equivalences verified:
  (x+1)**2      ==  x**2 + 2*x + 1
  ln(exp(2))    ==  2
  sin(x)**2 + cos(x)**2 == 1
  2/4           ==  1/2
  0.333...      ==  1/3   (within tolerance)
"""

from __future__ import annotations

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

from agents.schemas import CheckAnswerResult

_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)
_FLOAT_TOLERANCE = 1e-9


def _parse(expr_str: str) -> sp.Expr | None:
    """Parse a student or canonical answer string into a SymPy expression."""
    cleaned = (
        expr_str.strip()
        .replace("^", "**")
        .replace("\\cdot", "*")
        .replace("\\times", "*")
        .replace("\\ln", "log")
        .replace("\\log", "log")
        .replace("\\sin", "sin")
        .replace("\\cos", "cos")
        .replace("\\tan", "tan")
        .replace("\\sqrt{", "sqrt(")
        .replace("\\pi", "pi")
        .replace("\\infty", "oo")
    )
    # Remove trailing '}' without matching '{' (leftover from LaTeX cleanup)
    while "}" in cleaned and "{" not in cleaned:
        cleaned = cleaned.replace("}", ")")
    try:
        return parse_expr(cleaned, transformations=_TRANSFORMATIONS)
    except Exception:
        return None


async def check(
    student_answer: str,
    canonical_answer: str,
    answer_type: str = "algebraic",
) -> CheckAnswerResult:
    """
    Check whether student_answer is mathematically equivalent to canonical_answer.

    Strategy:
      1. Exact string match (after normalisation)
      2. SymPy symbolic: simplify(student - canonical) == 0
      3. Numeric float approximation within _FLOAT_TOLERANCE
      4. If student contains '=', extract the RHS and compare

    Args:
        student_answer: LaTeX or plain math string from MathLive input.
        canonical_answer: Ground-truth answer stored with the Problem record.
        answer_type: Hint for parse strategy ('algebraic', 'numeric', 'set').

    Returns:
        CheckAnswerResult(correct, equivalent_form, partial_credit_reason)
    """
    student = student_answer.strip()
    canonical = canonical_answer.strip()

    # Step 1: exact match
    if _normalize(student) == _normalize(canonical):
        return CheckAnswerResult(correct=True, equivalent_form=False)

    # Step 2: parse both sides
    # Handle "x = <value>" style answers — extract the value part
    s_expr = _parse_answer_value(student)
    c_expr = _parse_answer_value(canonical)

    if s_expr is None or c_expr is None:
        # Cannot parse — fall back to string comparison
        return CheckAnswerResult(
            correct=False,
            equivalent_form=False,
            partial_credit_reason="Could not parse one or both answers symbolically."
        )

    # Step 3: symbolic equivalence — simplify(student - canonical) == 0
    try:
        diff = sp.simplify(s_expr - c_expr)
        if diff == 0:
            # equivalent_form: True when the student wrote a different-looking form
            # (e.g. (x+1)**2 vs x**2+2*x+1, or 2/4 vs 1/2)
            equivalent_form = _normalize(student) != _normalize(canonical)
            return CheckAnswerResult(correct=True, equivalent_form=equivalent_form)
    except Exception:
        pass

    # Step 4: numeric approximation
    try:
        s_num = complex(s_expr.evalf())
        c_num = complex(c_expr.evalf())
        if abs(s_num - c_num) < _FLOAT_TOLERANCE:
            return CheckAnswerResult(correct=True, equivalent_form=True)
    except Exception:
        pass

    # Step 5: try trigonometric / symbolic identity expansions
    try:
        expanded_diff = sp.trigsimp(sp.expand(s_expr - c_expr))
        if expanded_diff == 0:
            return CheckAnswerResult(correct=True, equivalent_form=True)
    except Exception:
        pass

    return CheckAnswerResult(correct=False, equivalent_form=False)


def _normalize(s: str) -> str:
    """Minimal string normalization for quick equality checks."""
    return (
        s.lower()
        .replace(" ", "")
        .replace("\\,", "")
        .replace("\\!", "")
    )


def _parse_answer_value(answer: str) -> sp.Expr | None:
    """
    Parse an answer string, handling 'var = value' style answers.
    Returns the value expression for comparison.
    """
    if "=" in answer:
        # "x = 5" → use "5" for comparison
        rhs = answer.split("=", 1)[1].strip()
        return _parse(rhs)
    return _parse(answer)
