"""
Session Orchestrator (7A) — the business brain of a live tutor session.

Extracted from ws_router.py's message loop so transport (WebSocket framing,
send/receive, connection lifecycle) is separated from logic (which agent
handles a message, EDGE/escalation, exam-mode transitions, hint leveling,
answer dispatch).

Contract — pure logic, no I/O:
- `handle(session, user, raw, deps)` mutates session state and returns a
  HandlerResult describing what the transport should do: an ordered list of
  outbound messages, plus optional `advance` / `end_session` control actions.
- The orchestrator never touches the WebSocket and never sends anything itself.
- All LLM/answer/hint callables arrive via `deps` (dependency injection), so
  the orchestrator is unit-testable without mocking module globals and the
  transport's existing test seams are preserved.

The transport (ws_router) owns: receive_json, sending HandlerResult.messages,
running _advance_problem / _end_session for the control actions, and the
connection-level try/except that maps disconnects and server errors to credit
refunds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


# ── Transport contract ───────────────────────────────────────────────────────

@dataclass
class Outbound:
    """One message for the transport to send, in order."""
    type: str
    payload: dict = field(default_factory=dict)


@dataclass
class Advance:
    """Ask the transport to advance the problem queue after sending messages."""
    source_label: str = "solved"
    exhausted_reason: str = "solved"  # _end_session reason if the queue is empty


@dataclass
class Prefetch:
    """Ask the transport to background-generate the next problem at this difficulty."""
    conceptual_diff: int


@dataclass
class HandlerResult:
    messages: list[Outbound] = field(default_factory=list)
    advance: Optional[Advance] = None
    end_session: Optional[str] = None  # reason → transport ends the session and breaks
    prefetch: Optional[Prefetch] = None  # transport fires async problem generation

    def send(self, type: str, **payload) -> "HandlerResult":
        self.messages.append(Outbound(type=type, payload=payload))
        return self


@dataclass
class SessionDeps:
    """
    Injected callables. ws_router builds this per message by reading its own
    (test-patchable) module globals, so existing characterization-test patch
    points keep working while the orchestrator stays pure.
    """
    generate_tutor_response: Callable[..., Awaitable[tuple[str, bool]]]
    handle_going_too_fast: Callable[[Any], Awaitable[str]]
    check_exam_readiness: Callable[[Any], bool]
    get_exam_mode_proposal: Callable[[Any], Awaitable[str]]
    get_exam_start_message: Callable[[Any], Awaitable[str]]
    check_answer: Callable[[str, str], Awaitable[Any]]
    get_hint: Callable[..., Awaitable[str]]
    log_event: Callable[..., Any]
    update_session: Callable[[Any], Any]
    looks_like_correction: Callable[[str], bool]
    user_tier: str = "free"


# ── Dispatch ─────────────────────────────────────────────────────────────────

async def handle(session: Any, user: Any, raw: dict, deps: SessionDeps) -> HandlerResult:
    """Route one inbound message to its handler. Returns a HandlerResult."""
    msg_type = raw.get("type", "")
    handler = _HANDLERS.get(msg_type)
    if handler is None:
        return HandlerResult()  # unknown message → no-op (transport ignores)
    return await handler(session, user, raw, deps)


# ── In-session adaptive difficulty (L2-3) ────────────────────────────────────

# Streak thresholds: N correct in a row raises difficulty, M wrong lowers it.
CORRECT_STREAK_TO_RAISE = 3
WRONG_STREAK_TO_LOWER = 2
# Prefetch one correct answer BEFORE the raise, so the harder problem is being
# generated in the background while the student finishes the current one.
_PREFETCH_AT_CORRECT_STREAK = CORRECT_STREAK_TO_RAISE - 1


def _current_diff(session) -> int:
    """Current conceptual difficulty (1-5), seeded lazily from intake difficulty."""
    td = getattr(session, "target_diff", 0) or 0
    if td:
        return td
    intake = getattr(session, "difficulty", 3) or 3
    return max(1, min(5, round(intake * 5 / 6)))


def _apply_streak(session, correct: bool) -> Optional[Prefetch]:
    """
    Update streak counters and difficulty after an answer. Returns a Prefetch
    directive when the transport should background-generate the next problem at
    a new difficulty. No-op (and no prefetch) in exam mode — exams give no
    adaptive support. Pure; mutates only session counters/target_diff.
    """
    if getattr(session, "exam_mode", False):
        return None

    cur = _current_diff(session)
    if correct:
        session.correct_streak = getattr(session, "correct_streak", 0) + 1
        session.wrong_streak = 0
        if session.correct_streak == _PREFETCH_AT_CORRECT_STREAK and cur < 5:
            return Prefetch(conceptual_diff=min(5, cur + 1))
        if session.correct_streak >= CORRECT_STREAK_TO_RAISE:
            session.target_diff = min(5, cur + 1)
            session.correct_streak = 0
    else:
        session.wrong_streak = getattr(session, "wrong_streak", 0) + 1
        session.correct_streak = 0
        if session.wrong_streak >= WRONG_STREAK_TO_LOWER and cur > 1:
            session.target_diff = max(1, cur - 1)
            session.wrong_streak = 0
            return Prefetch(conceptual_diff=session.target_diff)
    return None


# ── Handlers ─────────────────────────────────────────────────────────────────

async def _student_text(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    text = str(raw.get("text", "")).strip()
    if not text:
        return res  # empty text → no-op

    deps.log_event(session_id=session.session_id, user_id=user.id,
                   topic_id=session.topic_id, difficulty=session.difficulty,
                   event_type="student_question", payload={"text": text})
    session.conversation.append({"role": "student", "content": text})

    reply, entered_lesson = await deps.generate_tutor_response(session, text)
    session.conversation.append({"role": "tutor", "content": reply})
    session.consecutive_no_progress += 1  # reset on correct answer

    if deps.looks_like_correction(reply):
        session.soft_error_count += 1

    deps.update_session(session)

    if entered_lesson:
        res.send("lesson_start", topic=session.class_name)
    res.send("agent_text", text=reply)
    if entered_lesson:
        res.send("lesson_end")
    return res


async def _answer_submit(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    student_answer = str(raw.get("answer", "")).strip()
    if not student_answer or session.problem is None:
        return res

    result = await deps.check_answer(student_answer, session.problem.answer)
    deps.log_event(session_id=session.session_id, user_id=user.id,
                   topic_id=session.topic_id, difficulty=session.difficulty,
                   event_type="answer_attempt",
                   payload={"answer": student_answer, "correct": result.correct})

    res.send("answer_result", correct=result.correct,
             equivalent_form=result.equivalent_form,
             partial_credit_reason=result.partial_credit_reason)

    # In-session adaptive difficulty: update streaks and maybe prefetch the
    # next problem at a new difficulty in the background
    res.prefetch = _apply_streak(session, result.correct)

    if result.correct:
        session.is_solved = True
        session.consecutive_no_progress = 0
        deps.log_event(session_id=session.session_id, user_id=user.id,
                       topic_id=session.topic_id, difficulty=session.difficulty,
                       event_type="correct", payload={"answer": student_answer})

        if (not session.exam_mode and not session.exam_mode_proposed
                and deps.check_exam_readiness(session)):
            session.exam_mode_proposed = True
            proposal = await deps.get_exam_mode_proposal(session)
            session.conversation.append({"role": "tutor", "content": proposal})
            deps.update_session(session)
            res.send("exam_mode_propose", message=proposal)
        else:
            res.advance = Advance(source_label="solved", exhausted_reason="solved")
    else:
        session.attempts.append(student_answer)
        session.consecutive_no_progress += 1
        try:
            followup, _ = await deps.generate_tutor_response(
                session, f"I submitted '{student_answer}' but it was wrong."
            )
        except Exception:
            followup = "That's not quite right. What step do you think went differently?"
        session.conversation.append({"role": "tutor", "content": followup})
        deps.update_session(session)
        res.send("agent_text", text=followup)
    return res


async def _hint_request(session, user, raw, deps) -> HandlerResult:
    from agents.schemas import HintRequest

    res = HandlerResult()
    if session.exam_mode:
        return res.send("error", code=4003, message="Hints are disabled in exam mode.")
    if session.problem is None:
        return res

    next_level = session.hint_level + 1
    hint_req = HintRequest(
        problem_id=session.session_id,
        hint_ladder=session.problem.hint_ladder,
        hint_level=next_level,
    )
    try:
        hint_text = await deps.get_hint(hint_req, user_tier=deps.user_tier)
        session.hint_level = next_level
        session.consecutive_no_progress += 1
        deps.log_event(session_id=session.session_id, user_id=user.id,
                       topic_id=session.topic_id, difficulty=session.difficulty,
                       event_type="hint_request", payload={"level": next_level})
        deps.update_session(session)
        res.send("hint", text=hint_text, level=next_level,
                 max_level=len(session.problem.hint_ladder))
    except PermissionError as exc:
        res.send("error", code=4003, message=str(exc))
    except IndexError:
        res.send("error", code=4003, message="No more hints available for this problem.")
    return res


async def _walk_me_through(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    session.conversation.append({"role": "student", "content": "Walk me through this."})
    reply, _ = await deps.generate_tutor_response(
        session, "Walk me through this.", force_lesson=True
    )
    session.conversation.append({"role": "tutor", "content": reply})
    deps.update_session(session)
    res.send("lesson_start", topic=session.class_name)
    res.send("agent_text", text=reply)
    res.send("lesson_end")
    return res


async def _going_too_fast(session, user, raw, deps) -> HandlerResult:
    reply = await deps.handle_going_too_fast(session)
    session.conversation.append({"role": "tutor", "content": reply})
    deps.update_session(session)
    return HandlerResult().send("agent_text", text=reply)


async def _next_problem(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    res.advance = Advance(source_label="skip", exhausted_reason="student_end")
    return res


async def _exam_mode_accept(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    session.exam_mode_proposed = False
    session.exam_mode = True
    res.send("wb_clear", snapshot=True)
    start_msg = await deps.get_exam_start_message(session)
    session.conversation.append({"role": "tutor", "content": start_msg})
    deps.update_session(session)
    res.send("exam_mode_active")
    res.send("agent_text", text=start_msg)
    res.advance = Advance(source_label="exam_start", exhausted_reason="student_end")
    return res


async def _wb_student_work(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    work_str = str(raw.get("latex", raw.get("strokes", ""))).strip()
    if not work_str:
        return res
    content = f"[My work]: {work_str[:500]}"
    session.conversation.append({"role": "student", "content": content})
    reply, _ = await deps.generate_tutor_response(session, content)
    session.conversation.append({"role": "tutor", "content": reply})
    deps.update_session(session)
    return res.send("agent_text", text=reply)


async def _student_canvas_snapshot(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    snapshot_b64 = str(raw.get("image_b64", "")).strip()
    snapshot_source = str(raw.get("source", "whiteboard"))
    if not snapshot_b64:
        return res
    problem_stmt = session.problem.statement if session.problem else ""
    from agents.drawing_recognizer import recognize_and_annotate
    result = await recognize_and_annotate(
        snapshot_b64=snapshot_b64,
        problem_statement=problem_stmt,
        tutor_name=session.tutor_name,
    )
    res.send("agent_text", text=result["chat_text"])
    if result.get("annotation") and snapshot_source == "whiteboard":
        res.send("wb_annotate_student", **result["annotation"])
    session.conversation.append({"role": "tutor", "content": result["chat_text"]})
    deps.update_session(session)
    return res


async def _image_drop(session, user, raw, deps) -> HandlerResult:
    import base64
    import os as _os
    import tempfile
    import logging

    res = HandlerResult()
    image_b64 = str(raw.get("image_b64", "")).strip()
    media_type = str(raw.get("media_type", "image/png"))
    if not image_b64:
        return res
    try:
        ext = ".png" if "png" in media_type else ".jpg"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.write(base64.b64decode(image_b64))
        tmp.close()
        from agents.document_extractor import extract_problems
        extracted = await extract_problems([tmp.name])
        _os.unlink(tmp.name)
    except Exception as exc:
        logging.getLogger(__name__).error("image_drop extraction failed: %s", exc)
        extracted = []
    if extracted:
        stmt = extracted[0]["statement_latex"]
        reply = (
            f"I can see the problem: {stmt}. "
            "Let's work through it. What's the first thing you notice about this?"
        )
    else:
        reply = (
            "I had trouble reading that image clearly. "
            "Can you try uploading it again or describe what the problem says?"
        )
    session.conversation.append({"role": "tutor", "content": reply})
    deps.update_session(session)
    return res.send("agent_text", text=reply)


async def _rag_search(session, user, raw, deps) -> HandlerResult:
    return HandlerResult().send("agent_text", text="Problem library search coming soon.")


async def _session_end(session, user, raw, deps) -> HandlerResult:
    return HandlerResult(end_session="student_end")


_HANDLERS: dict[str, Callable[..., Awaitable[HandlerResult]]] = {
    "student_text": _student_text,
    "answer_submit": _answer_submit,
    "hint_request": _hint_request,
    "walk_me_through": _walk_me_through,
    "going_too_fast": _going_too_fast,
    "next_problem": _next_problem,
    "exam_mode_accept": _exam_mode_accept,
    "wb_student_work": _wb_student_work,
    "student_canvas_snapshot": _student_canvas_snapshot,
    "image_drop": _image_drop,
    "rag_search": _rag_search,
    "session_end": _session_end,
}
