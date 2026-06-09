"""
Socratic Tutor Agent.

The only agent that calls Claude in the real-time WebSocket path.
Stateless — all context is passed per call.

System prompt is assembled via prompt_assembler.build_system_prompt() so that:
- CONSTITUTION + OUTPUT_CONSTRAINTS are always-on (Anthropic-cached static prefix)
- ROLE_LAYERS["SOCRATIC"] provides the structural rules
- Situational SCENARIO_SNIPPETS are injected only when signals fire
- DEEP_GUIDE is injected (cached) only when the escalation gate opens

The duplicated rules that previously lived inline in _SYSTEM_PROMPT_TEMPLATE
(Never-state-answer, one-question, KaTeX-only, no em-dash, etc.) are now
authoritative in tutor_guide.py and removed from here to prevent drift.
"""

from __future__ import annotations

from llm_anthropic_client import _call_with_backoff
from concept_taxonomy import labels_for_topic

_CONCEPT_SECTION = """\
Known misconception labels for this topic (use these exact labels when tagging errors):
{labels}
When a student makes an error, silently identify which label fits best. \
Let this shape your guiding question, but never name the label aloud.
"""


def _build_messages(
    problem_statement: str,
    conversation: list[dict],
    student_message: str,
    hint_ladder: list[str],
    hint_level: int,
    wrong_attempts: list[str],
    session_summary: list[str],
) -> list[dict]:
    """Build the Claude messages list for one Socratic turn."""
    messages: list[dict] = []

    # Replay prior conversation (student→user, tutor→assistant)
    for turn in conversation:
        role = "user" if turn["role"] == "student" else "assistant"
        messages.append({"role": role, "content": turn["content"]})

    # Build the context block for this turn
    context_parts = [f"Problem: {problem_statement}"]

    if session_summary:
        context_parts.append(
            "Prior problems in this session:\n"
            + "\n".join(f"• {b}" for b in session_summary)
        )

    if wrong_attempts:
        context_parts.append(
            "Student's incorrect attempts so far: "
            + "; ".join(f'"{a}"' for a in wrong_attempts)
        )

    if hint_level > 0 and hint_level <= len(hint_ladder):
        context_parts.append(
            f"Hint context (level {hint_level}/{len(hint_ladder)}): "
            + hint_ladder[hint_level - 1]
        )

    context_block = "\n".join(context_parts)
    user_turn = f"[Context]\n{context_block}\n\n[Student message]\n{student_message}"
    messages.append({"role": "user", "content": user_turn})

    return messages


async def respond(
    problem_statement: str,
    conversation: list[dict],
    student_message: str,
    hint_ladder: list[str],
    hint_level: int,
    wrong_attempts: list[str],
    tutor_name: str = "Josh",
    session_summary: list[str] | None = None,
    topic_id: str | None = None,
    history_briefing: str = "",
    snippets: list[str] | None = None,
    topic_guidance: str | None = None,
    deep: bool = False,
) -> str:
    """
    Generate a Socratic response to the student's message.

    Args:
        problem_statement: Full problem text (may include LaTeX).
        conversation: Running dialogue [{role: "student"|"tutor", content: str}].
        student_message: The student's current input.
        hint_ladder: 4-item pre-generated hint ladder (internal context only).
        hint_level: Index of last hint served (0 = none yet).
        wrong_attempts: All incorrect answer strings submitted so far.
        tutor_name: Tutor persona name injected into system prompt.
        session_summary: Bullet summaries of earlier problems in this session.
        topic_id: Topic identifier for concept-label lookup.
        history_briefing: Cross-session weak concept briefing (optional).
        snippets: Scenario snippet keys from select_snippets() — injected into prompt.
        topic_guidance: Block from select_topic_guidance() — injected into prompt.
        deep: If True, inject the full guide (escalation-gated).

    Returns:
        Socratic response string — always ends with a question.
    """
    from agents.prompt_assembler import build_system_prompt

    # Build dynamic context section for the system prompt
    concept_labels = labels_for_topic(topic_id) if topic_id else []
    concept_section = (
        _CONCEPT_SECTION.format(labels="\n".join(f"• {l}" for l in concept_labels[:30]))
        if concept_labels else ""
    )
    history_section = f"\nPrior session context: {history_briefing}" if history_briefing else ""
    tutor_section = f"You are {tutor_name}."

    context = "\n".join(filter(None, [tutor_section, concept_section, history_section]))

    system_prompt = build_system_prompt(
        role="SOCRATIC",
        context=context,
        snippets=snippets,
        topic_guidance=topic_guidance,
        deep=deep,
        cacheable=True,
    )

    messages = _build_messages(
        problem_statement, conversation, student_message,
        hint_ladder, hint_level, wrong_attempts,
        session_summary or [],
    )
    return await _call_with_backoff(
        messages=messages,
        system=system_prompt,
        max_tokens=300,
    )
