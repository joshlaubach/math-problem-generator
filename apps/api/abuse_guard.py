"""
Rolling-window abuse detection for student accounts.

Tracks per-user LLM endpoint calls over a 1-hour sliding window.
Students who exceed STUDENT_HOURLY_LIMIT are auto-suspended and must
contact support to be reactivated via PATCH /admin/users/{id}.

Teachers and admins are exempt from all thresholds.
"""
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException

_hourly_calls: dict[str, list[float]] = defaultdict(list)

STUDENT_HOURLY_LIMIT = 30
_EXEMPT_ROLES = frozenset({"teacher", "admin"})


def check_and_record(user_id: str, role: str, user_repo) -> None:
    """Record a call; auto-suspend the user if they exceed the hourly limit."""
    if role in _EXEMPT_ROLES:
        return

    now = datetime.now(timezone.utc).timestamp()
    window_start = now - 3600.0

    calls = _hourly_calls[user_id]
    _hourly_calls[user_id] = [t for t in calls if t > window_start]
    _hourly_calls[user_id].append(now)

    if len(_hourly_calls[user_id]) > STUDENT_HOURLY_LIMIT:
        user = user_repo.get_user_by_id(user_id)
        if user and user.is_active:
            user.is_active = False
            user_repo.update_user(user)
        raise HTTPException(
            status_code=429,
            detail=(
                "Unusual activity detected. Your account has been suspended. "
                "Contact support to appeal."
            ),
        )


def reset_for_testing() -> None:
    """Clear all counters — for use in tests only."""
    _hourly_calls.clear()
