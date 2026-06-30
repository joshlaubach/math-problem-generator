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
class Flagged:
    """A moderation hit the transport must persist + alert on (H3)."""
    category: str
    excerpt: str


@dataclass
class HandlerResult:
    messages: list[Outbound] = field(default_factory=list)
    advance: Optional[Advance] = None
    end_session: Optional[str] = None  # reason → transport ends the session and breaks
    prefetch: Optional[Prefetch] = None  # transport fires async problem generation
    flagged: Optional[Flagged] = None  # transport persists FlaggedContentRecord + alerts

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
    check_quiz_readiness: Callable[[Any], bool]
    get_quiz_proposal: Callable[[Any], Awaitable[str]]
    get_quiz_start_message: Callable[[Any], Awaitable[str]]
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


# ── Lesson-cycle cascade (Phase 1.6) ─────────────────────────────────────────

LESSON_CASCADE_THRESHOLD = 3  # lesson cycles on one concept before cascade fires


def _concept_key(session) -> str:
    """Stable key for the current concept — prefer the active problem's topic_id."""
    problem = getattr(session, "problem", None)
    if problem and getattr(problem, "topic_id", None):
        return problem.topic_id
    return getattr(session, "topic_id", "") or ""


def _get_intro_scene(topic_id: str) -> Optional[list]:
    """Return the pre-authored intro scene for a topic, or None (never raises)."""
    if not topic_id:
        return None
    try:
        from agents.intro_scenes import INTRO_SCENES
        scene = INTRO_SCENES.get(topic_id)
        if scene:
            return scene
        # Fallback: check for an intro_scene stored in the lesson cache
        from agents.lesson_store import get_lesson
        lesson = get_lesson(topic_id) or {}
        return lesson.get("intro_scene")
    except Exception:
        return None


def _prereq_names(topic_id: str) -> list[str]:
    """First-degree prerequisite concept names for a topic (best-effort; never raises)."""
    if not topic_id:
        return []
    try:
        from concepts import get_concepts_for_topic, get_concept
        seen: set[str] = set()
        names: list[str] = []
        for concept in get_concepts_for_topic(topic_id):
            for prereq_id in concept.prerequisites:
                if prereq_id not in seen:
                    seen.add(prereq_id)
                    try:
                        names.append(get_concept(prereq_id).name)
                    except Exception:
                        pass
        return names
    except Exception:
        return []


async def _maybe_lesson_cascade(session, deps) -> Optional[HandlerResult]:
    """
    Track lesson cycles for the current concept and fire a cascade at
    LESSON_CASCADE_THRESHOLD cycles:
      - exam < 8h away → honesty close (end session, no blame)
      - otherwise      → prerequisite back-up message + flag in session_summary
    Returns None when below the threshold (no cascade yet).
    """
    key = _concept_key(session)
    counts = getattr(session, "concept_lesson_counts", {}) or {}
    count = counts.get(key, 0) + 1
    counts[key] = count
    session.concept_lesson_counts = counts

    if count < LESSON_CASCADE_THRESHOLD:
        deps.update_session(session)
        return None

    # Only fire the cascade exactly at the threshold, not on every subsequent lesson
    if count > LESSON_CASCADE_THRESHOLD:
        deps.update_session(session)
        return None

    res = HandlerResult()

    # ── Check exam proximity ──────────────────────────────────────────────────
    exam_dt_str = getattr(session, "exam_datetime", None)
    is_exam_soon = False
    if exam_dt_str:
        try:
            from datetime import datetime, timezone
            exam_dt = datetime.fromisoformat(exam_dt_str)
            if exam_dt.tzinfo is None:
                exam_dt = exam_dt.replace(tzinfo=timezone.utc)
            hours_away = (exam_dt - datetime.now(timezone.utc)).total_seconds() / 3600
            is_exam_soon = 0 < hours_away < 8
        except Exception:
            pass

    if is_exam_soon:
        # Honesty close — warm, direct, no blame
        closing = (
            "I want to be straight with you: we've been through this concept a few times "
            "today and it's not clicking yet — and that's completely okay. But it's also "
            "not going to click in the next few hours before your exam. The most useful "
            "thing you can do right now is get a good night's sleep. Rest genuinely helps "
            "your brain consolidate what it's absorbed today. You've worked hard — come "
            "back tomorrow and it'll feel different."
        )
        session.conversation.append({"role": "tutor", "content": closing})
        deps.update_session(session)
        res.send("agent_text", text=closing)
        res.end_session = "student_end"
        return res

    # ── Prerequisite back-up ──────────────────────────────────────────────────
    prereqs = _prereq_names(key)
    if prereqs:
        back_up_msg = (
            f"We've hit this same wall a few times now, and I think the real gap "
            f"is underneath the current material — specifically {prereqs[0]}. "
            f"I'd suggest stepping back and making sure that's solid first. "
            f"Want me to shift us there?"
        )
    else:
        back_up_msg = (
            "We've revisited this concept a few times and I think there's a gap "
            "underneath it that's holding things up. It might help to take a short "
            "break and come back to some prerequisite material before pushing further."
        )

    session.conversation.append({"role": "tutor", "content": back_up_msg})
    session.session_summary.append({
        "type": "concept_flagged",
        "topic_id": key,
        "note": f"Needed {LESSON_CASCADE_THRESHOLD}+ explanation cycles — prerequisite review recommended",
    })
    deps.update_session(session)
    res.send("agent_text", text=back_up_msg)
    return res


