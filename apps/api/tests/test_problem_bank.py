"""Tests for problem_bank.py — bank-first supply with per-student dedup (L1)."""
import pytest

import problem_bank
import session_quota
from agents.schemas import GeneratedProblem, WorkedStep, Distractor


def _make_problem(statement="Solve $x+1=5$"):
    return GeneratedProblem(
        statement=statement,
        answer="4",
        worked_steps=[WorkedStep(step="Subtract 1", explanation="Both sides")],
        hint_ladder=["H1", "H2", "H3", "H4"],
        distractors=[
            Distractor(answer="3", mistake="off by one"),
            Distractor(answer="5", mistake="added"),
            Distractor(answer="6", mistake="arithmetic"),
        ],
    )


@pytest.fixture()
def jsonl_bank(tmp_path, monkeypatch):
    monkeypatch.setattr(problem_bank, "BANK_JSONL_PATH", tmp_path / "bank.jsonl")
    monkeypatch.setattr(problem_bank, "_uses_database", lambda: False)
    monkeypatch.setattr(session_quota, "QUOTA_LOG_PATH", tmp_path / "quota.jsonl")
    monkeypatch.setattr(session_quota, "_uses_database", lambda: False)
    return tmp_path


class TestSaveAndFetch:
    def test_round_trip(self, jsonl_bank):
        pid = problem_bank.save_generated(_make_problem(), topic_id="alg1_t1", conceptual_diff=3)
        assert pid.startswith("bank-")

        fetched = problem_bank.fetch_unserved("student-1", "alg1_t1", 3)
        assert len(fetched) == 1
        assert fetched[0].statement == "Solve $x+1=5$"
        assert fetched[0].problem_id == pid

    def test_dedup_excludes_served(self, jsonl_bank):
        """The launch rule: cross-student reuse yes, same-student repeat never."""
        pid = problem_bank.save_generated(_make_problem(), topic_id="t", conceptual_diff=3)
        session_quota.record_served_problem("student-1", pid, "sess-1")

        assert problem_bank.fetch_unserved("student-1", "t", 3) == []
        # A different student still gets it (cross-student reuse)
        other = problem_bank.fetch_unserved("student-2", "t", 3)
        assert len(other) == 1 and other[0].problem_id == pid

    def test_difficulty_tolerance_and_ordering(self, jsonl_bank):
        problem_bank.save_generated(_make_problem("near"), topic_id="t", conceptual_diff=4)
        problem_bank.save_generated(_make_problem("exact"), topic_id="t", conceptual_diff=3)
        problem_bank.save_generated(_make_problem("far"), topic_id="t", conceptual_diff=5)

        fetched = problem_bank.fetch_unserved("s", "t", 3, limit=3)
        statements = [p.statement for p in fetched]
        assert statements[0] == "exact"          # exact difficulty first
        assert "far" not in statements           # outside ±1 tolerance

    def test_other_topic_not_returned(self, jsonl_bank):
        problem_bank.save_generated(_make_problem(), topic_id="t1", conceptual_diff=3)
        assert problem_bank.fetch_unserved("s", "t2", 3) == []

    def test_fetch_never_raises(self, jsonl_bank, monkeypatch):
        monkeypatch.setattr(session_quota, "get_served_problem_ids",
                            lambda uid: (_ for _ in ()).throw(RuntimeError("down")))
        assert problem_bank.fetch_unserved("s", "t", 3) == []


class TestServedTracking:
    def test_record_and_get(self, jsonl_bank):
        session_quota.record_served_problem("u", "bank-abc", "sess-1")
        session_quota.record_served_problem("u", "bank-def", "sess-2")
        assert session_quota.get_served_problem_ids("u") == {"bank-abc", "bank-def"}

    def test_served_does_not_count_against_problem_quota(self, jsonl_bank):
        before = session_quota.get_problems_used("u")
        session_quota.record_served_problem("u", "bank-abc", "sess-1")
        assert session_quota.get_problems_used("u") == before
