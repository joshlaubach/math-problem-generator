"""
EDGE phase assessor — determines where in the EDGE teaching framework to enter.

After the topic is confirmed, the assessor asks one diagnostic question and
determines which phase to start in: Explain, Demonstrate, Guide, or Enable.

EDGE is an internal framework — the phase labels are NEVER exposed to the student.
"""
from __future__ import annotations

import json


ASSESSMENT_SYSTEM_PROMPT = """\
You are a math tutor assessing where to begin with a student.

Based on the topic and the student's message, decide which teaching phase to use:
- "explain": Student needs the concept introduced from scratch. Use when they say things like "I don't know what X is", "I've never seen this", "can you explain".
- "demonstrate": Student has heard of it but hasn't seen a worked example. Use when they seem vaguely familiar but uncertain.
- "guide": Student understands the concept but is stuck on a specific problem or step. Use for homework help or "I got this but then got stuck".
- "enable": Student knows the method, wants to practice and verify. Use when they say "I think I know how, let me try" or ask for practice problems.

Return ONLY valid JSON (no markdown):
{
  "phase": "explain|demonstrate|guide|enable",
  "diagnostic_question": "One warm, concise question to ask the student right now",
  "reasoning": "brief internal note on why this phase"
}

The diagnostic_question should feel natural, NOT robotic. It must end with a question mark.
Examples:
- explain: "Before we dive in, have you come across the chain rule before, or is this brand new?"
- demonstrate: "Have you seen an example worked out yet, or would it help to walk through one together?"
- guide: "What have you tried so far — can you show me where you got stuck?"
- enable: "Great! Want me to give you a problem to try, or do you have one in mind?"
"""


async def assess_entry_phase(
    topic_name: str,
    course_name: str,
    mode: str,
    student_message: str,
    conversation_history: list[dict],
) -> dict:
    """
    Determine EDGE entry phase and return the opening diagnostic question.

    Returns: {phase, diagnostic_question, reasoning}
    """
    from anthropic import AsyncAnthropic
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

    if not ANTHROPIC_API_KEY:
        return _default_diagnostic(mode)

    history_text = "\n".join(
        f"{'Student' if m.get('role') == 'student' else 'Tutor'}: {m.get('content', '')}"
        for m in conversation_history[-6:]
    )

    user_content = f"""Topic: {topic_name} ({course_name})
Session mode: {mode}
Conversation so far:
{history_text}
Student just said: {student_message}

Determine the EDGE phase and diagnostic question."""

    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=200,
            system=ASSESSMENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text.strip()
        result = json.loads(text)
        result.setdefault("phase", "guide")
        result.setdefault("diagnostic_question", _default_diagnostic(mode)["diagnostic_question"])
        result.setdefault("reasoning", "")
        return result
    except Exception:
        return _default_diagnostic(mode)


def _default_diagnostic(mode: str) -> dict:
    questions = {
        "concept": "Have you come across this topic before, or is it brand new to you?",
        "homework": "What have you tried so far — can you show me where you got stuck?",
        "practice": "Would you like me to give you a problem to try, or do you have one in mind?",
    }
    phases = {"concept": "explain", "homework": "guide", "practice": "enable"}
    return {
        "phase": phases.get(mode, "guide"),
        "diagnostic_question": questions.get(mode, "What would you like to work on?"),
        "reasoning": "default",
    }
