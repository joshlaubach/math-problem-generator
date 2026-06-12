"""Tests for progress_store.py — cross-session mastery persistence (L1/7B)."""
import pytest

import progress_store


@pytest.fixture()
def jsonl_store(tmp_path, monkeypatch):
    monkeypatch.setattr(progress_store, "PROGRESS_JSONL_PATH", tmp_path / "progress.jsonl")
    monkeypatch.setattr(progress_store, "_uses_database", lambda: False)


class TestApplySessionResults:
    def test_strong_increases_mastery_and_difficulty(self, jsonl_store):
        progress_store.apply_session_results("u1", {"alg1_t1": "strong"})
        rec = progress_store.get_progress("u1", "alg1_t1")
        assert rec["mastery_score"] == pytest.approx(0.10)
        assert rec["current_conceptual_diff"] == 2
        assert rec["streak"] == 1

    def test_needs_work_decreases(self, jsonl_store):
        progress_store.apply_session_results("u1", {"t": "strong"})
        progress_store.apply_session_results("u1", {"t": "needs_work"})
        rec = progress_store.get_progress("u1", "t")
        assert rec["mastery_score"] == pytest.approx(0.05)
        assert rec["current_conceptual_diff"] == 1
        assert rec["streak"] == 0

    def test_attempted_small_positive(self, jsonl_store):
        progress_store.apply_session_results("u1", {"t": "attempted"})
        rec = progress_store.get_progress("u1", "t")
        assert rec["mastery_score"] == pytest.approx(0.02)
        assert rec["current_conceptual_diff"] == 1  # attempted doesn't bump difficulty

    def test_mastery_clamped_to_unit_interval(self, jsonl_store):
        for _ in range(15):
            progress_store.apply_session_results("u1", {"t": "strong"})
        assert progress_store.get_progress("u1", "t")["mastery_score"] <= 1.0

        for _ in range(30):
            progress_store.apply_session_results("u1", {"t": "needs_work"})
        assert progress_store.get_progress("u1", "t")["mastery_score"] >= 0.0

    def test_difficulty_clamped_1_to_5(self, jsonl_store):
        for _ in range(10):
            progress_store.apply_session_results("u1", {"t": "strong"})
        assert progress_store.get_progress("u1", "t")["current_conceptual_diff"] == 5

    def test_single_session_delta_capped(self):
        """The risk-register rail: no grade may exceed MAX_SESSION_DELTA."""
        assert all(
            abs(d) <= progress_store.MAX_SESSION_DELTA
            for d in progress_store._PERFORMANCE_DELTAS.values()
        )

    def test_unknown_grade_ignored(self, jsonl_store):
        progress_store.apply_session_results("u1", {"t": "banana"})
        assert progress_store.get_progress("u1", "t") is None

    def test_srs_schedule_written(self, jsonl_store):
        progress_store.apply_session_results("u1", {"t": "strong"})
        rec = progress_store.get_progress("u1", "t")
        assert rec["next_review_at"] is not None


class TestSeedDifficulty:
    def test_new_student_gets_default(self, jsonl_store):
        assert progress_store.seed_difficulty("nobody", "t", default=3) == 3

    def test_returning_student_gets_stored(self, jsonl_store):
        progress_store.apply_session_results("u1", {"t": "strong"})
        progress_store.apply_session_results("u1", {"t": "strong"})
        assert progress_store.seed_difficulty("u1", "t", default=1) == 3

    def test_never_raises(self, jsonl_store, monkeypatch):
        monkeypatch.setattr(progress_store, "get_progress",
                            lambda *a: (_ for _ in ()).throw(RuntimeError("db down")))
        assert progress_store.seed_difficulty("u1", "t", default=2) == 2


class TestWeakTopics:
    def test_weak_topic_surfaces(self, jsonl_store):
        progress_store.apply_session_results("u1", {"weak_t": "needs_work"})
        progress_store.apply_session_results("u1", {"strong_t": "strong"})
        for _ in range(5):
            progress_store.apply_session_results("u1", {"strong_t": "strong"})

        weak = progress_store.weak_topics("u1", ["weak_t", "strong_t", "untouched_t"])
        ids = [tid for tid, _ in weak]
        assert "weak_t" in ids
        assert "strong_t" not in ids
        assert "untouched_t" not in ids  # never seen → not "weak", just new
