"""
Shared LaTeX → SymPy parsing for answer checking and problem verification.

MathLive (the answer input widget) emits raw LaTeX — \\frac{1}{2}, \\sqrt{2},
\\left(x+1\\right)^2 — which the legacy string cleaners in answer_checker and
verifier could not parse, so correct answers were graded wrong (pre-beta audit
Blocker C1). This module is the single parse path for both callers:

  1. sympy.parsing.latex.parse_latex (ANTLR-backed; requires
     antlr4-python3-runtime, pinned in requirements.txt)
  2. normalize_latex() + parse_expr — a brace-matching structural rewrite that
     covers MathLive output when the ANTLR grammar rejects an input
  3. bare parse_expr with the legacy substitutions

All paths return None instead of raising, matching the old contract.
"""

from __future__ import annotations

import re
from typing import Optional

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

# LaTeX commands that map to SymPy function names (applied before the generic
# backslash-strip so \ln doesn't become the symbol "ln").
_FUNCTION_MAP = [
    (r"\\ln", "log"),
    (r"\\log", "log"),
    (r"\\sin", "sin"),
    (r"\\cos", "cos"),
    (r"\\tan", "tan"),
    (r"\\sec", "sec"),
    (r"\\csc", "csc"),
    (r"\\cot", "cot"),
    (r"\\arcsin", "asin"),
    (r"\\arccos", "acos"),
    (r"\\arctan", "atan"),
    (r"\\exp", "exp"),
]

_CONSTANT_MAP = [
    (r"\\pi", "pi"),
    (r"\\infty", "oo"),
    (r"\\cdot", "*"),
    (r"\\times", "*"),
    (r"\\div", "/"),
    (r"\\pm", "+"),  # answers like "\pm 2" degrade to the positive branch
]

_FRAC_CMD = re.compile(r"\\[dt]?frac")
_SQRT_IDX = re.compile(r"\\sqrt\s*\[([^\]]*)\]")
_LEFTOVER_CMD = re.compile(r"\\([a-zA-Z]+)")


