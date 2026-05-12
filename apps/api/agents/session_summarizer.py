"""
Session summarizer — generates a 3-5 bullet post-session summary.

Called at the end of every tutor session. Returns plain-English bullets
the student can act on. Never mentions EDGE phases or internal mechanics.
"""
from __future__ import annotations

import json


SUMMARIZER_SYSTEM_PROMPT = """\
You are summarizing a math tutoring session for a student.

Write exactly 3-5 bullet points that:
1. Name the specific concept or skill covered (no generic phrases like "math concepts")
2. Note whether the student solved it (and how quickly / how many hints if relevant)
3. Give one specific thing to review or practice before the next session (actionable)

Rules:
- Plain English, no jargon, no teaching terminology
- Do NOT mention "hints", "EDGE", "Socratic", "tutor", or "AI"
- Each bullet is one sentence, under 20 words
- Return ONLY valid JSON: {"bullets": ["...", "...", "..."]}
- No markdown, no extra keys
"""


async def summarize_session(
    topic_name: str,
    mode: str,
    conversation: list[dict],
    problems_attempted: int,
    problems_solved: int,
    hints_used: int,
    duration_seconds: float,
) -> list[str]:
    """
    Generate a 3-5 bullet session summary.
    Returns a list of bullet strings.
    Falls back to a generic summary if LLM is unavailable.
    """
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

    if not ANTHROPIC_API_KEY:
        return _fallback_summary(topic_name, problems_solved, problems_attempted, hints_used)

    conversation_excerpt = _build_excerpt(conversation)
    duration_min = round(duration_seconds / 60, 1)

    user_content = f"""Topic: {topic_name}
Mode: {mode}
Duration: {duration_min} minutes
Problems attempted: {problems_attempted}
Problems solved: {problems_solved}
Hints used: {hints_used}

Conversation excerpt:
{conversation_excerpt}

Generate the session summary."""

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            system=SUMMARIZER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        data = json.loads(response.content[0].text.strip())
        bullets = data.get("bullets", [])
        if isinstance(bullets, list) and len(bullets) >= 2:
            return bullets[:5]
    except Exception:
        pass

    return _fallback_summary(topic_name, problems_solved, problems_attempted, hints_used)


def _build_excerpt(conversation: list[dict], max_turns: int = 8) -> str:
    lines = []
    for msg in conversation[-max_turns:]:
        role = "You" if msg.get("role") == "student" else "Tutor"
        lines.append(f"{role}: {msg.get('content', '')[:150]}")
    return "\n".join(lines) if lines else "(no conversation)"


def _fallback_summary(
    topic_name: str,
    problems_solved: int,
    problems_attempted: int,
    hints_used: int,
) -> list[str]:
    bullets = [f"Worked on {topic_name}."]
    if problems_solved > 0:
        bullets.append(f"Solved {problems_solved} of {problems_attempted} problem(s).")
    else:
        bullets.append(f"Attempted {problems_attempted} problem(s) — review the steps before next time.")
    if hints_used > 2:
        bullets.append(f"Used {hints_used} hints — try to work further before asking for one next session.")
    bullets.append(f"Practice {topic_name} problems on your own to reinforce today's work.")
    return bullets[:5]
