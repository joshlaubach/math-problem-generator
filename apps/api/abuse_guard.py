"""
Rolling-window abuse detection for student accounts.

Tracks per-user LLM endpoint calls over a 1-hour sliding window via the shared
rate_limit module (Redis-backed across replicas when REDIS_URL is set, in-memory
otherwise). Students who exceed STUDENT_HOURLY_LIMIT enter a TIMED COOLDOWN
(not a permanent suspension) and are throttled until it expires.

Teachers and admins are exempt from all thresholds.
"""
from fastapi import HTTPException

import rate_limit

STUDENT_HOURLY_LIMIT = 30
COOLDOWN_SECONDS = 3600  # 1 hour timed cooldown on breach (was: permanent suspend)
_WINDOW_SECONDS = 3600
_EXEMPT_ROLES = frozenset({"teacher", "admin"})


def check_and_record(user_id: str, role: str, user_repo) -> None:
    """
    Record a call; throttle the user with a timed cooldown if they exceed the
    hourly limit. Raises HTTP 429 while cooling down. Self-heals when the
    cooldown expires — no manual reactivation required.
    """
    if role in _EXEMPT_ROLES:
        return

    remaining = rate_limit.cooldown_remaining(f"abuse:{user_id}")
    if remaining > 0:
        raise HTTPException(
            status_code=429,
            detail=(
                "Unusual activity detected. Please slow down — access resumes in "
                f"about {max(1, remaining // 60)} minute(s)."
            ),
        )

    allowed, _count = rate_limit.hit(f"abuse:{user_id}", STUDENT_HOURLY_LIMIT, _WINDOW_SECONDS)
    if not allowed:
        rate_limit.set_cooldown(f"abuse:{user_id}", COOLDOWN_SECONDS)
        raise HTTPException(
            status_code=429,
            detail=(
                "Unusual activity detected. Access is paused for a short period. "
                "If this seems wrong, contact support."
            ),
        )


def reset_for_testing() -> None:
    """Clear all counters and cooldowns — for use in tests only."""
    rate_limit.reset_for_testing()
