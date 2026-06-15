"""
Server-side answer grading via SymPy equivalence.

The practice loop used to grade answers in the browser with a crude string
compare (`normalizeAnswer`), which both leaked the answer and was wrong in
both directions: `\\sqrt{2}` and `2` collapsed to the same string (false
positive) while `1/2` and `\\frac{1}{2}` did not (false negative). This module
replaces that with a CAS-backed equivalence check so the product's
"CAS-verified, won't lie to you" promise is true at the moment of grading.

`answers_equivalent(student, correct, answer_type)` never raises — on any
parse failure it falls back to a conservative normalized-text compare, so a
word answer ("increasing") or an unparseable expression degrades to the old
behavior rather than erroring.

No new dependency: SymPy is already required, and we avoid `parse_latex`
(which needs antlr4) by normalizing a useful LaTeX subset to SymPy syntax by
hand.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

import sympy
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)
_NUMERIC_TOL = 1e-6

# LaTeX command names that map to a SymPy function/constant by dropping the
# backslash. \infty is special-cased to oo below.
_PASSTHROUGH_NAMES = [
    "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh",
    "sin", "cos", "tan", "csc", "sec", "cot",
    "log", "ln", "exp", "pi", "theta", "alpha", "beta", "gamma",
    "lambda", "mu", "phi", "omega",
]


def _text_norm(s: str) -> str:
    """Conservative normalization for non-math / fallback comparison.

    Unlike the old client normalizer this does NOT strip LaTeX command bodies,
    so `\\sqrt{2}` and `2` stay distinct. It only removes whitespace, dollar
    signs, and \\left/\\right spacing wrappers, and lowercases.
    """
    s = s.strip().lower()
    s = s.replace("$", "")
    s = re.sub(r"\\approx\s*", "", s)
    s = re.sub(r"≈\s*", "", s)
    s = s.replace("\\left", "").replace("\\right", "")
    s = re.sub(r"\\(,|;|:|!|quad|qquad)", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def _latex_to_sympy_str(raw: str) -> str:
    """Convert a useful subset of LaTeX / MathLive output to a SymPy-parseable
    string. Best-effort and intentionally forgiving."""
    s = raw.strip()
    s = s.replace("$", "")
    # Strip approximation markers before any further processing
    s = re.sub(r"\\approx\s*", "", s)
    s = re.sub(r"≈\s*", "", s)
    s = s.replace("\\left", "").replace("\\right", "")
    s = re.sub(r"\\(,|;|:|!|quad|qquad)", "", s)
    s = s.replace("\\\\", "")
    # \text{...} and \mathrm{...} → bare contents
    s = re.sub(r"\\(?:text|mathrm|mathbf|operatorname)\s*\{([^{}]*)\}", r"\1", s)
    # multiplication / division words
    s = s.replace("\\cdot", "*").replace("\\times", "*").replace("\\ast", "*")
    s = s.replace("\\div", "/")
    # degree markers — drop
    s = s.replace("^\\circ", "").replace("\\circ", "").replace("\\degree", "")
    # \frac{a}{b} → ((a)/(b)); loop to resolve nesting (innermost first)
    frac_re = re.compile(r"\\(?:d|t)?frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")
    while frac_re.search(s):
        s = frac_re.sub(r"((\1)/(\2))", s)
    # \sqrt[n]{a} → ((a)**(1/(n)))
    s = re.sub(r"\\sqrt\s*\[([^\]]+)\]\s*\{([^{}]+)\}", r"((\2)**(1/(\1)))", s)
    # \sqrt{a} → sqrt(a); loop for nesting
    sqrt_re = re.compile(r"\\sqrt\s*\{([^{}]+)\}")
    while sqrt_re.search(s):
        s = sqrt_re.sub(r"sqrt(\1)", s)
    # \infty → oo
    s = s.replace("\\infty", "oo")
    # known functions / greek → drop the backslash
    for name in _PASSTHROUGH_NAMES:
        s = s.replace("\\" + name, name)
    # exponent: ^ → **  (before brace→paren so x^{2} becomes x**{2} → x**(2))
    s = s.replace("^", "**")
    # remaining grouping braces → parens
    s = s.replace("{", "(").replace("}", ")")
    # drop any stray backslashes left over
    s = s.replace("\\", "")
    s = re.sub(r"\s+", "", s)
    return s


def _parse(raw: str) -> Optional[Tuple[str, sympy.Expr]]:
    """Parse a normalized answer into ('expr', expr) or ('eq', lhs-rhs).

    Returns None when the string is empty or cannot be parsed.
    """
    txt = _latex_to_sympy_str(raw)
    if not txt:
        return None
    if txt.count("=") == 1:
        lhs_s, rhs_s = txt.split("=")
        if not lhs_s or not rhs_s:
            return None
        lhs = parse_expr(lhs_s, transformations=_TRANSFORMS, evaluate=True)
        rhs = parse_expr(rhs_s, transformations=_TRANSFORMS, evaluate=True)
        return ("eq", sympy.sympify(lhs - rhs))
    if "=" in txt:
        return None  # chained or malformed equation
    expr = parse_expr(txt, transformations=_TRANSFORMS, evaluate=True)
    return ("expr", sympy.sympify(expr))


def _both_numeric(a: sympy.Expr, b: sympy.Expr) -> Optional[bool]:
    """If both expressions are pure numbers, compare with tolerance; else None."""
    if a.free_symbols or b.free_symbols:
        return None
    try:
        diff = complex(complex(a.evalf()) - complex(b.evalf()))
        scale = max(1.0, abs(complex(a.evalf())), abs(complex(b.evalf())))
        return abs(diff) <= _NUMERIC_TOL * scale
    except (TypeError, ValueError):
        return None


_THEOREM_STOPWORDS = frozenset({
    "the", "of", "a", "an", "by", "to", "is", "are", "in", "that", "for", "with", "and",
})


def _theorem_norm(s: str) -> frozenset[str]:
    """Normalize a theorem/property name to a frozenset of key content words."""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return frozenset(w for w in s.split() if w not in _THEOREM_STOPWORDS and len(w) > 1)


def _theorem_match(student: str, correct: str) -> bool:
    """Fuzzy keyword match for proof-reason answers.

    Accepts if ≥80% of the correct property's key words appear in the student
    answer. This lets "subtraction property" match "Subtraction Property of
    Equality" without requiring every word.
    """
    ns = _theorem_norm(student)
    nc = _theorem_norm(correct)
    if not nc:
        return False
    overlap = len(nc & ns) / len(nc)
    return overlap >= 0.80


def answers_equivalent(
    student: str,
    correct: str,
    answer_type: Optional[str] = None,
) -> bool:
    """Return True iff the student's answer is mathematically equivalent to the
    canonical answer. Never raises."""
    if student is None or not str(student).strip():
        return False
    if correct is None or not str(correct).strip():
        return False

    student = str(student)
    correct = str(correct)

    # Theorem / property name answers (proof steps): fuzzy keyword match.
    if answer_type in ("text", "proof_reason"):
        return _theorem_match(student, correct)

    # Fast path / fallback for word answers and exact matches.
    if _text_norm(student) == _text_norm(correct):
        return True

    try:
        a = _parse(student)
        b = _parse(correct)
    except Exception:
        return False
    if a is None or b is None:
        return False

    ka, ea = a
    kb, eb = b

    try:
        # Pure numbers → tolerant compare (handles 0.5 vs 1/2 vs decimals).
        if ka == "expr" and kb == "expr":
            num = _both_numeric(ea, eb)
            if num is not None:
                return num

        # Equation vs bare value: does the equation's solution match the value?
        if ka != kb:
            eq_expr = ea if ka == "eq" else eb
            val_expr = eb if ka == "eq" else ea
            syms = eq_expr.free_symbols
            if len(syms) == 1 and not val_expr.free_symbols:
                try:
                    sols = sympy.solve(eq_expr, list(syms)[0])
                except Exception:
                    sols = []
                for sol in sols:
                    try:
                        if abs(complex((sol - val_expr).evalf())) <= _NUMERIC_TOL:
                            return True
                    except (TypeError, ValueError):
                        if sympy.simplify(sol - val_expr) == 0:
                            return True
                return False
            # otherwise fall through to structural compare below

        # Structural equivalence.
        diff = sympy.simplify(ea - eb)
        if diff == 0:
            return True

        # Equations are equivalent up to a non-zero scalar multiple
        # (e.g. 2x = 10 vs x = 5). This is NOT valid for bare expressions.
        if ka == "eq" and kb == "eq" and eb != 0:
            ratio = sympy.simplify(ea / eb)
            if ratio.is_number and ratio != 0:
                return True

        return False
    except Exception:
        return False