# ── In-session adaptive difficulty (L2-3) ─────────────────────────────────────

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
    text = str(raw.get("text", "")).strip()[:2000]
    if not text:
        return res  # empty text → no-op

    # SECURITY (H3): screen for crisis/self-harm BEFORE the LLM. On a hit, the
    # student gets a safety response (never a math deflection), the message is
    # flagged for human review, and the LLM is not called.
    import content_moderation
    verdict = content_moderation.screen(text)
    if verdict.flagged:
        session.conversation.append({"role": "student", "content": text})
        session.conversation.append({"role": "tutor", "content": verdict.response})
        res.flagged = Flagged(category=verdict.category, excerpt=verdict.matched_excerpt or text[:120])
        deps.update_session(session)
        return res.send("agent_text", text=verdict.response)

    # Walkthrough branch: when the student is narrating steps after a wrong answer,
    # route to the dedicated walkthrough handler instead of the normal Socratic turn.
    if getattr(session, "walkthrough_active", False):
        return await _walkthrough_step(session, user, raw, deps)

    deps.log_event(session_id=session.session_id, user_id=user.id,
                   topic_id=session.topic_id, difficulty=session.difficulty,
                   event_type="student_question", payload={"text": text})
    session.conversation.append({"role": "student", "content": text})

    reply, entered_lesson = await deps.generate_tutor_response(session, text)
    session.conversation.append({"role": "tutor", "content": reply})
    session.consecutive_no_progress += 1  # reset on correct answer

    if deps.looks_like_correction(reply):
        session.soft_error_count += 1

    # Per-session token budget tracking
    try:
        from llm_anthropic_client import _last_output_tokens
        from config import SESSION_TOKEN_BUDGET
        session.output_tokens_used = getattr(session, "output_tokens_used", 0) + _last_output_tokens
        if session.output_tokens_used >= SESSION_TOKEN_BUDGET:
            session.time_budget_exhausted = True
    except Exception:
        pass

    deps.update_session(session)

    if entered_lesson:
        # Emit intro diagram once on the very first lesson cycle for this concept (Phase 1.7)
        key = _concept_key(session)
        counts = getattr(session, "concept_lesson_counts", {}) or {}
        if counts.get(key, 0) == 0:
            scene = _get_intro_scene(key)
            if scene:
                res.send("wb_write", scene=scene)
        res.send("lesson_start", topic=session.class_name)
    res.send("agent_text", text=reply)
    if entered_lesson:
        res.send("lesson_end")
        cascade = await _maybe_lesson_cascade(session, deps)
        if cascade:
            res.messages.extend(cascade.messages)
            if cascade.end_session:
                res.end_session = cascade.end_session
    return res


