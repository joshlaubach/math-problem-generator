"""
Topic lesson store — the single read/write path for cached topic lessons.

Production (USE_DATABASE=true): lessons live in the topic_lessons Postgres
table (db_models.TopicLessonRecord). The container filesystem on Railway is
ephemeral, so the file cache alone would silently vanish on every deploy.

Dev/test (USE_DATABASE=false): lessons live in data/topic_lessons/{id}.json,
same as always.

Read order with DB enabled: DB → file fallback (covers partially migrated
environments) → None. Writes go to the DB when enabled, to the file otherwise.

Callers: api.py /topics/{id}/lesson (read+write), ws_router._fetch_worked_example
(read), tutor_engine._lesson_response (read), scripts/migrate_lessons_to_db.py
(bulk write).
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)

_LESSONS_DIR = DATA_DIR / "topic_lessons"


def _uses_database() -> bool:
    from config import USE_DATABASE
    return USE_DATABASE


# ── Read ───────────────────────────────────────────────────────────────────────

def get_lesson(topic_id: str) -> Optional[dict]:
    """Return the cached lesson dict for a topic, or None if not cached."""
    if _uses_database():
        lesson = _get_from_db(topic_id)
        if lesson is not None:
            return lesson
        # Fall through: partially migrated environment may still have files

    return _get_from_file(topic_id)


def _get_from_db(topic_id: str) -> Optional[dict]:
    try:
        from db_models import TopicLessonRecord
        from db_session import get_session

        db = get_session()
        try:
            record = db.query(TopicLessonRecord).filter(
                TopicLessonRecord.topic_id == topic_id
            ).first()
            return dict(record.content) if record is not None else None
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Lesson DB read failed for %s: %s", topic_id, exc)
        return None


def _get_from_file(topic_id: str) -> Optional[dict]:
    path = _LESSONS_DIR / f"{topic_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Corrupt lesson cache file for %s: %s", topic_id, exc)
        return None


# ── Write ──────────────────────────────────────────────────────────────────────

def save_lesson(topic_id: str, content: dict) -> None:
    """Persist a generated lesson (upsert by topic_id)."""
    if _uses_database():
        _save_to_db(topic_id, content)
    else:
        _save_to_file(topic_id, content)


def _save_to_db(topic_id: str, content: dict) -> None:
    from db_models import TopicLessonRecord
    from db_session import get_session

    db = get_session()
    try:
        record = db.query(TopicLessonRecord).filter(
            TopicLessonRecord.topic_id == topic_id
        ).first()
        if record is None:
            db.add(TopicLessonRecord(topic_id=topic_id, content=content))
        else:
            record.content = content
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _save_to_file(topic_id: str, content: dict) -> None:
    _LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    path = _LESSONS_DIR / f"{topic_id}.json"
    path.write_text(json.dumps(content, indent=2), encoding="utf-8")


# ── Introspection (startup validation, migration verify) ─────────────────────

def lesson_count() -> tuple[int, int]:
    """Return (db_count, file_count) of cached lessons."""
    db_count = 0
    if _uses_database():
        try:
            from db_models import TopicLessonRecord
            from db_session import get_session

            db = get_session()
            try:
                db_count = db.query(TopicLessonRecord).count()
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Lesson DB count failed: %s", exc)

    file_count = (
        sum(1 for _ in _LESSONS_DIR.glob("*.json")) if _LESSONS_DIR.exists() else 0
    )
    return db_count, file_count
