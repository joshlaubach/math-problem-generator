"""
Comprehensive tests for Phase 3–6: general tutor features.

Phase 3 — POST /tutor/session/create, POST /tutor/session/{id}/upload,
           document_extractor.extract_problems, file-size / type guards
Phase 4 — agents/tutor_engine.py (opening msg, queue build, response routing,
           going_too_fast, walk_me_through, escalation)
Phase 5 — exam mode: readiness check, board-clear proposal, hint suppression
Phase 6 — session_summarizer extended dict return (bullets/performance/practice)

Async tests use anyio (already installed; use @pytest.mark.anyio).
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Auth + tier setup ─────────────────────────────────────────────────────────

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-not-for-production")
os.environ.setdefault("AUTH_PROVIDER", "jwt")
os.environ.setdefault("USE_DATABASE", "false")


def _make_paid_student():
    """A student on a paid tier (passes the PAID_TIERS gate)."""
    from users_models import User
    return User(
        id="paid-student-001",
        email="paid@test.com",
        password_hash="",
        role="student",
        created_at=datetime.utcnow(),
        is_active=True,
        tier="student",
    )


@pytest.fixture()
def tutor_client(reset_user_repo):
    """Test client with require_student overridden to a paid student."""
    from fastapi.testclient import TestClient
    from api import app
    from auth_dependencies import require_student

    app.dependency_overrides[require_student] = _make_paid_student
    yield TestClient(app)
    app.dependency_overrides.pop(require_student, None)


# Helper: minimal GeneratedProblem
def _make_problem(statement="Solve $x+1=5$", answer="4"):
    from agents.schemas import GeneratedProblem, WorkedStep, Distractor
    return GeneratedProblem(
        statement=statement,
        answer=answer,
        worked_steps=[WorkedStep(step="Step 1", explanation="Subtract 1")],
        hint_ladder=["H1", "H2", "H3", "H4"],
        distractors=[
            Distractor(answer="3", mistake="Off by one"),
            Distractor(answer="5", mistake="Added instead"),
            Distractor(answer="6", mistake="Arithmetic error"),
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3a — POST /tutor/session/create
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionCreate:
    def test_create_returns_session_id(self, tutor_client):
        resp = tutor_client.post("/tutor/session/create", json={
            "class_name": "Algebra I",
            "unit_names": ["Linear Equations"],
            "topic_ids": ["alg1_linear_one_step"],
            "freeform_topics": [],
            "why": "test_prep",
            "notes": "",
            "session_type": "1hr",
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 36  # UUID4

    def test_create_freeform_topic(self, tutor_client):
        """Out-of-curriculum class with freeform topic should work (Mode B)."""
        resp = tutor_client.post("/tutor/session/create", json={
            "class_name": "Other",
            "unit_names": [],
            "topic_ids": [],
            "freeform_topics": ["SAT Algebra"],
            "why": None,
            "notes": "My SAT is in 2 weeks",
            "session_type": "1hr",
        })
        assert resp.status_code == 200
        assert "session_id" in resp.json()

    def test_create_stores_session_in_registry(self, tutor_client):
        """Session should be retrievable from ws_session after creation."""
        from ws_session import get_session
        resp = tutor_client.post("/tutor/session/create", json={
            "class_name": "Calculus 2",
            "topic_ids": [],
            "session_type": "1hr",
        })
        sid = resp.json()["session_id"]
        session = get_session(sid)
        assert session is not None
        assert session.class_name == "Calculus 2"
        assert session.user_id == "paid-student-001"

    def test_create_2hr_session(self, tutor_client):
        from ws_session import get_session, SESSION_TYPES
        resp = tutor_client.post("/tutor/session/create", json={
            "class_name": "Algebra I",
            "session_type": "2hr",
        })
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        session = get_session(sid)
        assert session.max_duration_seconds == SESSION_TYPES["2hr"]

    def test_create_invalid_session_type(self, tutor_client):
        resp = tutor_client.post("/tutor/session/create", json={
            "class_name": "Algebra I",
            "session_type": "3hr",
        })
        assert resp.status_code == 422

    def test_create_notes_too_long(self, tutor_client):
        resp = tutor_client.post("/tutor/session/create", json={
            "class_name": "Algebra I",
            "session_type": "1hr",
            "notes": "x" * 2001,
        })
        assert resp.status_code == 422

    def test_unpaid_tier_rejected(self, reset_user_repo):
        """Free-tier students cannot create sessions."""
        from fastapi.testclient import TestClient
        from api import app
        from auth_dependencies import require_student
        from users_models import User

        def free_student():
            return User(
                id="free-001", email="free@test.com", password_hash="",
                role="student", created_at=datetime.utcnow(),
                is_active=True, tier="free",
            )

        app.dependency_overrides[require_student] = free_student
        client = TestClient(app)
        resp = client.post("/tutor/session/create", json={
            "class_name": "Algebra I",
            "session_type": "1hr",
        })
        app.dependency_overrides.pop(require_student, None)
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3b — POST /tutor/session/{id}/upload
# ─────────────────────────────────────────────────────────────────────────────

def _create_session_for_upload(tutor_client) -> str:
    """Helper: create a session and return its ID."""
    resp = tutor_client.post("/tutor/session/create", json={
        "class_name": "Calculus 2",
        "session_type": "1hr",
    })
    return resp.json()["session_id"]


# Minimal valid 1×1 white PNG
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90\x77\x53\xde\x00\x00\x00\x0cIDATx\x9cc\xf8"
    b"\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestSessionUpload:
    def test_upload_png_returns_extracted(self, tutor_client):
        """Upload a PNG; mock extract_problems to return two problems."""
        sid = _create_session_for_upload(tutor_client)

        fake_problems = [
            {"number": 1, "statement_latex": r"Solve: $x^2+5x+6=0$", "points": 10},
            {"number": 2, "statement_latex": r"Find $\int x^2\,dx$", "points": 15},
        ]
        with patch(
            "agents.document_extractor.extract_problems",
            new=AsyncMock(return_value=fake_problems),
        ):
            resp = tutor_client.post(
                f"/tutor/session/{sid}/upload",
                files=[("files", ("test.png", io.BytesIO(_TINY_PNG), "image/png"))],
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["files_saved"] == 1
        assert data["problems_extracted"] == 2
        assert data["problems"][0]["number"] == 1

    def test_upload_updates_session_uploaded_problems(self, tutor_client):
        """Extracted problems must be persisted on the session."""
        from ws_session import get_session

        sid = _create_session_for_upload(tutor_client)
        fake = [{"number": 1, "statement_latex": r"$x+1=0$", "points": None}]
        with patch("agents.document_extractor.extract_problems", new=AsyncMock(return_value=fake)):
            tutor_client.post(
                f"/tutor/session/{sid}/upload",
                files=[("files", ("hw.png", io.BytesIO(_TINY_PNG), "image/png"))],
            )
        session = get_session(sid)
        assert len(session.uploaded_problems) == 1
        assert session.uploaded_problems[0]["number"] == 1

    def test_upload_wrong_owner_rejected(self, reset_user_repo):
        """A different user cannot upload to another user's session."""
        from fastapi.testclient import TestClient
        from api import app
        from auth_dependencies import require_student
        from users_models import User

        def user_a():
            return User(id="user-a", email="a@test.com", password_hash="",
                        role="student", created_at=datetime.utcnow(),
                        is_active=True, tier="student")

        app.dependency_overrides[require_student] = user_a
        client_a = TestClient(app)
        resp = client_a.post("/tutor/session/create", json={"class_name": "Algebra I", "session_type": "1hr"})
        sid = resp.json()["session_id"]

        def user_b():
            return User(id="user-b", email="b@test.com", password_hash="",
                        role="student", created_at=datetime.utcnow(),
                        is_active=True, tier="student")

        app.dependency_overrides[require_student] = user_b
        client_b = TestClient(app)
        with patch("agents.document_extractor.extract_problems", new=AsyncMock(return_value=[])):
            resp = client_b.post(
                f"/tutor/session/{sid}/upload",
                files=[("files", ("hw.png", io.BytesIO(_TINY_PNG), "image/png"))],
            )
        app.dependency_overrides.pop(require_student, None)
        assert resp.status_code == 403

    def test_upload_session_not_found(self, tutor_client):
        with patch("agents.document_extractor.extract_problems", new=AsyncMock(return_value=[])):
            resp = tutor_client.post(
                "/tutor/session/nonexistent-session-id/upload",
                files=[("files", ("hw.png", io.BytesIO(_TINY_PNG), "image/png"))],
            )
        assert resp.status_code == 404

    def test_upload_disallowed_filetype(self, tutor_client):
        sid = _create_session_for_upload(tutor_client)
        with patch("agents.document_extractor.extract_problems", new=AsyncMock(return_value=[])):
            resp = tutor_client.post(
                f"/tutor/session/{sid}/upload",
                files=[("files", ("notes.docx", io.BytesIO(b"docx content"), "application/octet-stream"))],
            )
        assert resp.status_code == 415

    def test_upload_file_too_large(self, tutor_client):
        sid = _create_session_for_upload(tutor_client)
        big = io.BytesIO(b"x" * (10 * 1024 * 1024 + 1))
        with patch("agents.document_extractor.extract_problems", new=AsyncMock(return_value=[])):
            resp = tutor_client.post(
                f"/tutor/session/{sid}/upload",
                files=[("files", ("big.png", big, "image/png"))],
            )
        assert resp.status_code == 413

    def test_upload_max_5_files_enforced(self, tutor_client):
        """Only first 5 files are processed even if 6 are sent."""
        sid = _create_session_for_upload(tutor_client)
        six_files = [
            ("files", (f"file{i}.png", io.BytesIO(_TINY_PNG), "image/png"))
            for i in range(6)
        ]
        with patch("agents.document_extractor.extract_problems", new=AsyncMock(return_value=[])) as mock_ext:
            tutor_client.post(f"/tutor/session/{sid}/upload", files=six_files)
        call_args = mock_ext.call_args[0][0]
        assert len(call_args) <= 5

    def test_upload_empty_extraction_still_200(self, tutor_client):
        """If Claude Vision returns nothing, endpoint should still succeed."""
        sid = _create_session_for_upload(tutor_client)
        with patch("agents.document_extractor.extract_problems", new=AsyncMock(return_value=[])):
            resp = tutor_client.post(
                f"/tutor/session/{sid}/upload",
                files=[("files", ("blank.png", io.BytesIO(_TINY_PNG), "image/png"))],
            )
        assert resp.status_code == 200
        assert resp.json()["problems_extracted"] == 0

    def test_upload_cleanup_deletes_dir(self, tutor_client, tmp_path, monkeypatch):
        """cleanup_session_uploads should remove the directory."""
        from tutor_router import cleanup_session_uploads
        import config
        monkeypatch.setattr(config, "DATA_DIR", tmp_path)

        fake_dir = tmp_path / "session_uploads" / "fake-session-id"
        fake_dir.mkdir(parents=True)
        (fake_dir / "file.png").write_bytes(b"data")

        cleanup_session_uploads("fake-session-id")
        assert not fake_dir.exists()


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3c — document_extractor unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentExtractor:
    @pytest.mark.anyio
    async def test_extract_problems_from_image(self, tmp_path):
        """extract_problems with a PNG calls call_with_images and parses result."""
        from agents.document_extractor import extract_problems

        img_path = tmp_path / "hw.png"
        img_path.write_bytes(_TINY_PNG)

        mock_response = json.dumps({
            "problems": [
                {"number": 1, "statement_latex": r"$x^2 = 4$", "points": 10},
            ]
        })
        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch(
                "llm_anthropic_client.call_with_images",
                new=AsyncMock(return_value=mock_response),
            ):
                result = await extract_problems([img_path])

        assert len(result) == 1
        assert result[0]["number"] == 1
        assert "x^2" in result[0]["statement_latex"]

    @pytest.mark.anyio
    async def test_extract_handles_llm_json_wrapped_in_fences(self, tmp_path):
        """LLM sometimes wraps JSON in markdown fences; extractor strips them."""
        from agents.document_extractor import extract_problems

        img_path = tmp_path / "hw.png"
        img_path.write_bytes(_TINY_PNG)

        fenced = '```json\n{"problems":[{"number":1,"statement_latex":"$x=1$","points":null}]}\n```'
        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch(
                "llm_anthropic_client.call_with_images",
                new=AsyncMock(return_value=fenced),
            ):
                result = await extract_problems([img_path])
        assert len(result) == 1

    @pytest.mark.anyio
    async def test_extract_handles_empty_problems_array(self, tmp_path):
        from agents.document_extractor import extract_problems
        img_path = tmp_path / "blank.png"
        img_path.write_bytes(_TINY_PNG)

        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch(
                "llm_anthropic_client.call_with_images",
                new=AsyncMock(return_value='{"problems":[]}'),
            ):
                result = await extract_problems([img_path])
        assert result == []

    @pytest.mark.anyio
    async def test_extract_handles_malformed_llm_response(self, tmp_path):
        """Garbage JSON from LLM → returns [] without raising."""
        from agents.document_extractor import extract_problems
        img_path = tmp_path / "bad.png"
        img_path.write_bytes(_TINY_PNG)

        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch(
                "llm_anthropic_client.call_with_images",
                new=AsyncMock(return_value="Not valid JSON at all!"),
            ):
                result = await extract_problems([img_path])
        assert result == []

    @pytest.mark.anyio
    async def test_extract_empty_list_returns_empty(self):
        """No file paths → skip Vision call, return []."""
        from agents.document_extractor import extract_problems
        result = await extract_problems([])
        assert result == []

    @pytest.mark.anyio
    async def test_extract_no_api_key_returns_empty(self, tmp_path):
        """Missing ANTHROPIC_API_KEY → returns [] without calling Vision."""
        from agents.document_extractor import extract_problems
        img_path = tmp_path / "hw.png"
        img_path.write_bytes(_TINY_PNG)

        with patch("config.ANTHROPIC_API_KEY", ""):
            with patch("llm_anthropic_client.call_with_images", new=AsyncMock()) as mock_call:
                result = await extract_problems([img_path])
        mock_call.assert_not_called()
        assert result == []

    @pytest.mark.anyio
    async def test_extract_oversized_file_skipped(self, tmp_path):
        """Files larger than _MAX_FILE_BYTES are skipped (no Vision call)."""
        import agents.document_extractor as doc_ext

        img_path = tmp_path / "big.png"
        img_path.write_bytes(b"x" * 10)  # tiny actual content

        original_max = doc_ext._MAX_FILE_BYTES
        doc_ext._MAX_FILE_BYTES = 0  # force all files to exceed limit
        try:
            with patch("config.ANTHROPIC_API_KEY", "fake-key"):
                with patch("llm_anthropic_client.call_with_images", new=AsyncMock()) as mock_call:
                    result = await doc_ext.extract_problems([img_path])
            mock_call.assert_not_called()
            assert result == []
        finally:
            doc_ext._MAX_FILE_BYTES = original_max


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — tutor_engine unit tests
# ─────────────────────────────────────────────────────────────────────────────

