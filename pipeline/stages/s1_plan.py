"""
pipeline/stages/s1_plan.py — Stage 1: Generate a structured video plan for one lesson.

Input : lesson_id (e.g. "pc_024"), lesson JSON from the API or local store
Output: video_plan dict written into state under lesson_id → "plan"

The plan is a 5-clip structure validated against the viz library.
"""
from __future__ import annotations
import json
import os
import re
import logging
from typing import Any

from pipeline.config import (
    ANTHROPIC_MODEL,
    CLIP_ORDER,
    VIZ_TYPES,
)
from pipeline.state import read_state, write_state

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def _load(fname: str) -> str:
    with open(os.path.join(_PROMPT_DIR, fname), encoding="utf-8") as f:
        return f.read()


PLAN_SYSTEM    = _load("plan_prompt.txt")
LAYOUT_BIBLE   = _load("layout_bible.txt")
MATH_TO_SPEECH = _load("math_to_speech.txt")

# ---------------------------------------------------------------------------
# VIZ type validation
# ---------------------------------------------------------------------------

def _pick_viz(clip_type: str, suggested: str) -> str:
    """Return suggested if it's in the approved list, else a safe default."""
    if suggested in VIZ_TYPES:
        return suggested
    # Per-clip defaults
    defaults = {
        "hook":             "StepRevealScene",
        "concept":          "EquationAnatomyScene",
        "worked_example":   "EquationTransformScene",
        "common_mistakes":  "MistakeComparisonScene",
        "summary":          "StepRevealScene",
    }
    fallback = defaults.get(clip_type, "StepRevealScene")
    logger.warning("Viz type %r not in approved list; falling back to %s", suggested, fallback)
    return fallback


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(lesson_id: str, lesson: dict[str, Any]) -> dict[str, Any]:
    """
    Call the LLM to build a 5-clip video plan for *lesson*.
    Returns the plan dict and persists it to state.
    """
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic package not installed — pip install anthropic") from e

    client = anthropic.Anthropic()

    user_content = _build_user_message(lesson_id, lesson)

    logger.info("[%s] Stage 1 — requesting plan from %s", lesson_id, ANTHROPIC_MODEL)
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=f"{PLAN_SYSTEM}\n\n{MATH_TO_SPEECH}\n\n{LAYOUT_BIBLE}",
        messages=[{"role": "user", "content": user_content}],
    )

    raw = resp.content[0].text.strip()
    plan = _parse_plan(raw, lesson_id)
    plan = _validate_plan(plan, lesson_id)

    write_state(lesson_id, {"plan": plan, "stage": "planned"})
    logger.info("[%s] Stage 1 complete — %d clips planned", lesson_id, len(plan["clips"]))
    return plan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_user_message(lesson_id: str, lesson: dict) -> str:
    lesson_json = json.dumps(lesson, ensure_ascii=False, indent=2)
    return (
        f"Lesson ID: {lesson_id}\n\n"
        f"Lesson JSON:\n```json\n{lesson_json}\n```\n\n"
        "Please generate the 5-clip video plan as described in the system prompt. "
        "Output ONLY the JSON object — no prose, no markdown fences."
    )


def _parse_plan(raw: str, lesson_id: str) -> dict:
    """Extract the JSON plan from the LLM response."""
    # Strip accidental markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw.strip(), flags=re.MULTILINE)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        logger.error("[%s] Failed to parse plan JSON:\n%s", lesson_id, raw[:500])
        raise ValueError(f"Stage 1 JSON parse error for {lesson_id}: {e}") from e


def _validate_plan(plan: dict, lesson_id: str) -> dict:
    """
    Ensure the plan has exactly 5 clips in the right order, all required keys,
    and approved viz types.
    """
    if "clips" not in plan:
        raise ValueError(f"[{lesson_id}] Plan missing 'clips' key")

    clips = plan["clips"]
    if len(clips) != len(CLIP_ORDER):
        logger.warning(
            "[%s] Expected %d clips, got %d — truncating/padding",
            lesson_id, len(CLIP_ORDER), len(clips),
        )
        # Pad or truncate to match CLIP_ORDER
        while len(clips) < len(CLIP_ORDER):
            clips.append({
                "clip_type": CLIP_ORDER[len(clips)],
                "title": "Summary",
                "beats": ["Recap the key ideas."],
                "viz_type": "StepRevealScene",
                "viz_config": {},
                "duration_hint": 30,
            })
        clips = clips[:len(CLIP_ORDER)]
        plan["clips"] = clips

    required_keys = {"clip_type", "title", "beats", "viz_type", "duration_hint"}
    for i, clip in enumerate(clips):
        # Enforce clip_type ordering
        clip["clip_type"] = CLIP_ORDER[i]

        missing = required_keys - set(clip.keys())
        if missing:
            logger.warning("[%s] Clip %d missing keys %s", lesson_id, i, missing)
            for k in missing:
                clip.setdefault(k, "" if k not in ("beats", "duration_hint") else ([] if k == "beats" else 30))

        # Validate / fix viz_type
        clip["viz_type"] = _pick_viz(clip["clip_type"], clip.get("viz_type", ""))

        # Ensure viz_config exists
        clip.setdefault("viz_config", {})

    return plan
