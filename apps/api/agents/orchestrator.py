"""
Orchestrator agent — routes student actions to the correct specialist agent.
Never calls Claude directly. All routing logic is deterministic Python.
"""

from __future__ import annotations

from agents.schemas import OrchestratorRequest


async def handle(request: OrchestratorRequest) -> dict:
    """
    Route an OrchestratorRequest to the appropriate agent.

    Returns a dict whose shape depends on the action:
      get_problem     → GeneratedProblem | Problem (from bank)
      check_answer    → CheckAnswerResult
      get_hint        → {hint: str, level: int}
      get_solution    → SolutionExplanation
      get_recommendation → AdaptiveOutput
      get_analytics   → AnalyticsOutput
    """
    if request.action == "get_problem":
        return await _get_problem(request)
    if request.action == "check_answer":
        return await _check_answer(request)
    if request.action == "get_hint":
        return await _get_hint(request)
    if request.action == "get_solution":
        return await _get_solution(request)
    if request.action == "get_recommendation":
        return await _get_recommendation(request)
    if request.action == "get_analytics":
        return await _get_analytics(request)
    raise ValueError(f"Unknown action: {request.action}")


async def _get_problem(req: OrchestratorRequest) -> dict:
    # Phase 7: try free bank first, fall back to live generation for paid users
    raise NotImplementedError("get_problem — implement in Phase 7")


async def _check_answer(req: OrchestratorRequest) -> dict:
    from agents.answer_checker import check
    return (await check(req.student_answer or "", req.problem_id or "")).model_dump()


async def _get_hint(req: OrchestratorRequest) -> dict:
    # Phase 7: load problem, call hint_scaffolder
    raise NotImplementedError("get_hint — implement in Phase 7")


async def _get_solution(req: OrchestratorRequest) -> dict:
    # Phase 7: load problem+attempts, call solution_explainer
    raise NotImplementedError("get_solution — implement in Phase 7")


async def _get_recommendation(req: OrchestratorRequest) -> dict:
    from agents.adaptive_engine import recommend
    return (await recommend(req.user_id)).model_dump()


async def _get_analytics(req: OrchestratorRequest) -> dict:
    from agents.analytics import summarise
    return (await summarise(req.classroom_id or "")).model_dump()
