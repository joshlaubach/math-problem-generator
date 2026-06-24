"""
Severity classifier for wrong math answers.

Classifies a wrong student answer into one of three levels:
  careless    — correct method, small arithmetic / sign / transcription slip
  method      — wrong procedure or technique for this problem type
  fundamental — missing understanding of the underlying concept

Uses a cheap, fast Haiku call (max_tokens=5). Returns None on any failure so
callers degrade gracefully (default board + correction behavior).
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"

_PROMPT = """\
A math student submitted a wrong answer. Classify the error severity.

Student answer: {student_answer}
Correct answer: {canonical_answer}
{steps_block}
Error types:
  careless    — student knows the method, small arithmetic / sign / transcription slip
  method      — student used the wrong procedure or technique for this problem type
  fundamental — student does not understand the underlying concept

Reply with exactly one word (careless, method, or fundamental)."""


async def classify_severity(
    student_answer: str,
    canonical_answer: str,
    worked_steps: list,
) -> Optional[str]:
    """
    Return 'careless', 'method', 'fundamental', or None if classification fails.
    Only call for wrong answers — result is undefined for correct ones.
    """
    from config import ANTHROPIC_API_KEY

    if not ANTHROPIC_API_KEY:
        return None

    steps_text = ""
    for i, step in enumerate(worked_steps[:6], 1):
        if isinstance(step, dict):
            s = step.get("step", "") or step.get("explanation", "")
        else:
            s = getattr(step, "step", "") or getattr(step, "explanation", "")
        if s:
            steps_text += f"Step {i}: {s}\n"

    steps_block = f"Solution steps:\n{steps_text}" if steps_text else ""

    prompt = _PROMPT.format(
        student_answer=student_answer,
        canonical_answer=canonical_answer,
        steps_block=steps_block,
    )

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model=_CLASSIFIER_MODEL,
            max_tokens=5,
            messages=[{"role": "user", "content": prompt}],
        )
        word = resp.content[0].text.strip().lower()
        for label in ("careless", "method", "fundamental"):
            if label in word:
                return label
    except Exception as exc:
        logger.debug("Severity classification failed: %s", exc)

    return None
