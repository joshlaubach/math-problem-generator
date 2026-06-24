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
        correct_streak=0, wrong_streak=0, target_diff=0,
        prefetched=None, prefetch_in_flight=False,
        walkthrough_active=False,
        time_budget_exhausted=False,
        concept_lesson_counts={},
        exam_datetime=None,
        session_summary=[],
    )
    for k, v in over.items():
        setattr(s, k, v)
    return s


def _deps(**over):
    async def gen(session, message, force_lesson=False):
        el = force_lesson or over.get("_entered_lesson", False)
        return ("LESSON" if el else "REPLY", el)

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
        check_quiz_readiness=lambda s: over.get("_exam_ready", False),
        get_quiz_proposal=proposal,
        get_quiz_start_message=exam_start,
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
        assert [m.type for m in res.messages] == ["answer_result", "quiz_propose"]
        assert res.advance is None
        assert s.exam_mode_proposed is True

    async def test_exam_not_reproposed(self):
        s = _session(exam_mode_proposed=True)
        res = await so.handle(s, _USER, {"type": "answer_submit", "answer": "4"},
                              _deps(_correct=True, _exam_ready=True))
        # Already proposed → advance instead of re-proposing
        assert res.advance is not None
        assert all(m.type != "quiz_propose" for m in res.messages)

    async def test_wrong_answer_records_attempt_and_followup(self):
        s = _session()
        res = await so.handle(s, _USER, {"type": "answer_submit", "answer": "9"},
                              _deps(_correct=False))
        # No ANTHROPIC_API_KEY in tests → severity=None → wb_mark_incorrect is sent
        assert [m.type for m in res.messages] == [
            "answer_result", "wb_mark_incorrect", "agent_text"
        ]
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
        res = await so.handle(s, _USER, {"type": "quiz_accept"}, _deps())
        assert [m.type for m in res.messages] == ["wb_clear", "quiz_active", "agent_text"]
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

    async def test_careless_wrong_sets_walkthrough_active(self, monkeypatch):
        import agents.severity as severity_module
        async def fake_classify(*a, **k):
            return "careless"
        monkeypatch.setattr(severity_module, "classify_severity", fake_classify)
        s = _session()
        res = await so.handle(s, _USER, {"type": "answer_submit", "answer": "5"}, _deps(_correct=False))
        assert s.walkthrough_active is True
        # careless → no board message, just answer_result + agent_text
        assert [m.type for m in res.messages] == ["answer_result", "agent_text"]

    async def test_method_wrong_sets_walkthrough_active(self, monkeypatch):
        import agents.severity as severity_module
        async def fake_classify(*a, **k):
            return "method"
        monkeypatch.setattr(severity_module, "classify_severity", fake_classify)
        s = _session()
        await so.handle(s, _USER, {"type": "answer_submit", "answer": "5"}, _deps(_correct=False))
        assert s.walkthrough_active is True

    async def test_fundamental_wrong_does_not_set_walkthrough_active(self, monkeypatch):
        import agents.severity as severity_module
        async def fake_classify(*a, **k):
            return "fundamental"
        monkeypatch.setattr(severity_module, "classify_severity", fake_classify)
        s = _session()
        await so.handle(s, _USER, {"type": "answer_submit", "answer": "5"}, _deps(_correct=False))
        assert s.walkthrough_active is False

    async def test_walkthrough_step_routes_student_text(self):
        s = _session(walkthrough_active=True)
        res = await so.handle(s, _USER, {"type": "student_text", "text": "I multiplied both sides by 2"}, _deps())
        # In walkthrough mode the response is just agent_text (no lesson wrapping)
        assert [m.type for m in res.messages] == ["agent_text"]

    async def test_answer_submit_clears_walkthrough(self):
        s = _session(walkthrough_active=True)
        await so.handle(s, _USER, {"type": "answer_submit", "answer": "4"}, _deps(_correct=True))
        assert s.walkthrough_active is False

    async def test_budget_exhausted_ends_on_correct_solve(self):
        s = _session(time_budget_exhausted=True)
        res = await so.handle(s, _USER, {"type": "answer_submit", "answer": "4"}, _deps(_correct=True))
        # Must close the session (not advance to next problem)
        assert res.end_session == "timeout"
        assert res.advance is None
        # Sends answer_result + closing agent_text
        assert [m.type for m in res.messages] == ["answer_result", "agent_text"]
        assert s.is_solved is True


