"""
Phase 2 gating tests: verify all agent modules import correctly and expose
the expected public functions/classes with the right signatures.
"""

import pytest


# ---------------------------------------------------------------------------
# Import tests — if any agent module fails to import, the test fails immediately
# ---------------------------------------------------------------------------

def test_agents_package_imports():
    import agents


def test_orchestrator_imports():
    from agents.orchestrator import handle
    import inspect
    assert inspect.iscoroutinefunction(handle)


def test_generator_imports():
    from agents.generator import generate
    import inspect
    assert inspect.iscoroutinefunction(generate)


def test_debate_imports():
    from agents.debate import run
    import inspect
    assert inspect.iscoroutinefunction(run)


def test_verifier_imports():
    from agents.verifier import verify
    import inspect
    assert inspect.iscoroutinefunction(verify)


def test_answer_checker_imports():
    from agents.answer_checker import check
    import inspect
    assert inspect.iscoroutinefunction(check)


def test_hint_scaffolder_imports():
    from agents.hint_scaffolder import get_hint
    import inspect
    assert inspect.iscoroutinefunction(get_hint)


def test_solution_explainer_imports():
    from agents.solution_explainer import explain
    import inspect
    assert inspect.iscoroutinefunction(explain)


def test_lesson_writer_imports():
    from agents.lesson_writer import write_lesson
    import inspect
    assert inspect.iscoroutinefunction(write_lesson)


def test_adaptive_engine_imports():
    from agents.adaptive_engine import recommend
    import inspect
    assert inspect.iscoroutinefunction(recommend)


def test_analytics_imports():
    from agents.analytics import summarise
    import inspect
    assert inspect.iscoroutinefunction(summarise)


def test_schemas_import():
    from agents.schemas import (
        OrchestratorRequest,
        GeneratorInput,
        GeneratedProblem,
        DebateRequest,
        DebateResult,
        VerifierResult,
        CheckAnswerRequest,
        CheckAnswerResult,
        HintRequest,
        SolutionRequest,
        SolutionExplanation,
        AdaptiveInput,
        AdaptiveOutput,
        AnalyticsInput,
        AnalyticsOutput,
    )


# ---------------------------------------------------------------------------
# Debate cost guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_debate_cost_guard_raises_on_rounds_gt_3():
    from agents.debate import run
    from agents.schemas import DebateRequest

    request = DebateRequest(
        task="problem_generation",
        context={"topic": "algebra"},
        rounds=4,
    )
    with pytest.raises(ValueError, match="rounds must be <= 3"):
        await run(request)


@pytest.mark.asyncio
async def test_debate_cost_guard_allows_rounds_3():
    """rounds=3 is the maximum allowed — must NOT raise ValueError from the cost guard."""
    from agents.debate import run
    from agents.schemas import DebateRequest

    request = DebateRequest(
        task="problem_generation",
        context={"topic": "algebra"},
        rounds=3,
    )
    # rounds=3 must NOT raise ValueError("rounds must be <= 3")
    # It may raise other exceptions (ValidationError, RuntimeError) due to invalid/missing context
    try:
        await run(request)
    except ValueError as e:
        if "rounds must be <= 3" in str(e):
            pytest.fail(f"rounds=3 should be allowed but got ValueError: {e}")
    except Exception:
        pass  # ValidationError, RuntimeError etc. are all acceptable here


# ---------------------------------------------------------------------------
# Answer checker stub tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_answer_checker_exact_match():
    from agents.answer_checker import check

    result = await check("x = 5", "x = 5")
    assert result.correct is True
    assert result.equivalent_form is False


@pytest.mark.asyncio
async def test_answer_checker_numeric_equivalence():
    from agents.answer_checker import check

    result = await check("2.0", "2")
    assert result.correct is True
    assert result.equivalent_form is True


@pytest.mark.asyncio
async def test_answer_checker_wrong_answer():
    from agents.answer_checker import check

    result = await check("x = 3", "x = 5")
    assert result.correct is False


# ---------------------------------------------------------------------------
# Hint scaffolder tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hint_scaffolder_returns_correct_hint():
    from agents.hint_scaffolder import get_hint
    from agents.schemas import HintRequest

    ladder = [
        "Think about what operation undoes addition.",
        "Subtraction is the inverse of addition.",
        "Subtract 5 from both sides.",
        "x + 5 - 5 = 10 - 5, so x = 5.",
    ]
    req = HintRequest(problem_id="p1", hint_ladder=ladder, hint_level=2)
    hint = await get_hint(req, user_tier="student")
    assert hint == ladder[1]


@pytest.mark.asyncio
async def test_hint_scaffolder_free_user_blocked_on_hint_4():
    from agents.hint_scaffolder import get_hint
    from agents.schemas import HintRequest

    ladder = ["h1", "h2", "h3", "h4"]
    req = HintRequest(problem_id="p1", hint_ladder=ladder, hint_level=4)
    with pytest.raises(PermissionError):
        await get_hint(req, user_tier="free")


@pytest.mark.asyncio
async def test_hint_scaffolder_paid_user_gets_hint_4():
    from agents.hint_scaffolder import get_hint
    from agents.schemas import HintRequest

    ladder = ["h1", "h2", "h3", "h4"]
    req = HintRequest(problem_id="p1", hint_ladder=ladder, hint_level=4)
    hint = await get_hint(req, user_tier="honors")
    assert hint == "h4"


# ---------------------------------------------------------------------------
# Anthropic client factory test (no API call — just validates instantiation path)
# ---------------------------------------------------------------------------

def test_llm_factory_returns_dummy_by_default():
    """With LLM_PROVIDER=dummy, factory returns DummyLLMClient without API call."""
    import os
    os.environ["LLM_PROVIDER"] = "dummy"
    os.environ["USE_LLM"] = "false"

    import llm_factory
    llm_factory.reset_llm_clients()

    client = llm_factory.get_llm_client()
    from llm_interfaces import DummyLLMClient
    assert isinstance(client, DummyLLMClient)


def test_llm_factory_anthropic_falls_back_on_missing_key():
    """With LLM_PROVIDER=anthropic but no key, factory falls back to DummyLLMClient."""
    import os
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["USE_LLM"] = "true"
    original_key = os.environ.pop("ANTHROPIC_API_KEY", None)

    try:
        import importlib
        import config as cfg
        importlib.reload(cfg)

        import llm_factory
        llm_factory.reset_llm_clients()
        importlib.reload(llm_factory)

        client = llm_factory.get_llm_client()
        from llm_interfaces import DummyLLMClient
        assert isinstance(client, DummyLLMClient)
    finally:
        if original_key:
            os.environ["ANTHROPIC_API_KEY"] = original_key
        os.environ["LLM_PROVIDER"] = "dummy"
        os.environ["USE_LLM"] = "false"
