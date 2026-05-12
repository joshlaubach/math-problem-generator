"""
Parent monitoring endpoints.

Students generate a link code → share with parent → parent redeems → gains
read-only access to session summaries and (optionally) transcripts.

POST /me/parent-link          — student generates a link code
POST /parent/link/{code}      — parent redeems code to link accounts
GET  /parent/students         — parent lists their linked students
GET  /parent/students/{id}/sessions — parent views session summaries + transcripts
DELETE /me/parent-link/{parent_id}  — student removes a parent link
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth_dependencies import require_student, get_user_repository
from users_models import User

router = APIRouter(tags=["parent-monitoring"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uses_database() -> bool:
    from config import USE_DATABASE
    return USE_DATABASE


def _get_db():
    from db_session import get_session
    return get_session()


def _generate_link_code() -> str:
    """Generate a human-readable 8-char alphanumeric code."""
    return secrets.token_urlsafe(6).upper()[:8]


# ---------------------------------------------------------------------------
# Student endpoints
# ---------------------------------------------------------------------------

class ParentLinkResponse(BaseModel):
    link_code: str
    expires_hint: str = "Share this code with your parent. They'll enter it at /parent/link/{code}."


@router.post("/me/parent-link", response_model=ParentLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_parent_link(
    user: User = Depends(require_student),
):
    """Generate a one-time link code the student shares with a parent."""
    if not _uses_database():
        # Return a mock code in dev mode
        return ParentLinkResponse(link_code="DEVTEST1")

    from db_models import ParentLinkRecord
    db = _get_db()
    try:
        # Invalidate any existing unconfirmed codes for this student
        existing = (
            db.query(ParentLinkRecord)
            .filter(
                ParentLinkRecord.student_id == user.id,
                ParentLinkRecord.confirmed.is_(False),
            )
            .all()
        )
        for rec in existing:
            db.delete(rec)

        code = _generate_link_code()
        record = ParentLinkRecord(
            id=str(uuid4()),
            parent_id="",  # filled when parent redeems
            student_id=user.id,
            link_code=code,
            confirmed=False,
        )
        db.add(record)
        db.commit()
        return ParentLinkResponse(link_code=code)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.delete("/me/parent-link/{parent_id}", status_code=status.HTTP_200_OK)
async def remove_parent_link(
    parent_id: str,
    user: User = Depends(require_student),
):
    """Student removes a parent from their monitoring list."""
    if not _uses_database():
        return {"ok": True}

    from db_models import ParentLinkRecord
    db = _get_db()
    try:
        record = (
            db.query(ParentLinkRecord)
            .filter(
                ParentLinkRecord.student_id == user.id,
                ParentLinkRecord.parent_id == parent_id,
            )
            .first()
        )
        if record:
            db.delete(record)
            db.commit()
        return {"ok": True}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Parent endpoints
# ---------------------------------------------------------------------------

@router.post("/parent/link/{code}", status_code=status.HTTP_200_OK)
async def redeem_parent_link(
    code: str,
    user: User = Depends(require_student),
):
    """Parent redeems a link code to connect to a student's account."""
    if not _uses_database():
        return {"ok": True, "student_email": "student@example.com (dev mode)"}

    from db_models import ParentLinkRecord
    db = _get_db()
    try:
        record = (
            db.query(ParentLinkRecord)
            .filter(
                ParentLinkRecord.link_code == code.upper(),
                ParentLinkRecord.confirmed.is_(False),
            )
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Invalid or expired link code.")
        if record.student_id == user.id:
            raise HTTPException(status_code=400, detail="You cannot link to your own account.")

        record.parent_id = user.id
        record.confirmed = True
        db.commit()

        # Get student email
        from users_repository import DBUserRepository
        user_repo = DBUserRepository(lambda: db)
        student = user_repo.get_user_by_id(record.student_id)
        student_email = student.email if student else "unknown"

        return {"ok": True, "student_email": student_email}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/parent/students", status_code=status.HTTP_200_OK)
async def list_linked_students(
    user: User = Depends(require_student),
):
    """Parent views all students linked to their account."""
    if not _uses_database():
        return {"students": [], "note": "Parent monitoring requires database mode."}

    from db_models import ParentLinkRecord
    db = _get_db()
    try:
        records = (
            db.query(ParentLinkRecord)
            .filter(
                ParentLinkRecord.parent_id == user.id,
                ParentLinkRecord.confirmed.is_(True),
            )
            .all()
        )
        students = []
        for rec in records:
            students.append({
                "student_id": rec.student_id,
                "linked_at": rec.created_at.isoformat() if rec.created_at else None,
            })
        return {"students": students}
    finally:
        db.close()


@router.get("/parent/students/{student_id}/sessions", status_code=status.HTTP_200_OK)
async def get_student_sessions(
    student_id: str,
    user: User = Depends(require_student),
):
    """
    Parent views session summaries (and transcripts where opted in) for a linked student.

    Only returns sessions where parent_monitor=True.
    """
    if not _uses_database():
        return {"sessions": [], "note": "Session history requires database mode."}

    from db_models import ParentLinkRecord, TutorSessionRecord
    db = _get_db()
    try:
        # Verify parent is linked to this student
        link = (
            db.query(ParentLinkRecord)
            .filter(
                ParentLinkRecord.parent_id == user.id,
                ParentLinkRecord.student_id == student_id,
                ParentLinkRecord.confirmed.is_(True),
            )
            .first()
        )
        if not link:
            raise HTTPException(status_code=403, detail="You are not linked to this student.")

        sessions = (
            db.query(TutorSessionRecord)
            .filter(
                TutorSessionRecord.user_id == student_id,
                TutorSessionRecord.parent_monitor.is_(True),
            )
            .order_by(TutorSessionRecord.started_at.desc())
            .limit(50)
            .all()
        )

        import json
        result = []
        for s in sessions:
            summary = json.loads(s.summary_json) if s.summary_json else None
            transcript = json.loads(s.transcript_json) if s.transcript_json else None
            result.append({
                "session_id": s.id,
                "topic": s.topic_name or s.topic_id,
                "started_at": s.started_at.isoformat(),
                "duration_seconds": s.duration_seconds,
                "problems_solved": s.problems_solved,
                "problems_attempted": s.problems_attempted,
                "summary": summary,
                "transcript": transcript,
            })
        return {"sessions": result}
    except HTTPException:
        raise
    finally:
        db.close()
