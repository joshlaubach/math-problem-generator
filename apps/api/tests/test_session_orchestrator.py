"""
Unit tests for session_orchestrator (7A).

The point of the extraction: business logic is now testable with plain
dependency injection — no WebSocket, no TestClient, no module-global
monkeypatching. These complement test_ws_protocol.py (which proves the
transport wiring) by exercising the decision logic directly.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import session_orchestrator as so
from agents.schemas import GeneratedProblem, WorkedStep, Distractor


def _problem(answer="4"):
    return GeneratedProblem(
        statement="Solve $x+1=5$",
        answer=answer,
        worked_steps=[WorkedStep(step="s", explanation="e")],
        hint_ladder=["h1", "h2", "h3", "h4"],
        distractors=[
            Distractor(answer="a", mistake="m1"),
            Distractor(answer="b", mistake="m2"),
            Distractor(answer="c", mistake="m3"),
        ],
    )


def _session(**over):
    s = SimpleNamespace(
        session_id="s1", topic_id="t1", difficulty=3, class_name="Algebra 2",
        problem=_problem(), conversation=[], attempts=[], hint_level=0,
        is_solved=False, consecutive_no_progress=0, soft_error_count=0,
        exam_mode=False, exam_mode_proposed=False, tutor_name="Josh",
    )
    for k, v in over.items():
        setattr(s, k, v)
    return s


def _deps(**over):
    async def gen(session, message, force_lesson=False):
        return ("LESSON" if force_lesson else "REPLY", force_lesson)

    async def too_fast(session):
        return "SLOW"

    async def proposal(session):
        return "EXAM?"

    async def exam_start(session):
        return "GO"

    async def check(ans, canon):
        return SimpleNamespace(correct=over.get("_correct", False),
                               equivalent_form=False, partial_credit_reason=None)

    async def hint(req, user_tier="free"):
        return "HINT"

    d = so.SessionDeps(
        generate_tutor_response=gen,
        handle_going_too_fast=too_fast,
        check_exam_readiness=lambda s: over.get("_exam_ready", False),
        get_exam_mode_proposal=proposal,
        get_exam_start_message=exam_start,
        check_answer=check,
        get_hint=hint,
        log_event=lambda **k: None,
        update_session=lambda s: None,
        looks_like_correction=lambda r: over.get("_is_correction", False),
        user_tier="free",
    )
    return d


_USER = SimpleNamespace(id="u1", tier="free")


@pytest.mark.asyncio
class TestDispatch:
    async def test_unknown_message_is_noop(self):
        res = await so.handle(_session(), _USER, {"type": "nonsense"}, _deps())
        assert res.messages == [] and res.advance is None and res.end_session is None

    async def test_student_text_appends_turns_and_replies(self):
        s = _session()
        res = await so.handle(s, _USER, {"type": "student_text", "text": "hi"}, _deps())
        assert [m.type for m in res.messages] == ["agent_text"]
        assert s.conversation[-1] == {"role": "tutor", "content": "REPLY"}
        assert s.consecutive_no_progress == 1

    async def test_student_text_empty_noop(self):
        res = await so.handle(_session(), _USER, {"type": "student_text", "text": "  "}, _deps())
        assert res.messages == []

    async def test_correction_increments_soft_errors(self):
        s = _session()
        await so.handle(s, _USER, {"type": "student_text", "text": "x"}, _deps(_is_correction=True))
        assert s.soft_error_count == 1

    async def test_correct_answer_advances(self):
        s = _session()
        res = await so.handle(s, _USER, {"type": "answer_submit", "answer": "4"},
                              _deps(_correct=True, _exam_ready=False))
        assert res.messages[0].type == "answer_result"
        assert res.messages[0].payload["correct"] is True
        assert res.advance is not None
        assert res.advance.source_label == "solved"
        assert s.is_solved is True

    async def test_correct_answer_proposes_exam_when_ready(self):
        s = _session()
        res = await so.handle(s, _USER, {"type": "answer_submit", "answer": "4"},
                              _deps(_correct=True, _exam_ready=True))
        assert [m.type for m in res.messages] == ["answer_result", "exam_mode_propose"]
        assert res.advance is None
        assert s.exam_mode_proposed is True

    async def test_exam_not_reproposed(self):
        s = _session(exam_mode_proposed=True)
        res = await so.handle(s, _USER, {"type": "answer_submit", "answer": "4"},
                              _deps(_correct=True, _exam_ready=True))
        # Already proposed → advance instead of re-proposing
        assert res.advance is not None
        assert all(m.type != "exam_mode_propose" for m in res.messages)

    async def test_wrong_answer_records_attempt_and_followup(self):
        s = _session()
        res = await so.handle(s, _USER, {"type": "answer_submit", "answer": "9"},
                              _deps(_correct=False))
        assert [m.type for m in res.messages] == ["answer_result", "agent_text"]
        assert s.attempts == ["9"]
        assert s.consecutive_no_progress == 1

    async def test_hint_served(self):
        s = _session()
        res = await so.handle(s, _USER, {"type": "hint_request"}, _deps())
        assert res.messages[0].type == "hint"
        assert res.messages[0].payload["level"] == 1
        assert s.hint_level == 1

    async def test_hint_blocked_in_exam(self):
        s = _session(exam_mode=True)
        res = await so.handle(s, _USER, {"type": "hint_request"}, _deps())
        assert res.messages[0].type == "error"
        assert res.messages[0].payload["code"] == 4003
        assert s.hint_level == 0

    async def test_session_end_signals_end(self):
        res = await so.handle(_session(), _USER, {"type": "session_end"}, _deps())
        assert res.end_session == "student_end"

    async def test_skip_advances_with_student_end_exhaust(self):
        res = await so.handle(_session(), _USER, {"type": "next_problem"}, _deps())
        assert res.advance.source_label == "skip"
        assert res.advance.exhausted_reason == "student_end"

    async def test_exam_accept_sequence(self):
        s = _session()
        res = await so.handle(s, _USER, {"type": "exam_mode_accept"}, _deps())
        assert [m.type for m in res.messages] == ["wb_clear", "exam_mode_active", "agent_text"]
        assert res.advance.source_label == "exam_start"
        assert s.exam_mode is True
        assert s.exam_mode_proposed is False

    async def test_walk_me_through_forces_lesson(self):
        s = _session()
        res = await so.handle(s, _USER, {"type": "walk_me_through"}, _deps())
        assert [m.type for m in res.messages] == ["lesson_start", "agent_text", "lesson_end"]
        assert res.messages[1].payload["text"] == "LESSON"

    async def test_going_too_fast(self):
        res = await so.handle(_session(), _USER, {"type": "going_too_fast"}, _deps())
        assert res.messages[0].payload["text"] == "SLOW"
