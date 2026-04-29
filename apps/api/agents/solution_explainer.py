"""
Solution Explainer agent — full pedagogical explanation with a debate pass.

Called only when: student explicitly requests full solution OR exhausts all available hints.
Uses Claude with debate rounds=1 (one critique round to keep latency acceptable).

The explanation:
  - Walks through each step with WHY, not just what
  - Identifies the specific misconception from the student's wrong answers
  - Connects the concept to relevant prerequisites
  - Is distinct from raw worked_steps — this is prose instruction

This runs the debate at rounds=1:
  Two instances generate in parallel; the judge picks the clearer explanation.
  Added latency (~1 extra Claude call) is acceptable since the student is already waiting.
"""

from __future__ import annotations

from agents.schemas import SolutionRequest, SolutionExplanation


async def explain(request: SolutionRequest) -> SolutionExplanation:
    """
    Generate a full pedagogical solution explanation.

    Phase 3: implement via debate.run(task='solution_explanation', rounds=1).

    Args:
        request: SolutionRequest with problem, worked steps, and student's wrong attempts.

    Returns:
        SolutionExplanation with a prose explanation paragraph.
    """
    raise NotImplementedError(
        "solution_explainer.explain — implement in Phase 3 using "
        "debate.run(task='solution_explanation', rounds=1)"
    )
