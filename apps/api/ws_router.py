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
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from agents.answer_checker import check as check_answer
from agents.generator import generate as generate_problem
from agents.hint_scaffolder import get_hint
from agents.schemas import GeneratorInput, HintRequest
from agents.socratic import respond as socratic_respond
from auth_dependencies import get_user_repository
from auth_utils import decode_access_token
from config import AUTH_PROVIDER, JWT_SECRET_KEY, JWT_ALGORITHM
from rl_logger import compute_reward, log_event
from session_quota import (
    PAID_TIERS,
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
)

router = APIRouter(tags=["tutor"])


# ── Auth helper ───────────────────────────────────────────────────────────────

async def _authenticate_ws_token(token: Optional[str]) -> User:
    """
    Validate a bearer token passed as a query param.
    Supports both JWT (AUTH_PROVIDER=jwt) and Clerk (AUTH_PROVIDER=clerk).
    Raises ValueError with a human-readable message on failure.
    """
    if not token:
        raise ValueError("Missing auth token")

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
    import json
    from config import DATA_DIR

    cache_path = DATA_DIR / "topic_lessons" / f"{topic_id}.json"
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text())
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
    ws: WebSocket,
    session: TutorSession,
    reason: Literal["solved", "student_end", "disconnect", "timeout"] = "student_end",
) -> None:
    """Compute reward, log, record attempt, send summary, and clean up."""
    from credit_router import restore_credit
    from ws_session import within_restore_window

    started = session.started_at
    duration_seconds = (datetime.now(timezone.utc) - started).total_seconds()

    # Restore credit if session ended very early (technical failure, not student quitting)
    if (
        session.credit_id
        and reason == "disconnect"
        and within_restore_window(session)
    ):
        restore_credit(session.credit_id)
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
        },
        reward=reward,
    )

    # Record actual tutor hours used
    record_tutor_session(
        user_id=session.user_id,
        session_id=session.session_id,
        duration_hours=duration_hours,
    )

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

    # Generate AI session summary (non-blocking — use fallback on error)
    from agents.session_summarizer import summarize_session
    try:
        topic_name = TOPIC_REGISTRY[session.topic_id].topic_name if session.topic_id in TOPIC_REGISTRY else session.topic_id or "this topic"
        ai_bullets = await summarize_session(
            topic_name=topic_name,
            mode=session.mode,
            conversation=session.conversation,
            problems_attempted=len(session.attempts) + (1 if is_correct else 0),
            problems_solved=1 if is_correct else 0,
            hints_used=hints_used,
            duration_seconds=duration_seconds,
        )
    except Exception:
        ai_bullets = []

    summary = {
        "hints_used": hints_used,
        "attempts": len(session.attempts),
        "correct": is_correct,
        "reward": round(reward, 3),
        "duration_seconds": round(duration_seconds, 1),
        "ai_summary": ai_bullets,
    }

    msg_type = "session_timeout" if reason == "timeout" else "session_end"
    await _send(ws, type=msg_type, summary=summary)
    delete_session(session.session_id)


# ── Timeout background task ───────────────────────────────────────────────────

