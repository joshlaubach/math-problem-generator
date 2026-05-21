"""
pipeline/stages/s4_render.py — Stage 4: Final high-quality render with beat-duration injection.

Before rendering, replaces self.wait("BEAT_N") placeholders in the source
with actual float durations produced by Stage 5 (audio).

If beat durations are not yet available (audio not done), renders with
default fallback durations so the pipeline can proceed in any order.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import logging

from pipeline.config import (
    GENERATED_DIR,
    MEDIA_DIR,
    MANIM_HQ_FLAGS,
    FFMPEG_BIN,
    CLIP_ORDER,
)
from pipeline.state import read_state, write_state

logger = logging.getLogger(__name__)

# Default wait duration when no TTS timing is available yet
_DEFAULT_BEAT_SEC = 3.0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(lesson_id: str, clip_types: list[str] | None = None) -> dict[str, str]:
    """
    Final-render each clip, injecting beat durations if available.
    Returns {clip_type: output_mp4_path}.
    """
    state     = read_state(lesson_id)
    targets   = clip_types or CLIP_ORDER
    beat_map  = state.get("beat_durations", {})   # populated by Stage 5
    results   = {}

    for clip_type in targets:
        out_path = _render_clip(lesson_id, clip_type, beat_map.get(clip_type, {}))
        if out_path:
            results[clip_type] = out_path

    write_state(lesson_id, {"rendered_clips": results, "stage": "rendered"})
    logger.info("[%s] Stage 4 complete — %d clips rendered", lesson_id, len(results))
    return results


# ---------------------------------------------------------------------------
# Per-clip render
# ---------------------------------------------------------------------------

def _render_clip(lesson_id: str, clip_type: str, beat_durations: dict) -> str | None:
    """Inject beats → render → return output mp4 path."""
    src_path     = os.path.join(GENERATED_DIR, lesson_id, f"{clip_type}.py")
    injected_dir = os.path.join(GENERATED_DIR, lesson_id, "injected")
    os.makedirs(injected_dir, exist_ok=True)
    injected_path = os.path.join(injected_dir, f"{clip_type}.py")

    if not os.path.exists(src_path):
        logger.error("[%s/%s] Source file missing", lesson_id, clip_type)
        return None

    with open(src_path, encoding="utf-8") as f:
        source = f.read()

    source = _inject_beats(source, beat_durations)

    with open(injected_path, "w", encoding="utf-8") as f:
        f.write(source)

    class_name = _detect_class_name(injected_path)
    if not class_name:
        logger.error("[%s/%s] No Scene class found", lesson_id, clip_type)
        return None

    out_media = os.path.join(MEDIA_DIR, "final", lesson_id)
    cmd = [
        "python", "-m", "manim",
        injected_path, class_name,
        *MANIM_HQ_FLAGS,
        "--disable_caching",
        "--media_dir", out_media,
    ]
    logger.info("[%s/%s] Final render → %s", lesson_id, clip_type, out_media)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error("[%s/%s] Render error:\n%s", lesson_id, clip_type, result.stderr[-2000:])
            return None
    except subprocess.TimeoutExpired:
        logger.error("[%s/%s] Render timed out (600s)", lesson_id, clip_type)
        return None

    # Locate output
    expected = os.path.join(
        out_media, "videos",
        os.path.basename(injected_path)[:-3], "1080p60", f"{class_name}.mp4"
    )
    if os.path.exists(expected):
        return expected

    for root, _, files in os.walk(out_media):
        for f in files:
            if f == f"{class_name}.mp4" and "partial_movie" not in root:
                return os.path.join(root, f)

    logger.error("[%s/%s] Could not find output mp4", lesson_id, clip_type)
    return None


# ---------------------------------------------------------------------------
# Beat injection
# ---------------------------------------------------------------------------

def _inject_beats(source: str, beat_durations: dict) -> str:
    """
    Replace  self.wait("BEAT_N")  →  self.wait(D)
    where D is beat_durations["BEAT_N"] or _DEFAULT_BEAT_SEC if not found.
    """
    def replace(m: re.Match) -> str:
        key = m.group(1)          # e.g. "BEAT_3"
        dur = beat_durations.get(key, _DEFAULT_BEAT_SEC)
        return f"self.wait({float(dur):.3f})"

    return re.sub(r'self\.wait\("(BEAT_\d+)"\)', replace, source)


def _detect_class_name(source_path: str) -> str | None:
    with open(source_path, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"class\s+(\w+)\s*\(.*Scene.*\)", src)
    return m.group(1) if m else None