def _make_session(
    topic_ids=None,
    uploaded_problems=None,
    why=None,
    class_name="Calculus 2",
    current_index=0,
    consecutive_no_progress=0,
    exam_mode=False,
    session_summary=None,
    problem_queue=None,
    freeform_topics=None,
    difficulty=3,
):
    """Build a minimal TutorSession for engine tests."""
    from ws_session import TutorSession

    return TutorSession(
        session_id="test-sess-001",
        user_id="u1",
        topic_id="",
        difficulty=difficulty,
        session_type="1hr",
        max_duration_seconds=3600,
        class_name=class_name,
        topic_ids=topic_ids or ["alg1_linear_one_step"],
        freeform_topics=freeform_topics or [],
        uploaded_problems=uploaded_problems or [],
        why=why,
        problem_queue=problem_queue or [],
        current_index=current_index,
        consecutive_no_progress=consecutive_no_progress,
        exam_mode=exam_mode,
        session_summary=session_summary or [],
    )


class TestTutorEngineOpening:
    @pytest.mark.anyio
    async def test_opening_no_uploads(self):
        from agents.tutor_engine import get_opening_message
        msg = await get_opening_message(
            session_why=None,
            uploaded_problem_count=0,
            class_name="Algebra I",
            topic_names=["Linear Equations"],
            tutor_name="Josh",
        )
        assert isinstance(msg, str)
        assert len(msg) > 20

    @pytest.mark.anyio
    async def test_opening_with_uploads(self):
        from agents.tutor_engine import get_opening_message
        msg = await get_opening_message(
            session_why="homework",
            uploaded_problem_count=3,
            class_name="Calculus 2",
            topic_names=[],
            tutor_name="Josh",
        )
        assert isinstance(msg, str)
        assert "3" in msg or "problem" in msg.lower()

    @pytest.mark.anyio
    async def test_opening_test_prep_variant(self):
        from agents.tutor_engine import get_opening_message
        msg = await get_opening_message(
            session_why="test_prep",
            uploaded_problem_count=0,
            class_name="Calculus 2",
            topic_names=["Integration by Parts"],
            tutor_name="Josh",
        )
        assert isinstance(msg, str)
        assert len(msg) > 10

    @pytest.mark.anyio
    async def test_opening_all_why_variants(self):
        from agents.tutor_engine import get_opening_message
        for why in ["learn_concept", "homework", "test_prep", "grade_improvement", "get_ahead", "other"]:
            msg = await get_opening_message(
                session_why=why,
                uploaded_problem_count=0,
                class_name="Algebra I",
                topic_names=["Linear Equations"],
                tutor_name="Josh",
            )
            assert isinstance(msg, str), f"Opening for why={why!r} should be a string"


