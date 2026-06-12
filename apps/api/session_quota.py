"""
Session quota tracking — monthly tutor hours, problem generation limits,
served-problem dedup, and TTS budgets.

Storage: QuotaEventRecord in Postgres when USE_DATABASE=true (durable across
deploys — Railway's filesystem is ephemeral); data/session_quotas.jsonl in
dev/test. Each record is one event: tutor session end, problem generation,
problem served to a student, or TTS synthesis.

Quota resets on the first day of each calendar month.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

QUOTA_LOG_PATH = Path("data/session_quotas.jsonl")


def _uses_database() -> bool:
    from config import USE_DATABASE
    return USE_DATABASE

# Tutor access is credits-only (launch decision 2026-06-12): owning a credit IS
# the quota. This flat ceiling exists solely to bound abuse (stolen card buying
# unlimited sessions) — it is generous enough that no legitimate student hits it.
ABUSE_CEILING_HOURS_PER_MONTH = 40.0

# Problems per calendar month (bank + live combined)
PROBLEM_MONTH_LIMITS: dict[str, int] = {
    "free": 10,
    "student": 100,
    "honors": 250,
    "classroom-student": 150,
}

# Daily problem cap for free tier only
FREE_DAILY_PROBLEM_LIMIT = 3

# Practice-subscription tiers. NOT used to gate tutor access (credits-only since
# 2026-06-12) — only meaningful for problem-generation quotas above.
PAID_TIERS = {"student", "honors", "classroom-student"}


def _ensure_data_dir() -> None:
    QUOTA_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_records_jsonl() -> list[dict]:
    _ensure_data_dir()
    if not QUOTA_LOG_PATH.exists():
        return []
    records = []
    with QUOTA_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def _query_records(
    rec_type: str,
    user_id: str,
    year_month: Optional[str] = None,
    date: Optional[str] = None,
) -> list[dict]:
    """All events of one type for one user, optionally filtered by period."""
    if _uses_database():
        try:
            from db_models import QuotaEventRecord
            from db_session import get_session

            db = get_session()
            try:
                q = db.query(QuotaEventRecord).filter(
                    QuotaEventRecord.type == rec_type,
                    QuotaEventRecord.user_id == user_id,
                )
                if year_month is not None:
                    q = q.filter(QuotaEventRecord.year_month == year_month)
                if date is not None:
                    q = q.filter(QuotaEventRecord.date == date)
                return [
                    {
                        "type": r.type,
                        "user_id": r.user_id,
                        "problem_id": r.problem_id,
                        "session_id": r.session_id,
                        "duration_hours": r.duration_hours,
                        "chars": r.chars,
                        "source": r.source,
                        "year_month": r.year_month,
                        "date": r.date,
                    }
                    for r in q.all()
                ]
            finally:
                db.close()
        except Exception:
            return []  # quota checks degrade open in prod rather than blocking sessions

    records = _load_records_jsonl()
    return [
        r for r in records
        if r.get("type") == rec_type
        and r.get("user_id") == user_id
        and (year_month is None or r.get("year_month") == year_month)
        and (date is None or r.get("date") == date)
    ]


def _append_record(record: dict) -> None:
    if _uses_database():
        try:
            from db_models import QuotaEventRecord
            from db_session import get_session

            db = get_session()
            try:
                db.add(QuotaEventRecord(
                    id=str(uuid.uuid4()),
                    type=record.get("type", ""),
                    user_id=record.get("user_id", ""),
                    problem_id=record.get("problem_id"),
                    session_id=record.get("session_id"),
                    duration_hours=record.get("duration_hours"),
                    chars=record.get("chars"),
                    source=record.get("source"),
                    year_month=record.get("year_month", _year_month()),
                    date=record.get("date", _today()),
                ))
                db.commit()
                return
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        except Exception:
            pass  # fall through to JSONL so the event is never lost silently

    _ensure_data_dir()
    with QUOTA_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _year_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── Tutor hour tracking ───────────────────────────────────────────────────────

def get_tutor_hours_used(user_id: str, year_month: Optional[str] = None) -> float:
    ym = year_month or _year_month()
    return sum(
        r.get("duration_hours") or 0.0
        for r in _query_records("tutor_session", user_id, year_month=ym)
    )


def check_tutor_quota(
    user_id: str,
    tier: str,
    requested_hours: float,
) -> tuple[bool, float, float]:
    """
    Returns (allowed, used_hours, limit_hours).

    Tutor access is credits-only — tier plays no role in access. This check is
    purely an anti-abuse ceiling (ABUSE_CEILING_HOURS_PER_MONTH), flat for all
    users regardless of tier. The `tier` parameter is retained for call-site
    compatibility and future per-tier ceilings.
    """
    limit = ABUSE_CEILING_HOURS_PER_MONTH
    used = get_tutor_hours_used(user_id)
    allowed = (used + requested_hours) <= limit
    return allowed, used, limit


def record_tutor_session(
    user_id: str,
    session_id: str,
    duration_hours: float,
) -> None:
    """Append a tutor session record. Call at session END with actual duration."""
    _append_record({
        "type": "tutor_session",
        "user_id": user_id,
        "session_id": session_id,
        "duration_hours": round(duration_hours, 4),
        "year_month": _year_month(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def get_prior_session_count(user_id: str) -> int:
    """Return the number of completed tutor sessions ever recorded for this user.

    Used by ws_router to populate TutorSession.is_first_ever_session so the
    diagnostic protocol is injected correctly on a user's very first session.
    """
    return len(_query_records("tutor_session", user_id))


# ── Problem generation tracking ───────────────────────────────────────────────

def get_problems_used(user_id: str, year_month: Optional[str] = None) -> int:
    ym = year_month or _year_month()
    return len(_query_records("problem", user_id, year_month=ym))


def get_problems_used_today(user_id: str, date_str: Optional[str] = None) -> int:
    today = date_str or _today()
    return len(_query_records("problem", user_id, date=today))


def check_problem_quota(user_id: str, tier: str) -> tuple[bool, int, int]:
    """
    Returns (allowed, used_this_month, monthly_limit).
    Free tier also enforces a daily sub-limit of FREE_DAILY_PROBLEM_LIMIT.
    """
    limit = PROBLEM_MONTH_LIMITS.get(tier, PROBLEM_MONTH_LIMITS["free"])
    used = get_problems_used(user_id)

    if used >= limit:
        return False, used, limit

    if tier == "free":
        used_today = get_problems_used_today(user_id)
        if used_today >= FREE_DAILY_PROBLEM_LIMIT:
            return False, used, limit

    return True, used, limit


def record_problem(
    user_id: str,
    problem_id: str,
    source: str,  # "bank" or "live"
) -> None:
    _append_record({
        "type": "problem",
        "user_id": user_id,
        "problem_id": problem_id,
        "source": source,
        "year_month": _year_month(),
        "date": _today(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ── Served-problem dedup (bank-first queue) ───────────────────────────────────
# A separate event type from "problem" so tutor-session serving never counts
# against practice problem quotas. Cross-student problem reuse is fine (every
# textbook does it); the same student seeing a repeat is not.

def record_served_problem(user_id: str, problem_id: str, session_id: str) -> None:
    _append_record({
        "type": "served",
        "user_id": user_id,
        "problem_id": problem_id,
        "session_id": session_id,
        "year_month": _year_month(),
        "date": _today(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def get_served_problem_ids(user_id: str) -> set[str]:
    """All bank problem IDs ever served to this student."""
    return {
        r["problem_id"]
        for r in _query_records("served", user_id)
        if r.get("problem_id")
    }


# ── Voice (TTS) budget tracking ───────────────────────────────────────────────

# Per-user daily TTS character budget (cost control, launch decision
# 2026-06-12). ~100k chars ≈ several full voice-mode sessions; legitimate use
# never hits it, a replay-button-mashing session does.
DAILY_TTS_CHAR_BUDGET = 100_000


def get_tts_chars_today(user_id: str, date_str: Optional[str] = None) -> int:
    today = date_str or _today()
    return sum(
        int(r.get("chars") or 0)
        for r in _query_records("tts", user_id, date=today)
    )


def check_tts_budget(user_id: str, requested_chars: int) -> tuple[bool, int, int]:
    """Returns (allowed, used_today, daily_budget)."""
    used = get_tts_chars_today(user_id)
    return (used + requested_chars) <= DAILY_TTS_CHAR_BUDGET, used, DAILY_TTS_CHAR_BUDGET


def record_tts_chars(user_id: str, chars: int) -> None:
    _append_record({
        "type": "tts",
        "user_id": user_id,
        "chars": int(chars),
        "date": _today(),
        "year_month": _year_month(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ── Shared ────────────────────────────────────────────────────────────────────

def get_reset_date() -> str:
    """ISO date string of the first day of next month."""
    now = datetime.now(timezone.utc)
    if now.month == 12:
        return f"{now.year + 1}-01-01"
    return f"{now.year}-{now.month + 1:02d}-01"
