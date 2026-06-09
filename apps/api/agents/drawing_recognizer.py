"""
Drawing recognizer — Claude Vision analysis of student whiteboard snapshots.

Receives a base64 PNG of the student's Fabric.js canvas, identifies what the
student drew, flags any mathematical errors, and returns:
  - A short Socratic chat response (2-3 sentences, ends with a question)
  - An optional annotation instruction (JSON) for the whiteboard tutor layer

The annotation positions the response adjacent to the student's work, never
on top of it.  Color signals: "correction" (amber) for errors, "confirmation"
(green) for correct work, "neutral" (muted) for observations.

System prompt is assembled via prompt_assembler.build_system_prompt(role="DRAWING")
so CONSTITUTION + OUTPUT_CONSTRAINTS always-on rules ride every vision call.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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

    from agents.prompt_assembler import build_system_prompt
    from llm_anthropic_client import call_with_images

    system_prompt = build_system_prompt(
        role="DRAWING",
        context=f"You are {tutor_name}.",
        cacheable=True,
    )

    prompt = (
        "A student drew the above on their whiteboard while working on this problem:\n\n"
        f"{problem_statement}\n\n"
        "Analyze what you see and return the JSON response."
    )
    image = {"data": snapshot_b64, "media_type": "image/png"}

    try:
        raw = await call_with_images(
            text_prompt=prompt,
            images=[image],
            system=system_prompt,
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
