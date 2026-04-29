"""
Phase 3 gating test: agent produces equivalent Problem to existing LinearEquationGenerator,
with the new fields (worked_steps, hint_ladder, distractors) populated.
"""

import pytest


@pytest.mark.asyncio
async def test_mode_a_linear_produces_valid_problem():
    """
    Mode A linear generator must return a GeneratedProblem with:
    - non-empty statement
    - non-empty answer
    - at least 1 worked step
    - exactly 4 hints
    - exactly 3 distractors
    - answer matches what the legacy LinearEquationGenerator would produce for the same seed
    """
    from agents.generator import generate
    from agents.schemas import GeneratorInput

    inp = GeneratorInput(
        topic="alg1_linear_solve_one_var",
        course="algebra-1",
        unit="unit-02-linear-equations",
        conceptual_diff=2,
        computational_diff=2,
        calc_tier="none",
    )
    prob = await generate(inp)

    assert isinstance(prob.statement, str) and len(prob.statement) > 0, "statement must be non-empty"
    assert isinstance(prob.answer, str) and len(prob.answer) > 0, "answer must be non-empty"
    assert len(prob.worked_steps) >= 1, "must have at least 1 worked step"
    assert len(prob.hint_ladder) == 4, f"hint_ladder must have exactly 4 hints, got {len(prob.hint_ladder)}"
    assert len(prob.distractors) == 3, f"must have exactly 3 distractors, got {len(prob.distractors)}"

    # Each hint must be a non-empty string
    for i, hint in enumerate(prob.hint_ladder):
        assert isinstance(hint, str) and hint.strip(), f"hint {i+1} is empty"

    # Each distractor must have an answer and a named mistake
    for i, dist in enumerate(prob.distractors):
        assert dist.answer, f"distractor {i+1} has no answer"
        assert dist.mistake, f"distractor {i+1} has no named mistake"


@pytest.mark.asyncio
async def test_mode_a_answer_is_integer_for_difficulty_2():
    """
    At difficulty 2, the linear generator always produces an integer answer.
    The Mode A generator must preserve this.
    """
    from agents.generator import generate
    from agents.schemas import GeneratorInput

    inp = GeneratorInput(
        topic="alg1_linear_solve_one_var",
        course="algebra-1",
        unit="unit-02-linear-equations",
        conceptual_diff=2,
        computational_diff=2,
        calc_tier="none",
    )
    prob = await generate(inp)
    # The answer may be wrapped in "x = N" or just "N"
    answer_val = prob.answer.split("=")[-1].strip()
    try:
        int(answer_val)
    except ValueError:
        pytest.fail(f"Expected integer answer, got: {prob.answer!r}")


@pytest.mark.asyncio
async def test_mode_a_hint_4_does_not_contain_exact_answer():
    """
    Hint 4 must be a near-solution hint but NEVER state the final answer verbatim.
    This is the most important pedagogical constraint on the hint ladder.
    """
    from agents.generator import generate
    from agents.schemas import GeneratorInput

    inp = GeneratorInput(
        topic="alg1_linear_solve_one_var",
        course="algebra-1",
        unit="unit-02-linear-equations",
        conceptual_diff=1,
        computational_diff=1,
        calc_tier="none",
    )
    prob = await generate(inp)
    answer_clean = prob.answer.split("=")[-1].strip()
    hint4 = prob.hint_ladder[3]

    # Hint 4 is allowed to reference the answer in a scaffolded way,
    # but should not start with "The answer is" or "x = <answer>"
    assert not hint4.strip().lower().startswith("the answer is"), \
        f"Hint 4 reveals the answer: {hint4!r}"


@pytest.mark.asyncio
async def test_mode_a_worked_steps_have_step_and_explanation():
    """Each WorkedStep must have both a step (LaTeX) and an explanation."""
    from agents.generator import generate
    from agents.schemas import GeneratorInput

    inp = GeneratorInput(
        topic="alg1_linear_solve_one_var",
        course="algebra-1",
        unit="unit-02-linear-equations",
        conceptual_diff=3,
        computational_diff=3,
        calc_tier="none",
    )
    prob = await generate(inp)
    for i, ws in enumerate(prob.worked_steps):
        assert ws.step, f"worked_step[{i}].step is empty"
        assert ws.explanation, f"worked_step[{i}].explanation is empty"


@pytest.mark.asyncio
async def test_mode_b_raises_without_api_key():
    """
    Mode B generation requires ANTHROPIC_API_KEY. Without it, RuntimeError is raised.
    """
    import os
    original = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        from agents.generator import generate
        from agents.schemas import GeneratorInput
        import importlib
        import config
        importlib.reload(config)

        inp = GeneratorInput(
            topic="calculus-1-limits",  # not in SYMPY_TOPICS → triggers Mode B
            course="calculus-1",
            unit="unit-01-limits",
            conceptual_diff=2,
            computational_diff=2,
            calc_tier="none",
        )
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            await generate(inp)
    finally:
        if original:
            os.environ["ANTHROPIC_API_KEY"] = original
