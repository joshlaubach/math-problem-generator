"""
WebSocket tutor session store.

Uses Redis (redis.asyncio) when REDIS_URL is set; falls back to an in-process
dict otherwise.  All callers use the same create/get/update/delete API — the
storage backend is transparent.

Keys: tutor:session:{session_id}
TTL:  max_duration + GRACE_PERIOD_SECONDS + 300 (safety margin)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from agents.schemas import GeneratedProblem

logger = logging.getLogger(__name__)

SESSION_TYPES: dict[str, int] = {"1hr": 3600, "2hr": 7200}
GRACE_PERIOD_SECONDS = 600  # 10 min extension after nominal end
CREDIT_RESTORE_WINDOW_SECONDS = 120  # 2 min

_KEY_PREFIX = "tutor:session:"

# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------

_sessions: dict[str, "TutorSession"] = {}
_redis_client = None  # set by init_redis()


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
    hint_level: int = 0
    attempts: list[str] = field(default_factory=list)
    is_solved: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    credit_id: Optional[str] = None
    scratchpad_has_work: bool = False
    mode: str = "practice"             # 'concept'|'homework'|'practice'
    tutor_name: str = "Josh"           # display name injected into Socratic system prompt
    session_summary: list = field(default_factory=list)  # bullet summaries from completed problems
    history_briefing: str = ""         # cross-session weak concept briefing injected at start


# ---------------------------------------------------------------------------
# Redis init (called from api.py startup)
# ---------------------------------------------------------------------------

async def init_redis() -> None:
    global _redis_client
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        logger.debug("REDIS_URL not set — using in-memory session store")
        return
    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
        await _redis_client.ping()
        logger.info("Redis session store connected: %s", redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — falling back to in-memory store", exc)
        _redis_client = None


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _session_to_dict(session: TutorSession) -> dict:
    d = asdict(session)
    # datetime → ISO string
    d["started_at"] = session.started_at.isoformat()
    # GeneratedProblem → dict already via asdict
    return d


def _session_from_dict(d: dict) -> TutorSession:
    d = dict(d)
    d["started_at"] = datetime.fromisoformat(d["started_at"])
    # Re-hydrate GeneratedProblem
    from agents.schemas import GeneratedProblem as GP
    if isinstance(d.get("problem"), dict):
        d["problem"] = GP(**d["problem"])
    return TutorSession(**d)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_session(
    session_id: str,
    user_id: str,
    topic_id: str,
    difficulty: int,
    session_type: Literal["1hr", "2hr"],
    problem: GeneratedProblem,
    credit_id: Optional[str] = None,
    mode: str = "practice",
    tutor_name: str = "Josh",
    history_briefing: str = "",
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
        tutor_name=tutor_name,
        history_briefing=history_briefing,
    )
    _sessions[session_id] = session
    # Redis write is fire-and-forget; done via update_session
    _sync_to_redis(session)
    return session


def get_session(session_id: str) -> Optional[TutorSession]:
    # In-memory first (always authoritative within a process)
    if session_id in _sessions:
        return _sessions[session_id]
    # Try Redis (for cross-process read, though WS is single-process)
    if _redis_client is not None:
        try:
            import asyncio
            data = asyncio.get_event_loop().run_until_complete(
                _redis_client.get(f"{_KEY_PREFIX}{session_id}")
            )
            if data:
                session = _session_from_dict(json.loads(data))
                _sessions[session_id] = session
                return session
        except Exception:
            pass
    return None


def update_session(session: TutorSession) -> None:
    _sessions[session.session_id] = session
    _sync_to_redis(session)


def delete_session(session_id: str) -> Optional[TutorSession]:
    session = _sessions.pop(session_id, None)
    if _redis_client is not None:
        try:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                _redis_client.delete(f"{_KEY_PREFIX}{session_id}")
            )
        except Exception:
            pass
    return session


def within_restore_window(session: TutorSession) -> bool:
    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
    return elapsed < CREDIT_RESTORE_WINDOW_SECONDS


def seconds_remaining(session: TutorSession) -> int:
    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
    hard_deadline = session.max_duration_seconds + GRACE_PERIOD_SECONDS
    remaining = hard_deadline - elapsed
    return max(0, int(remaining))


def is_in_grace_period(session: TutorSession) -> bool:
    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
    return session.max_duration_seconds < elapsed <= session.max_duration_seconds + GRACE_PERIOD_SECONDS


# ---------------------------------------------------------------------------
# Internal Redis sync (best-effort, never raises)
# ---------------------------------------------------------------------------

def _sync_to_redis(session: TutorSession) -> None:
    if _redis_client is None:
        return
    try:
        import asyncio
        ttl = session.max_duration_seconds + GRACE_PERIOD_SECONDS + 300
        payload = json.dumps(_session_to_dict(session), default=str)
        asyncio.get_event_loop().run_until_complete(
            _redis_client.setex(f"{_KEY_PREFIX}{session.session_id}", ttl, payload)
        )
    except Exception as exc:
        logger.debug("Redis write failed (using in-memory fallback): %s", exc)
