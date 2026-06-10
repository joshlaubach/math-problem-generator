"""
Session summarizer — generates a post-session summary with three sections (Phase 6).

Section 1: Bullets (what was covered, how the student did)
Section 2: Per-topic performance dict {topic_name: "strong"|"needs_work"|"attempted"}
Section 3: Practice problems for weak areas (list of problem statement strings)

Called at session end. Falls back gracefully if the LLM is unavailable.
Backward-compatible: if called with old signature (no topics_covered), returns list of bullets.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

def _get_summarizer_system_prompt() -> str:
    """Build the summarizer system prompt via the assembler (lazy, cached by the assembler)."""
    from agents.prompt_assembler import build_system_prompt
    result = build_system_prompt(role="SUMMARY", cacheable=False)
    # build_system_prompt with cacheable=False returns a plain string
    assert isinstance(result, str)
    return result


# Keep module-level constant for backward compat with any external imports
SUMMARIZER_SYSTEM_PROMPT: str = ""  # populated on first call via _get_summarizer_system_prompt()


async def summarize_session(
    topic_name: str,
    mode: str,
    conversation: list[dict],
    problems_attempted: int,
    problems_solved: int,
    hints_used: int,
    duration_seconds: float,
    # Phase 6 extensions (optional — default to backward-compat list return)
    topics_covered: list[str] | None = None,
    session_summary_bullets: list | None = None,
) -> dict | list:
    """
    Generate a session summary.

    Returns:
        If topics_covered is provided (Phase 6): dict with keys
            bullets, per_topic_performance, practice_problems.
        Otherwise (legacy): list of bullet strings.
    """
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

    legacy_mode = topics_covered is None

    if not ANTHROPIC_API_KEY:
        fallback = _fallback_summary(topic_name, problems_solved, problems_attempted, hints_used)
        return fallback if legacy_mode else {
            "bullets": fallback, "per_topic_performance": {}, "practice_problems": []
        }

    conversation_excerpt = _build_excerpt(conversation)
    duration_min = round(duration_seconds / 60, 1)
    topics_str = ", ".join(topics_covered) if topics_covered else topic_name

    # Include prior bullet summaries from mid-session compression
    prior_bullets_text = ""
    if session_summary_bullets:
        bullets_list = [str(b) for b in session_summary_bullets[:6]]
        prior_bullets_text = (
            "\n\nPrior problem bullets (from this session):\n"
            + "\n".join(f"• {b}" for b in bullets_list)
        )

    user_content = f"""Topics covered: {topics_str}
Mode: {mode}
Duration: {duration_min} minutes
Problems attempted: {problems_attempted}
Problems solved: {problems_solved}
Hints used: {hints_used}
{prior_bullets_text}

Recent conversation excerpt:
{conversation_excerpt}

Generate the session summary JSON."""

    try:
        from anthropic import AsyncAnthropic
        summarizer_prompt = _get_summarizer_system_prompt()
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=600,
            system=summarizer_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        data = json.loads(text)
        bullets = data.get("bullets", [])
        if isinstance(bullets, list) and len(bullets) >= 2:
            result = {
                "bullets": bullets[:5],
                "per_topic_performance": data.get("per_topic_performance", {}),
                "practice_problems": data.get("practice_problems", [])[:4],
            }
            return result["bullets"] if legacy_mode else result
    except Exception as exc:
        logger.debug("Summarizer LLM call failed: %s", exc)

    fallback = _fallback_summary(topic_name, problems_solved, problems_attempted, hints_used)
    return fallback if legacy_mode else {
        "bullets": fallback,
        "per_topic_performance": {},
        "practice_problems": [],
    }


def _build_excerpt(conversation: list[dict], max_turns: int = 10) -> str:
    lines = []
    for msg in conversation[-max_turns:]:
        role_str = msg.get("role", "")
        if role_str == "student":
            role = "You"
        elif role_str == "tutor":
            role = "Tutor"
        elif role_str == "student_wb":
            role = "You (whiteboard)"
        else:
            continue
        lines.append(f"{role}: {str(msg.get('content', ''))[:150]}")
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
        bullets.append(f"Used {hints_used} hints — try working further before asking for one next session.")
    bullets.append(f"Practice {topic_name} problems on your own to reinforce today's work.")
    return bullets[:5]
