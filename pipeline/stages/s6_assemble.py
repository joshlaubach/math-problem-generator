"""
pipeline/stages/s6_assemble.py — Stage 6: Merge video + audio via ffmpeg.

For each clip:
  1. Concatenate all per-beat audio files into one clip audio track
  2. Merge that audio track with the rendered video
  3. Concatenate all 5 clips into the final lesson video

Output: media/final/<lesson_id>/lesson_<lesson_id>.mp4
"""
from __future__ import annotations
import os
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from pipeline.config import (
    MEDIA_DIR,
    FFMPEG_BIN,
    CLIP_ORDER,
)
from pipeline.state import read_state, write_state

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(lesson_id: str) -> Optional[str]:
    """
    Assemble all clips into one lesson video.
    Returns the path to the final mp4 or None on failure.
    """
    state         = read_state(lesson_id)
    rendered      = state.get("rendered_clips", {})
    beat_map      = state.get("beat_durations", {})
    audio_base    = Path(MEDIA_DIR) / "audio" / lesson_id
    final_dir     = Path(MEDIA_DIR) / "final" / lesson_id
    final_dir.mkdir(parents=True, exist_ok=True)

    merged_clips: list[str] = []

    for clip_type in CLIP_ORDER:
        video_path = rendered.get(clip_type)
        if not video_path or not os.path.exists(video_path):
            logger.warning("[%s/%s] No rendered video — skipping in assembly", lesson_id, clip_type)
            continue

        clip_audio = _concat_beat_audio(lesson_id, clip_type, beat_map.get(clip_type, {}), audio_base)
        merged     = _merge_av(lesson_id, clip_type, video_path, clip_audio, final_dir)
        if merged:
            merged_clips.append(merged)

    if not merged_clips:
        logger.error("[%s] No clips to assemble", lesson_id)
        return None

    final_path = str(final_dir / f"lesson_{lesson_id}.mp4")
    success    = _concat_clips(merged_clips, final_path)

    if success:
        write_state(lesson_id, {"final_video": final_path, "stage": "assembled"})
        logger.info("[%s] Stage 6 complete → %s", lesson_id, final_path)
        return final_path

    return None


# ---------------------------------------------------------------------------
# Step 1: Concatenate per-beat audio into one clip audio track
# ---------------------------------------------------------------------------

def _concat_beat_audio(
    lesson_id: str,
    clip_type: str,
    beat_durs: dict[str, float],
    audio_base: Path,
) -> Optional[str]:
    """
    Concatenate beat_01.mp3 … beat_N.mp3 in order.
    Returns path to combined mp3, or None if no audio found.
    """
    beat_dir  = audio_base / clip_type
    mp3_files = sorted(beat_dir.glob("beat_*.mp3")) if beat_dir.exists() else []

    if not mp3_files:
        return None

    if len(mp3_files) == 1:
        return str(mp3_files[0])

    # Write ffmpeg concat list
    out_path = str(audio_base / f"{clip_type}_combined.mp3")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for mp3 in mp3_files:
            f.write(f"file '{mp3.as_posix()}'\n")
        list_path = f.name

    cmd = [
        FFMPEG_BIN,
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        out_path, "-y",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    os.unlink(list_path)

    if result.returncode == 0:
        return out_path
    logger.error("[%s/%s] Audio concat failed:\n%s", lesson_id, clip_type, result.stderr.decode()[-1000:])
    return None


# ---------------------------------------------------------------------------
# Step 2: Merge video + audio
# ---------------------------------------------------------------------------

def _merge_av(
    lesson_id: str,
    clip_type: str,
    video_path: str,
    audio_path: Optional[str],
    out_dir: Path,
) -> Optional[str]:
    """Merge video and audio into a single mp4."""
    out_path = str(out_dir / f"{clip_type}.mp4")

    if audio_path and os.path.exists(audio_path):
        cmd = [
            FFMPEG_BIN,
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            out_path, "-y",
        ]
    else:
        # No audio — copy video as-is
        logger.warning("[%s/%s] No audio; copying video without sound", lesson_id, clip_type)
        cmd = [FFMPEG_BIN, "-i", video_path, "-c", "copy", out_path, "-y"]

    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode == 0:
        return out_path
    logger.error("[%s/%s] A/V merge failed:\n%s", lesson_id, clip_type, result.stderr.decode()[-1000:])
    return None


# ---------------------------------------------------------------------------
# Step 3: Concatenate all clips
# ---------------------------------------------------------------------------

def _concat_clips(clip_paths: list[str], out_path: str) -> bool:
    """Concatenate multiple mp4 clips into one final mp4."""
    if len(clip_paths) == 1:
        import shutil
        shutil.copy2(clip_paths[0], out_path)
        return True

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{Path(p).as_posix()}'\n")
        list_path = f.name

    cmd = [
        FFMPEG_BIN,
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        out_path, "-y",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    os.unlink(list_path)

    if result.returncode == 0:
        logger.info("Final concat → %s", out_path)
        return True
    logger.error("Final concat failed:\n%s", result.stderr.decode()[-1000:])
    return False
