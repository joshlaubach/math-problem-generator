"""
Topic Lesson Writer — generates structured JSON lessons per topic using Claude.

Called by GET /topics/{topic_id}/lesson (on-demand with disk caching).

Output: structured JSON with 8 sections:
  hook, concept, anatomy, worked_example, partial_example,
  practice_problems, common_mistakes, untested_variants

worked_example and partial_example are step-arrays:
  [{ expression_latex, description_latex, student_completes }]

practice_problems: [{ prompt_latex, answer_latex }]
common_mistakes, untested_variants: string[]
"""
from __future__ import annotations

import json
from typing import Optional

_SYSTEM = """\
You are an expert mathematics educator writing topic-level lessons for a tutoring platform.
Your lessons are used both for reading AND by an AI tutor during live sessions.

Rules:
- Use LaTeX: $...$ for inline math, no display $$ (the frontend handles rendering)
- description_latex fields must be NARRATIVE PROSE — full sentences explaining WHY,
  not just labels. Write like you're talking to a student who's slightly stuck.
- Be mathematically precise but accessible
- Never use the words "EDGE", "hook", "anatomy" — these are internal labels only
"""

_PROMPT = """\
Write a structured lesson for this topic:

Course: {course_name}
Unit: {unit_name}
Topic: {topic_name}
Topic ID: {topic_id}

Return ONLY valid JSON matching this exact schema. No markdown fences, no explanation:

{{
  "hook": "One paragraph (2-4 sentences) posing a specific problem the student cannot yet solve. Start with what they already know, then reveal the gap. End with a question.",

  "concept": "One paragraph defining the concept: plain-English explanation first, then the formal definition with inline LaTeX. Keep it under 100 words.",

  "anatomy": "One paragraph explicitly naming and defining the distinct components/parts of this concept. For every topic there is always something worth naming — operations, functions, variables, geometric elements, or structural parts. Be specific to this topic.",

  "worked_example": [
    {{
      "expression_latex": "the LaTeX expression or equation for this step",
      "description_latex": "2-3 sentence narrative explaining what we are doing and WHY at this step, written directly to the student",
      "student_completes": false
    }}
  ],

  "partial_example": [
    {{
      "expression_latex": "the expression (empty string '' for steps the student fills in)",
      "description_latex": "narrative explanation or prompt for the student",
      "student_completes": false
    }},
    {{
      "expression_latex": "",
      "description_latex": "A specific prompt asking the student to complete this step",
      "student_completes": true
    }}
  ],

  "practice_problems": [
    {{
      "prompt_latex": "the problem statement in LaTeX",
      "answer_latex": "the final answer in LaTeX"
    }}
  ],

  "common_mistakes": [
    "Full sentence describing a specific mistake students make, what goes wrong, and a one-sentence fix."
  ],

  "untested_variants": [
    "A specific problem type or context this lesson does NOT cover that students would encounter on an exam."
  ]
}}

Requirements:
- worked_example: 3-5 steps. Each description_latex is a full narrative sentence or two.
- partial_example: 3-4 steps total. Mark exactly 1-2 steps as student_completes: true.
  These should be the KEY steps that test understanding, not trivial algebra.
- practice_problems: exactly 4-5 problems. Difficulty progression:
  1. Trivial (build confidence)
  2-3. Medium (core skill)
  4. Harder (combines this topic with something previously learned)
  5. Word problem or non-standard context (if applicable)
- common_mistakes: exactly 3 mistakes specific to THIS topic (not generic math errors)
- untested_variants: exactly 3-4 specific variants NOT covered by the 4-5 practice problems above.
  Write these AFTER deciding what the practice problems cover, so there is no overlap.
"""


async def write_topic_lesson(
    topic_id: str,
    topic_name: str,
    unit_name: str,
    course_name: str,
) -> dict:
    """
    Generate a structured JSON lesson for a single topic using Claude.

    Returns the parsed lesson dict. Raises on generation failure.
    """
    from llm_anthropic_client import _call_with_backoff

    prompt = _PROMPT.format(
        topic_id=topic_id,
        topic_name=topic_name,
        unit_name=unit_name,
        course_name=course_name,
    )

    raw = await _call_with_backoff(
        messages=[{"role": "user", "content": prompt}],
        system=_SYSTEM,
        max_tokens=4000,
        retries=5,
    )

    return _parse_and_validate(raw, topic_id, topic_name, course_name)


def _parse_and_validate(raw: str, topic_id: str, topic_name: str, course_name: str) -> dict:
    """
    Parse Claude's response and validate the schema.
    Returns a valid lesson dict — falls back to a minimal stub on parse failure.
    """
    # Strip markdown fences if Claude wrapped the JSON
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Find the first { and last } and try again
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                return _fallback_stub(topic_id, topic_name, course_name)
        else:
            return _fallback_stub(topic_id, topic_name, course_name)

    required_fields = [
        "hook", "concept", "anatomy", "worked_example",
        "partial_example", "practice_problems", "common_mistakes", "untested_variants",
    ]
    if not all(f in data for f in required_fields):
        return _fallback_stub(topic_id, topic_name, course_name)

    # Normalize step arrays — ensure student_completes is a bool
    for step in data.get("worked_example", []):
        step.setdefault("student_completes", False)
        step.setdefault("expression_latex", "")
        step.setdefault("description_latex", "")

    for step in data.get("partial_example", []):
        step.setdefault("student_completes", False)
        step.setdefault("expression_latex", "")
        step.setdefault("description_latex", "")

    for prob in data.get("practice_problems", []):
        prob.setdefault("prompt_latex", "")
        prob.setdefault("answer_latex", "")

    return data


def _fallback_stub(topic_id: str, topic_name: str, course_name: str) -> dict:
    """Minimal valid lesson returned when Claude's output cannot be parsed."""
    return {
        "hook": f"This lesson covers {topic_name}.",
        "concept": f"{topic_name} is a key concept in {course_name}. Check back soon for a full explanation.",
        "anatomy": f"The key components of {topic_name} will be described here.",
        "worked_example": [
            {
                "expression_latex": "",
                "description_latex": "A worked example will appear here shortly.",
                "student_completes": False,
            }
        ],
        "partial_example": [
            {
                "expression_latex": "",
                "description_latex": "Try this step yourself.",
                "student_completes": True,
            }
        ],
        "practice_problems": [
            {"prompt_latex": f"\\text{{Practice problem for }} {topic_name}", "answer_latex": ""}
        ],
        "common_mistakes": [f"Common mistakes for {topic_name} will be listed here."],
        "untested_variants": [f"Additional variants of {topic_name} to explore."],
        "_fallback": True,
    }
