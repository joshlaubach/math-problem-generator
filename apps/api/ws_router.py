"""
WebSocket router for the Socratic tutor.

Mount in api.py:
    from ws_router import router as ws_router
    app.include_router(ws_router)

Endpoint: ws://host/ws/tutor/{session_id}
Required query params: token, topic_id
Optional query params:  difficulty (1-6, default 3), session_type (1hr|2hr, default 1hr),
                        calculator_mode (none|scientific|graphing|cas, default none)

Close codes used:
  1000  normal close
  1011  internal server error
  4001  auth failure
  4003  access denied (free tier or hint cap)
  4004  topic not found
  4029  monthly quota exhausted
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from agents.answer_checker import check as check_answer
from agents.generator import generate as generate_problem
from agents.hint_scaffolder import get_hint
from agents.schemas import GeneratorInput, HintRequest
from agents.socratic import respond as socratic_respond
import session_orchestrator
import rate_limit
from llm_anthropic_client import LLMTimeoutError

# SECURITY (H1): WebSocket message ceilings. A 2-hour session of genuine
# back-and-forth is well under these; they exist to bound a scripted flood.
MAX_MESSAGES_PER_SESSION = 600
MAX_MESSAGES_PER_MINUTE = 60
from auth_dependencies import get_user_repository
from auth_utils import decode_access_token
from config import AUTH_PROVIDER, JWT_SECRET_KEY, JWT_ALGORITHM
from rl_logger import compute_reward, log_event
from input_mode_heuristics import get_input_mode
from session_quota import (
    check_tutor_quota,
    record_tutor_session,
    record_problem,
)
from topic_registry import TOPIC_REGISTRY
from tracking import Attempt
from repo_factory import get_attempt_repository as factory_get_attempt_repository
from users_models import User
from ws_session import (
    GRACE_PERIOD_SECONDS,
    TutorSession,
    create_session,
    delete_session,
    get_session,
    is_in_grace_period,
    seconds_remaining,
    update_session,
)

router = APIRouter(tags=["tutor"])


# ── Auth helper ───────────────────────────────────────────────────────────────

async def _authenticate_ws_token(token: Optional[str], session_id: Optional[str] = None) -> User:
    """
    Validate a bearer token passed as a query param.
    Supports both JWT (AUTH_PROVIDER=jwt), Clerk (AUTH_PROVIDER=clerk),
    and short-lived guest tokens (Phase 2.2).
    Raises ValueError with a human-readable message on failure.
    """
    if not token:
        raise ValueError("Missing auth token")

    # ── Guest token fast-path ─────────────────────────────────────────────────
    payload = decode_access_token(token, secret_key=JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    if payload and payload.get("guest") is True:
        guest_id = payload.get("guest_id")
        token_session_id = payload.get("session_id")
        if not guest_id:
            raise ValueError("Malformed guest token")
        if session_id and token_session_id and token_session_id != session_id:
            raise ValueError("Guest token does not match this session")
        # Synthetic User — no DB record
        return User(
            id=guest_id,
            email="guest@demo",
            password_hash="",
            role="student",
            created_at=datetime.now(timezone.utc),
            is_active=True,
            age_confirmed=True,
            tier="free",
        )

    user_repo = get_user_repository()

    import config as _cfg
    if _cfg.AUTH_PROVIDER == "clerk":
        from clerk_auth import verify_clerk_token, fetch_clerk_user_email
        payload = verify_clerk_token(token)
        if payload is None:
            raise ValueError("Invalid or expired Clerk token")
        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise ValueError("Invalid token payload")
        user = user_repo.get_user_by_clerk_id(clerk_user_id)
        if user is None:
            # JIT provision
            from auth_dependencies import _provision_clerk_user
            user = _provision_clerk_user(clerk_user_id, user_repo, fetch_clerk_user_email)
    else:
        payload = decode_access_token(token, secret_key=JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        if payload is None:
            raise ValueError("Invalid or expired token")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload")
        user = user_repo.get_user_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

    if not user.is_active:
        raise ValueError("Inactive user")
    if not user.age_confirmed:
        raise ValueError("Age verification required")
    return user


# ── Outgoing message helpers ──────────────────────────────────────────────────

async def _send(ws: WebSocket, **kwargs) -> None:
    try:
        await ws.send_json(kwargs)
    except Exception:
        pass


async def _close_with_error(ws: WebSocket, code: int, message: str) -> None:
    await _send(ws, type="error", code=code, message=message)
    try:
        await ws.close(code=code)
    except Exception:
        pass


# ── Lesson helpers ───────────────────────────────────────────────────────────

async def _fetch_worked_example(topic_id: str) -> Optional[list]:
    """
    Fetch the worked_example array from a cached topic lesson.

    Used during the Demonstrate EDGE phase so the tutor narrates the
    pre-generated example instead of re-generating one from scratch.
    Returns None if the lesson isn't cached yet (tutor falls back to Socratic).
    """
    from agents.lesson_store import get_lesson

    try:
        data = get_lesson(topic_id)
        if data:
            steps = data.get("worked_example")
            if isinstance(steps, list) and steps:
                return steps
    except Exception:
        pass
    return None


# ── Session end helpers ───────────────────────────────────────────────────────

async def _end_session_early(ws: WebSocket, credit_id: Optional[str]) -> None:
    """Restore credit and close cleanly when session ends before topic is resolved."""
    if credit_id:
        from credit_router import restore_credit
        restore_credit(credit_id)
    try:
        await ws.close(code=1000)
    except Exception:
        pass

async def _end_session(
    ws: Optional[WebSocket],
    session: TutorSession,
    reason: Literal["solved", "student_end", "disconnect", "timeout", "server_error"] = "student_end",
) -> None:
    """Compute reward, log, record attempt, send summary, and clean up."""
    from credit_router import restore_credit
    from ws_session import within_restore_window

    is_demo = getattr(session, "session_tier", "basic") == "demo"
    started = session.started_at
    duration_seconds = (datetime.now(timezone.utc) - started).total_seconds()

    # Failed-session refund policy:
    # - server_error → always restore (our fault, regardless of elapsed time)
    # - disconnect within the restore window → restore (student got nothing)
    # - solved / student_end / timeout → credit was used as intended
    credit_restored = False
    if session.credit_id and (
        reason == "server_error"
        or (reason == "disconnect" and within_restore_window(session))
    ):
        restore_credit(session.credit_id)
        credit_restored = True
    duration_hours = duration_seconds / 3600

    is_correct = session.is_solved
    hints_used = session.hint_level
    reward = compute_reward(is_correct, hints_used)

    log_event(
        session_id=session.session_id,
        user_id=session.user_id,
        topic_id=session.topic_id,
        difficulty=session.difficulty,
        event_type="timeout" if reason == "timeout" else "session_end",
        payload={
            "reason": reason,
            "hints_used": hints_used,
            "attempts": len(session.attempts),
            "duration_seconds": round(duration_seconds, 1),
            "credit_restored": credit_restored,  # audit trail for refund-abuse review
        },
        reward=reward,
    )

    # Record actual tutor hours used
    record_tutor_session(
        user_id=session.user_id,
        session_id=session.session_id,
        duration_hours=duration_hours,
    )

    # Demo sessions: skip all persistence, send a simplified summary, and exit
    if is_demo:
        summary = {
            "hints_used": hints_used,
            "attempts": session.current_index + (1 if session.attempts or is_correct else 0),
            "correct": is_correct,
            "reward": 0,
            "duration_seconds": round(duration_seconds, 1),
            "ai_summary": [],
            "topics_covered": [],
            "per_topic_performance": {},
            "practice_problems": [],
            "problems_solved": session.current_index + (1 if is_correct else 0),
            "queue_total": _queue_length(session),
            "demo": True,
        }
        msg_type = "session_timeout" if reason == "timeout" else "session_end"
        if ws is not None:
            await _send(ws, type=msg_type, summary=summary)
        delete_session(session.session_id)
        return

    # Update cross-session misconception tracking based on wrong attempts
    if session.attempts:
        try:
            from concept_taxonomy import labels_for_topic, concept_by_label
            from misconception_service import upsert_concept_error
            topic_labels = labels_for_topic(session.topic_id or "")
            if topic_labels:
                # Distribute error count evenly across relevant topic concepts
                for label in topic_labels[:3]:
                    c = concept_by_label(label)
                    if c:
                        upsert_concept_error(session.user_id, c["id"])
        except Exception:
            pass  # Never block session cleanup

    # Persist attempt record
    try:
        attempt_repo = factory_get_attempt_repository()
        attempt = Attempt(
            user_id=session.user_id,
            problem_id=session.session_id,  # session_id acts as problem_id for tutor sessions
            topic_id=session.topic_id,
            course_id=TOPIC_REGISTRY[session.topic_id].course_id
            if session.topic_id in TOPIC_REGISTRY else "unknown",
            difficulty=session.difficulty,
            is_correct=is_correct,
            timestamp=datetime.now(timezone.utc),
            time_taken_seconds=duration_seconds,
        )
        attempt_repo.save_attempt(attempt)
    except Exception:
        pass  # Don't let attempt persistence block session cleanup

    # Collect topics covered across queue + uploaded problems
    topics_covered: list[str] = []
    for tid in session.topic_ids:
        meta = TOPIC_REGISTRY.get(tid)
        if meta:
            topics_covered.append(meta.topic_name)
    for ft in session.freeform_topics:
        topics_covered.append(ft)
    if not topics_covered and session.topic_id and session.topic_id in TOPIC_REGISTRY:
        topics_covered = [TOPIC_REGISTRY[session.topic_id].topic_name]

    problems_attempted = session.current_index + (1 if session.attempts or is_correct else 0)
    problems_solved = session.current_index + (1 if is_correct else 0)

    # Generate AI session summary (extended for Phase 6)
    from agents.session_summarizer import summarize_session
    try:
        ai_result = await summarize_session(
            topic_name=", ".join(topics_covered) or (session.topic_id or "this topic"),
            mode=session.mode,
            conversation=session.conversation,
            problems_attempted=problems_attempted,
            problems_solved=problems_solved,
            hints_used=hints_used,
            duration_seconds=duration_seconds,
            topics_covered=topics_covered,
            session_summary_bullets=session.session_summary,
        )
    except Exception:
        ai_result = {}

    # Support both old (list) and new (dict) return formats
    if isinstance(ai_result, list):
        ai_bullets = ai_result
        performance_by_topic = {}
        practice_problems = []
    else:
        ai_bullets = ai_result.get("bullets", [])
        performance_by_topic = ai_result.get("per_topic_performance", {})
        practice_problems = ai_result.get("practice_problems", [])

    # Persist mastery deltas (L1/7B). Runs on ALL exit reasons — solved,
    # student_end, timeout, AND disconnect — so closing the laptop mid-session
    # still updates the student model. Summarizer keys performance by topic
    # NAME; map back to topic_ids (freeform topics have no id and are skipped).
    if performance_by_topic:
        try:
            from progress_store import apply_session_results
            name_to_id: dict[str, str] = {}
            for tid in (session.topic_ids or []) + ([session.topic_id] if session.topic_id else []):
                meta = TOPIC_REGISTRY.get(tid)
                if meta:
                    name_to_id[meta.topic_name.strip().lower()] = tid
            performance_by_topic_id = {
                name_to_id[name.strip().lower()]: grade
                for name, grade in performance_by_topic.items()
                if name.strip().lower() in name_to_id
            }
            if performance_by_topic_id:
                apply_session_results(session.user_id, performance_by_topic_id)
        except Exception:
            pass  # Never block session cleanup on the student model

    summary = {
        "hints_used": hints_used,
        "attempts": problems_attempted,
        "correct": is_correct,
        "reward": round(reward, 3),
        "duration_seconds": round(duration_seconds, 1),
        "ai_summary": ai_bullets,
        "topics_covered": topics_covered,
        "per_topic_performance": performance_by_topic,
        "practice_problems": practice_problems,
        "problems_solved": problems_solved,
        "queue_total": _queue_length(session),
    }

    msg_type = "session_timeout" if reason == "timeout" else "session_end"
    if ws is not None:
        await _send(ws, type=msg_type, summary=summary)
    delete_session(session.session_id)

    # Clean up any uploaded files for this session (Phase 3)
    from tutor_router import cleanup_session_uploads
    cleanup_session_uploads(session.session_id)

    # Fire session report email (background, non-blocking)
    asyncio.create_task(_send_session_report_email(
        user_id=session.user_id,
        topic_id=session.topic_id or "",
        tutor_name=session.tutor_name,
        duration_minutes=int(duration_seconds // 60),
        ai_bullets=ai_bullets,
        hints_used=hints_used,
        attempts=len(session.attempts),
        score_pct=int(round(reward * 100)),
    ))


# ── Email helpers ─────────────────────────────────────────────────────────────

async def _send_session_report_email(
    user_id: str,
    topic_id: str,
    tutor_name: str,
    duration_minutes: int,
    ai_bullets: list[str],
    hints_used: int,
    attempts: int,
    score_pct: int,
) -> None:
    """Fetch user email and fire session report. Silently swallowed on error."""
    try:
        from email_service import send_session_report
        user_repo = get_user_repository()
        user = user_repo.get_user_by_id(user_id)
        if not user or not user.email:
            return
        topic_name = TOPIC_REGISTRY[topic_id].topic_name if topic_id in TOPIC_REGISTRY else topic_id
        send_session_report(
            user_email=user.email,
            user_name=user.email,
            topic_name=topic_name,
            tutor_name=tutor_name,
            duration_minutes=duration_minutes,
            summary_bullets=ai_bullets,
            hints_used=hints_used,
            attempts=attempts,
            score_pct=score_pct,
        )
    except Exception:
        pass


# ── Context compression ───────────────────────────────────────────────────────

async def _compress_conversation(session: TutorSession) -> None:
    """
    Background task: summarise the current problem's conversation into a bullet,
    append to session.session_summary, then trim conversation to last 20 turns.
    Silently swallowed on any error — must never block the session.
    """
    MAX_VERBATIM_TURNS = 20
    MAX_SUMMARY_BULLETS = 10

    try:
        from agents.session_summarizer import summarize_session
        from topic_registry import TOPIC_REGISTRY

        if not session.conversation:
            return

        topic_name = (
            TOPIC_REGISTRY[session.topic_id].topic_name
            if session.topic_id in TOPIC_REGISTRY
            else session.topic_id or "this topic"
        )
        bullets = await summarize_session(
            topic_name=topic_name,
            mode=session.mode,
            conversation=session.conversation,
            problems_attempted=len(session.attempts) + (1 if session.is_solved else 0),
            problems_solved=1 if session.is_solved else 0,
            hints_used=session.hint_level,
            duration_seconds=0,  # not needed for mid-session bullet
        )

        if bullets:
            # Prepend most recent bullet (keep newest at front)
            session.session_summary = (bullets + session.session_summary)[:MAX_SUMMARY_BULLETS]

        # Trim conversation window
        if len(session.conversation) > MAX_VERBATIM_TURNS:
            session.conversation = session.conversation[-MAX_VERBATIM_TURNS:]

        from ws_session import update_session
        update_session(session)

    except Exception:
        pass  # Silently ignore — compression is best-effort


# ── Timeout background task ───────────────────────────────────────────────────

# Keyed by session_id; value is the asyncio Task running _run_disconnect_timer.
# Cancelled when the student reconnects before the 10-min grace expires.
_disconnect_timers: dict[str, asyncio.Task] = {}

_SAFETY_CAP_SECONDS = 1800  # 30 min beyond nominal end before forcing a hard close


async def _run_session_timer(
    session_id: str,
    websocket: WebSocket,
    max_duration_seconds: int,
) -> None:
    """
    Async background task managing session time limits.

    For demo sessions (session_tier="demo"):
      - At 25min: send demo_warning
      - At 30min: send demo_expired and hard-end

    For normal sessions:
      Phase 1: sleep until 10 min before nominal end, send time_warning.
      Phase 2: sleep through the 10-min grace period, then set
               TutorSession.time_budget_exhausted so the orchestrator closes
               cleanly at the next problem boundary (post-solve).
      Phase 3: if the session is still alive _SAFETY_CAP_SECONDS later, hard-end
               it — prevents runaway sessions from never reaching a boundary.

    Cancelled via task.cancel() when the session ends normally.
    """
    try:
        # ── Demo session timer ────────────────────────────────────────────────
        session = get_session(session_id)
        if session is not None and getattr(session, "session_tier", "basic") == "demo":
            await asyncio.sleep(max(0, max_duration_seconds - 300))  # warn at 25min
            await _send(websocket, type="demo_warning",
                        message="You have 5 minutes left in your free demo session.")
            await asyncio.sleep(300)
            session = get_session(session_id)
            if session is not None:
                await _send(websocket, type="demo_expired")
                await _end_session(websocket, session, reason="timeout")
            try:
                await websocket.close(code=1000)
            except Exception:
                pass
            return

        # ── Phase 1: 10-min warning ───────────────────────────────────────────
        warning_delay = max(0, max_duration_seconds - GRACE_PERIOD_SECONDS)
        await asyncio.sleep(warning_delay)

        session = get_session(session_id)
        if session is None:
            return

        await _send(websocket, type="time_warning", minutes_remaining=10)

        # ── Phase 2: soft budget exhaustion ───────────────────────────────────
        await asyncio.sleep(GRACE_PERIOD_SECONDS)

        session = get_session(session_id)
        if session is None:
            return

        session.time_budget_exhausted = True
        update_session(session)
        # Notify the frontend so it can show a "wrapping up after this problem"
        # indicator — the session doesn't end here, just at the next boundary.
        await _send(websocket, type="session_budget_exhausted")

        # ── Phase 3: absolute safety cap ──────────────────────────────────────
        # If the student is still mid-problem after _SAFETY_CAP_SECONDS, hard-end
        # regardless (e.g., a very long stumble, or frontend never reached boundary).
        await asyncio.sleep(_SAFETY_CAP_SECONDS)

        session = get_session(session_id)
        if session is None:
            return

        await _end_session(websocket, session, reason="timeout")
        try:
            await websocket.close(code=1000)
        except Exception:
            pass

    except asyncio.CancelledError:
        pass  # Normal — cancelled when session ends cleanly


async def _run_disconnect_timer(session_id: str) -> None:
    """
    10-min grace timer started when a student's WS drops unexpectedly.
    If the student reconnects before it fires, it is cancelled by
    _run_reconnect_session. If it fires, the session is ended (credit
    restored since reason="disconnect") and cleaned up.
    """
    try:
        await asyncio.sleep(GRACE_PERIOD_SECONDS)
        session = get_session(session_id)
        if session is None:
            return  # Already cleaned up by another path
        if session.disconnected_at is None:
            return  # Reconnect already cleared the flag
        await _end_session(None, session, reason="disconnect")
    except asyncio.CancelledError:
        pass  # Normal — reconnect cancelled this
    finally:
        _disconnect_timers.pop(session_id, None)


# ── Problem-queue helpers ─────────────────────────────────────────────────────

def _problem_from_queue_or_uploads(session) -> Optional[object]:
    """
    Get the current problem from the queue or uploaded problems.
    Returns a GeneratedProblem, or a bare dict (for uploaded), or None if exhausted.
    """
    from agents.schemas import GeneratedProblem as GP
    idx = session.current_index

    # Uploaded problems (raw dicts) take priority over generated queue
    if session.uploaded_problems:
        if idx < len(session.uploaded_problems):
            raw = session.uploaded_problems[idx]
            # Wrap as GeneratedProblem if possible (uploaded problems are dicts)
            try:
                stmt = raw.get("statement_latex", raw.get("statement", ""))
                return GP(
                    statement=stmt,
                    answer="(see tutor)",  # no canonical answer for uploads
                    worked_steps=[],
                    hint_ladder=["Think about what the problem is asking.", "Try breaking it into steps.", "What formula or technique applies here?", "Apply the method to find the answer."],
                    distractors=[],
                )
            except Exception:
                return None
        return None  # exhausted

    if session.problem_queue:
        if idx < len(session.problem_queue):
            item = session.problem_queue[idx]
            if isinstance(item, GP):
                return item
            if isinstance(item, dict):
                try:
                    return GP(**item)
                except Exception:
                    return None
        return None  # exhausted

    # Single-problem session (legacy or no queue built yet)
    return session.problem


def _queue_length(session) -> int:
    """Total number of problems in the queue (uploaded or generated)."""
    if session.uploaded_problems:
        return len(session.uploaded_problems)
    if session.problem_queue:
        return len(session.problem_queue)
    return 1 if session.problem else 0


def _record_flagged_content(user_id: str, session_id: str, category: str, excerpt: str) -> None:
    """
    Persist a moderation flag (H3) and emit an admin alert. Best-effort: a
    logging/DB failure must never break the student's session or suppress the
    safety response they already received.
    """
    # Always alert, even if the DB write fails — this is the signal Josh needs.
    logger.warning(
        "CONTENT_FLAG category=%s user=%s session=%s excerpt=%r",
        category, user_id, session_id, excerpt,
    )
    try:
        from config import USE_DATABASE
        if not USE_DATABASE:
            return
        from db_models import FlaggedContentRecord
        from db_session import get_session as _get_db
        import uuid as _uuid
        db = _get_db()
        try:
            db.add(FlaggedContentRecord(
                id=str(_uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                category=category,
                excerpt=excerpt,
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to persist flagged content (alert already logged)")


async def _prefetch_problem(session, conceptual_diff: int) -> None:
    """
    Background-generate the next problem at `conceptual_diff` and stash it on
    the session (L2-3). Fired when a streak signals an upcoming difficulty
    change. Single-flight; never raises (best-effort optimization).
    """
    if getattr(session, "prefetch_in_flight", False):
        return
    from ws_session import update_session
    from agents.generator import generate as generate_problem
    from agents.schemas import GeneratorInput
    from problem_bank import save_generated

    topic_id = session.topic_id or (session.topic_ids[0] if session.topic_ids else "")
    meta = TOPIC_REGISTRY.get(topic_id)
    if meta is None:
        return  # freeform/uploaded sessions don't prefetch

    session.prefetch_in_flight = True
    update_session(session)
    try:
        p = await generate_problem(GeneratorInput(
            topic=meta.topic_name, course=meta.course_name, unit=meta.unit_name,
            conceptual_diff=conceptual_diff, computational_diff=conceptual_diff,
            calc_tier="none",
        ))
        try:
            p.problem_id = save_generated(
                p, topic_id=topic_id,
                course_id=getattr(meta, "course_id", "") or "",
                unit_id=getattr(meta, "unit_id", "") or "",
                conceptual_diff=conceptual_diff, computational_diff=conceptual_diff,
            )
        except Exception:
            pass
        session.prefetched = p.dict()
    except Exception as exc:
        logger.warning("Prefetch failed for %s @diff%s: %s", topic_id, conceptual_diff, exc)
    finally:
        session.prefetch_in_flight = False
        update_session(session)


async def _advance_problem(websocket: WebSocket, session, source_label: str = "solved") -> bool:
    """
    Advance to the next problem in the queue.
    Sends `next_problem` or `queue_complete` WS messages.
    Returns True if there is a next problem, False if the queue is exhausted.
    """
    from ws_session import update_session
    from agents.schemas import GeneratedProblem as GP

    # Compress current conversation to session_summary (background)
    asyncio.create_task(_compress_conversation(session))

    session.current_index += 1
    session.hint_level = 0
    session.attempts = []
    session.is_solved = False
    session.consecutive_no_progress = 0
    session.soft_error_count = 0

    # Prefer a background-prefetched problem (difficulty already adapted, L2-3),
    # else fall back to the pre-built queue
    next_problem = None
    if getattr(session, "prefetched", None):
        try:
            next_problem = GP(**session.prefetched)
        except Exception:
            next_problem = None
        session.prefetched = None
    if next_problem is None:
        next_problem = _problem_from_queue_or_uploads(session)

    if next_problem is None:
        # Queue exhausted
        await _send(websocket, type="queue_complete",
                    message="You've worked through all the problems! Let's wrap up.")
        return False

    session.problem = next_problem
    update_session(session)

    # Per-student dedup: a presented bank problem is never re-served to this student
    if getattr(next_problem, "problem_id", None):
        try:
            from session_quota import record_served_problem
            record_served_problem(session.user_id, next_problem.problem_id, session.session_id)
        except Exception:
            pass

    total = _queue_length(session)
    await _send(websocket, type="wb_new_section",
                label=f"Problem {session.current_index + 1}")
    await _send(
        websocket,
        type="next_problem",
        problem={
            "statement": next_problem.statement,
            "answer_type": "expression",
            "hint_ladder_length": len(next_problem.hint_ladder),
        },
        index=session.current_index,
        total=total,
        source=source_label,
    )
    return True


# ── General session ────────────────────────────────────────────────────────────

async def _run_general_session(
    websocket: WebSocket,
    session_id: str,
    session,       # TutorSession (pre-created by REST endpoint)
    user,          # User
    calculator_mode: str = "none",
) -> None:
    """
    Phase 4 general session flow for sessions pre-created via /tutor/session/create.
    """
    from credit_router import consume_credit, restore_credit
    from ws_session import update_session

    is_demo = getattr(session, "session_tier", "basic") == "demo"

    # ── 1. Credit check (skipped for demo sessions) ───────────────────────────
    if not is_demo:
        credit_id = consume_credit(user.id, kind=session.session_type)
        if credit_id is None:
            await _close_with_error(
                websocket, 4029,
                "No session credits available. Purchase credits at /credits/checkout."
            )
            return
        session.credit_id = credit_id

        # ── 2. Anti-abuse ceiling (flat, generous — credits are the real quota)
        requested_hours = 1.0 if session.session_type == "1hr" else 2.0
        allowed, used_hours, limit_hours = check_tutor_quota(
            user.id, user.tier, requested_hours
        )
        if not allowed:
            restore_credit(credit_id)
            await _close_with_error(
                websocket, 4029,
                f"Monthly tutor limit reached ({used_hours:.1f}/{limit_hours:.0f} hrs used). "
                "Limit resets on the 1st of next month."
            )
            return

    # ── 4. Build problem queue ─────────────────────────────────────────────────
    await _send(websocket, type="session_loading", message="Building your problem set…")

    from agents.tutor_engine import (
        build_problem_queue, get_opening_message, generate_tutor_response,
        handle_going_too_fast, check_quiz_readiness,
        get_quiz_proposal, get_quiz_start_message,
    )

    # Build queue (skip if uploads already set uploaded_problems)
    if not session.uploaded_problems:
        try:
            queue = await build_problem_queue(session)
            session.problem_queue = [p.dict() for p in queue] if queue else []
        except Exception as exc:
            session.problem_queue = []

    # Attach cross-session history briefing: misconception labels + weak-topic
    # mastery from the progress store, so the tutor opens with real memory
    try:
        from misconception_service import weak_concepts_briefing
        session.history_briefing = weak_concepts_briefing(user.id)
    except Exception:
        pass
    try:
        from progress_store import weak_topics
        weak = weak_topics(user.id, session.topic_ids or [])
        if weak:
            lines = []
            for tid, mastery in weak[:4]:
                meta = TOPIC_REGISTRY.get(tid)
                if meta:
                    lines.append(f"{meta.topic_name} (mastery {mastery:.0%}, struggled previously)")
            if lines:
                briefing_add = "Topics needing extra care from prior sessions: " + "; ".join(lines)
                session.history_briefing = (
                    f"{session.history_briefing}\n{briefing_add}".strip()
                    if session.history_briefing else briefing_add
                )
    except Exception:
        pass

    # Mark first-ever session (used by should_inject_deep for diagnostic protocol).
    # is_returning gates the opener greeting: only claim "welcome back" when the
    # lookup SUCCEEDS with prior sessions — on failure, default to a neutral intro.
    is_returning = False
    try:
        from session_quota import get_prior_session_count
        prior_count = get_prior_session_count(user.id)
        session.is_first_ever_session = prior_count == 0
        is_returning = prior_count > 0
    except Exception:
        session.is_first_ever_session = False

    # Set first problem
    first_problem = _problem_from_queue_or_uploads(session)
    if first_problem is not None:
        session.problem = first_problem
        record_problem(user.id, session_id, source="live")
        # Per-student dedup: never re-serve a presented bank problem
        if getattr(first_problem, "problem_id", None):
            try:
                from session_quota import record_served_problem
                record_served_problem(user.id, first_problem.problem_id, session_id)
            except Exception:
                pass
    update_session(session)

    max_dur = session.max_duration_seconds

    # ── 5. Get topic names for opening message ─────────────────────────────────
    topic_names: list[str] = []
    for tid in session.topic_ids:
        meta = TOPIC_REGISTRY.get(tid)
        if meta:
            topic_names.append(meta.topic_name)
    for ft in session.freeform_topics:
        topic_names.append(ft)

    # ── 6. Send session_ready ──────────────────────────────────────────────────
    problem_payload = None
    if first_problem:
        problem_payload = {
            "statement": first_problem.statement,
            "answer_type": "expression",
            "hint_ladder_length": len(first_problem.hint_ladder),
        }

    total = _queue_length(session)
    _first_topic_id = session.topic_id or (session.topic_ids[0] if session.topic_ids else None)
    _topic_meta = TOPIC_REGISTRY.get(_first_topic_id or "")
    _default_input_mode = get_input_mode(
        _topic_meta.course_id if _topic_meta else "",
        _topic_meta.unit_id if _topic_meta else None,
    )
    await _send(
        websocket,
        type="session_ready",
        session_id=session_id,
        problem=problem_payload,
        session_type=session.session_type,
        max_duration_seconds=max_dur,
        grace_period_seconds=GRACE_PERIOD_SECONDS,
        index=session.current_index,
        total=total,
        diagnostic_question="",
        default_input_mode=_default_input_mode,
    )

    # ── 7. Opening message ─────────────────────────────────────────────────────
    opening = await get_opening_message(
        session_why=session.why,
        uploaded_problem_count=len(session.uploaded_problems),
        class_name=session.class_name,
        topic_names=topic_names,
        tutor_name=session.tutor_name,
        problem_statement=first_problem.statement if first_problem else None,
        is_returning=is_returning,
    )
    session.conversation.append({"role": "tutor", "content": opening})
    await _send(websocket, type="agent_text", text=opening)

    # ── 8. Timer ───────────────────────────────────────────────────────────────
    timer_task = asyncio.create_task(
        _run_session_timer(session_id, websocket, max_dur)
    )

    # ── 9. Message loop ────────────────────────────────────────────────────────
    await _run_message_loop(websocket, session_id, user, timer_task)


# ── Shared message loop ───────────────────────────────────────────────────────

async def _run_message_loop(
    websocket: WebSocket,
    session_id: str,
    user,
    timer_task: asyncio.Task,
) -> None:
    """
    Receive → orchestrate → send loop shared by new and reconnected sessions.

    On WebSocketDisconnect: soft disconnect — marks disconnected_at, keeps the
    session alive in Redis, and starts a 10-min timer. Reconnect cancels the
    timer; expiry ends the session and restores the credit.
    On server error: hard end (credit always restored).
    """
    from agents.tutor_engine import (
        generate_tutor_response, handle_going_too_fast,
        check_quiz_readiness, get_quiz_proposal, get_quiz_start_message,
    )
    from agents.tutor_guide import looks_like_correction

    try:
        while True:
            raw = await websocket.receive_json()

            session = get_session(session_id)
            if session is None:
                break

            # ── SECURITY (H1): message rate limits ───────────────────────────
            session.message_count += 1
            if session.message_count > MAX_MESSAGES_PER_SESSION:
                timer_task.cancel()
                await _close_with_error(
                    websocket, 4029,
                    "Session message limit reached. Please start a new session.",
                )
                break
            _allowed, _ = rate_limit.hit(
                f"ws:{user.id}", MAX_MESSAGES_PER_MINUTE, 60
            )
            if not _allowed:
                await _send(
                    websocket, type="error", code=4029,
                    message="You're sending messages too quickly. Please slow down.",
                )
                continue

            # Resolve dependencies from the (test-patchable) current module state
            deps = session_orchestrator.SessionDeps(
                generate_tutor_response=generate_tutor_response,
                handle_going_too_fast=handle_going_too_fast,
                check_quiz_readiness=check_quiz_readiness,
                get_quiz_proposal=get_quiz_proposal,
                get_quiz_start_message=get_quiz_start_message,
                check_answer=check_answer,
                get_hint=get_hint,
                log_event=log_event,
                update_session=update_session,
                looks_like_correction=looks_like_correction,
                user_tier=user.tier,
            )

            result = await session_orchestrator.handle(session, user, raw, deps)

            for msg in result.messages:
                await _send(websocket, type=msg.type, **msg.payload)

            # SECURITY (H3): a flagged message → persist for admin review + alert.
            if result.flagged is not None:
                _record_flagged_content(
                    user.id, session_id, result.flagged.category, result.flagged.excerpt
                )

            # Background-generate the next problem at a new difficulty (L2-3).
            if result.prefetch is not None:
                asyncio.create_task(
                    _prefetch_problem(session, result.prefetch.conceptual_diff)
                )

            if result.end_session is not None:
                timer_task.cancel()
                await _end_session(websocket, session, reason=result.end_session)
                break

            if result.advance is not None:
                has_next = await _advance_problem(
                    websocket, session, source_label=result.advance.source_label
                )
                if not has_next:
                    timer_task.cancel()
                    await _end_session(
                        websocket, session, reason=result.advance.exhausted_reason
                    )
                    break

    except WebSocketDisconnect:
        timer_task.cancel()
        session = get_session(session_id)
        if session is not None:
            # Phase 1.5: soft disconnect — keep session alive for 10 min.
            # Reconnect cancels the timer; expiry ends the session.
            session.disconnected_at = datetime.now(timezone.utc)
            update_session(session)
            task = asyncio.create_task(_run_disconnect_timer(session_id))
            _disconnect_timers[session_id] = task
    except LLMTimeoutError:
        # The AI tutor did not respond in time — restore the credit and close
        # gracefully so the student knows this is our fault, not theirs.
        logger.error("LLM timeout in session %s — ending session and refunding credit", session_id)
        timer_task.cancel()
        session = get_session(session_id)
        if session is not None:
            try:
                await _send(
                    websocket,
                    type="error",
                    message="The tutor is taking too long to respond. Your session credit has been restored. Please try again.",
                )
            except Exception:
                pass
            await _end_session(websocket, session, reason="server_error")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    except Exception:
        # Unhandled server-side failure: always restore the credit (our fault)
        logger.exception("Server error in session %s", session_id)
        timer_task.cancel()
        session = get_session(session_id)
        if session is not None:
            await _end_session(websocket, session, reason="server_error")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


# ── Reconnect session ─────────────────────────────────────────────────────────

async def _run_reconnect_session(
    websocket: WebSocket,
    session_id: str,
    session: TutorSession,
    user,
    calculator_mode: str = "none",
) -> None:
    """
    Resume a session after a WebSocket drop (disconnected_at is set on `session`).
    Cancels the pending disconnect timer, clears the flag, sends session_ready
    with remaining time + a short resume line, then re-enters the message loop.
    """
    from agents.tutor_engine import generate_tutor_response

    # Cancel the pending end-session timer
    pending = _disconnect_timers.pop(session_id, None)
    if pending:
        pending.cancel()

    # Clear disconnect flag
    session.disconnected_at = None
    update_session(session)

    # Compute remaining time so the frontend's countdown is accurate
    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
    nominal_remaining = max(0, int(session.max_duration_seconds - elapsed))
    # Total remaining = nominal + grace (what the frontend countdown shows)
    seconds_remaining_total = max(0, int(session.max_duration_seconds + GRACE_PERIOD_SECONDS - elapsed))

    current_problem = _problem_from_queue_or_uploads(session)
    problem_payload = None
    if current_problem:
        problem_payload = {
            "statement": current_problem.statement,
            "answer_type": "expression",
            "hint_ladder_length": len(current_problem.hint_ladder),
        }

    total = _queue_length(session)
    await _send(
        websocket,
        type="session_ready",
        session_id=session_id,
        problem=problem_payload,
        session_type=session.session_type,
        max_duration_seconds=session.max_duration_seconds,
        grace_period_seconds=GRACE_PERIOD_SECONDS,
        seconds_remaining=seconds_remaining_total,
        index=session.current_index,
        total=total,
        is_reconnect=True,
    )

    # Brief resume line from the tutor
    try:
        resume_msg, _ = await generate_tutor_response(
            session,
            "[RECONNECT: The student just reconnected after a brief disconnect. "
            "Give a warm one-sentence welcome back — acknowledge the drop without "
            "making it a big deal, then remind them where we left off.]",
        )
    except Exception:
        resume_msg = "Hey, you're back — let's pick up where we left off!"

    session.conversation.append({"role": "tutor", "content": resume_msg})
    update_session(session)
    await _send(websocket, type="agent_text", text=resume_msg)

    # Restart the session timer with remaining time
    timer_task = asyncio.create_task(
        _run_session_timer(session_id, websocket, nominal_remaining)
    )

    await _run_message_loop(websocket, session_id, user, timer_task)


# ── Legacy session ─────────────────────────────────────────────────────────────

async def _run_legacy_session(
    websocket: WebSocket,
    session_id: str,
    topic_id: Optional[str],
    difficulty: int,
    session_type: Literal["1hr", "2hr"],
    calculator_mode: str,
    tutor_name: str,
    user,
) -> None:
    """
    Original discovery-based session flow (topic_id via query param).
    Preserved for backward compatibility with old client code.
    """
    # ── 2. Credit check (tutor access is credits-only; tier plays no role) ────
    from credit_router import consume_credit, restore_credit
    credit_id = consume_credit(user.id, kind=session_type)
    if credit_id is None:
        await _close_with_error(
            websocket, 4029,
            "No session credits available. Purchase credits at /credits/checkout."
        )
        return

    # ── 3. Anti-abuse ceiling (flat, generous — credits are the real quota) ───
    requested_hours = 1.0 if session_type == "1hr" else 2.0
    allowed, used_hours, limit_hours = check_tutor_quota(
        user.id, user.tier, requested_hours
    )
    if not allowed:
        restore_credit(credit_id)
        await _close_with_error(
            websocket, 4029,
            f"Monthly tutor limit reached ({used_hours:.1f}/{limit_hours:.0f} hrs used). "
            f"Limit resets on the 1st of next month."
        )
        return

    # ── 4. Discovery mode ─────────────────────────────────────────────────────
    resolved_topic_id = topic_id
    resolved_mode = "practice"

    if not topic_id:
        await _send(
            websocket,
            type="discovery_start",
            prompt="Hi! I'm your math tutor. What would you like to work on today?",
        )

        from agents.topic_detector import detect_topic, build_picklist

        discovery_conversation: list[dict] = []
        max_discovery_turns = 4
        turns = 0

        while turns < max_discovery_turns:
            try:
                raw = await websocket.receive_json()
            except Exception:
                await _end_session_early(websocket, credit_id)
                return

            msg_type = raw.get("type", "")

            if msg_type == "topic_accept":
                resolved_topic_id = raw.get("topic_id")
                resolved_mode = raw.get("mode", "practice")
                break
            if msg_type == "topic_reject":
                await _send(websocket, type="discovery_start",
                    prompt="No problem! Can you tell me more about what you need help with?")
                turns += 1
                continue
            if msg_type == "session_end":
                await _end_session_early(websocket, credit_id)
                return
            if msg_type == "student_text":
                text = str(raw.get("text", "")).strip()[:2000]
                if not text:
                    continue
                discovery_conversation.append({"role": "student", "content": text})
                result = await detect_topic(text, discovery_conversation, TOPIC_REGISTRY)
                confidence = result.get("confidence", 0.0)
                if confidence >= 0.6 and result.get("topic_id"):
                    await _send(websocket, type="topic_confirm",
                        topic_id=result["topic_id"], topic_name=result["topic_name"],
                        mode=result["mode"], message=result["confirmation_message"])
                    discovery_conversation.append({"role": "tutor",
                        "content": result["confirmation_message"]})
                else:
                    picklist = build_picklist(TOPIC_REGISTRY, text)
                    if picklist:
                        await _send(websocket, type="topic_picklist",
                            message="I'm not quite sure which topic. Could you pick from these?",
                            options=picklist)
                    else:
                        await _send(websocket, type="discovery_start",
                            prompt="I want to help, but I need a bit more info. What subject or concept is this about?")
                turns += 1

        if not resolved_topic_id:
            await _close_with_error(websocket, 4004,
                "Could not identify topic. Please try selecting from the catalog.")
            restore_credit(credit_id)
            return

    # ── 5. Topic lookup ───────────────────────────────────────────────────────
    topic_meta = TOPIC_REGISTRY.get(resolved_topic_id)
    if topic_meta is None:
        await _close_with_error(websocket, 4004, f"Topic {resolved_topic_id!r} not found")
        restore_credit(credit_id)
        return

    # ── 6. Generate problem ───────────────────────────────────────────────────
    conceptual_diff = max(1, min(5, round(difficulty * 5 / 6)))
    gen_input = GeneratorInput(
        topic=topic_meta.topic_name,
        course=topic_meta.course_name,
        unit=topic_meta.unit_name,
        conceptual_diff=conceptual_diff,
        computational_diff=conceptual_diff,
        calc_tier=calculator_mode if calculator_mode in ("none", "scientific", "graphing", "cas") else "none",
    )
    try:
        problem = await generate_problem(gen_input)
    except Exception as exc:
        await _close_with_error(websocket, 1011, f"Problem generation failed: {exc}")
        return

    record_problem(user.id, session_id, source="live")

    # ── 7. EDGE diagnostic ────────────────────────────────────────────────────
    from agents.edge_assessor import assess_entry_phase
    try:
        edge_result = await assess_entry_phase(
            topic_name=topic_meta.topic_name,
            course_name=topic_meta.course_name,
            mode=resolved_mode,
            student_message="",
            conversation_history=[],
        )
        diagnostic_question = edge_result.get("diagnostic_question", "")
        edge_phase = edge_result.get("phase", "guide")
    except Exception:
        diagnostic_question = ""
        edge_phase = "guide"

    worked_example = None
    if edge_phase == "demonstrate" and resolved_topic_id:
        worked_example = await _fetch_worked_example(resolved_topic_id)

    # ── 8. Create session ─────────────────────────────────────────────────────
    from ws_session import SESSION_TYPES
    max_dur = SESSION_TYPES[session_type]

    _VALID_TUTOR_NAMES = {"Josh", "James", "Isaac", "Robert", "Sarah", "Emily", "Natalie"}
    safe_tutor_name = tutor_name if tutor_name in _VALID_TUTOR_NAMES else "Josh"

    from misconception_service import weak_concepts_briefing
    history_briefing = weak_concepts_briefing(user.id)

    # Check if this is the user's very first session (diagnostic protocol gate)
    try:
        from session_quota import get_prior_session_count as _get_prior
        _is_first = _get_prior(user.id) == 0
    except Exception:
        _is_first = False

    try:
        session = create_session(
            session_id=session_id,
            user_id=user.id,
            topic_id=resolved_topic_id,
            difficulty=difficulty,
            session_type=session_type,
            problem=problem,
            credit_id=credit_id,
            mode=resolved_mode,
            tutor_name=safe_tutor_name,
            history_briefing=history_briefing,
        )
    except ValueError as _ve:
        if "already_active" in str(_ve):
            await websocket.close(4029, "You already have an active session. Please end your existing session first.")
            return
        raise
    session.is_first_ever_session = _is_first

    _legacy_meta = TOPIC_REGISTRY.get(resolved_topic_id or "")
    _legacy_input_mode = get_input_mode(
        _legacy_meta.course_id if _legacy_meta else "",
        _legacy_meta.unit_id if _legacy_meta else None,
    )
    await _send(
        websocket,
        type="session_ready",
        session_id=session_id,
        problem={
            "statement": problem.statement,
            "answer_type": "expression",
            "hint_ladder_length": len(problem.hint_ladder),
        },
        session_type=session_type,
        max_duration_seconds=max_dur,
        grace_period_seconds=GRACE_PERIOD_SECONDS,
        diagnostic_question=diagnostic_question,
        worked_example=worked_example,
        default_input_mode=_legacy_input_mode,
    )

    if worked_example and edge_phase == "demonstrate":
        y_cursor = 2
        for i, step in enumerate(worked_example[:8]):
            expr = step.get("expression_latex", "")
            desc = step.get("description_latex", "")
            if expr or desc:
                latex = f"{desc}: {expr}" if (desc and expr) else (desc or expr)
                await _send(websocket, type="whiteboard", action="write",
                            latex=latex, x=2, y=y_cursor)
                y_cursor += 12
                await asyncio.sleep(0.25)

    timer_task = asyncio.create_task(
        _run_session_timer(session_id, websocket, max_dur)
    )

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type", "")

            session = get_session(session_id)
            if session is None:
                break

            # SECURITY (H1): same message ceilings as the general path, so the
            # legacy flow can't be used to bypass per-session/per-user limits.
            session.message_count += 1
            if session.message_count > MAX_MESSAGES_PER_SESSION:
                timer_task.cancel()
                await _close_with_error(
                    websocket, 4029,
                    "Session message limit reached. Please start a new session.",
                )
                break
            _allowed, _ = rate_limit.hit(f"ws:{user.id}", MAX_MESSAGES_PER_MINUTE, 60)
            if not _allowed:
                await _send(websocket, type="error", code=4029,
                            message="You're sending messages too quickly. Please slow down.")
                continue

            if msg_type == "student_text":
                text = str(raw.get("text", "")).strip()[:2000]
                if not text:
                    continue
                log_event(session_id=session_id, user_id=user.id, topic_id=topic_id,
                          difficulty=difficulty, event_type="student_question",
                          payload={"text": text})
                session.conversation.append({"role": "student", "content": text})
                try:
                    reply = await socratic_respond(
                        problem_statement=problem.statement,
                        conversation=session.conversation[:-1],
                        student_message=text,
                        hint_ladder=problem.hint_ladder,
                        hint_level=session.hint_level,
                        wrong_attempts=session.attempts,
                        tutor_name=session.tutor_name,
                        session_summary=session.session_summary,
                        topic_id=session.topic_id,
                        history_briefing=session.history_briefing,
                    )
                except Exception:
                    reply = "Let me think about that. What have you tried so far?"
                session.conversation.append({"role": "tutor", "content": reply})
                await _send(websocket, type="agent_text", text=reply)

            elif msg_type == "answer_submit":
                student_answer = str(raw.get("answer", "")).strip()
                if not student_answer:
                    continue
                result = await check_answer(student_answer, problem.answer)
                log_event(session_id=session_id, user_id=user.id, topic_id=topic_id,
                          difficulty=difficulty, event_type="answer_attempt",
                          payload={"answer": student_answer, "correct": result.correct})
                await _send(websocket, type="answer_result",
                            correct=result.correct,
                            equivalent_form=result.equivalent_form,
                            partial_credit_reason=result.partial_credit_reason)
                if result.correct:
                    session.is_solved = True
                    log_event(session_id=session_id, user_id=user.id, topic_id=topic_id,
                              difficulty=difficulty, event_type="correct",
                              payload={"answer": student_answer})
                    asyncio.create_task(_compress_conversation(session))
                    timer_task.cancel()
                    await _end_session(websocket, session, reason="solved")
                    break
                else:
                    session.attempts.append(student_answer)
                    try:
                        followup = await socratic_respond(
                            problem_statement=problem.statement,
                            conversation=session.conversation,
                            student_message=f"I submitted '{student_answer}' but it was wrong.",
                            hint_ladder=problem.hint_ladder,
                            hint_level=session.hint_level,
                            wrong_attempts=session.attempts,
                            tutor_name=session.tutor_name,
                            session_summary=session.session_summary,
                            topic_id=session.topic_id,
                            history_briefing=session.history_briefing,
                        )
                    except Exception:
                        followup = "That's not quite right. What step do you think went differently?"
                    session.conversation.append({"role": "tutor", "content": followup})
                    await _send(websocket, type="agent_text", text=followup)

            elif msg_type == "hint_request":
                next_level = session.hint_level + 1
                hint_req = HintRequest(
                    problem_id=session_id,
                    hint_ladder=problem.hint_ladder,
                    hint_level=next_level,
                )
                try:
                    hint_text = await get_hint(hint_req, user_tier=user.tier)
                    session.hint_level = next_level
                    log_event(session_id=session_id, user_id=user.id, topic_id=topic_id,
                              difficulty=difficulty, event_type="hint_request",
                              payload={"level": next_level})
                    await _send(websocket, type="hint", text=hint_text,
                                level=next_level, max_level=len(problem.hint_ladder))
                except PermissionError as exc:
                    await _send(websocket, type="error", code=4003, message=str(exc))
                except IndexError:
                    await _send(websocket, type="error", code=4003,
                                message="No more hints available for this problem.")

            elif msg_type == "session_end":
                timer_task.cancel()
                await _end_session(websocket, session, reason="student_end")
                break

    except WebSocketDisconnect:
        timer_task.cancel()
        session = get_session(session_id)
        if session is not None:
            await _end_session(websocket, session, reason="disconnect")
    except Exception:
        # Unhandled server-side failure: always restore the credit (our fault)
        logger.exception("Server error in legacy session %s", session_id)
        timer_task.cancel()
        session = get_session(session_id)
        if session is not None:
            await _end_session(websocket, session, reason="server_error")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.websocket("/ws/tutor/{session_id}")
async def tutor_ws(
    websocket: WebSocket,
    session_id: str,
    topic_id: Optional[str] = Query(None),
    difficulty: int = Query(3, ge=1, le=6),
    session_type: Literal["1hr", "2hr"] = Query("1hr"),
    calculator_mode: str = Query("none"),
    tutor_name: str = Query("Josh"),
) -> None:
    # SECURITY (M3): the auth token is NOT accepted in the URL query string
    # (URLs leak into access logs, proxies, and browser history). The client
    # sends it via Sec-WebSocket-Protocol as ["bearer", "<token>"]; we echo the
    # "bearer" subprotocol on accept.
    subprotocols = websocket.scope.get("subprotocols", []) or []
    token: Optional[str] = None
    accept_subprotocol: Optional[str] = None
    if len(subprotocols) >= 2 and subprotocols[0] == "bearer":
        token = subprotocols[1]
        accept_subprotocol = "bearer"

    await websocket.accept(subprotocol=accept_subprotocol)

    # Auth (pass session_id so guest tokens are validated against the right session)
    try:
        user = await _authenticate_ws_token(token, session_id=session_id)
    except ValueError as exc:
        await _close_with_error(websocket, 4001, str(exc))
        return

    # Route: pre-created session (Phase 4 general flow, or reconnect)
    existing = get_session(session_id)
    if existing is not None and existing.user_id == user.id:
        if existing.disconnected_at is not None:
            # Phase 1.5: student is reconnecting after a WS drop
            await _run_reconnect_session(websocket, session_id, existing, user, calculator_mode)
        else:
            await _run_general_session(websocket, session_id, existing, user, calculator_mode)
    else:
        # Legacy flow (discovery via query param)
        await _run_legacy_session(
            websocket, session_id, topic_id, difficulty,
            session_type, calculator_mode, tutor_name, user,
        )
