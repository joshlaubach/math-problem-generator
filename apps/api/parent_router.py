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
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from auth_dependencies import require_student, get_user_repository
from users_models import User

router = APIRouter(tags=["parent-monitoring"])

# H2 hardening parameters
LINK_CODE_TTL_HOURS = 24
MAX_REDEEM_ATTEMPTS_PER_HOUR = 5   # per IP+user sliding window
MAX_FAILED_ATTEMPTS_PER_CODE = 5   # a code self-destructs after this many misses


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
    """
    Generate a high-entropy, unguessable link code (H2).

    Was `token_urlsafe(6).upper()[:8]` — the .upper() collapsed case and the
    truncation left ~40 bits, brute-forceable. token_urlsafe(16) is 128 bits
    of case-sensitive entropy.
    """
    return secrets.token_urlsafe(16)


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
            expires_at=datetime.now(timezone.utc) + timedelta(hours=LINK_CODE_TTL_HOURS),
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

    from db_models import ParentLinkRecord, ConsentLogRecord
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
            was_confirmed = record.confirmed
            db.delete(record)
            # M4: audit trail when a monitoring relationship is severed. The
            # current launch model is 13+ self-attestation (monitoring link is
            # not the consent gate), so we record the event rather than auto-
            # suspending; when a true parental-consent gate exists, suspension
            # wires in here by clearing the child's age_confirmed.
            if was_confirmed:
                db.add(ConsentLogRecord(
                    id=str(uuid4()), user_id=user.id,
                    event="parent_link_removed", ip_address=None, user_agent=None,
                ))
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
    request: Request,
    user: User = Depends(require_student),
):
    """Parent redeems a link code to connect to a student's account."""
    if not _uses_database():
        return {"ok": True, "student_email": "student@example.com (dev mode)"}

    # SECURITY (H2): throttle redemption per IP+user so the code space cannot be
    # brute-forced to link an attacker to a stranger's (possibly minor's) account.
    import rate_limit
    client_ip = request.client.host if request.client else "unknown"
    allowed, _ = rate_limit.hit(
        f"parent_redeem:{client_ip}:{user.id}", MAX_REDEEM_ATTEMPTS_PER_HOUR, 3600
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many link attempts. Please wait an hour and try again.",
        )

    # Codes are now full-entropy and case-sensitive; do NOT upper-case.
    from db_models import ParentLinkRecord
    db = _get_db()
    try:
        record = (
            db.query(ParentLinkRecord)
            .filter(
                ParentLinkRecord.link_code == code,
                ParentLinkRecord.confirmed.is_(False),
            )
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Invalid or expired link code.")

        # Expired → delete and reject
        now = datetime.now(timezone.utc)
        if record.expires_at is not None and record.expires_at < now:
            db.delete(record)
            db.commit()
            raise HTTPException(status_code=404, detail="Invalid or expired link code.")

        if record.student_id == user.id:
            # Count as a failed attempt and lock out after too many
            record.failed_attempts = (record.failed_attempts or 0) + 1
            if record.failed_attempts >= MAX_FAILED_ATTEMPTS_PER_CODE:
                db.delete(record)
            db.commit()
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
