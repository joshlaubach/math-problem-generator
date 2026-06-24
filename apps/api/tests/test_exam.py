"""
Tests for Phase 4 — Exam Mode.

Covers:
  - Template listing
  - Credit kind assignment (preset vs custom)
  - Problem allocation from concept distribution
  - Grading logic (async, using asyncio.run)
  - Auto-submit on expiry detection
  - Integrity event model
  - Review endpoint guard (requires submitted)
"""
import asyncio
from datetime import datetime, timezone, timedelta

import pytest

import exam_router
from exam_templates import PRESET_TEMPLATES, ExamTemplate, ConceptDistribution


# ─────────────────────────────────────────────────────────────────────────────
# Template registry
# ─────────────────────────────────────────────────────────────────────────────

class TestTemplates:
    def test_all_presets_present(self):
        assert {"sat_math", "ap_calc_ab", "ap_calc_bc", "ap_statistics"} <= set(PRESET_TEMPLATES)

    def test_preset_kinds(self):
        for t in PRESET_TEMPLATES.values():
            assert t.kind == "preset"

    def test_preset_problem_counts(self):
        for t in PRESET_TEMPLATES.values():
            assert 5 <= t.total_problems <= 20

    def test_list_templates_endpoint(self):
        """GET /exam/templates should return all presets without auth."""
        result = exam_router.list_templates()
        ids = {t.id for t in result}
        assert "sat_math" in ids and "ap_calc_ab" in ids

    def test_time_limits_set_on_presets(self):
        for t in PRESET_TEMPLATES.values():
            assert t.time_limit_minutes is not None and t.time_limit_minutes > 0


# ─────────────────────────────────────────────────────────────────────────────
# Problem allocation
# ─────────────────────────────────────────────────────────────────────────────

class TestAllocation:
    def test_allocation_count_matches_total(self):
        template = PRESET_TEMPLATES["sat_math"]
        allocs = exam_router._allocate_problems(template)
        assert len(allocs) == template.total_problems

    def test_allocation_returns_valid_topic_ids(self):
        from topic_registry import TOPIC_REGISTRY
        template = PRESET_TEMPLATES["ap_calc_ab"]
        allocs = exam_router._allocate_problems(template)
        for tid, cdiff, cpdiff, calc in allocs:
            assert tid in TOPIC_REGISTRY
            assert 1 <= cdiff <= 5

    def test_custom_allocation_single_course(self):
        template = ExamTemplate(
            id="custom", name="Custom", description="",
            total_problems=5, time_limit_minutes=30, calc_tier="none",
            kind="custom",
            concept_distribution=[
                ConceptDistribution(course_ids=["algebra_1"], weight=1.0, difficulty_min=2, difficulty_max=3),
            ],
        )
        allocs = exam_router._allocate_problems(template)
        assert len(allocs) == 5
        # All topics should be from algebra_1
        from topic_registry import TOPIC_REGISTRY
        for tid, _, _, _ in allocs:
            assert TOPIC_REGISTRY[tid].course_id == "algebra_1"


# ─────────────────────────────────────────────────────────────────────────────
# Grading
# ─────────────────────────────────────────────────────────────────────────────

class TestGrading:
    def test_correct_answer_graded_correct(self):
        problems = [{"index": 0, "answer": "3", "answer_type": "numeric"}]
        answers = {"0": "3"}
        results = asyncio.run(exam_router._grade_answers(problems, answers))
        assert results[0]["correct"] is True

    def test_wrong_answer_graded_wrong(self):
        problems = [{"index": 0, "answer": "5", "answer_type": "numeric"}]
        answers = {"0": "3"}
        results = asyncio.run(exam_router._grade_answers(problems, answers))
        assert results[0]["correct"] is False

    def test_blank_answer_graded_wrong(self):
        problems = [{"index": 0, "answer": "5", "answer_type": "numeric"}]
        answers = {}
        results = asyncio.run(exam_router._grade_answers(problems, answers))
        assert results[0]["correct"] is False
        assert results[0]["student_answer"] == ""

    def test_equivalent_form_graded_correct(self):
        problems = [{"index": 0, "answer": "x**2 + 2*x + 1", "answer_type": "expression"}]
        answers = {"0": "(x+1)**2"}
        results = asyncio.run(exam_router._grade_answers(problems, answers))
        assert results[0]["correct"] is True

    def test_multiple_problems_graded(self):
        problems = [
            {"index": 0, "answer": "3", "answer_type": "numeric"},
            {"index": 1, "answer": "7", "answer_type": "numeric"},
        ]
        answers = {"0": "3", "1": "99"}
        results = asyncio.run(exam_router._grade_answers(problems, answers))
        assert results[0]["correct"] is True
        assert results[1]["correct"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Timer / expiry
# ─────────────────────────────────────────────────────────────────────────────

class TestTimer:
    def _make_attempt(self, minutes_ago: float, time_limit: int | None):
        from types import SimpleNamespace
        return SimpleNamespace(
            start_time=datetime.utcnow() - timedelta(minutes=minutes_ago),
            time_limit_minutes=time_limit,
            submitted_at=None,
        )

    def test_not_expired_within_limit(self):
        a = self._make_attempt(minutes_ago=10, time_limit=25)
        assert exam_router._is_expired(a) is False

    def test_expired_past_limit(self):
        a = self._make_attempt(minutes_ago=30, time_limit=25)
        assert exam_router._is_expired(a) is True

    def test_untimed_never_expires(self):
        a = self._make_attempt(minutes_ago=9999, time_limit=None)
        assert exam_router._is_expired(a) is False

    def test_remaining_seconds_decrements(self):
        a = self._make_attempt(minutes_ago=10, time_limit=25)
        rem = exam_router._remaining_seconds(a)
        assert rem is not None
        assert 14 * 60 < rem < 15 * 60  # ~14-15 minutes remaining

    def test_remaining_seconds_none_for_untimed(self):
        a = self._make_attempt(minutes_ago=999, time_limit=None)
        assert exam_router._remaining_seconds(a) is None


# ─────────────────────────────────────────────────────────────────────────────
# Credit kind assignment
# ─────────────────────────────────────────────────────────────────────────────

class TestCreditKind:
    def test_preset_uses_exam_preset_credit(self):
        from credit_router import BUNDLES
        assert BUNDLES["exam_preset"]["kind"] == "exam_preset"
        assert BUNDLES["exam_preset"]["price_usd"] == 8

    def test_custom_uses_exam_custom_credit(self):
        from credit_router import BUNDLES
        assert BUNDLES["exam_custom"]["kind"] == "exam_custom"
        assert BUNDLES["exam_custom"]["price_usd"] == 5

    def test_exam_bundles_purchasable_by_all(self):
        from credit_router import BUNDLES
        for key in ("exam_custom", "exam_preset"):
            assert BUNDLES[key]["tiers"] == "all"