@pytest.mark.asyncio
class TestStreakAdaptation:
    async def _submit(self, s, correct):
        return await so.handle(s, _USER, {"type": "answer_submit", "answer": "x"},
                               _deps(_correct=correct))

    async def test_two_correct_prefetches_harder(self):
        s = _session(difficulty=3)  # seeds to conceptual 3 (≈ round(3*5/6)=2... )
        await self._submit(s, True)
        res = await self._submit(s, True)
        assert res.prefetch is not None
        assert res.prefetch.conceptual_diff == so._current_diff(s) + 1

    async def test_three_correct_raises_difficulty(self):
        s = _session(difficulty=3)
        base = so._current_diff(s)
        await self._submit(s, True)
        await self._submit(s, True)
        await self._submit(s, True)
        assert s.target_diff == base + 1
        assert s.correct_streak == 0  # reset after raise

    async def test_two_wrong_lowers_and_prefetches_easier(self):
        s = _session(difficulty=4)
        base = so._current_diff(s)
        await self._submit(s, False)
        res = await self._submit(s, False)
        assert s.target_diff == base - 1
        assert res.prefetch is not None
        assert res.prefetch.conceptual_diff == base - 1

    async def test_correct_resets_wrong_streak(self):
        s = _session(difficulty=3)
        await self._submit(s, False)
        await self._submit(s, True)
        assert s.wrong_streak == 0
        assert s.correct_streak == 1

    async def test_no_adaptation_in_exam_mode(self):
        s = _session(difficulty=3, exam_mode=True)
        for _ in range(4):
            res = await self._submit(s, True)
        assert s.target_diff == 0  # untouched
        assert res.prefetch is None

    async def test_difficulty_capped_at_5(self):
        s = _session(difficulty=6, target_diff=5)
        res = await self._submit(s, True)
        res = await self._submit(s, True)
        # already at 5 → no prefetch past cap
        assert res.prefetch is None

    async def test_difficulty_floored_at_1(self):
        s = _session(difficulty=1, target_diff=1)
        await self._submit(s, False)
        res = await self._submit(s, False)
        assert res.prefetch is None  # already at floor


class TestLessonCascade:
    """Phase 1.6: cascade after LESSON_CASCADE_THRESHOLD lesson cycles on one concept."""

    def _run(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_cascade_not_before_threshold(self):
        s = _session(concept_lesson_counts={"t1": 1})  # becomes 2 — below threshold
        res = self._run(so.handle(
            s, _USER, {"type": "student_text", "text": "explain"}, _deps(_entered_lesson=True)
        ))
        assert res.end_session is None
        assert not any(
            "sleep" in (m.payload.get("text") or "")
            for m in res.messages if m.type == "agent_text"
        )

    def test_cascade_prereq_at_threshold(self):
        # concept_lesson_counts starts at 2, so this is the 3rd cycle
        s = _session(concept_lesson_counts={"t1": 2})
        res = self._run(so.handle(
            s, _USER, {"type": "student_text", "text": "explain"}, _deps(_entered_lesson=True)
        ))
        assert res.end_session is None  # no exam → no honesty close
        # Last agent_text should mention stepping back / prerequisite
        texts = [m.payload.get("text", "") for m in res.messages if m.type == "agent_text"]
        last = texts[-1].lower()
        assert "same wall" in last or "gap" in last or "stepping back" in last or "prerequisite" in last
        # Concept should be flagged in session summary
        assert any(e.get("type") == "concept_flagged" for e in s.session_summary)

    def test_cascade_honesty_close_exam_soon(self):
        from datetime import datetime, timezone, timedelta
        exam_in_6h = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        s = _session(concept_lesson_counts={"t1": 2}, exam_datetime=exam_in_6h)
        res = self._run(so.handle(
            s, _USER, {"type": "student_text", "text": "explain"}, _deps(_entered_lesson=True)
        ))
        assert res.end_session == "student_end"
        texts = [m.payload.get("text", "") for m in res.messages if m.type == "agent_text"]
        last = texts[-1].lower()
        assert "sleep" in last or "rest" in last

    def test_cascade_no_honesty_close_exam_far(self):
        from datetime import datetime, timezone, timedelta
        exam_in_48h = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
        s = _session(concept_lesson_counts={"t1": 2}, exam_datetime=exam_in_48h)
        res = self._run(so.handle(
            s, _USER, {"type": "student_text", "text": "explain"}, _deps(_entered_lesson=True)
        ))
        assert res.end_session is None  # far away → prereq suggestion, not honesty close

    def test_cascade_does_not_repeat(self):
        # At count 4, 5, etc., no additional cascade message
        s = _session(concept_lesson_counts={"t1": 3})  # already at threshold
        res = self._run(so.handle(
            s, _USER, {"type": "student_text", "text": "explain"}, _deps(_entered_lesson=True)
        ))
        # No cascade fires (count becomes 4, above threshold, skipped)
        assert res.end_session is None
        texts = [m.payload.get("text", "") for m in res.messages if m.type == "agent_text"]
        # Should be exactly the lesson reply, not a cascade message after it
        assert len(texts) == 1

    def test_walk_me_through_counts_as_lesson_cycle(self):
        s = _session(concept_lesson_counts={"t1": 2})
        res = self._run(so.handle(
            s, _USER, {"type": "walk_me_through"}, _deps()
        ))
        # walk_me_through always force_lesson=True → 3rd cycle → cascade fires
        assert res.end_session is None  # no exam
        assert any(e.get("type") == "concept_flagged" for e in s.session_summary)
