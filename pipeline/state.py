"""
state.py — thread-safe read/write of pipeline/state.json.

Public API:
    read_state(lesson_id)           -> dict (lesson entry, or {})
    write_state(lesson_id, updates) -> None (merges updates into entry)
    read_all()                      -> dict (full state file)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from filelock import FileLock

from pipeline.config import STATE_FILE, LOCK_FILE

_lock = FileLock(str(LOCK_FILE), timeout=10)


def _load() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_state(lesson_id: str) -> dict:
    """Return the state entry for lesson_id, or {} if not found."""
    with _lock:
        return _load().get(lesson_id, {})


def write_state(lesson_id: str, updates: dict[str, Any]) -> None:
    """Merge updates into the state entry for lesson_id."""
    with _lock:
        data = _load()
        entry = data.get(lesson_id, {})
        # Deep-merge clips_done list to avoid overwriting
        if "clips_done" in updates and "clips_done" in entry:
            existing = entry["clips_done"]
            for clip in updates["clips_done"]:
                if clip not in existing:
                    existing.append(clip)
            updates = {k: v for k, v in updates.items() if k != "clips_done"}
        entry.update(updates)
        data[lesson_id] = entry
        _save(data)


def read_all() -> dict:
    """Return the full state dictionary."""
    with _lock:
        return _load()


def mark_done(lesson_id: str, full_video_path: str) -> None:
    write_state(lesson_id, {"status": "done", "full_video": full_video_path})


def mark_needs_review(lesson_id: str, failed_clip: str, round_count: int) -> None:
    write_state(lesson_id, {
        "status": "needs_review",
        "failed_clip": failed_clip,
        "correction_rounds": round_count,
    })


def mark_clip_done(lesson_id: str, clip_type: str) -> None:
    write_state(lesson_id, {
        "status": "rendering",
        "clips_done": [clip_type],
    })
