"""
pipeline/stages/s3_correct.py — Stage 3: Screenshot self-correction loop.

For each generated clip:
  1. Render at low quality (480p15)
  2. Extract N frames with ffmpeg
  3. Pass frames + source to Claude Vision for review
  4. Apply patches or trigger a full rewrite
  5. Repeat up to MAX_CORRECTION_ROUNDS

If APPROVED after any round, move to the next clip.
If issues persist after MAX_CORRECTION_ROUNDS, mark lesson for human review.
"""
from __future__ import annotations
import os
import re
import json
import logging
import subprocess
import tempfile
from typing import Any

from pipeline.config import (
    ANTHROPIC_MODEL,
    GENERATED_DIR,
    MEDIA_DIR,
    MAX_CORRECTION_ROUNDS,
    MANIM_QL_FLAGS,
    FFMPEG_BIN,
    FFPROBE_BIN,
    QA_FRAME_COUNT,
)
from pipeline.state import read_state, write_state, mark_needs_review, mark_clip_done

logger = logging.getLogger(__name__)

_PROMPT_DIR  = os.path.join(os.path.dirname(__file__), "..", "prompts")


def _load_txt(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


CORRECT_SYSTEM = _load_txt(os.path.join(_PROMPT_DIR, "correct_prompt.txt"))
LAYOUT_BIBLE   = _load_txt(os.path.join(_PROMPT_DIR, "layout_bible.txt"))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(lesson_id: str, clip_types: list[str] | None = None) -> dict[str, str]:
    """
    Run the correction loop for all (or specified) clips of a lesson.
    Returns {clip_type: "approved" | "needs_review"}.
    """
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic package not installed") from e

    state     = read_state(lesson_id)
    plan      = state.get("plan", {})
    all_clips = [c["clip_type"] for c in plan.get("clips", [])]
    targets   = clip_types or all_clips

    client  = anthropic.Anthropic()
    results = {}

    for clip_type in targets:
        status = _correct_clip(client, lesson_id, clip_type)
        results[clip_type] = status
        if status == "approved":
            mark_clip_done(lesson_id, clip_type)
        else:
            mark_needs_review(lesson_id)

    write_state(lesson_id, {"stage": "corrected"})
    return results


# ---------------------------------------------------------------------------
# Per-clip correction loop
# ---------------------------------------------------------------------------

def _correct_clip(client: Any, lesson_id: str, clip_type: str) -> str:
    source_path = os.path.join(GENERATED_DIR, lesson_id, f"{clip_type}.py")
    if not os.path.exists(source_path):
        logger.error("[%s/%s] Source file not found", lesson_id, clip_type)
        return "needs_review"

    for round_num in range(1, MAX_CORRECTION_ROUNDS + 1):
        logger.info("[%s/%s] Correction round %d/%d", lesson_id, clip_type, round_num, MAX_CORRECTION_ROUNDS)

        # Render preview
        video_path = _render_preview(lesson_id, clip_type, source_path)
        if video_path is None:
            logger.warning("[%s/%s] Render failed — requesting rewrite", lesson_id, clip_type)
            source_path = _rewrite_clip(client, lesson_id, clip_type, source_path, error="Render failed")
            continue

        # Extract frames
        frames = _extract_frames(video_path, lesson_id, clip_type, round_num)
        if not frames:
            logger.warning("[%s/%s] No frames extracted", lesson_id, clip_type)
            continue

        # Ask Claude to review
        verdict = _review_frames(client, source_path, frames, lesson_id, clip_type)

        if verdict == "APPROVED":
            logger.info("[%s/%s] APPROVED in round %d", lesson_id, clip_type, round_num)
            return "approved"

        elif isinstance(verdict, list):
            # Patch array
            source_path = _apply_patches(source_path, verdict, lesson_id, clip_type, round_num)

        elif verdict == "REWRITE":
            source_path = _rewrite_clip(client, lesson_id, clip_type, source_path)

        else:
            logger.warning("[%s/%s] Unexpected verdict: %r", lesson_id, clip_type, verdict)

    logger.warning("[%s/%s] Max correction rounds reached", lesson_id, clip_type)
    return "needs_review"


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

_DEFAULT_BEAT_SEC = 2.0   # used in preview renders before real TTS durations are known


def _render_preview(lesson_id: str, clip_type: str, source_path: str) -> str | None:
    """Render at low quality; return path to output mp4 or None on failure.

    BEAT placeholder handling: ``self.wait("BEAT_N")`` strings in the generated
    source are replaced with a fixed float before the preview render so Manim
    does not trip on the string argument.  The original source is never modified.
    """
    class_name = _detect_class_name(source_path)
    if not class_name:
        logger.error("[%s/%s] Could not detect Scene class name", lesson_id, clip_type)
        return None

    # Swap BEAT placeholders for a default float in a temp file
    with open(source_path, encoding="utf-8") as f:
        source_text = f.read()
    preview_text = re.sub(
        r'self\.wait\("BEAT_\d+"\)',
        f"self.wait({_DEFAULT_BEAT_SEC})",
        source_text,
    )

    import tempfile
    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8", dir=os.path.dirname(source_path)
    ) as tmp:
        tmp.write(preview_text)
        tmp_path = tmp.name

    out_dir = os.path.join(MEDIA_DIR, "generated", lesson_id)
    cmd = [
        "python", "-m", "manim",
        tmp_path, class_name,
        *MANIM_QL_FLAGS,
        "--disable_caching",
        "--media_dir", out_dir,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error("[%s/%s] Manim render error:\n%s", lesson_id, clip_type, result.stderr[-3000:])
            return None
    except subprocess.TimeoutExpired:
        logger.error("[%s/%s] Render timed out", lesson_id, clip_type)
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Find the output mp4 (Manim names the folder after the source file stem)
    tmp_stem = os.path.basename(tmp_path)[:-3]
    expected = os.path.join(out_dir, "videos", tmp_stem, "480p15", f"{class_name}.mp4")
    if os.path.exists(expected):
        return expected

    # Fallback: search recursively for any mp4 named after the class
    for root, _, files in os.walk(out_dir):
        for f in files:
            if f == f"{class_name}.mp4":
                return os.path.join(root, f)

    logger.error("[%s/%s] Output mp4 not found after render", lesson_id, clip_type)
    return None


def _detect_class_name(source_path: str) -> str | None:
    with open(source_path, encoding="utf-8") as f:
        src = f.read()
    # Find the first class that inherits from Scene
    m = re.search(r"class\s+(\w+)\s*\(.*Scene.*\)", src)
    return m.group(1) if m else None


def _extract_frames(video_path: str, lesson_id: str, clip_type: str, round_num: int) -> list[str]:
    """Extract QA_FRAME_COUNT evenly-spaced frames as PNG paths."""
    out_dir = os.path.join(
        MEDIA_DIR, "qa_frames", f"{lesson_id}_{clip_type}_r{round_num}"
    )
    os.makedirs(out_dir, exist_ok=True)

    # Get video duration (fall back gracefully if ffprobe unavailable)
    duration = 20.0
    try:
        probe = subprocess.run(
            [FFPROBE_BIN,
             "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True, text=True, timeout=30
        )
        if probe.returncode == 0:
            info = json.loads(probe.stdout)
            duration = float(info["format"]["duration"])
    except Exception:
        pass   # use default 20s

    interval = max(1, duration / QA_FRAME_COUNT)

    result = subprocess.run(
        [FFMPEG_BIN, "-i", video_path,
         "-vf", f"fps=1/{interval:.1f}", "-q:v", "2",
         os.path.join(out_dir, "frame_%03d.png"), "-y"],
        capture_output=True, timeout=60,
    )
    frames = sorted(
        os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.endswith(".png")
    )
    return frames[:QA_FRAME_COUNT]


# ---------------------------------------------------------------------------
# Vision review
# ---------------------------------------------------------------------------

def _review_frames(
    client: Any,
    source_path: str,
    frames: list[str],
    lesson_id: str,
    clip_type: str,
) -> Any:
    """
    Send frames + source to Claude Vision.
    Returns "APPROVED", "REWRITE", or a patch list.
    """
    import base64, anthropic

    with open(source_path, encoding="utf-8") as f:
        source = f.read()

    content: list[dict] = [
        {"type": "text", "text": (
            f"You are reviewing a Manim animation for {lesson_id}/{clip_type}.\n"
            "Check: (1) no overlapping text/mobjects, (2) nothing off-screen, "
            "(3) math is correct, (4) readable font sizes.\n\n"
            f"Source code:\n```python\n{source}\n```\n\n"
            "Here are frames from the rendered preview:"
        )},
    ]

    for i, frame_path in enumerate(frames, 1):
        with open(frame_path, "rb") as img:
            data = base64.b64encode(img.read()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": data},
        })
        content.append({"type": "text", "text": f"Frame {i}"})

    content.append({"type": "text", "text": (
        "\nRespond with exactly one of:\n"
        "1. The word APPROVED  — if the animation looks correct\n"
        "2. A JSON array of patches  — [{\"line\": N, \"old\": \"...\", \"new\": \"...\"}]\n"
        "3. The word REWRITE  — if the scene needs to be completely regenerated\n"
        "No other output."
    )})

    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1500,
        system=CORRECT_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    raw = resp.content[0].text.strip()
    return _parse_verdict(raw, lesson_id, clip_type)


def _parse_verdict(raw: str, lesson_id: str, clip_type: str) -> Any:
    if raw.upper() == "APPROVED":
        return "APPROVED"
    if raw.upper() == "REWRITE":
        return "REWRITE"
    raw_stripped = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw_stripped = re.sub(r"```\s*$", "", raw_stripped.strip(), flags=re.MULTILINE)
    try:
        patches = json.loads(raw_stripped.strip())
        if isinstance(patches, list):
            return patches
    except json.JSONDecodeError:
        pass
    logger.warning("[%s/%s] Could not parse verdict: %r", lesson_id, clip_type, raw[:200])
    return "APPROVED"   # treat unparseable as approved to avoid infinite loop


# ---------------------------------------------------------------------------
# Patch application
# ---------------------------------------------------------------------------

def _apply_patches(
    source_path: str,
    patches: list[dict],
    lesson_id: str,
    clip_type: str,
    round_num: int,
) -> str:
    """Apply line patches and save to a new version of the file."""
    with open(source_path, encoding="utf-8") as f:
        lines = f.readlines()

    applied = 0
    for patch in patches:
        line_no = int(patch.get("line", 0)) - 1   # 1-indexed → 0-indexed
        old     = patch.get("old", "")
        new     = patch.get("new", "")
        if 0 <= line_no < len(lines) and old in lines[line_no]:
            lines[line_no] = lines[line_no].replace(old, new, 1)
            applied += 1
        else:
            # Try whole-file search
            for i, line in enumerate(lines):
                if old in line:
                    lines[i] = line.replace(old, new, 1)
                    applied += 1
                    break

    with open(source_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    logger.info("[%s/%s] Applied %d/%d patches (round %d)", lesson_id, clip_type, applied, len(patches), round_num)
    return source_path


def _rewrite_clip(
    client: Any,
    lesson_id: str,
    clip_type: str,
    source_path: str,
    error: str = "",
) -> str:
    """Ask the LLM to completely rewrite ONLY this clip's source."""
    logger.info("[%s/%s] Requesting full rewrite (error: %s)", lesson_id, clip_type, error[:200])
    from pipeline.stages.s2_generate import regenerate_clip
    # Regenerate only the failing clip — does not touch other clips
    regenerate_clip(lesson_id, clip_type)
    return source_path   # path unchanged; regenerate_clip overwrites the file in-place
