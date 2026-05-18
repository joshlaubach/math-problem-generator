"""
Cross-session misconception tracking service.

Reads/writes StudentConceptError rows so the Socratic tutor can personalise
its questions based on a student's historically weak concepts.

When USE_DATABASE=False, all calls are silently no-ops.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from concept_taxonomy import concept_by_label


def get_weak_concepts(user_id: str, limit: int = 5) -> list[dict]:
    """
    Return the top `limit` concepts this student has struggled with most.

    Returns a list of dicts: [{concept_id, label, count}]
    """
    from config import USE_DATABASE
    if not USE_DATABASE:
        return []

    from db_models import StudentConceptError
    from db_session import get_session as db_get_session

    db = db_get_session()
    try:
        rows = (
            db.query(StudentConceptError)
            .filter(StudentConceptError.user_id == user_id)
            .order_by(StudentConceptError.count.desc())
            .limit(limit)
            .all()
        )
        result = []
        for row in rows:
            c = concept_by_label(row.concept_id)
            label = c["label"] if c else row.concept_id
            result.append({"concept_id": row.concept_id, "label": label, "count": row.count})
        return result
    except Exception:
        return []
    finally:
        db.close()


def upsert_concept_error(user_id: str, concept_id: str) -> None:
    """Increment the error count for a user+concept pair, inserting if necessary."""
    from config import USE_DATABASE
    if not USE_DATABASE:
        return

    from db_models import StudentConceptError
    from db_session import get_session as db_get_session

    db = db_get_session()
    try:
        row = (
            db.query(StudentConceptError)
            .filter(
                StudentConceptError.user_id == user_id,
                StudentConceptError.concept_id == concept_id,
            )
            .first()
        )
        if row:
            row.count += 1
            row.last_seen_at = datetime.utcnow()
        else:
            db.add(StudentConceptError(
                id=str(uuid.uuid4()),
                user_id=user_id,
                concept_id=concept_id,
                count=1,
                last_seen_at=datetime.utcnow(),
            ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def weak_concepts_briefing(user_id: str) -> str:
    """
    Return a one-paragraph briefing string for injection into the Socratic
    system prompt at session start.  Empty string if no history.
    """
    weak = get_weak_concepts(user_id, limit=5)
    if not weak:
        return ""
    labels = [w["label"] for w in weak]
    return (
        "This student has previously struggled with: "
        + ", ".join(f'"{l}"' for l in labels)
        + ". Watch for these patterns and address them proactively."
    )
