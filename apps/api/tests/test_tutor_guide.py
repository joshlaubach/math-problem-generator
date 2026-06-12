"""
Tests for agents/tutor_guide.py

Covers:
- CONSTITUTION completeness (REQUIRED_RULES all present)
- Sync gate (GUIDE_SOURCE_SHA256 matches docs/ai_math_tutor_guide.md)
- select_snippets() priority order, cap, and signal logic
- should_inject_deep() four gate conditions (including raw-counter decoupling)
- select_topic_guidance() course-family lookup
"""
import sys
import os

# Ensure apps/api is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers — build a minimal TutorSession-like mock
# ---------------------------------------------------------------------------

def _make_session(
    *,
    attempts: list | None = None,
    consecutive_no_progress: int = 0,
    is_first_ever_session: bool = False,
    current_index: int = 0,
    topic_id: str = "alg1_unit2_topic3",
    topic_ids: list | None = None,
) -> MagicMock:
    s = MagicMock()
    s.attempts = attempts if attempts is not None else []
    s.consecutive_no_progress = consecutive_no_progress
    s.is_first_ever_session = is_first_ever_session
    s.current_index = current_index
    s.topic_id = topic_id
    s.topic_ids = topic_ids or []
    return s


# ---------------------------------------------------------------------------
# CONSTITUTION completeness
# ---------------------------------------------------------------------------

class TestConstitutionCompleteness:
    def test_required_rules_present(self):
        from agents.tutor_guide import CONSTITUTION, REQUIRED_RULES
        for phrase in REQUIRED_RULES:
            assert phrase.lower() in CONSTITUTION.lower(), (
                f"REQUIRED_RULES phrase missing from CONSTITUTION: {phrase!r}"
            )

    def test_constitution_not_empty(self):
        from agents.tutor_guide import CONSTITUTION
        assert len(CONSTITUTION) > 500, "CONSTITUTION seems too short"

    def test_output_constraints_not_empty(self):
        from agents.tutor_guide import OUTPUT_CONSTRAINTS
        assert "LaTeX" in OUTPUT_CONSTRAINTS
        assert "dollar signs" in OUTPUT_CONSTRAINTS

    def test_role_layers_have_six_roles(self):
        from agents.tutor_guide import ROLE_LAYERS
        for role in ("SOCRATIC", "LESSON", "OPENING", "PACING", "DRAWING", "SUMMARY"):
            assert role in ROLE_LAYERS, f"Missing role layer: {role}"
            assert len(ROLE_LAYERS[role]) > 50, f"Role layer {role} seems too short"

    def test_scenario_snippets_keys_present(self):
        from agents.tutor_guide import SCENARIO_SNIPPETS
        for key in ("anxiety", "frustration", "answer_refusal", "repair", "stuck", "misconception", "verify"):
            assert key in SCENARIO_SNIPPETS, f"Missing snippet: {key}"

    def test_lesson_layer_forbids_live_problem_solve(self):
        """Regression (audit Scenario E): lesson mode must never work the
        student's own problem to completion."""
        from agents.tutor_guide import ROLE_LAYERS
        lesson = ROLE_LAYERS["LESSON"]
        assert "NEVER use the student's current problem" in lesson
        assert "parallel problem" in lesson

    def test_socratic_layer_forbids_inline_formatting(self):
        """Regression (audit Scenario C): no bold/italics in conversational replies."""
        from agents.tutor_guide import ROLE_LAYERS
        assert "never use bold" in ROLE_LAYERS["SOCRATIC"].lower()


# ---------------------------------------------------------------------------
# Sync gate
# ---------------------------------------------------------------------------

class TestSyncGate:
    def test_guide_source_in_sync(self):
        """GUIDE_SOURCE_SHA256 must match the current docs/ai_math_tutor_guide.md."""
        from agents.tutor_guide import GUIDE_SOURCE_SHA256, compute_guide_sha256
        actual = compute_guide_sha256()
        if not actual:
            pytest.skip("docs/ai_math_tutor_guide.md not found — skipping sync gate")
        assert actual == GUIDE_SOURCE_SHA256, (
            f"docs/ai_math_tutor_guide.md has changed but GUIDE_SOURCE_SHA256 was not "
            f"updated.\n  Expected: {GUIDE_SOURCE_SHA256}\n  Got:      {actual}\n"
            "Re-review tutor_guide.py constants then update GUIDE_SOURCE_SHA256."
        )


# ---------------------------------------------------------------------------
# select_snippets()
# ---------------------------------------------------------------------------

