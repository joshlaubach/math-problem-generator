"""
Analytics agent — generates natural language insights for teacher dashboards.

Receives structured analytics data (computed in Python from DB queries).
Returns 2-3 natural language sentences surfacing actionable observations:
  - Which topics the class is struggling with
  - Which students haven't been active
  - Where to focus re-teaching before moving on

Claude is used for the insight generation only; the underlying data
computation happens in concept_analytics.py (pure Python).
"""

from __future__ import annotations

from agents.schemas import AnalyticsInput, AnalyticsOutput


async def summarise(classroom_id: str, analytics_data: AnalyticsInput | None = None) -> AnalyticsOutput:
    """
    Generate a natural language insight summary for a teacher's classroom dashboard.

    Phase 9: implement by calling Claude with the structured analytics data.
    Ports concept_analytics.py data aggregation logic.

    Args:
        classroom_id: The Classroom ID to generate insights for.
        analytics_data: Pre-computed analytics (if already loaded by caller).

    Returns:
        AnalyticsOutput with a 2-3 sentence insight string.
    """
    raise NotImplementedError(
        "analytics.summarise — implement in Phase 9 using Claude to narrate "
        "structured data from concept_analytics.py"
    )
