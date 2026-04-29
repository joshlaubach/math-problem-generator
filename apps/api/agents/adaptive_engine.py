"""
Adaptive Engine — determines next problem difficulty and spaced repetition schedule.

Core logic is deterministic Python (no LLM).
Claude is used ONLY for the recommendation rationale string (1-2 sentences).

Rules:
  - 3 correct in a row on a topic → masteryScore += 0.1, currentConceptualDiff = min(5, current+1)
  - 2 wrong in a row → currentComputationalDiff = max(1, current-1)
  - Mastery score caps at 1.0
  - Spaced repetition: nextReviewAt = lastReviewedAt + timedelta(days=masteryScore * 7)
  - If nextReviewAt <= now and masteryScore < 0.9 → add topic to topicsForReview

Ports existing backend/adaptive.py heuristics (80%/60% thresholds preserved for backward compat).
"""

from __future__ import annotations

from agents.schemas import AdaptiveOutput


async def recommend(user_id: str, recent_attempts: list[dict] | None = None, progress_records: list[dict] | None = None) -> AdaptiveOutput:
    """
    Compute the next recommended topic and difficulty adjustment for a user.

    Phase 8: implement full spaced repetition + consecutive-streak rules.
    Phase 3 partial: wire in the Claude rationale call.

    Args:
        user_id: Clerk user ID.
        recent_attempts: Recent Attempt records (if already loaded by caller).
        progress_records: Progress records for the user (if already loaded).

    Returns:
        AdaptiveOutput with recommended topic, adjustment, review list, and rationale.
    """
    raise NotImplementedError(
        "adaptive_engine.recommend — implement in Phase 8; "
        "port mastery/streak logic from backend/adaptive.py"
    )
