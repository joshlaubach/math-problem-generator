"""
Session quota tracking — monthly tutor hours and problem generation limits.

Stored in data/session_quotas.jsonl (append-only, same pattern as rest of codebase).
Each line is one event record: a tutor session end or a problem generation.

Quota resets on the first day of each calendar month.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

QUOTA_LOG_PATH = Path("data/session_quotas.jsonl")

# Tutor hours per calendar month (wall-clock; 1hr session = 1.0, 2hr = 2.0)
TUTOR_HOUR_LIMITS: dict[str, int] = {
    "student": 6,
    "honors": 12,
    "classroom-student": 10,
}

# Problems per calendar month (bank + live combined)
PROBLEM_MONTH_LIMITS: dict[str, int] = {
    "free": 10,
    "student": 100,
    "honors": 250,
    "classroom-student": 150,
}

# Daily problem cap for free tier only
FREE_DAILY_PROBLEM_LIMIT = 3

PAID_TIERS = {"student", "honors", "classroom-student"}


def _ensure_data_dir() -> None:
    QUOTA_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_records() -> list[dict]:
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


def _append_record(record: dict) -> None:
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
    records = _load_records()
    return sum(
        r.get("duration_hours", 0.0)
        for r in records
        if r.get("type") == "tutor_session"
        and r.get("user_id") == user_id
        and r.get("year_month") == ym
    )


def check_tutor_quota(
    user_id: str,
    tier: str,
    requested_hours: float,
) -> tuple[bool, float, int]:
    """
    Returns (allowed, used_hours, limit_hours).
    allowed = (used + requested) <= limit.
    Raises ValueError if tier is not a paid tier.
    """
    if tier not in PAID_TIERS:
        raise ValueError(f"Tier {tier!r} does not have tutor access")
    limit = TUTOR_HOUR_LIMITS[tier]
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


# ── Problem generation tracking ───────────────────────────────────────────────

def get_problems_used(user_id: str, year_month: Optional[str] = None) -> int:
    ym = year_month or _year_month()
    records = _load_records()
    return sum(
        1 for r in records
        if r.get("type") == "problem"
        and r.get("user_id") == user_id
        and r.get("year_month") == ym
    )


def get_problems_used_today(user_id: str, date_str: Optional[str] = None) -> int:
    today = date_str or _today()
    records = _load_records()
    return sum(
        1 for r in records
        if r.get("type") == "problem"
        and r.get("user_id") == user_id
        and r.get("date") == today
    )


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


# ── Shared ────────────────────────────────────────────────────────────────────

def get_reset_date() -> str:
    """ISO date string of the first day of next month."""
    now = datetime.now(timezone.utc)
    if now.month == 12:
        return f"{now.year + 1}-01-01"
    return f"{now.year}-{now.month + 1:02d}-01"
