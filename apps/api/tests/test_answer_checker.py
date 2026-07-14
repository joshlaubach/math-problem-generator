"""
Tests for agents/answer_checker.py — SymPy-based equivalence checking.

Spec requirements:
  - (x+1)**2  ==  x**2 + 2*x + 1
  - ln(exp(2)) == 2
  - sin(x)**2 + cos(x)**2 == 1
  - 2/4 == 1/2
  - 0.333... ≈ 1/3  (floating point within tolerance)
"""

import pytest


@pytest.mark.asyncio
async def test_exact_match():
    from agents.answer_checker import check
    r = await check("x = 5", "x = 5")
    assert r.correct is True
    assert r.equivalent_form is False


@pytest.mark.asyncio
async def test_polynomial_expansion():
    """(x+1)**2 is equivalent to x**2 + 2*x + 1"""
    from agents.answer_checker import check
    r = await check("(x+1)**2", "x**2 + 2*x + 1")
    assert r.correct is True
    assert r.equivalent_form is True


@pytest.mark.asyncio
async def test_ln_exp_simplification():
    """ln(exp(2)) == 2"""
    from agents.answer_checker import check
    r = await check("log(exp(2))", "2")
    assert r.correct is True


@pytest.mark.asyncio
async def test_pythagorean_identity():
    """sin(x)**2 + cos(x)**2 == 1"""
    from agents.answer_checker import check
    r = await check("sin(x)**2 + cos(x)**2", "1")
    assert r.correct is True


@pytest.mark.asyncio
async def test_fraction_simplification():
    """2/4 == 1/2"""
    from agents.answer_checker import check
    r = await check("2/4", "1/2")
    assert r.correct is True


@pytest.mark.asyncio
async def test_float_equivalence():
    """0.333... ≈ 1/3 within tolerance"""
    from agents.answer_checker import check
    r = await check("0.3333333333", "1/3")
    assert r.correct is True


@pytest.mark.asyncio
async def test_wrong_answer():
    from agents.answer_checker import check
    r = await check("x = 3", "x = 5")
    assert r.correct is False


@pytest.mark.asyncio
async def test_variable_assignment_strip():
    """x = 5 and 5 should match"""
    from agents.answer_checker import check
    r = await check("x = 5", "5")
    assert r.correct is True


@pytest.mark.asyncio
async def test_numeric_int():
    from agents.answer_checker import check
    r = await check("2.0", "2")
    assert r.correct is True
    assert r.equivalent_form is True


@pytest.mark.asyncio
async def test_negative_equivalence():
    """-(x-1) == 1-x"""
    from agents.answer_checker import check
    r = await check("-(x-1)", "1-x")
    assert r.correct is True


@pytest.mark.asyncio
async def test_incorrect_polynomial():
    from agents.answer_checker import check
    r = await check("x**2 + 3*x + 1", "x**2 + 2*x + 1")
    assert r.correct is False


# ─────────────────────────────────────────────────────────────────────────────
# MathLive LaTeX regression suite (audit Blocker C1)
#
# MathInput emits raw LaTeX (\frac{1}{2}, \sqrt{2}, \left(x+1\right)^2 …).
# Before latex_parse.py these were unparseable and correct answers were
# graded wrong. Every case here is (student_latex, canonical, expected).
# ─────────────────────────────────────────────────────────────────────────────

_LATEX_CORRECT_CASES = [
    # Fractions — the reproduced audit case first
    (r"\frac{1}{2}", "1/2"),
    (r"\frac{1}{2}", "0.5"),
    (r"x = \frac{5}{2}", "x = 5/2"),
    (r"\frac{3}{4}", "3/4"),
    (r"-\frac{2}{3}", "-2/3"),
    (r"\frac{-2}{3}", "-2/3"),
    (r"\dfrac{1}{2}", "1/2"),
    (r"\tfrac{1}{2}", "1/2"),
    (r"\frac{x+1}{2}", "(x+1)/2"),
    (r"\frac{1}{x+1}", "1/(x+1)"),
    (r"\frac{\frac{1}{2}}{3}", "1/6"),          # nested
    (r"\frac{a}{b}", "a/b"),
    (r"2 + \frac{1}{2}", "5/2"),
    (r"\frac{7}{7}", "1"),
    # Roots
    (r"\sqrt{2}", "sqrt(2)"),
    (r"\sqrt{4}", "2"),
    (r"\sqrt{x^2}", "sqrt(x**2)"),
    (r"3\sqrt{2}", "3*sqrt(2)"),
    (r"\sqrt[3]{8}", "2"),
    (r"\sqrt[4]{16}", "2"),
    # Delimiters and powers
    (r"\left(x+1\right)^2", "(x+1)**2"),
    (r"\left(x+1\right)^2", "x**2 + 2*x + 1"),
    (r"(x+1)^{2}", "(x+1)**2"),
    (r"x^{10}", "x**10"),
    (r"e^{2x}", "exp(2*x)"),
    (r"2^{-1}", "1/2"),
    # Multiplication forms
    (r"2\cdot3", "6"),
    (r"2 \cdot 3", "6"),
    (r"2\times3", "6"),
    (r"6\div2", "3"),
    (r"2\cdot\frac{1}{4}", "1/2"),
    # Constants and functions
    (r"\pi", "pi"),
    (r"\frac{\pi}{2}", "pi/2"),
    (r"2\pi", "2*pi"),
    (r"\sin(x)^2 + \cos(x)^2", "1"),
    (r"\ln(e^2)", "2"),
    (r"\tan(0)", "0"),
    # Assignment forms
    (r"x=\frac{1}{2}", "x = 1/2"),
    (r"y = \sqrt{9}", "y = 3"),
    (r"x = -\frac{3}{2}", "-3/2"),
    # Decimals / negatives / mixed
    (r"-\frac{1}{2}", "-0.5"),
    (r"\frac{1}{3}", "0.333333333"),
    (r"0.25", r"\frac{1}{4}"),                   # canonical side in LaTeX
    (r"\frac{2}{4}", r"\frac{1}{2}"),            # both sides LaTeX
    # Spacing commands
    (r"\frac{1}{2}\,x", "x/2"),
    (r"\left( 2x + 4 \right)", "2*x + 4"),
]

_LATEX_WRONG_CASES = [
    (r"\frac{1}{3}", "1/2"),
    (r"\sqrt{2}", "2"),
    (r"\left(x+1\right)^2", "x**2 + 1"),
    (r"x = \frac{5}{2}", "x = 2"),
    (r"2\cdot3", "5"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("student,canonical", _LATEX_CORRECT_CASES)
async def test_mathlive_latex_correct(student, canonical):
    from agents.answer_checker import check
    r = await check(student, canonical)
    assert r.correct is True, f"{student!r} should equal {canonical!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize("student,canonical", _LATEX_WRONG_CASES)
async def test_mathlive_latex_wrong(student, canonical):
    from agents.answer_checker import check
    r = await check(student, canonical)
    assert r.correct is False, f"{student!r} should NOT equal {canonical!r}"


@pytest.mark.asyncio
async def test_unparseable_still_graceful():
    """Garbage input must return incorrect with a parse reason, never raise."""
    from agents.answer_checker import check
    r = await check(r"\begin{matrix}???", "1/2")
    assert r.correct is False
    assert r.partial_credit_reason is not None