class TestSelectSnippets:
    def test_anxiety_fires_on_keyword(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("I'm freaking out about this problem", s)
        assert "anxiety" in result

    def test_frustration_fires_on_keyword(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("I hate this, it's so stupid", s)
        assert "frustration" in result

    def test_answer_refusal_fires(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("just give me the answer please", s)
        assert "answer_refusal" in result

    def test_stuck_fires_on_idk(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("idk where to start", s)
        assert "stuck" in result

    def test_verify_fires_on_ok(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("ok", s)
        assert "verify" in result

    def test_misconception_fires_on_two_attempts(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=["x=3", "x=5"])  # 2 wrong attempts
        result = select_snippets("I think x=7", s)
        assert "misconception" in result

    def test_misconception_does_not_fire_on_one_attempt(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=["x=3"])  # only 1
        result = select_snippets("I think x=7", s)
        assert "misconception" not in result

    def test_max_two_snippets_returned(self):
        from agents.tutor_guide import select_snippets
        # Fire anxiety + frustration + stuck simultaneously
        s = _make_session(attempts=[])
        result = select_snippets("I'm freaking out I hate this idk where to start", s)
        assert len(result) <= 2

    def test_priority_order_anxiety_beats_frustration(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("I'm freaking out I hate this", s)
        assert result[0] == "anxiety", f"Expected anxiety first, got {result}"

    def test_frustration_before_answer_refusal(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("I hate this just give me the answer", s)
        # frustration (rank 2) should beat answer_refusal (rank 3)
        if "frustration" in result and "answer_refusal" in result:
            assert result.index("frustration") < result.index("answer_refusal")

    def test_empty_message_no_snippets(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("", s)
        assert result == []

    def test_returns_list(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("Let me try x = 4", s)
        assert isinstance(result, list)

    # ── Audit regressions: signal-reading fixes ──────────────────────────────

    def test_answer_refusal_not_fired_by_genuine_attempt(self):
        """'is the answer x=2?' is an attempt, not a demand — must NOT fire."""
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        result = select_snippets("is the answer x=2?", s)
        assert "answer_refusal" not in result

    def test_answer_refusal_still_fires_on_demand(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        for msg in ("just tell me the answer", "what's the answer",
                    "give me the answer", "solve it for me"):
            assert "answer_refusal" in select_snippets(msg, s), msg

    def test_frustration_negation_guard(self):
        """'I'm not stupid' / 'I won't give up' must NOT fire frustration."""
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        assert "frustration" not in select_snippets("I'm not stupid, I just missed a sign", s)
        assert "frustration" not in select_snippets("I'm not giving up on this", s)

    def test_frustration_still_fires_without_negation(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        assert "frustration" in select_snippets("this is stupid I hate it", s)

    def test_verify_fires_with_whats_next_tail(self):
        """'got it, what's next?' is still a confirmation signal."""
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        assert "verify" in select_snippets("got it, what's next?", s)
        assert "verify" in select_snippets("ok, next one", s)

    def test_verify_not_fired_by_followup_question(self):
        """'ok, but why ...' is a question, not a confirmation."""
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        assert "verify" not in select_snippets("ok, but why is row 2 negative?", s)

    def test_repair_fires_on_repeat_request(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        for msg in ("wait, what did you say?", "can you say that again",
                    "repeat that please", "sorry I didn't catch that"):
            assert "repair" in select_snippets(msg, s), msg

    def test_misconception_fires_on_soft_errors(self):
        """Chat-borne corrected errors count toward the misconception gate."""
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=[])
        s.soft_error_count = 2
        assert "misconception" in select_snippets("I think x=7", s)

    def test_misconception_fires_on_mixed_attempt_and_soft_error(self):
        from agents.tutor_guide import select_snippets
        s = _make_session(attempts=["x=3"])
        s.soft_error_count = 1
        assert "misconception" in select_snippets("I think x=7", s)


class TestLooksLikeCorrection:
    def test_positive_phrases(self):
        from agents.tutor_guide import looks_like_correction
        for reply in (
            "Not quite, check the second row again. What changed?",
            "I see where you're going, but the columns and rows got swapped somewhere.",
            "Close, but there's a sign error in step 2. Where did it come from?",
        ):
            assert looks_like_correction(reply), reply

    def test_negative_phrases(self):
        from agents.tutor_guide import looks_like_correction
        for reply in (
            "Go ahead.",
            "Right, that's the augmented matrix. What's your next row operation?",
            "Good instinct. What does that give you for y?",
        ):
            assert not looks_like_correction(reply), reply


# ---------------------------------------------------------------------------
# should_inject_deep()
# ---------------------------------------------------------------------------

class TestShouldInjectDeep:
    def test_fires_on_consecutive_no_progress(self):
        from agents.tutor_guide import should_inject_deep, ESCALATION_THRESHOLD
        s = _make_session(consecutive_no_progress=ESCALATION_THRESHOLD)
        assert should_inject_deep(s, [])

    def test_fires_on_anxiety_snippet(self):
        from agents.tutor_guide import should_inject_deep
        s = _make_session(consecutive_no_progress=0)
        assert should_inject_deep(s, ["anxiety"])

    def test_fires_on_two_raw_attempts(self):
        from agents.tutor_guide import should_inject_deep
        # 2 wrong attempts — raw counter, NOT the snippet list
        s = _make_session(attempts=["wrong1", "wrong2"], consecutive_no_progress=0)
        # snippets list has NO misconception (e.g. filled by anxiety+frustration)
        assert should_inject_deep(s, ["anxiety", "frustration"])

    def test_fires_on_first_ever_session_at_index_zero(self):
        from agents.tutor_guide import should_inject_deep
        s = _make_session(is_first_ever_session=True, current_index=0)
        assert should_inject_deep(s, [])

    def test_does_not_fire_on_first_ever_session_past_index_zero(self):
        from agents.tutor_guide import should_inject_deep
        s = _make_session(is_first_ever_session=True, current_index=1)
        assert not should_inject_deep(s, [])

    def test_does_not_fire_when_no_signals(self):
        from agents.tutor_guide import should_inject_deep
        s = _make_session(
            attempts=[],
            consecutive_no_progress=0,
            is_first_ever_session=False,
            current_index=0,
        )
        assert not should_inject_deep(s, [])

    def test_fires_on_soft_errors(self):
        """Two chat-borne corrected errors open the deep gate even with no
        formal answer submissions."""
        from agents.tutor_guide import should_inject_deep
        s = _make_session(attempts=[], consecutive_no_progress=0)
        s.soft_error_count = 2
        assert should_inject_deep(s, [])

    def test_raw_counter_independent_of_snippet_cap(self):
        """
        Regression: anxiety+frustration fill the 2-snippet cap, so "misconception"
        never appears in snippets even when session.attempts >= 2. The raw counter
        check in should_inject_deep must still catch it.
        """
        from agents.tutor_guide import should_inject_deep
        s = _make_session(attempts=["x=3", "x=5"], consecutive_no_progress=0)
        # snippets list deliberately omits "misconception"
        snippets_without_misconception = ["anxiety", "frustration"]
        assert should_inject_deep(s, snippets_without_misconception)


# ---------------------------------------------------------------------------
# select_topic_guidance()
# ---------------------------------------------------------------------------

class TestSelectTopicGuidance:
    def test_algebra1_prefix_matches(self):
        from agents.tutor_guide import select_topic_guidance, TOPIC_GUIDANCE
        s = _make_session(topic_id="alg1_unit2_topic3")
        guidance = select_topic_guidance(s)
        assert guidance == TOPIC_GUIDANCE["algebra_1"]

    def test_calculus_prefix_matches(self):
        from agents.tutor_guide import select_topic_guidance, TOPIC_GUIDANCE
        s = _make_session(topic_id="calc_ab_derivatives")
        guidance = select_topic_guidance(s)
        assert guidance == TOPIC_GUIDANCE["calculus"]

    def test_geometry_prefix_matches(self):
        from agents.tutor_guide import select_topic_guidance, TOPIC_GUIDANCE
        s = _make_session(topic_id="geo_proofs_congruence")
        guidance = select_topic_guidance(s)
        assert guidance == TOPIC_GUIDANCE["geometry"]

    def test_unknown_topic_returns_none(self):
        from agents.tutor_guide import select_topic_guidance
        s = _make_session(topic_id="unknown_xyz_topic_99")
        assert select_topic_guidance(s) is None

    def test_empty_topic_returns_none(self):
        from agents.tutor_guide import select_topic_guidance
        s = _make_session(topic_id="", topic_ids=[])
        assert select_topic_guidance(s) is None

    def test_falls_back_to_topic_ids_when_topic_id_empty(self):
        from agents.tutor_guide import select_topic_guidance, TOPIC_GUIDANCE
        s = _make_session(topic_id="", topic_ids=["alg1_unit1_topic1"])
        guidance = select_topic_guidance(s)
        assert guidance == TOPIC_GUIDANCE["algebra_1"]
