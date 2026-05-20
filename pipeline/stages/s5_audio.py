"""
pipeline/stages/s5_audio.py — Stage 5: TTS audio generation via OpenAI.

For each clip, converts the narration beats to spoken audio using the
OpenAI TTS API (model: tts-1-hd, voice: configurable).

Output layout:
  media/audio/<lesson_id>/<clip_type>/beat_01.mp3
  media/audio/<lesson_id>/<clip_type>/beat_02.mp3
  ...

Duration of each beat .mp3 is measured with ffprobe and stored in state
so Stage 4 can inject the exact float into self.wait().
"""
from __future__ import annotations
import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from pipeline.config import (
    OPENAI_TTS_MODEL,
    OPENAI_TTS_VOICE,
    MEDIA_DIR,
    FFPROBE_BIN,
)
from pipeline.state import read_state, write_state

logger = logging.getLogger(__name__)

_FFPROBE_BIN = FFPROBE_BIN   # from config (handles system PATH + imageio-ffprobe fallback)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(lesson_id: str, clip_types: list[str] | None = None) -> dict[str, dict[str, float]]:
    """
    Generate TTS audio for every beat in every clip.
    Returns {clip_type: {BEAT_N: duration_seconds}}.
    """
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai package not installed — pip install openai") from e

    state = read_state(lesson_id)
    plan  = state.get("plan", {})
    if not plan:
        raise ValueError(f"[{lesson_id}] No plan found — run Stage 1 first")

    all_clips = [c for c in plan.get("clips", [])]
    if clip_types:
        all_clips = [c for c in all_clips if c["clip_type"] in clip_types]

    client      = OpenAI()
    beat_map: dict[str, dict[str, float]] = {}

    for clip in all_clips:
        clip_type = clip["clip_type"]
        beats     = clip.get("beats", [])
        beat_durs = _generate_clip_audio(client, lesson_id, clip_type, beats)
        beat_map[clip_type] = beat_durs

    write_state(lesson_id, {"beat_durations": beat_map, "stage": "audio_done"})
    logger.info("[%s] Stage 5 complete — audio for %d clips", lesson_id, len(beat_map))
    return beat_map


# ---------------------------------------------------------------------------
# Per-clip audio generation
# ---------------------------------------------------------------------------

def _generate_clip_audio(
    client: Any,
    lesson_id: str,
    clip_type: str,
    beats: list[str],
) -> dict[str, float]:
    """Generate one .mp3 per beat; return {BEAT_N: duration_sec}."""
    out_dir = Path(MEDIA_DIR) / "audio" / lesson_id / clip_type
    out_dir.mkdir(parents=True, exist_ok=True)

    beat_durs: dict[str, float] = {}

    for i, beat_text in enumerate(beats, 1):
        key      = f"BEAT_{i}"
        mp3_path = out_dir / f"beat_{i:02d}.mp3"

        if mp3_path.exists():
            # Already generated; measure duration only
            dur = _measure_duration(str(mp3_path))
            beat_durs[key] = dur
            logger.info("[%s/%s] %s already exists (%.2fs)", lesson_id, clip_type, key, dur)
            continue

        logger.info("[%s/%s] Generating TTS for %s: %r", lesson_id, clip_type, key, beat_text[:60])
        try:
            response = client.audio.speech.create(
                model=OPENAI_TTS_MODEL,
                voice=OPENAI_TTS_VOICE,
                input=beat_text,
                response_format="mp3",
            )
            mp3_path.write_bytes(response.content)
        except Exception as exc:
            logger.error("[%s/%s] TTS failed for %s: %s", lesson_id, clip_type, key, exc)
            beat_durs[key] = 3.0   # fallback duration
            continue

        dur = _measure_duration(str(mp3_path))
        beat_durs[key] = dur
        logger.info("[%s/%s] %s → %.2fs", lesson_id, clip_type, key, dur)

    return beat_durs


# ---------------------------------------------------------------------------
# Duration measurement
# ---------------------------------------------------------------------------

def _measure_duration(mp3_path: str) -> float:
    """Return duration of audio file in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [_FFPROBE_BIN,
             "-v", "quiet",
             "-print_format", "json",
             "-show_format",
             mp3_path],
            capture_output=True, text=True, timeout=15,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception as e:
        logger.warning("Could not measure duration of %s: %s", mp3_path, e)
        return 3.0