def _match_brace(s: str, i: int) -> tuple[Optional[str], int]:
    """s[i] must be '{'. Return (inner content, index just past the '}')."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1 : j], j + 1
    return None, len(s)


def _convert_fracs(s: str) -> str:
    """Rewrite every \\frac{a}{b} (and \\dfrac/\\tfrac) as ((a)/(b))."""
    while True:
        m = _FRAC_CMD.search(s)
        if not m:
            return s
        i = m.end()
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s) or s[i] != "{":
            # \frac12 shorthand: two single-token args
            if i + 1 < len(s):
                s = s[: m.start()] + f"(({s[i]})/({s[i + 1]}))" + s[i + 2 :]
                continue
            return s
        num, j = _match_brace(s, i)
        if num is None:
            return s
        while j < len(s) and s[j].isspace():
            j += 1
        if j >= len(s) or s[j] != "{":
            return s
        den, k = _match_brace(s, j)
        if den is None:
            return s
        s = s[: m.start()] + f"(({num})/({den}))" + s[k:]


def _convert_sqrts(s: str) -> str:
    """\\sqrt[n]{x} → ((x))**(1/(n));  \\sqrt{x} → sqrt(x)."""
    while True:
        m = _SQRT_IDX.search(s)
        if not m:
            break
        idx = m.group(1)
        i = m.end()
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s) or s[i] != "{":
            break
        inner, j = _match_brace(s, i)
        if inner is None:
            break
        s = s[: m.start()] + f"(({inner}))**(1/({idx}))" + s[j:]

    while True:
        pos = s.find("\\sqrt")
        if pos == -1:
            return s
        i = pos + len("\\sqrt")
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s) or s[i] != "{":
            # \sqrt2 shorthand
            if i < len(s):
                s = s[:pos] + f"sqrt({s[i]})" + s[i + 1 :]
                continue
            return s
        inner, j = _match_brace(s, i)
        if inner is None:
            return s
        s = s[:pos] + f"sqrt({inner})" + s[j:]


def _convert_caret_groups(s: str) -> str:
    """x^{ab} → x**(ab); leaves bare x^2 for the final ^→** pass."""
    while True:
        pos = s.find("^{")
        if pos == -1:
            return s
        inner, j = _match_brace(s, pos + 1)
        if inner is None:
            return s
        s = s[:pos] + f"**({inner})" + s[j:]


def normalize_latex(s: str) -> str:
    """Rewrite a LaTeX math string into parse_expr-compatible text."""
    s = s.strip().strip("$").strip()

    # Structural passes first (need intact braces)
    s = _convert_fracs(s)
    s = _convert_sqrts(s)

    # \text{...} / \mathrm{...} / \operatorname{...} — keep or drop content
    s = re.sub(r"\\text\s*\{[^{}]*\}", "", s)
    s = re.sub(r"\\(?:mathrm|operatorname)\s*\{([^{}]*)\}", r"\1", s)

    # Delimiter and spacing commands vanish
    s = re.sub(r"\\left|\\right|\\[Bb]igg?[lr]?", "", s)
    s = s.replace(r"\,", "").replace(r"\;", "").replace(r"\!", "").replace(r"\:", "")
    s = s.replace("\\ ", " ")

    for pat, repl in _FUNCTION_MAP:
        s = re.sub(pat + r"(?![a-zA-Z])", repl, s)
    for pat, repl in _CONSTANT_MAP:
        s = re.sub(pat + r"(?![a-zA-Z])", repl, s)

    # Subscripts: x_{12} → x_12 (parse_expr accepts underscore symbol names)
    s = re.sub(r"_\{([^{}]+)\}", r"_\1", s)

    s = _convert_caret_groups(s)

    # Any remaining \command becomes a bare symbol name (\alpha → alpha)
    s = _LEFTOVER_CMD.sub(r"\1", s)

    # Leftover grouping braces act as parentheses
    s = s.replace("{", "(").replace("}", ")")
    s = s.replace("^", "**")
    return s.strip()


# parse_latex (and plain parse_expr on the letter e) yield bare Symbols where
# math answers mean the constants — normalize so `e^{2x}` == `exp(2x)` and
# `\pi` == `pi`.
_CANONICAL_SUBS = {sp.Symbol("e"): sp.E, sp.Symbol("pi"): sp.pi}


def _canonicalize(expr: sp.Expr) -> sp.Expr:
    try:
        return expr.subs(_CANONICAL_SUBS)
    except Exception:
        return expr


def _try_parse_latex(s: str) -> Optional[sp.Expr]:
    try:
        from sympy.parsing.latex import parse_latex
    except ImportError:
        return None
    try:
        expr = parse_latex(s.strip().strip("$"))
    except Exception:
        return None
    if isinstance(expr, sp.Equality):
        expr = expr.rhs
    return _canonicalize(expr)


def _try_parse_expr(s: str) -> Optional[sp.Expr]:
    try:
        return _canonicalize(parse_expr(s, transformations=_TRANSFORMATIONS))
    except Exception:
        return None


def latex_to_expr(expr_str: str) -> Optional[sp.Expr]:
    """
    Parse a student/canonical answer string (LaTeX or plain math) into a
    SymPy expression. Returns None if nothing parses.
    """
    if expr_str is None:
        return None
    s = expr_str.strip().strip("$").strip()
    if not s:
        return None

    looks_latex = "\\" in s or "{" in s

    if looks_latex:
        expr = _try_parse_latex(s)
        if expr is not None:
            return expr
        expr = _try_parse_expr(normalize_latex(s))
        if expr is not None:
            return expr
        return None

    # Plain-math fast path (legacy behavior): ^ means power
    expr = _try_parse_expr(s.replace("^", "**"))
    if expr is not None:
        return expr
    # Rare: plain-looking strings that are still LaTeX-parseable ("2 \\cdot 3"
    # is caught above; things like "50%" are not — give normalize a chance)
    return _try_parse_expr(normalize_latex(s))