async def _walkthrough_step(session, user, raw, deps) -> HandlerResult:
    """Handle one student-narrated step during step-walkthrough mode.

    The student is walking through their work one step at a time after a wrong answer.
    We inject a STEP_WALKTHROUGH context bracket so the LLM either affirms the step
    ("okay, keep going") or flags it ("wait — look at that") without revealing the error.
    """
    res = HandlerResult()
    text = str(raw.get("text", "")).strip()
    if not text:
        return res

    deps.log_event(
        session_id=session.session_id, user_id=user.id,
        topic_id=session.topic_id, difficulty=session.difficulty,
        event_type="walkthrough_step", payload={"text": text},
    )
    session.conversation.append({"role": "student", "content": text})

    context = (
        "[STEP WALKTHROUGH: The student is narrating their solution one step at a time "
        "after a wrong answer. This is one narrated step. If the step is correct, reply "
        "'okay, keep going' and ask what they did next (2 sentences max). If the step "
        "contains the error, say 'wait — look at that' and ask one focused question about "
        "what they computed — do NOT state what is wrong, do NOT show the correct version. "
        "End with exactly one question.]"
    )
    walkthrough_prompt = f"{context} Student: {text}"

    try:
        reply, _ = await deps.generate_tutor_response(session, walkthrough_prompt)
    except Exception:
        reply = "Okay, keep going — what did you do next?"

    session.conversation.append({"role": "tutor", "content": reply})
    deps.update_session(session)
    return res.send("agent_text", text=reply)


