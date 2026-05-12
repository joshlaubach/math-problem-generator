"""
Socratic Tutor Agent.

The only agent that calls Claude in the real-time WebSocket path.
Stateless — all context is passed per call.

Rules enforced via system prompt:
- Never reveal the answer, even indirectly.
- Always end with a guiding question.
- Target the most recent misconception when wrong attempts exist.
- Use hint ladder internally as context — never quote verbatim.
- Keep responses concise (2-4 sentences).
"""

from __future__ import annotations

from llm_anthropic_client import _call_with_backoff

_SYSTEM_PROMPT = """\
You are a patient, encouraging Socratic math tutor. Your job is to guide students \
to discover the answer themselves — never to give it to them.

Rules you must follow without exception:
1. NEVER state or strongly imply the final answer, even if the student begs.
2. Ask exactly one focused guiding question per response.
3. If the student made a wrong attempt, identify the specific misconception in \
that attempt and ask a question that directly targets it.
4. If a hint has been served (hint_level > 0), use the hint concept internally \
to shape your question — but do NOT quote the hint text verbatim.
5. Keep your response to 2-4 sentences. End every response with a question mark.
6. If the student expresses frustration, acknowledge it warmly in one sentence, \
then redirect with your guiding question.
7. Do not repeat a question you have already asked in this conversation.
"""


def _build_messages(
    problem_statement: str,
    conversation: list[dict],
    student_message: str,
    hint_ladder: list[str],
    hint_level: int,
    wrong_attempts: list[str],
) -> list[dict]:
    """Build the Claude messages list for one Socratic turn."""
    messages: list[dict] = []

    # Replay prior conversation (student→user, tutor→assistant)
    for turn in conversation:
        role = "user" if turn["role"] == "student" else "assistant"
        messages.append({"role": role, "content": turn["content"]})

    # Build the context block for this turn
    context_parts = [f"Problem: {problem_statement}"]

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

    Returns:
        Socratic response string — always ends with a question.
    """
    messages = _build_messages(
        problem_statement, conversation, student_message,
        hint_ladder, hint_level, wrong_attempts,
    )
    return await _call_with_backoff(
        messages=messages,
        system=_SYSTEM_PROMPT,
        max_tokens=300,
    )
