"""
Email endpoints.

POST /email/schedule-reminder — schedule a session reminder email
  Body: {topic_name, tutor_name, scheduled_at (ISO), session_type}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth_dependencies import require_student
from users_models import User

router = APIRouter(prefix="/email", tags=["email"])


class ScheduleReminderRequest(BaseModel):
    topic_name: str
    tutor_name: str
    scheduled_at: str   # ISO 8601
    session_type: str = "1hr"


@router.post("/schedule-reminder", status_code=200)
def schedule_reminder(
    body: ScheduleReminderRequest,
    user: User = Depends(require_student),
) -> dict:
    """Fire a reminder email (best-effort; never raises)."""
    from email_service import send_session_reminder
    import asyncio

    try:
        send_session_reminder(
            user_email=user.email or "",
            user_name=user.email or "",
            topic_name=body.topic_name,
            tutor_name=body.tutor_name,
            scheduled_at_iso=body.scheduled_at,
            session_type=body.session_type,
        )
    except Exception:
        pass  # Best-effort; never fail the HTTP response

    return {"scheduled": True}