async def _answer_submit(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    student_answer = str(raw.get("answer", "")).strip()
    if not student_answer or session.problem is None:
        return res

    # Any answer submission exits walkthrough mode. A fresh wrong answer below
    # re-activates it when the new severity is careless or method.
    session.walkthrough_active = False

    result = await deps.check_answer(student_answer, session.problem.answer)

    # Classify severity for wrong answers before sending answer_result so the
    # frontend gets severity in the same message that signals incorrect.
    severity: Optional[str] = None
    if not result.correct:
        from agents.severity import classify_severity
        try:
            severity = await classify_severity(
                student_answer,
                session.problem.answer,
                getattr(session.problem, "worked_steps", None) or [],
            )
        except Exception:
            pass

    deps.log_event(session_id=session.session_id, user_id=user.id,
                   topic_id=session.topic_id, difficulty=session.difficulty,
                   event_type="answer_attempt",
                   payload={"answer": student_answer, "correct": result.correct,
                            "severity": severity})

    res.send("answer_result", correct=result.correct,
             equivalent_form=result.equivalent_form,
             partial_credit_reason=result.partial_credit_reason,
             severity=severity)

    # In-session adaptive difficulty: update streaks and maybe prefetch the
    # next problem at a new difficulty in the background
    res.prefetch = _apply_streak(session, result.correct)

    if result.correct:
        session.is_solved = True
        session.consecutive_no_progress = 0
        deps.log_event(session_id=session.session_id, user_id=user.id,
                       topic_id=session.topic_id, difficulty=session.difficulty,
                       event_type="correct", payload={"answer": student_answer})

        # ── Soft session close at problem boundary ────────────────────────────
        # time_budget_exhausted is set by the timer when max_duration elapses;
        # we end here (at a natural boundary) rather than advancing mid-problem.
        if getattr(session, "time_budget_exhausted", False):
            closing = (
                "That's our time for today — great work getting through that one. "
                "I'll send you a session summary by email!"
            )
            session.conversation.append({"role": "tutor", "content": closing})
            deps.update_session(session)
            res.send("agent_text", text=closing)
            res.end_session = "timeout"
            return res

        if (not session.exam_mode and not session.exam_mode_proposed
                and deps.check_quiz_readiness(session)):
            session.exam_mode_proposed = True
            proposal = await deps.get_quiz_proposal(session)
            session.conversation.append({"role": "tutor", "content": proposal})
            deps.update_session(session)
            res.send("quiz_propose", message=proposal)
        else:
            res.advance = Advance(source_label="solved", exhausted_reason="solved")
    else:
        session.attempts.append(student_answer)

        # ── Board routing by severity ─────────────────────────────────────────
        # careless  → no board change, no red highlight (student knows the method)
        # method    → mark incorrect + open a new section for the correct approach
        # fundamental → clear board and start fresh (wb_clear saves a snapshot)
        # None/unknown → mark incorrect only (safe default)
        if severity == "careless":
            pass  # no board change
        elif severity == "method":
            res.send("wb_mark_incorrect")
            res.send("wb_new_section", label="Let's try the right method")
        elif severity == "fundamental":
            res.send("wb_clear", snapshot=True)
        else:
            res.send("wb_mark_incorrect")

        # ── Escalation gating ─────────────────────────────────────────────────
        # careless slips don't count toward the lesson-mode escalation threshold.
        # fundamental gaps skip straight to lesson mode on the followup message.
        if severity != "careless":
            session.consecutive_no_progress += 1
        if severity == "fundamental":
            from agents.tutor_engine import ESCALATION_THRESHOLD
            session.consecutive_no_progress = max(
                session.consecutive_no_progress, ESCALATION_THRESHOLD
            )

        # ── Step-walkthrough activation ───────────────────────────────────────
        # Careless and method errors keep the board legible and the student
        # knows (or nearly knows) the method — narrating steps surfaces the slip
        # without the tutor pointing it out directly.
        if severity in ("careless", "method"):
            session.walkthrough_active = True

        # ── Followup response ─────────────────────────────────────────────────
        # Thread a bracketed context hint into the student message so the tutor
        # LLM adjusts its tone without changing its EDGE framing.
        context_hint = {
            "careless": (
                "The student made a small slip but knows the method. "
                "Do NOT reveal the error. Ask them to narrate their steps one at a time."
            ),
            "method": (
                "The student used the wrong procedure. "
                "Redirect them toward the correct technique without revealing the answer."
            ),
            "fundamental": (
                "The student has a fundamental gap. "
                "Prepare to teach the underlying concept from scratch."
            ),
        }.get(severity or "", "")

        followup_prompt = (
            f"I submitted '{student_answer}' but it was wrong."
            + (f" [Context: {context_hint}]" if context_hint else "")
        )

        try:
            followup, _ = await deps.generate_tutor_response(session, followup_prompt)
        except Exception:
            followup = (
                "Let me see — walk me through what you did, step by step."
                if severity == "careless"
                else "That's not quite right. What step do you think went differently?"
            )
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
    # Intro diagram on first lesson cycle for this concept (Phase 1.7)
    key = _concept_key(session)
    counts = getattr(session, "concept_lesson_counts", {}) or {}
    if counts.get(key, 0) == 0:
        scene = _get_intro_scene(key)
        if scene:
            res.send("wb_write", scene=scene)
    res.send("lesson_start", topic=session.class_name)
    res.send("agent_text", text=reply)
    res.send("lesson_end")
    cascade = await _maybe_lesson_cascade(session, deps)
    if cascade:
        res.messages.extend(cascade.messages)
        if cascade.end_session:
            res.end_session = cascade.end_session
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


async def _quiz_accept(session, user, raw, deps) -> HandlerResult:
    res = HandlerResult()
    session.exam_mode_proposed = False
    session.exam_mode = True
    res.send("wb_clear", snapshot=True)
    start_msg = await deps.get_quiz_start_message(session)
    session.conversation.append({"role": "tutor", "content": start_msg})
    deps.update_session(session)
    res.send("quiz_active")
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
    "quiz_accept": _quiz_accept,
    "wb_student_work": _wb_student_work,
    "student_canvas_snapshot": _student_canvas_snapshot,
    "image_drop": _image_drop,
    "rag_search": _rag_search,
    "session_end": _session_end,
}
