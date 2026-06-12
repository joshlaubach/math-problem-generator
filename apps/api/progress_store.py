"""
Progress store — per-user, per-topic mastery persistence (launch plan L1/7B).

This is what makes the tutor remember a student between sessions:
- session END writes mastery deltas derived from per_topic_performance
- session START reads mastery to seed problem difficulty and enrich the
  history briefing

Storage follows the lesson_store pattern: ProgressRecord in Postgres when
USE_DATABASE=true, data/progress.jsonl (append-only, last-write-wins) in dev.

Safety rails (launch plan risk register):
- A single session can never move mastery by more than ±MAX_SESSION_DELTA
  (the summarizer LLM classifies performance; a misclassification must not
  crater a student's history).
- Mastery is clamped to [0, 1]; difficulty to [1, 5].
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROGRESS_JSONL_PATH = Path("data/progress.jsonl")

# Per-performance-grade mastery deltas (summarizer vocabulary)
_PERFORMANCE_DELTAS: dict[str, float] = {
    "strong": +0.10,
    "attempted": +0.02,
    "needs_work": -0.05,
}

# Hard cap on what one session may do to one topic's mastery
MAX_SESSION_DELTA = 0.15

# Mastery below this counts as a weak topic for the history briefing
WEAK_TOPIC_THRESHOLD = 0.4


def _uses_database() -> bool:
    from config import USE_DATABASE
    return USE_DATABASE


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ── Read ───────────────────────────────────────────────────────────────────────

def get_progress(user_id: str, topic_id: str) -> Optional[dict]:
    """
    Return {mastery_score, current_conceptual_diff, current_computational_diff,
    streak, last_reviewed_at, next_review_at} or None if no record exists.
    """
    if _uses_database():
        return _get_db(user_id, topic_id)
    return _get_jsonl(user_id, topic_id)


def seed_difficulty(user_id: str, topic_id: str, default: int) -> int:
    """
    Conceptual difficulty to start this topic at, from stored progress.
    Falls back to `default` (intake-derived) when the student is new to the
    topic or the store is unavailable. Never raises.
    """
    try:
        record = get_progress(user_id, topic_id)
        if record is None:
            return default
        return int(_clamp(record.get("current_conceptual_diff", default), 1, 5))
    except Exception as exc:
        logger.warning("seed_difficulty failed for %s/%s: %s", user_id, topic_id, exc)
        return default


def weak_topics(user_id: str, topic_ids: list[str]) -> list[tuple[str, float]]:
    """
    Of the given topics, return [(topic_id, mastery)] for those the student
    has touched before and shown weakness on (mastery < WEAK_TOPIC_THRESHOLD).
    Used to enrich the session-start history briefing. Never raises.
    """
    weak: list[tuple[str, float]] = []
    for tid in topic_ids:
        try:
            record = get_progress(user_id, tid)
        except Exception:
            continue
        if record is not None and record["mastery_score"] < WEAK_TOPIC_THRESHOLD:
            weak.append((tid, record["mastery_score"]))
    return weak


# ── Write ──────────────────────────────────────────────────────────────────────

def apply_session_results(user_id: str, performance_by_topic_id: dict[str, str]) -> None:
    """
    Apply one session's per-topic performance to stored mastery.

    performance_by_topic_id: {topic_id: "strong"|"attempted"|"needs_work"}
    (the summarizer's vocabulary; unknown grades are ignored).

    Rules:
    - mastery += grade delta, clamped to ±MAX_SESSION_DELTA per session
      and [0, 1] overall
    - strong  → conceptual difficulty +1 (cap 5), streak +1
    - needs_work → conceptual difficulty −1 (floor 1), streak reset
    - SRS: next_review_at = now + days(new_mastery * 7)
    """
    now = datetime.now(timezone.utc)

    for topic_id, grade in performance_by_topic_id.items():
        delta = _PERFORMANCE_DELTAS.get(str(grade).lower())
        if delta is None:
            continue
        delta = _clamp(delta, -MAX_SESSION_DELTA, MAX_SESSION_DELTA)

        current = get_progress(user_id, topic_id) or {
            "mastery_score": 0.0,
            "current_conceptual_diff": 1,
            "current_computational_diff": 1,
            "streak": 0,
        }

        new_mastery = _clamp(current["mastery_score"] + delta, 0.0, 1.0)
        diff = current["current_conceptual_diff"]
        streak = current["streak"]
        if grade == "strong":
            diff = int(_clamp(diff + 1, 1, 5))
            streak += 1
        elif grade == "needs_work":
            diff = int(_clamp(diff - 1, 1, 5))
            streak = 0

        updated = {
            "mastery_score": round(new_mastery, 4),
            "current_conceptual_diff": diff,
            "current_computational_diff": diff,
            "streak": streak,
            "last_reviewed_at": now,
            "next_review_at": now + timedelta(days=new_mastery * 7),
        }

        try:
            if _uses_database():
                _upsert_db(user_id, topic_id, updated)
            else:
                _upsert_jsonl(user_id, topic_id, updated)
        except Exception as exc:
            logger.error("Progress write failed for %s/%s: %s", user_id, topic_id, exc)


# ── DB backend ─────────────────────────────────────────────────────────────────

def _get_db(user_id: str, topic_id: str) -> Optional[dict]:
    try:
        from db_models import ProgressRecord
        from db_session import get_session

        db = get_session()
        try:
            r = db.query(ProgressRecord).filter(
                ProgressRecord.user_id == user_id,
                ProgressRecord.topic_id == topic_id,
            ).first()
            if r is None:
                return None
            return {
                "mastery_score": r.mastery_score,
                "current_conceptual_diff": r.current_conceptual_diff,
                "current_computational_diff": r.current_computational_diff,
                "streak": r.streak,
                "last_reviewed_at": r.last_reviewed_at,
                "next_review_at": r.next_review_at,
            }
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Progress DB read failed for %s/%s: %s", user_id, topic_id, exc)
        return None


def _upsert_db(user_id: str, topic_id: str, fields: dict) -> None:
    from db_models import ProgressRecord
    from db_session import get_session

    db = get_session()
    try:
        r = db.query(ProgressRecord).filter(
            ProgressRecord.user_id == user_id,
            ProgressRecord.topic_id == topic_id,
        ).first()
        if r is None:
            r = ProgressRecord(id=str(uuid.uuid4()), user_id=user_id, topic_id=topic_id)
            db.add(r)
        for key, value in fields.items():
            setattr(r, key, value)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── JSONL backend (dev/test) ───────────────────────────────────────────────────

def _serialize(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _get_jsonl(user_id: str, topic_id: str) -> Optional[dict]:
    if not PROGRESS_JSONL_PATH.exists():
        return None
    latest: Optional[dict] = None
    with PROGRESS_JSONL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("user_id") == user_id and rec.get("topic_id") == topic_id:
                latest = rec  # last-write-wins
    if latest is None:
        return None
    return {
        "mastery_score": latest["mastery_score"],
        "current_conceptual_diff": latest["current_conceptual_diff"],
        "current_computational_diff": latest["current_computational_diff"],
        "streak": latest["streak"],
        "last_reviewed_at": latest.get("last_reviewed_at"),
        "next_review_at": latest.get("next_review_at"),
    }


def _upsert_jsonl(user_id: str, topic_id: str, fields: dict) -> None:
    PROGRESS_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"user_id": user_id, "topic_id": topic_id}
    record.update({k: _serialize(v) for k, v in fields.items()})
    with PROGRESS_JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
