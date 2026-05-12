"""
In-memory WebSocket tutor session store.

One TutorSession per student-problem interaction. Keyed by session_id (UUID).
Replace _sessions dict with Redis when scaling beyond a single process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from agents.schemas import GeneratedProblem

SESSION_TYPES: dict[str, int] = {"1hr": 3600, "2hr": 7200}
GRACE_PERIOD_SECONDS = 600  # 10 min extension after nominal end

_sessions: dict[str, "TutorSession"] = {}


CREDIT_RESTORE_WINDOW_SECONDS = 120  # 2 minutes


@dataclass
class TutorSession:
    session_id: str
    user_id: str
    topic_id: str
    difficulty: int
    session_type: Literal["1hr", "2hr"]
    max_duration_seconds: int
    problem: GeneratedProblem
    conversation: list[dict] = field(default_factory=list)  # [{role, content}]
    hint_level: int = 0       # 0 = none served; 1-4 = last hint index
    attempts: list[str] = field(default_factory=list)  # wrong answer strings
    is_solved: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    credit_id: Optional[str] = None   # session credit consumed at start
    scratchpad_has_work: bool = False  # True once student submits any scratchpad entry
    mode: str = "practice"             # 'concept'|'homework'|'practice'


def create_session(
    session_id: str,
    user_id: str,
    topic_id: str,
    difficulty: int,
    session_type: Literal["1hr", "2hr"],
    problem: GeneratedProblem,
    credit_id: Optional[str] = None,
    mode: str = "practice",
) -> TutorSession:
    if session_id in _sessions:
        raise ValueError(f"Session {session_id!r} already exists")
    session = TutorSession(
        session_id=session_id,
        user_id=user_id,
        topic_id=topic_id,
        difficulty=difficulty,
        session_type=session_type,
        max_duration_seconds=SESSION_TYPES[session_type],
        problem=problem,
        credit_id=credit_id,
        mode=mode,
    )
    _sessions[session_id] = session
    return session


def within_restore_window(session: TutorSession) -> bool:
    """True if the session started less than 2 minutes ago (credit can be restored)."""
    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
    return elapsed < CREDIT_RESTORE_WINDOW_SECONDS


def get_session(session_id: str) -> Optional[TutorSession]:
    return _sessions.get(session_id)


def update_session(session: TutorSession) -> None:
    # No-op for in-memory dict (object is already mutated in place).
    # Stub exists for Redis-compatibility later.
    _sessions[session.session_id] = session


def delete_session(session_id: str) -> Optional[TutorSession]:
    return _sessions.pop(session_id, None)


def seconds_remaining(session: TutorSession) -> int:
    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
    hard_deadline = session.max_duration_seconds + GRACE_PERIOD_SECONDS
    remaining = hard_deadline - elapsed
    return max(0, int(remaining))


def is_in_grace_period(session: TutorSession) -> bool:
    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
    return session.max_duration_seconds < elapsed <= session.max_duration_seconds + GRACE_PERIOD_SECONDS