class TestTutorEngineQueueBuild:
    @pytest.mark.anyio
    async def test_queue_empty_when_uploads_present(self):
        """If uploaded_problems exist, problem_queue should NOT be populated."""
        from agents.tutor_engine import build_problem_queue
        session = _make_session(uploaded_problems=[{"number": 1, "statement_latex": "$x=1$"}])
        with patch("agents.generator.generate") as mock_gen:
            result = await build_problem_queue(session)
        mock_gen.assert_not_called()
        assert result == []

    @pytest.mark.anyio
    async def test_queue_built_from_topic_ids(self):
        """With no uploads, queue is built via generate() for each topic_id."""
        from agents.tutor_engine import build_problem_queue
        from topic_registry import TOPIC_REGISTRY
        # Pick a topic that actually exists in the registry
        valid_topic_id = next(iter(TOPIC_REGISTRY.keys()))
        fake_problem = _make_problem()

        with patch("agents.generator.generate", new=AsyncMock(return_value=fake_problem)):
            session = _make_session(topic_ids=[valid_topic_id])
            result = await build_problem_queue(session)

        assert len(result) > 0

    @pytest.mark.anyio
    async def test_queue_built_from_freeform_topics(self):
        """Freeform topics also generate problems."""
        from agents.tutor_engine import build_problem_queue
        fake = _make_problem(statement="SAT problem", answer="2")

        with patch("agents.generator.generate", new=AsyncMock(return_value=fake)):
            session = _make_session(
                topic_ids=[],  # no in-curriculum topics
                freeform_topics=["SAT Algebra"],
            )
            result = await build_problem_queue(session)
        assert len(result) > 0

    @pytest.mark.anyio
    async def test_queue_gen_failure_is_swallowed(self):
        """If generate() raises, build_problem_queue returns [] without crashing."""
        from agents.tutor_engine import build_problem_queue

        with patch("agents.generator.generate", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
            session = _make_session(topic_ids=["alg1_linear_one_step"])
            result = await build_problem_queue(session)
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_queue_unknown_topic_id_skipped(self):
        """Topic IDs not in registry are silently skipped."""
        from agents.tutor_engine import build_problem_queue

        with patch("agents.generator.generate", new=AsyncMock()) as mock_gen:
            session = _make_session(topic_ids=["nonexistent_topic_xyz"])
            result = await build_problem_queue(session)
        mock_gen.assert_not_called()
        assert result == []


class TestTutorEngineResponse:
    @pytest.mark.anyio
    async def test_socratic_mode_returns_tuple(self):
        """Normal student message → Socratic response."""
        from agents.tutor_engine import generate_tutor_response

        session = _make_session()
        session.problem = _make_problem()
        session.conversation = []

        with patch(
            "agents.socratic.respond",
            new=AsyncMock(return_value="Have you tried isolating x?"),
        ):
            reply, escalated = await generate_tutor_response(session, "I don't know")

        assert isinstance(reply, str)
        assert len(reply) > 0
        assert escalated is False

    @pytest.mark.anyio
    async def test_force_lesson_escalates(self):
        """force_lesson=True should route to lesson mode."""
        from agents.tutor_engine import generate_tutor_response

        session = _make_session()
        session.problem = _make_problem()
        session.conversation = []

        with patch(
            "agents.tutor_engine._lesson_response",
            new=AsyncMock(return_value="Let me walk you through it: ..."),
        ):
            reply, escalated = await generate_tutor_response(
                session, "walk me through", force_lesson=True
            )

        assert escalated is True
        assert "walk" in reply.lower() or len(reply) > 0

    @pytest.mark.anyio
    async def test_auto_escalation_after_threshold(self):
        """consecutive_no_progress >= ESCALATION_THRESHOLD triggers lesson."""
        from agents.tutor_engine import generate_tutor_response, ESCALATION_THRESHOLD

        session = _make_session(consecutive_no_progress=ESCALATION_THRESHOLD)
        session.problem = _make_problem()
        session.conversation = []

        with patch(
            "agents.tutor_engine._lesson_response",
            new=AsyncMock(return_value="Let me explain the concept..."),
        ):
            reply, escalated = await generate_tutor_response(session, "I still don't get it")

        assert escalated is True

    @pytest.mark.anyio
    async def test_no_problem_returns_gracefully(self):
        """session.problem is None → returns a helpful message, doesn't crash."""
        from agents.tutor_engine import generate_tutor_response

        session = _make_session()
        session.problem = None

        reply, escalated = await generate_tutor_response(session, "Hello")
        assert isinstance(reply, str)
        assert len(reply) > 0
        assert escalated is False

    @pytest.mark.anyio
    async def test_going_too_fast_returns_string(self):
        """handle_going_too_fast returns a non-empty string."""
        from agents.tutor_engine import handle_going_too_fast

        session = _make_session()
        session.problem = _make_problem()

        # No API key → falls back to deterministic string
        with patch("config.ANTHROPIC_API_KEY", ""):
            msg = await handle_going_too_fast(session)

        assert isinstance(msg, str)
        assert len(msg) > 10

    @pytest.mark.anyio
    async def test_going_too_fast_no_problem_ok(self):
        """handle_going_too_fast when no current problem doesn't crash."""
        from agents.tutor_engine import handle_going_too_fast

        session = _make_session()
        session.problem = None

        with patch("config.ANTHROPIC_API_KEY", ""):
            msg = await handle_going_too_fast(session)

        assert isinstance(msg, str)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — exam mode
# ─────────────────────────────────────────────────────────────────────────────

class TestExamMode:
    def test_readiness_not_met_below_threshold(self):
        from agents.tutor_engine import check_exam_readiness, READINESS_THRESHOLD
        session = _make_session(current_index=READINESS_THRESHOLD - 1)
        assert check_exam_readiness(session) is False

    def test_readiness_met_requires_clean_bullets(self):
        from agents.tutor_engine import check_exam_readiness, READINESS_THRESHOLD
        # index at threshold, but all bullets mention hints → NOT ready
        session = _make_session(
            current_index=READINESS_THRESHOLD,
            session_summary=["Used 3 hints", "Needed hints again", "Still used a hint"],
        )
        assert check_exam_readiness(session) is False

    def test_readiness_met_with_clean_bullets(self):
        from agents.tutor_engine import check_exam_readiness, READINESS_THRESHOLD
        # index at threshold; bullets contain "solved"/"correct" but NOT "hint"
        session = _make_session(
            current_index=READINESS_THRESHOLD,
            session_summary=[
                "Solved on first attempt",
                "Correct answer immediately",
                "Solved independently",
            ],
        )
        assert check_exam_readiness(session) is True

    @pytest.mark.anyio
    async def test_get_exam_mode_proposal_string(self):
        from agents.tutor_engine import get_exam_mode_proposal
        session = _make_session(current_index=3)
        msg = await get_exam_mode_proposal(session)
        assert isinstance(msg, str)
        assert len(msg) > 20

    @pytest.mark.anyio
    async def test_get_exam_start_message_string(self):
        from agents.tutor_engine import get_exam_start_message
        session = _make_session()
        msg = await get_exam_start_message(session)
        assert isinstance(msg, str)
        assert len(msg) > 10

    def test_exam_mode_flag_on_session(self):
        """Setting exam_mode=True on session is readable."""
        session = _make_session(exam_mode=True)
        assert session.exam_mode is True

    def test_exam_mode_default_false(self):
        session = _make_session()
        assert session.exam_mode is False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — extended session summarizer
# ─────────────────────────────────────────────────────────────────────────────

def _mock_anthropic_response(text: str):
    """Build a mock anthropic Messages response with given text content."""
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    return resp


class TestSessionSummarizer:
    @pytest.mark.anyio
    async def test_legacy_mode_returns_list_when_no_api_key(self):
        """Without API key, legacy mode (topics_covered=None) must return a list."""
        from agents.session_summarizer import summarize_session

        with patch("config.ANTHROPIC_API_KEY", ""):
            result = await summarize_session(
                topic_name="Linear Equations",
                mode="practice",
                conversation=[{"role": "student", "content": "hello"}],
                problems_attempted=1,
                problems_solved=1,
                hints_used=0,
                duration_seconds=600,
                topics_covered=None,
            )
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.anyio
    async def test_extended_mode_returns_dict_when_no_api_key(self):
        """Without API key, extended mode returns a dict with all 3 keys."""
        from agents.session_summarizer import summarize_session

        with patch("config.ANTHROPIC_API_KEY", ""):
            result = await summarize_session(
                topic_name="Integration by Parts",
                mode="practice",
                conversation=[{"role": "student", "content": "ok"}],
                problems_attempted=2,
                problems_solved=1,
                hints_used=2,
                duration_seconds=1200,
                topics_covered=["Integration by Parts"],
            )
        assert isinstance(result, dict)
        assert "bullets" in result
        assert "per_topic_performance" in result
        assert "practice_problems" in result

    @pytest.mark.anyio
    async def test_extended_mode_with_llm_response(self):
        """With mocked LLM, extended mode parses and returns all 3 sections."""
        from agents.session_summarizer import summarize_session

        fake_json = json.dumps({
            "bullets": ["Covered integration by parts.", "Student needed 2 hints."],
            "per_topic_performance": {"Integration by Parts": "needs_work"},
            "practice_problems": [
                "Find $\\int x e^x\\,dx$ using integration by parts.",
            ],
        })
        mock_resp = _mock_anthropic_response(fake_json)
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_resp)

        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                result = await summarize_session(
                    topic_name="Integration by Parts",
                    mode="practice",
                    conversation=[{"role": "student", "content": "ok"}],
                    problems_attempted=2,
                    problems_solved=1,
                    hints_used=2,
                    duration_seconds=1200,
                    topics_covered=["Integration by Parts"],
                    session_summary_bullets=["Covered integration by parts."],
                )
        assert isinstance(result, dict)
        assert len(result["bullets"]) == 2
        assert "Integration by Parts" in result["per_topic_performance"]

    @pytest.mark.anyio
    async def test_extended_mode_per_topic_performance_values(self):
        """Performance values must be: strong / needs_work / attempted."""
        from agents.session_summarizer import summarize_session

        fake_json = json.dumps({
            "bullets": ["Covered differentiation.", "Did chain rule.", "Product rule reviewed."],
            "per_topic_performance": {
                "Derivatives": "strong",
                "Chain Rule": "needs_work",
                "Product Rule": "attempted",
            },
            "practice_problems": [],
        })
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_anthropic_response(fake_json))

        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                result = await summarize_session(
                    topic_name="Derivatives",
                    mode="practice",
                    conversation=[],
                    problems_attempted=3,
                    problems_solved=2,
                    hints_used=1,
                    duration_seconds=900,
                    topics_covered=["Derivatives", "Chain Rule", "Product Rule"],
                )
        valid = {"strong", "needs_work", "attempted"}
        for val in result["per_topic_performance"].values():
            assert val in valid, f"Unexpected performance value: {val!r}"

    @pytest.mark.anyio
    async def test_extended_mode_malformed_llm_response_degrades_gracefully(self):
        """Malformed JSON from LLM falls back to fallback dict — doesn't raise."""
        from agents.session_summarizer import summarize_session

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_anthropic_response("NOT JSON"))

        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                result = await summarize_session(
                    topic_name="Algebra",
                    mode="practice",
                    conversation=[{"role": "student", "content": "hi"}],
                    problems_attempted=1,
                    problems_solved=1,
                    hints_used=0,
                    duration_seconds=300,
                    topics_covered=["Algebra"],
                )
        assert isinstance(result, dict)
        assert "bullets" in result

    @pytest.mark.anyio
    async def test_extended_mode_practice_no_file_references(self):
        """Practice problems in summary must NOT reference filenames or uploads."""
        from agents.session_summarizer import summarize_session

        fake_json = json.dumps({
            "bullets": ["Did integration.", "Needed hints.", "Good progress."],
            "per_topic_performance": {"Integration": "needs_work"},
            "practice_problems": [
                r"Find $\int 2x\,dx$.",
                r"Compute $\int x^2\,dx$.",
            ],
        })
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_anthropic_response(fake_json))

        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                result = await summarize_session(
                    topic_name="Integration",
                    mode="practice",
                    conversation=[],
                    problems_attempted=2,
                    problems_solved=1,
                    hints_used=3,
                    duration_seconds=900,
                    topics_covered=["Integration"],
                )
        for p in result.get("practice_problems", []):
            assert ".png" not in p
            assert ".pdf" not in p
            assert "upload" not in p.lower()

    @pytest.mark.anyio
    async def test_extended_mode_empty_conversation(self):
        """Empty conversation should produce a valid dict summary."""
        from agents.session_summarizer import summarize_session

        with patch("config.ANTHROPIC_API_KEY", ""):
            result = await summarize_session(
                topic_name="",
                mode="practice",
                conversation=[],
                problems_attempted=0,
                problems_solved=0,
                hints_used=0,
                duration_seconds=0,
                topics_covered=[],
            )
        assert isinstance(result, dict)
        assert "bullets" in result

    @pytest.mark.anyio
    async def test_llm_exception_during_summarize_falls_back(self):
        """If the Anthropic call raises, summarize_session returns fallback dict."""
        from agents.session_summarizer import summarize_session

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("network error"))

        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                result = await summarize_session(
                    topic_name="Algebra",
                    mode="practice",
                    conversation=[],
                    problems_attempted=1,
                    problems_solved=0,
                    hints_used=0,
                    duration_seconds=300,
                    topics_covered=["Algebra"],
                )
        assert isinstance(result, dict)
        assert "bullets" in result


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3d — startup orphan sweep (api.py)
# ─────────────────────────────────────────────────────────────────────────────

