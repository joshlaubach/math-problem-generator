"""
WebSocket wire-protocol characterization tests (L2-1).

These FREEZE the observable behavior of the tutor WebSocket — the exact
sequence and shape of outbound messages for every inbound message type — so
the 7A orchestrator extraction can be verified as pure motion: this file must
stay GREEN, UNCHANGED, across the refactor. If a test here needs editing to
make the refactor pass, the wire protocol changed and the frontend breaks.

Strategy: drive the real /ws/tutor/{id} endpoint via Starlette's TestClient.
Auth and every LLM-backed function are mocked so message flow is deterministic;
the routing/dispatch/lifecycle logic under test runs for real.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from agents.schemas import GeneratedProblem, WorkedStep, Distractor


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _problem(statement: str, answer: str = "4") -> GeneratedProblem:
    return GeneratedProblem(
        statement=statement,
        answer=answer,
        worked_steps=[WorkedStep(step="s", explanation="e")],
        hint_ladder=["h1", "h2", "h3", "h4"],
        distractors=[
            Distractor(answer="a", mistake="m1"),
            Distractor(answer="b", mistake="m2"),
            Distractor(answer="c", mistake="m3"),
        ],
    )


def _user():
    from users_models import User
    return User(
        id="ws-test-student",
        email="ws@test.com",
        password_hash="",
        role="student",
        created_at=datetime.utcnow(),
        is_active=True,
        tier="free",  # free tier must have full tutor access (credits-only)
    )


@pytest.fixture()
def ws_harness(monkeypatch, tmp_path):
    """
    Yields a builder: connect(**engine_overrides) → (client, ws_context).

    Patches auth + all LLM-backed functions. Per-test behavior (lesson
    escalation, exam readiness, answer correctness) is set via overrides.
    """
    import ws_router
    import agents.tutor_engine as te
    import agents.session_summarizer as ss
    import session_quota
    from fastapi.testclient import TestClient
    from api import app
    from ws_session import create_pending_session, delete_session

    # Keep quota writes out of the repo data dir
    monkeypatch.setattr(session_quota, "QUOTA_LOG_PATH", tmp_path / "quota.jsonl")
    monkeypatch.setattr(session_quota, "_uses_database", lambda: False)

    # Auth: bypass JWT, return a known user
    async def fake_auth(token):
        return _user()
    monkeypatch.setattr(ws_router, "_authenticate_ws_token", fake_auth)

    # Engine knobs (mutable so individual tests can flip them)
    state = SimpleNamespace(
        reply="TUTOR_REPLY",
        entered_lesson=False,
        exam_ready=False,
        answer_correct=False,
    )

    async def fake_build_queue(session):
        return [_problem("PROBLEM_ONE"), _problem("PROBLEM_TWO")]

    async def fake_opening(**kwargs):
        return "OPENING_MESSAGE"

    async def fake_generate(session, message, force_lesson=False):
        if force_lesson:
            return "LESSON_REPLY", True
        return state.reply, state.entered_lesson

    async def fake_too_fast(session):
        return "SLOW_DOWN"

    def fake_exam_ready(session):
        return state.exam_ready

    async def fake_exam_proposal(session):
        return "EXAM_PROPOSAL"

    async def fake_exam_start(session):
        return "EXAM_START"

    async def fake_check_answer(student_answer, canonical):
        return SimpleNamespace(
            correct=state.answer_correct,
            equivalent_form=False,
            partial_credit_reason=None,
        )

    async def fake_get_hint(req, user_tier="free"):
        return "HINT_TEXT"

    async def fake_compress(session):
        return None

    async def fake_report_email(**kwargs):
        return None

    async def fake_summarize(**kwargs):
        return {"bullets": [], "per_topic_performance": {}, "practice_problems": []}

    monkeypatch.setattr(te, "build_problem_queue", fake_build_queue)
    monkeypatch.setattr(te, "get_opening_message", fake_opening)
    monkeypatch.setattr(te, "generate_tutor_response", fake_generate)
    monkeypatch.setattr(te, "handle_going_too_fast", fake_too_fast)
    monkeypatch.setattr(te, "check_exam_readiness", fake_exam_ready)
    monkeypatch.setattr(te, "get_exam_mode_proposal", fake_exam_proposal)
    monkeypatch.setattr(te, "get_exam_start_message", fake_exam_start)
    monkeypatch.setattr(ws_router, "check_answer", fake_check_answer)
    monkeypatch.setattr(ws_router, "get_hint", fake_get_hint)
    monkeypatch.setattr(ws_router, "_compress_conversation", fake_compress)
    monkeypatch.setattr(ws_router, "_send_session_report_email", fake_report_email)
    monkeypatch.setattr(ss, "summarize_session", fake_summarize)

    created: list[str] = []

    def connect(session_id="ws-sess-1", **topic_kwargs):
        create_pending_session(
            session_id=session_id,
            user_id="ws-test-student",
            session_type="1hr",
            class_name=topic_kwargs.get("class_name", "Algebra 2"),
            topic_ids=topic_kwargs.get("topic_ids", ["alg2_systems_matrices"]),
        )
        created.append(session_id)
        client = TestClient(app)
        return client.websocket_connect(f"/ws/tutor/{session_id}?token=t")

    yield SimpleNamespace(connect=connect, state=state)

    for sid in created:
        delete_session(sid)


def _drain_connect(ws) -> list[dict]:
    """Read the three connect-time messages: session_loading, session_ready, agent_text."""
    return [ws.receive_json(), ws.receive_json(), ws.receive_json()]


# ── Connect handshake ────────────────────────────────────────────────────────

class TestConnectHandshake:
    def test_connect_sequence(self, ws_harness):
        with ws_harness.connect() as ws:
            loading = ws.receive_json()
            ready = ws.receive_json()
            opening = ws.receive_json()

        assert loading["type"] == "session_loading"
        assert ready["type"] == "session_ready"
        assert ready["problem"]["statement"] == "PROBLEM_ONE"
        assert ready["problem"]["hint_ladder_length"] == 4
        assert "max_duration_seconds" in ready
        assert opening == {"type": "agent_text", "text": "OPENING_MESSAGE"}


# ── student_text ──────────────────────────────────────────────────────────────

class TestStudentText:
    def test_plain_reply(self, ws_harness):
        ws_harness.state.reply = "Here is a hint question?"
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "student_text", "text": "I'm stuck"})
            msg = ws.receive_json()
        assert msg == {"type": "agent_text", "text": "Here is a hint question?"}

    def test_lesson_wrapping(self, ws_harness):
        """When the engine escalates, agent_text is bracketed by lesson_start/lesson_end."""
        ws_harness.state.entered_lesson = True
        ws_harness.state.reply = "LESSON_CONTENT"
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "student_text", "text": "I don't get it"})
            start = ws.receive_json()
            body = ws.receive_json()
            end = ws.receive_json()
        assert start["type"] == "lesson_start"
        assert body == {"type": "agent_text", "text": "LESSON_CONTENT"}
        assert end["type"] == "lesson_end"

    def test_empty_text_ignored(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "student_text", "text": "   "})
            # No response to empty text; a subsequent real message still works
            ws.send_json({"type": "student_text", "text": "real"})
            msg = ws.receive_json()
        assert msg["type"] == "agent_text"


# ── answer_submit ─────────────────────────────────────────────────────────────

class TestAnswerSubmit:
    def test_wrong_answer_result_then_followup(self, ws_harness):
        ws_harness.state.answer_correct = False
        ws_harness.state.reply = "FOLLOWUP_Q"
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "answer_submit", "answer": "wrong"})
            result = ws.receive_json()
            followup = ws.receive_json()
        assert result["type"] == "answer_result"
        assert result["correct"] is False
        assert "equivalent_form" in result and "partial_credit_reason" in result
        assert followup == {"type": "agent_text", "text": "FOLLOWUP_Q"}

    def test_correct_answer_advances(self, ws_harness):
        ws_harness.state.answer_correct = True
        ws_harness.state.exam_ready = False
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "answer_submit", "answer": "4"})
            result = ws.receive_json()
            section = ws.receive_json()
            nxt = ws.receive_json()
        assert result["type"] == "answer_result" and result["correct"] is True
        assert section["type"] == "wb_new_section"
        assert nxt["type"] == "next_problem"
        assert nxt["problem"]["statement"] == "PROBLEM_TWO"
        assert nxt["index"] == 1

    def test_correct_answer_proposes_exam_when_ready(self, ws_harness):
        ws_harness.state.answer_correct = True
        ws_harness.state.exam_ready = True
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "answer_submit", "answer": "4"})
            result = ws.receive_json()
            propose = ws.receive_json()
        assert result["type"] == "answer_result"
        assert propose == {"type": "exam_mode_propose", "message": "EXAM_PROPOSAL"}


# ── hint_request ──────────────────────────────────────────────────────────────

class TestHintRequest:
    def test_hint_served(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "hint_request"})
            msg = ws.receive_json()
        assert msg["type"] == "hint"
        assert msg["text"] == "HINT_TEXT"
        assert msg["level"] == 1
        assert msg["max_level"] == 4

    def test_hint_blocked_in_exam_mode(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            # Enter exam mode first
            ws_harness.state.exam_ready = True
            ws_harness.state.answer_correct = True
            ws.send_json({"type": "exam_mode_accept"})
            # Drain exam-entry messages: wb_clear, exam_mode_active, agent_text, wb_new_section, next_problem
            for _ in range(5):
                ws.receive_json()
            ws.send_json({"type": "hint_request"})
            err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == 4003


# ── walk_me_through ───────────────────────────────────────────────────────────

class TestWalkMeThrough:
    def test_forces_lesson_bracketing(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "walk_me_through"})
            start = ws.receive_json()
            body = ws.receive_json()
            end = ws.receive_json()
        assert start["type"] == "lesson_start"
        assert body == {"type": "agent_text", "text": "LESSON_REPLY"}
        assert end["type"] == "lesson_end"


# ── going_too_fast ────────────────────────────────────────────────────────────

class TestGoingTooFast:
    def test_pacing_reply(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "going_too_fast"})
            msg = ws.receive_json()
        assert msg == {"type": "agent_text", "text": "SLOW_DOWN"}


# ── next_problem (skip) ───────────────────────────────────────────────────────

class TestSkipProblem:
    def test_skip_advances(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "next_problem"})
            section = ws.receive_json()
            nxt = ws.receive_json()
        assert section["type"] == "wb_new_section"
        assert nxt["type"] == "next_problem"
        assert nxt["problem"]["statement"] == "PROBLEM_TWO"


# ── exam_mode_accept ──────────────────────────────────────────────────────────

class TestExamModeAccept:
    def test_exam_entry_sequence(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "exam_mode_accept"})
            clear = ws.receive_json()
            active = ws.receive_json()
            start_text = ws.receive_json()
            section = ws.receive_json()
            nxt = ws.receive_json()
        assert clear["type"] == "wb_clear" and clear["snapshot"] is True
        assert active["type"] == "exam_mode_active"
        assert start_text == {"type": "agent_text", "text": "EXAM_START"}
        assert section["type"] == "wb_new_section"
        assert nxt["type"] == "next_problem"


# ── wb_student_work ───────────────────────────────────────────────────────────

class TestStudentWork:
    def test_work_gets_agent_text(self, ws_harness):
        ws_harness.state.reply = "WORK_FEEDBACK"
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "wb_student_work", "latex": "x=2"})
            msg = ws.receive_json()
        assert msg == {"type": "agent_text", "text": "WORK_FEEDBACK"}


# ── rag_search ────────────────────────────────────────────────────────────────

class TestRagSearch:
    def test_placeholder_reply(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "rag_search"})
            msg = ws.receive_json()
        assert msg["type"] == "agent_text"


# ── session_end ───────────────────────────────────────────────────────────────

class TestSessionEnd:
    def test_end_sends_summary(self, ws_harness):
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "session_end"})
            msg = ws.receive_json()
        assert msg["type"] == "session_end"
        assert "summary" in msg
        assert "ai_summary" in msg["summary"]


# ── Stateful flow: clean solves → exam proposal → accept ──────────────────────

class TestExamProposalFlow:
    def test_propose_then_accept(self, ws_harness):
        ws_harness.state.answer_correct = True
        ws_harness.state.exam_ready = True
        with ws_harness.connect() as ws:
            _drain_connect(ws)
            ws.send_json({"type": "answer_submit", "answer": "4"})
            assert ws.receive_json()["type"] == "answer_result"
            assert ws.receive_json()["type"] == "exam_mode_propose"
            # Accept
            ws.send_json({"type": "exam_mode_accept"})
            assert ws.receive_json()["type"] == "wb_clear"
            assert ws.receive_json()["type"] == "exam_mode_active"