async def _run_session_timer(
    session_id: str,
    websocket: WebSocket,
    max_duration_seconds: int,
) -> None:
    """
    Async background task that manages session time limits.
    Sends a 10-minute warning at nominal end, then auto-ends at grace period expiry.
    Cancelled via task.cancel() when the session ends normally.
    """
    try:
        # Sleep until 10 minutes before nominal end
        warning_delay = max(0, max_duration_seconds - GRACE_PERIOD_SECONDS)
        await asyncio.sleep(warning_delay)

        session = get_session(session_id)
        if session is None:
            return

        await _send(websocket, type="time_warning", minutes_remaining=10)

        # Sleep through the grace period
        await asyncio.sleep(GRACE_PERIOD_SECONDS)

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


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.websocket("/ws/tutor/{session_id}")
async def tutor_ws(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
    topic_id: Optional[str] = Query(None),  # Optional — omit to start in discovery mode
    difficulty: int = Query(3, ge=1, le=6),
    session_type: Literal["1hr", "2hr"] = Query("1hr"),
    calculator_mode: str = Query("none"),
) -> None:
    await websocket.accept()

    # ── 1. Auth ───────────────────────────────────────────────────────────────
    try:
        user = await _authenticate_ws_token(token)
    except ValueError as exc:
        await _close_with_error(websocket, 4001, str(exc))
        return

    # ── 2. Tier check ─────────────────────────────────────────────────────────
    if user.tier not in PAID_TIERS:
        await _close_with_error(websocket, 4003, "Tutor Mode requires a paid plan")
        return

    # ── 2b. Session credit check ──────────────────────────────────────────────
    from credit_router import consume_credit, restore_credit
    credit_id = consume_credit(user.id)
    if credit_id is None:
        await _close_with_error(
            websocket, 4029,
            "No session credits available. Purchase credits at /credits/checkout."
        )
        return

    # ── 3. Tutor quota check ──────────────────────────────────────────────────
    requested_hours = 1.0 if session_type == "1hr" else 2.0
    try:
        allowed, used_hours, limit_hours = check_tutor_quota(
            user.id, user.tier, requested_hours
        )
    except ValueError as exc:
        await _close_with_error(websocket, 4003, str(exc))
        return

    if not allowed:
        await _close_with_error(
            websocket, 4029,
            f"Monthly tutor limit reached ({used_hours:.1f}/{limit_hours} hrs used). "
            f"Limit resets on the 1st of next month."
        )
        return

    # ── 4. Discovery mode: resolve topic from conversation ────────────────────
    resolved_topic_id = topic_id
    resolved_mode = "practice"

    if not topic_id:
        # Enter discovery mode — tutor asks what the student needs
        await _send(
            websocket,
            type="discovery_start",
            prompt="Hi! I'm your math tutor. What would you like to work on today?",
        )

        from agents.topic_detector import detect_topic, build_picklist

        # Discovery loop: keep asking until topic is confirmed or student gives up
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
                # Student confirmed the proposed topic
                resolved_topic_id = raw.get("topic_id")
                resolved_mode = raw.get("mode", "practice")
                break

            if msg_type == "topic_reject":
                # Student rejected; ask again
                await _send(websocket, type="discovery_start",
                    prompt="No problem! Can you tell me more about what you need help with?")
                turns += 1
                continue

            if msg_type == "session_end":
                await _end_session_early(websocket, credit_id)
                return

            if msg_type == "student_text":
                text = str(raw.get("text", "")).strip()
                if not text:
                    continue

                discovery_conversation.append({"role": "student", "content": text})
                result = await detect_topic(text, discovery_conversation, TOPIC_REGISTRY)
                confidence = result.get("confidence", 0.0)

                if confidence >= 0.6 and result.get("topic_id"):
                    # High confidence — propose the topic
                    await _send(
                        websocket,
                        type="topic_confirm",
                        topic_id=result["topic_id"],
                        topic_name=result["topic_name"],
                        mode=result["mode"],
                        message=result["confirmation_message"],
                    )
                    # Add as tutor message in discovery conversation
                    discovery_conversation.append({
                        "role": "tutor",
                        "content": result["confirmation_message"],
                    })
                else:
                    # Low confidence — show pick-list
                    picklist = build_picklist(TOPIC_REGISTRY, text)
                    if picklist:
                        await _send(
                            websocket,
                            type="topic_picklist",
                            message="I'm not quite sure which topic. Could you pick from these?",
                            options=picklist,
                        )
                    else:
                        await _send(
                            websocket,
                            type="discovery_start",
                            prompt="I want to help, but I need a bit more info. What subject or concept is this about?",
                        )
                turns += 1

        if not resolved_topic_id:
            await _close_with_error(websocket, 4004, "Could not identify topic. Please try selecting from the catalog.")
            from credit_router import restore_credit
            restore_credit(credit_id)
            return

    # ── 5. Topic lookup ───────────────────────────────────────────────────────
    topic_meta = TOPIC_REGISTRY.get(resolved_topic_id)
    if topic_meta is None:
        await _close_with_error(websocket, 4004, f"Topic {resolved_topic_id!r} not found")
        from credit_router import restore_credit
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

    # ── 7b. Fetch worked_example for Demonstrate phase ────────────────────────
    worked_example = None
    if edge_phase == "demonstrate" and resolved_topic_id:
        worked_example = await _fetch_worked_example(resolved_topic_id)

    # ── 8. Create session + send session_ready ────────────────────────────────
    from ws_session import SESSION_TYPES
    max_dur = SESSION_TYPES[session_type]

    session = create_session(
        session_id=session_id,
        user_id=user.id,
        topic_id=resolved_topic_id,
        difficulty=difficulty,
        session_type=session_type,
        problem=problem,
        credit_id=credit_id,
        mode=resolved_mode,
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
    )

    # ── 9. Start timeout timer ────────────────────────────────────────────────
    timer_task = asyncio.create_task(
        _run_session_timer(session_id, websocket, max_dur)
    )

    # ── 8. Message loop ───────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type", "")

            session = get_session(session_id)
            if session is None:
                break  # Session was cleaned up by timer

            # ── student_text ──────────────────────────────────────────────────
            if msg_type == "student_text":
                text = str(raw.get("text", "")).strip()
                if not text:
                    continue

                log_event(
                    session_id=session_id, user_id=user.id, topic_id=topic_id,
                    difficulty=difficulty, event_type="student_question",
                    payload={"text": text},
                )

                session.conversation.append({"role": "student", "content": text})

                try:
                    reply = await socratic_respond(
                        problem_statement=problem.statement,
                        conversation=session.conversation[:-1],  # exclude just-appended
                        student_message=text,
                        hint_ladder=problem.hint_ladder,
                        hint_level=session.hint_level,
                        wrong_attempts=session.attempts,
                    )
                except Exception:
                    reply = "Let me think about that. What have you tried so far?"

                session.conversation.append({"role": "tutor", "content": reply})
                await _send(websocket, type="agent_text", text=reply)

            # ── answer_submit ─────────────────────────────────────────────────
            elif msg_type == "answer_submit":
                student_answer = str(raw.get("answer", "")).strip()
                if not student_answer:
                    continue

                result = await check_answer(student_answer, problem.answer)

                log_event(
                    session_id=session_id, user_id=user.id, topic_id=topic_id,
                    difficulty=difficulty, event_type="answer_attempt",
                    payload={"answer": student_answer, "correct": result.correct},
                )

                await _send(
                    websocket,
                    type="answer_result",
                    correct=result.correct,
                    equivalent_form=result.equivalent_form,
                    partial_credit_reason=result.partial_credit_reason,
                )

                if result.correct:
                    session.is_solved = True
                    log_event(
                        session_id=session_id, user_id=user.id, topic_id=topic_id,
                        difficulty=difficulty, event_type="correct",
                        payload={"answer": student_answer},
                    )
                    timer_task.cancel()
                    await _end_session(websocket, session, reason="solved")
                    break
                else:
                    session.attempts.append(student_answer)
                    # Socratic follow-up for wrong answer
                    try:
                        followup = await socratic_respond(
                            problem_statement=problem.statement,
                            conversation=session.conversation,
                            student_message=f"I submitted '{student_answer}' but it was wrong.",
                            hint_ladder=problem.hint_ladder,
                            hint_level=session.hint_level,
                            wrong_attempts=session.attempts,
                        )
                    except Exception:
                        followup = "That's not quite right. What step do you think went differently than expected?"

                    session.conversation.append({"role": "tutor", "content": followup})
                    await _send(websocket, type="agent_text", text=followup)

            # ── hint_request ──────────────────────────────────────────────────
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
                    log_event(
                        session_id=session_id, user_id=user.id, topic_id=topic_id,
                        difficulty=difficulty, event_type="hint_request",
                        payload={"level": next_level},
                    )
                    await _send(
                        websocket,
                        type="hint",
                        text=hint_text,
                        level=next_level,
                        max_level=len(problem.hint_ladder),
                    )
                except PermissionError as exc:
                    await _send(websocket, type="error", code=4003, message=str(exc))
                except IndexError:
                    await _send(
                        websocket, type="error", code=4003,
                        message="No more hints available for this problem."
                    )

            # ── session_end ───────────────────────────────────────────────────
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
        timer_task.cancel()
        session = get_session(session_id)
        if session is not None:
            await _end_session(websocket, session, reason="disconnect")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
