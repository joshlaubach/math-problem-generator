"""
Phase 1.1 streaming pipeline tests: math-aware sentence splitting, the
orchestrator's agent_sentence emission, and barge-in cancellation semantics
(partial reply committed to the conversation).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sentences import SentenceAccumulator, split_sentences


# ── split_sentences ───────────────────────────────────────────────────────────

def test_split_basic():
    assert split_sentences("First one. Second one.") == ["First one.", "Second one."]


def test_split_never_breaks_math():
    text = "Look at $f(x) = 2. 5x$ carefully. What do you see?"
    parts = split_sentences(text)
    assert parts[0] == "Look at $f(x) = 2. 5x$ carefully."
    assert parts[1] == "What do you see?"


def test_split_decimals_survive():
    parts = split_sentences("The answer is about 3.14 here. Try again.")
    assert parts == ["The answer is about 3.14 here.", "Try again."]


def test_split_question_and_exclaim():
    parts = split_sentences("Nice work! What comes next?")
    assert parts == ["Nice work!", "What comes next?"]


def test_split_single_sentence_no_terminator():
    assert split_sentences("just a fragment") == ["just a fragment"]


# ── SentenceAccumulator ───────────────────────────────────────────────────────

def test_accumulator_streams_sentences_incrementally():
    acc = SentenceAccumulator()
    out: list[str] = []
    for chunk in ["Right, so ", "start there. Now ", "what is $x$?", ""]:
        out.extend(acc.feed(chunk))
    out.extend(acc.flush())
    assert out == ["Right, so start there.", "Now what is $x$?"]
    assert acc.full_text == "Right, so start there. Now what is $x$?"


def test_accumulator_holds_math_span_open():
    acc = SentenceAccumulator()
    out = list(acc.feed("Consider $a. b"))
    assert out == []  # inside math — never split
    out += acc.feed("$ now. Done?")
    out += acc.flush()
    assert out == ["Consider $a. b$ now.", "Done?"]


# ── Orchestrator emission + cancellation ─────────────────────────────────────

def _session():
    return SimpleNamespace(
        session_id="s1", user_id="u1", topic_id="t1", difficulty=3,
        conversation=[], attempts=[], hint_level=0, is_solved=False,
        consecutive_no_progress=0, soft_error_count=0,
        problem=SimpleNamespace(statement="Solve $x+1=2$", answer="1",
                                hint_ladder=["h1", "h2"]),
        walkthrough_active=False, exam_mode=False, exam_mode_proposed=False,
        class_name="Algebra", session_summary=[], tutor_name="Josh",
        topic_ids=["t1"], history_briefing="", current_index=0,
        concept_lesson_counts={},
    )


def _deps(gen, emitted_msgs):
    import session_orchestrator as so

    async def emit(msg):
        emitted_msgs.append(msg)

    return so.SessionDeps(
        generate_tutor_response=gen,
        handle_going_too_fast=None,
        check_quiz_readiness=lambda s: False,
        get_quiz_proposal=None,
        get_quiz_start_message=None,
        check_answer=None,
        get_hint=None,
        log_event=lambda **k: None,
        update_session=lambda s: None,
        looks_like_correction=lambda r: False,
        user_tier="free",
        emit_partial=emit,
    )


@pytest.mark.asyncio
async def test_post_hoc_sentence_emission_for_unstreamed_reply():
    """A non-streaming generate stub still yields agent_sentence frames."""
    import session_orchestrator as so

    async def gen(session, message, force_lesson=False):
        return "First part. Second part?", False

    emitted: list[dict] = []
    session = _session()
    user = SimpleNamespace(id="u1", tier="free")
    res = await so.handle(session, user, {"type": "student_text", "text": "hi"},
                          _deps(gen, emitted))

    sentence_frames = [m for m in emitted if m["type"] == "agent_sentence"]
    assert [m["text"] for m in sentence_frames] == ["First part.", "Second part?"]
    assert len({m["turn_id"] for m in sentence_frames}) == 1
    agent_texts = [m for m in res.messages if m.type == "agent_text"]
    assert agent_texts[0].payload["text"] == "First part. Second part?"
    assert agent_texts[0].payload["turn_id"] == sentence_frames[0]["turn_id"]


@pytest.mark.asyncio
async def test_streaming_stub_receives_on_sentence_and_no_double_emission():
    """A streaming-capable stub gets on_sentence; orchestrator must not re-emit."""
    import session_orchestrator as so

    async def gen(session, message, force_lesson=False, on_sentence=None):
        assert on_sentence is not None
        await on_sentence(0, "Streamed one.")
        await on_sentence(1, "Streamed two?")
        return "Streamed one. Streamed two?", False

    emitted: list[dict] = []
    session = _session()
    user = SimpleNamespace(id="u1", tier="free")
    await so.handle(session, user, {"type": "student_text", "text": "hi"},
                    _deps(gen, emitted))

    texts = [m["text"] for m in emitted if m["type"] == "agent_sentence"]
    assert texts == ["Streamed one.", "Streamed two?"]  # exactly once each


@pytest.mark.asyncio
async def test_barge_in_cancellation_commits_partial_reply():
    """Cancelling mid-stream appends the already-spoken sentences to history."""
    import session_orchestrator as so

    started = asyncio.Event()

    async def gen(session, message, force_lesson=False, on_sentence=None):
        await on_sentence(0, "You started well.")
        started.set()
        await asyncio.sleep(30)  # simulates Claude still generating
        return "never reached", False

    emitted: list[dict] = []
    session = _session()
    user = SimpleNamespace(id="u1", tier="free")

    task = asyncio.create_task(
        so.handle(session, user, {"type": "student_text", "text": "help"},
                  _deps(gen, emitted))
    )
    await asyncio.wait_for(started.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Student turn + the partial tutor sentence are both in the conversation
    assert session.conversation[-1] == {"role": "tutor", "content": "You started well."}
