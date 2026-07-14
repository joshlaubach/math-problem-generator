"""
Voice-loop latency metrics (Phase 1.6 — audit A1: "you cannot manage what
you don't measure").

In-memory ring buffers of per-stage timings + a structured JSON log line per
sample, so percentiles survive in logs even across restarts. Percentiles are
always reported as P50/P90/P95 — never blended averages.

Stage names:
  client.*   — measured in the browser relative to speech_final
               (filler_ms, first_sentence_ms, first_audio_ms, first_wb_ms, total_ms)
  server.*   — measured here (llm_first_sentence_ms, llm_total_ms,
               latex_to_speech_ms, tts_ms, tts_first_byte_ms)

Single-process by design (matches the session store); a multi-worker
deployment aggregates via the JSON logs instead.
"""

from __future__ import annotations

import logging
import math
import threading
from collections import defaultdict, deque
from typing import Optional

logger = logging.getLogger("voice_metrics")

_WINDOW = 500  # samples kept per stage

_lock = threading.Lock()
_stages: dict[str, deque] = defaultdict(lambda: deque(maxlen=_WINDOW))


def record_stage(stage: str, ms: float, *, session_id: Optional[str] = None,
                 turn_id: Optional[str] = None, **extra) -> None:
    """Record one timing sample. Never raises."""
    try:
        ms = float(ms)
        if not math.isfinite(ms) or ms < 0 or ms > 600_000:
            return
        with _lock:
            _stages[stage].append(ms)
        logger.info(
            "voice_stage",
            extra={"stage": stage, "ms": round(ms, 1),
                   "session_id": session_id, "turn_id": turn_id, **extra},
        )
    except Exception:
        pass


def record_client_marks(session_id: str, turn_id: str, marks: dict) -> None:
    """Record the browser's per-turn marks (deltas from speech_final, in ms)."""
    if not isinstance(marks, dict):
        return
    for key, val in list(marks.items())[:12]:
        if isinstance(val, (int, float)) and isinstance(key, str):
            record_stage(f"client.{key[:40]}", val,
                         session_id=session_id, turn_id=turn_id)


def _percentile(sorted_vals: list, q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, math.ceil(q * len(sorted_vals)) - 1))
    return sorted_vals[idx]


def snapshot() -> dict:
    """P50/P90/P95 + count per stage over the in-memory window."""
    out: dict[str, dict] = {}
    with _lock:
        items = {k: list(v) for k, v in _stages.items()}
    for stage, vals in sorted(items.items()):
        vals.sort()
        out[stage] = {
            "count": len(vals),
            "p50_ms": round(_percentile(vals, 0.50), 1),
            "p90_ms": round(_percentile(vals, 0.90), 1),
            "p95_ms": round(_percentile(vals, 0.95), 1),
        }
    return out


def reset() -> None:
    with _lock:
        _stages.clear()
