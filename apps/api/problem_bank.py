"""
Problem bank — lazy cache of tutor-generated problems (launch decision
2026-06-12: bank-first supply with cross-student reuse).

Every Mode B generation costs LLM dollars and 5-20s of student-facing latency.
The bank makes each problem a one-time cost: generated once, audited async,
served to any student who hasn't seen it (per-student dedup via
session_quota served events).

Storage: ProblemRecord (problems table) when USE_DATABASE=true, using the
spec-aligned columns (statement/answer/worked_steps_json/hint_ladder_json/
distractors_json/conceptual_diff). data/problem_bank.jsonl in dev/test.

The async audit prunes by setting is_flagged=True — flagged problems are
never served from the bank again.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agents.schemas import GeneratedProblem

logger = logging.getLogger(__name__)

BANK_JSONL_PATH = Path("data/problem_bank.jsonl")


def _uses_database() -> bool:
    from config import USE_DATABASE
    return USE_DATABASE


# ── Save ───────────────────────────────────────────────────────────────────────

def save_generated(
    problem: GeneratedProblem,
    *,
    topic_id: str,
    course_id: str = "",
    unit_id: str = "",
    conceptual_diff: int = 3,
    computational_diff: int = 3,
    calc_tier: str = "none",
) -> str:
    """Persist a freshly generated problem to the bank. Returns its bank id."""
    problem_id = f"bank-{uuid.uuid4()}"

    if _uses_database():
        _save_db(problem_id, problem, topic_id, course_id, unit_id,
                 conceptual_diff, computational_diff, calc_tier)
    else:
        _save_jsonl(problem_id, problem, topic_id, course_id, unit_id,
                    conceptual_diff, computational_diff, calc_tier)
    return problem_id


def _save_db(problem_id, problem, topic_id, course_id, unit_id,
             conceptual_diff, computational_diff, calc_tier) -> None:
    from db_models import ProblemRecord
    from db_session import get_session

    db = get_session()
    try:
        db.add(ProblemRecord(
            id=problem_id,
            course_id=course_id,
            unit_id=unit_id,
            topic_id=topic_id,
            difficulty=conceptual_diff,
            calculator_mode=calc_tier,
            prompt_latex=problem.statement,           # legacy columns kept populated
            answer_type="expression",
            final_answer_json=json.dumps(problem.answer),
            solution_json="{}",
            metadata_json=json.dumps({"origin": "tutor_mode_b"}),
            statement=problem.statement,
            answer=problem.answer,
            worked_steps_json=json.dumps([s.model_dump() for s in problem.worked_steps]),
            hint_ladder_json=json.dumps(problem.hint_ladder),
            distractors_json=json.dumps([d.model_dump() for d in problem.distractors]),
            conceptual_diff=conceptual_diff,
            computational_diff=computational_diff,
            calc_tier=calc_tier,
            verified=True,  # Mode B output is SymPy post-verified before return
        ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _save_jsonl(problem_id, problem, topic_id, course_id, unit_id,
                conceptual_diff, computational_diff, calc_tier) -> None:
    BANK_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "id": problem_id,
        "topic_id": topic_id,
        "course_id": course_id,
        "unit_id": unit_id,
        "conceptual_diff": conceptual_diff,
        "computational_diff": computational_diff,
        "calc_tier": calc_tier,
        "is_flagged": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "problem": problem.model_dump(),
    }
    with BANK_JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ── Fetch ──────────────────────────────────────────────────────────────────────

def fetch_unserved(
    user_id: str,
    topic_id: str,
    conceptual_diff: int,
    limit: int = 2,
    diff_tolerance: int = 1,
) -> list[GeneratedProblem]:
    """
    Bank problems for this topic near this difficulty that THIS student has
    never seen. Exact-difficulty matches first, then ±diff_tolerance.
    Returned problems carry problem_id. Never raises.
    """
    try:
        from session_quota import get_served_problem_ids
        served = get_served_problem_ids(user_id)

        candidates = (
            _fetch_db(topic_id, conceptual_diff, diff_tolerance)
            if _uses_database()
            else _fetch_jsonl(topic_id, conceptual_diff, diff_tolerance)
        )

        fresh = [(diff, p) for diff, p in candidates if p.problem_id not in served]
        # Exact difficulty first, then nearest
        fresh.sort(key=lambda pair: abs(pair[0] - conceptual_diff))
        return [p for _, p in fresh[:limit]]
    except Exception as exc:
        logger.warning("Bank fetch failed for %s/%s: %s", user_id, topic_id, exc)
        return []


def _record_to_problem(rec) -> GeneratedProblem | None:
    """ProblemRecord (spec-aligned columns) → GeneratedProblem, or None."""
    try:
        if not rec.statement or not rec.answer:
            return None
        return GeneratedProblem(
            statement=rec.statement,
            answer=rec.answer,
            worked_steps=json.loads(rec.worked_steps_json or "[]"),
            hint_ladder=json.loads(rec.hint_ladder_json or "[]"),
            distractors=json.loads(rec.distractors_json or "[]"),
            problem_id=rec.id,
        )
    except Exception:
        return None  # malformed bank rows are skipped, never fatal


def _fetch_db(topic_id: str, conceptual_diff: int, tol: int) -> list[tuple[int, GeneratedProblem]]:
    from db_models import ProblemRecord
    from db_session import get_session

    db = get_session()
    try:
        rows = (
            db.query(ProblemRecord)
            .filter(
                ProblemRecord.topic_id == topic_id,
                ProblemRecord.is_flagged.is_(False),
                ProblemRecord.statement.isnot(None),
                ProblemRecord.conceptual_diff.isnot(None),
                ProblemRecord.conceptual_diff >= conceptual_diff - tol,
                ProblemRecord.conceptual_diff <= conceptual_diff + tol,
            )
            .limit(50)
            .all()
        )
        out = []
        for r in rows:
            p = _record_to_problem(r)
            if p is not None:
                out.append((r.conceptual_diff, p))
        return out
    finally:
        db.close()


def _fetch_jsonl(topic_id: str, conceptual_diff: int, tol: int) -> list[tuple[int, GeneratedProblem]]:
    if not BANK_JSONL_PATH.exists():
        return []
    out: list[tuple[int, GeneratedProblem]] = []
    with BANK_JSONL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("topic_id") != topic_id or rec.get("is_flagged"):
                continue
            diff = rec.get("conceptual_diff", 3)
            if abs(diff - conceptual_diff) > tol:
                continue
            try:
                problem = GeneratedProblem(**{**rec["problem"], "problem_id": rec["id"]})
            except Exception:
                continue
            out.append((diff, problem))
    return out