class TestStartupOrphanSweep:
    def test_sweep_removes_old_dirs(self, tmp_path, monkeypatch):
        """_sweep_orphaned_uploads deletes dirs older than 24h."""
        import time
        import config
        import api as api_module

        monkeypatch.setattr(config, "DATA_DIR", tmp_path)

        old_dir = tmp_path / "session_uploads" / "old-session"
        old_dir.mkdir(parents=True)
        (old_dir / "file.png").write_bytes(b"data")

        new_dir = tmp_path / "session_uploads" / "new-session"
        new_dir.mkdir(parents=True)
        (new_dir / "file.png").write_bytes(b"data")

        # Make old_dir appear 25 hours old
        old_time = time.time() - 90000
        os.utime(old_dir, (old_time, old_time))

        api_module._sweep_orphaned_uploads()

        assert not old_dir.exists(), "Old dir should have been swept"
        assert new_dir.exists(), "New dir should be retained"

    def test_sweep_noop_when_no_upload_dir(self, tmp_path, monkeypatch):
        """_sweep_orphaned_uploads doesn't crash if session_uploads doesn't exist."""
        import config
        import api as api_module

        monkeypatch.setattr(config, "DATA_DIR", tmp_path)
        # No session_uploads directory at all
        api_module._sweep_orphaned_uploads()  # Should not raise
