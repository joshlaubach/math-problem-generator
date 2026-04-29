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
