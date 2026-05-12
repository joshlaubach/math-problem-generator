"""
Unit Intro Writer — generates the unit introduction (hook + concept + topic roadmap).

Called by GET /units/{unit_id}/intro (on-demand with disk caching).

Topic ordering comes from the taxonomy — Claude only writes the one-sentence
descriptions; it never reorders topics.
"""
from __future__ import annotations

import json

_SYSTEM = """\
You are an expert mathematics educator writing unit introductions for a tutoring platform.
Be concise, warm, and motivating. Use LaTeX inline math ($...$) where appropriate.
"""

_PROMPT = """\
Write a unit introduction for:

Course: {course_name}
Unit: {unit_name}
Topics in order:
{topic_list}

Return ONLY valid JSON, no markdown fences:

{{
  "hook": "2-3 sentences. Start with something the student already knows. Reveal the gap that this unit fills. End with a motivating question or observation.",

  "concept": "1-2 sentences. What is the unifying idea that connects all these topics? Plain English first, then one formal phrase if helpful.",

  "topic_roadmap": [
    {{
      "topic_id": "exact topic_id as provided",
      "topic_name": "exact topic_name as provided",
      "description": "One sentence: what skill does the student gain from this topic? Be specific, not generic."
    }}
  ]
}}

Requirements:
- topic_roadmap MUST preserve the EXACT ORDER of the topics as listed above
- topic_roadmap MUST include ALL topics — do not skip any
- Each description is ONE sentence, active voice, student-facing ("You will learn...", "Master...", "Apply...")
- hook should make the student feel the unit is relevant and achievable
"""


async def write_unit_intro(
    unit_id: str,
    unit_name: str,
    course_name: str,
    topics: list[dict],  # [{ topic_id, topic_name }] in taxonomy order
) -> dict:
    """
    Generate a structured unit introduction using Claude.

    Args:
        unit_id: Unit identifier
        unit_name: Human-readable unit name
        course_name: Course name
        topics: List of {topic_id, topic_name} dicts in taxonomy order

    Returns parsed intro dict. Raises on generation failure.
    """
    from llm_anthropic_client import _call_with_backoff

    topic_list = "\n".join(
        f"  {i+1}. [{t['topic_id']}] {t['topic_name']}"
        for i, t in enumerate(topics)
    )

    prompt = _PROMPT.format(
        course_name=course_name,
        unit_name=unit_name,
        topic_list=topic_list,
    )

    raw = await _call_with_backoff(
        messages=[{"role": "user", "content": prompt}],
        system=_SYSTEM,
        max_tokens=1500,
    )

    return _parse_and_validate(raw, unit_id, unit_name, topics)


def _parse_and_validate(raw: str, unit_id: str, unit_name: str, topics: list[dict]) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                return _fallback_stub(unit_id, unit_name, topics)
        else:
            return _fallback_stub(unit_id, unit_name, topics)

    if not all(f in data for f in ["hook", "concept", "topic_roadmap"]):
        return _fallback_stub(unit_id, unit_name, topics)

    # Ensure roadmap preserves taxonomy order and has all topics
    roadmap_by_id = {r["topic_id"]: r for r in data.get("topic_roadmap", [])}
    data["topic_roadmap"] = [
        roadmap_by_id.get(t["topic_id"], {
            "topic_id": t["topic_id"],
            "topic_name": t["topic_name"],
            "description": f"Master the key concepts of {t['topic_name']}.",
        })
        for t in topics
    ]

    return data


def _fallback_stub(unit_id: str, unit_name: str, topics: list[dict]) -> dict:
    return {
        "hook": f"This unit covers {unit_name}.",
        "concept": f"{unit_name} builds essential skills for more advanced topics.",
        "topic_roadmap": [
            {
                "topic_id": t["topic_id"],
                "topic_name": t["topic_name"],
                "description": f"Master the key skills of {t['topic_name']}.",
            }
            for t in topics
        ],
        "_fallback": True,
    }
