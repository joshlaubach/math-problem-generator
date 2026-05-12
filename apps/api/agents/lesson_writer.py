"""
Lesson Writer agent — generates unit-level lesson notes using Claude.

Called by GET /units/{unit_id}/notes (on-demand with disk caching)
and by apps/api/scripts/generate_all_lessons.py (bulk pre-generation).

Output format: Markdown with $...$ inline math and $$...$$ display math,
structured with Overview, Key Concepts, Worked Examples, Key Formulas,
Common Mistakes, and Connections sections.
"""

from __future__ import annotations

_LESSON_SYSTEM = (
    "You are an expert mathematics educator writing clear, rigorous lesson notes "
    "for a university-level math learning platform. Use LaTeX math notation: "
    "$...$ for inline math and $$...$$ for display math equations. "
    "Be concise but thorough. Prioritize conceptual clarity and worked examples."
)

_LESSON_PROMPT_TEMPLATE = """Write lesson notes for the following unit:

Course: {course_name}
Unit: {unit_name}
Topics covered: {topic_list}

Structure your notes EXACTLY as follows (use Markdown headings):

## Overview
2-3 sentences explaining what this unit covers, why it matters, and where it fits in the curriculum.

## Key Concepts
A bullet list of 4-6 core ideas. Each bullet: concept name in bold, then a 1-sentence definition or explanation.

## Worked Examples
2-3 fully worked examples showing different aspects of the unit. For each:
- State the problem clearly
- Show every step with LaTeX math using $$...$$ for displayed equations
- Explain the key reasoning at each step

## Key Formulas
A reference block of the most important formulas. Use $$...$$ display math for each formula with a brief label.

## Common Mistakes
2-3 specific errors students frequently make in this unit. Explain what goes wrong and how to avoid it.

## Connections
Brief notes on: (1) what prerequisite knowledge this builds on, and (2) what later topics this unit unlocks.

Use $...$ for all inline math (e.g., "the variable $x$") and $$...$$ for all displayed equations.
Be mathematically precise. Write for a student who has completed the prerequisites.
"""


async def write_lesson(
    unit_id: str,
    unit_name: str,
    course_name: str,
    topic_names: list[str],
) -> str:
    """
    Generate markdown lesson notes for a unit using Claude.

    Args:
        unit_id: Unit identifier (e.g. 'a1_u04')
        unit_name: Human-readable unit name
        course_name: Course this unit belongs to
        topic_names: List of topic names in the unit

    Returns:
        Markdown string with lesson notes.
    """
    from llm_anthropic_client import _call_with_backoff

    topic_list = "\n".join(f"  - {name}" for name in topic_names[:20])  # cap at 20

    prompt = _LESSON_PROMPT_TEMPLATE.format(
        course_name=course_name,
        unit_name=unit_name,
        topic_list=topic_list,
    )

    content = await _call_with_backoff(
        messages=[{"role": "user", "content": prompt}],
        system=_LESSON_SYSTEM,
        max_tokens=2000,
    )
    return content
