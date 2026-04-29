"""
Hint Scaffolder — serves pre-generated hints from the Problem record.

Never generates hints fresh. Hint cap enforcement:
  - Free users: hints 1-3 only (hint_level 1, 2, 3)
  - Paid users (Student, Honors, Classroom): all 4 hints

Tier gating is enforced here, not in the router.
"""

from __future__ import annotations

from agents.schemas import HintRequest


async def get_hint(request: HintRequest, user_tier: str = "free") -> str:
    """
    Return the hint at the requested level from the pre-generated ladder.

    Args:
        request: HintRequest with problem_id, hint_ladder, hint_level.
        user_tier: 'free' | 'student' | 'honors' | 'classroom-student'

    Returns:
        The hint string at hint_level (1-indexed).

    Raises:
        PermissionError: if a free user requests hint level 4.
        IndexError: if hint_level exceeds the ladder length.
    """
    is_paid = user_tier in ("student", "honors", "classroom-student")

    if request.hint_level == 4 and not is_paid:
        raise PermissionError(
            "Hint 4 is only available for paid users (Student, Honors, or Classroom tier)."
        )

    if not request.hint_ladder:
        return "No hints are available for this problem."

    if request.hint_level < 1 or request.hint_level > len(request.hint_ladder):
        raise IndexError(
            f"hint_level {request.hint_level} is out of range for a {len(request.hint_ladder)}-hint ladder."
        )

    return request.hint_ladder[request.hint_level - 1]
