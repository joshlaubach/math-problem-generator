"""
Drawing recognizer — Claude Vision analysis of student whiteboard snapshots.

Receives a base64 PNG of the student's Fabric.js canvas, identifies what the
student drew, flags any mathematical errors, and returns:
  - A short Socratic chat response (2-3 sentences, ends with a question)
  - An optional annotation instruction (JSON) for the whiteboard tutor layer

The annotation positions the response adjacent to the student's work, never
on top of it.  Color signals: "correction" (amber) for errors, "confirmation"
(green) for correct work, "neutral" (muted) for observations.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_RECOGNIZER_SYSTEM = """\
You are a Socratic math tutor reviewing a student's whiteboard sketch.

Your job:
1. Identify what the student drew (equation, graph, diagram, scratch work, etc.)
2. Note any mathematical errors or promising steps
3. Respond with a short guiding question that helps them discover the answer themselves

Return ONLY valid JSON — no markdown, no explanation:
{
  "chat_text": "Your 2-3 sentence Socratic response ending with a question.",
  "annotation": {
    "latex": "Optional short KaTeX expression to place near the sketch (e.g. a correction label)",
    "label": "Optional short plain-text label (max 60 chars)",
    "x_hint": "left|center|right",
    "color": "correction|confirmation|neutral"
  }
}

Rules for chat_text:
- 2-3 sentences maximum, always end with a question mark
- Never reveal the final answer
- If the sketch is unreadable or blank, ask what the student was trying to draw
- No em-dashes; use commas or periods instead

Rules for annotation:
- Set annotation to null if the sketch is blank or unreadable
- Use "correction" (amber) when you see a mathematical error
- Use "confirmation" (green) when the approach looks correct so far
- Use "neutral" (muted) for observations or labels
- latex and label are both optional; include whichever is most useful
- x_hint tells the frontend which side of the sketch to place the annotation
"""

_RECOGNIZER_PROMPT = (
    "A student drew the above on their whiteboard while working on this problem:\n\n"
    "{problem_statement}\n\n"
    "Analyze what you see and return the JSON response."
)


async def recognize_and_annotate(
    snapshot_b64: str,
    problem_statement: str,
    tutor_name: str = "Josh",
) -> dict:
    """
    Analyze a base64 PNG snapshot of the student's canvas.

    Args:
        snapshot_b64: Base64-encoded PNG from Fabric.js canvas.toDataURL()
        problem_statement: The current problem text (LaTeX).
        tutor_name: Tutor persona name (used in fallback responses).

    Returns:
        {
            "chat_text": str,
            "annotation": {
                "latex": str | None,
                "label": str | None,
                "x_hint": "left"|"center"|"right",
                "color": "correction"|"confirmation"|"neutral"
            } | None
        }
    """
    from config import ANTHROPIC_API_KEY
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — drawing recognition skipped")
        return _fallback(tutor_name)

    image = {"data": snapshot_b64, "media_type": "image/png"}
    prompt = _RECOGNIZER_PROMPT.format(problem_statement=problem_statement)

    from llm_anthropic_client import call_with_images
    try:
        raw = await call_with_images(
            text_prompt=prompt,
            images=[image],
            system=_RECOGNIZER_SYSTEM,
            max_tokens=400,
        )
        return _parse_response(raw, tutor_name)
    except Exception as exc:
        logger.error("Drawing recognition failed: %s", exc)
        return _fallback(tutor_name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_response(raw: str, tutor_name: str) -> dict:
    """Parse and validate the JSON response from Claude."""
    try:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        data = json.loads(text)

        chat_text = str(data.get("chat_text", "")).strip()
        if not chat_text:
            return _fallback(tutor_name)

        annotation_raw = data.get("annotation")
        annotation: Optional[dict] = None
        if isinstance(annotation_raw, dict):
            x_hint = annotation_raw.get("x_hint", "right")
            if x_hint not in ("left", "center", "right"):
                x_hint = "right"
            color = annotation_raw.get("color", "neutral")
            if color not in ("correction", "confirmation", "neutral"):
                color = "neutral"
            annotation = {
                "latex": annotation_raw.get("latex") or None,
                "label": (annotation_raw.get("label") or "")[:60] or None,
                "x_hint": x_hint,
                "color": color,
            }

        return {"chat_text": chat_text, "annotation": annotation}

    except Exception as exc:
        logger.error("Failed to parse recognizer response: %s | raw=%s", exc, raw[:200])
        return _fallback(tutor_name)


def _fallback(tutor_name: str) -> dict:
    """Safe fallback when Vision call fails or returns garbage."""
    return {
        "chat_text": (
            "I can see you drew something on the board. "
            "Can you walk me through what you were thinking when you drew that?"
        ),
        "annotation": None,
    }
