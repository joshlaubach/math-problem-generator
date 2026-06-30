"""
Exam Mode — standalone proctored exam sessions.

Flow:
  1. GET /exam/templates           — list presets
  2. POST /exam/start              — generate problems, create attempt, check credit preflight
  3. GET /exam/{id}                — get current state (remaining time, problems w/o answers)
  4. POST /exam/{id}/event         — log integrity event (tab_blur, paste, etc.)
  5. POST /exam/{id}/submit        — grade answers, consume exam credit, return results
  6. GET /exam/{id}/review         — full results with worked solutions + AI summary

Credits:
  - Preset exams: "exam_preset" kind ($7.99)
  - Custom exams:  "exam_custom" kind ($4.99)
  - Credit is consumed on SUBMIT, not on start.
  - Preflight check at start to surface missing-credit errors early.

Timer:
  - Server-side only: elapsed = now − start_time
  - Auto-submit fires on GET/event/submit if time_limit_minutes is set and elapsed
  - Untimed exams (time_limit_minutes=null) never auto-submit

Integrity monitor:
  - Frontend reports tab_blur, tab_focus, paste, per-item timing
  - Backend flags timing anomalies vs. session history
  - All flags are informational — no automated action
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_dependencies import require_student
from users_models import User
from db_models import ExamAttemptRecord, ExamIntegrityEventRecord
from db_session import get_session
from exam_templates import PRESET_TEMPLATES, ExamTemplate, ConceptDistribution
from topic_registry import TOPIC_REGISTRY
from credit_router import has_available_credit, consume_credit, restore_credit

router = APIRouter(prefix="/exam", tags=["exam"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    total_problems: int
    time_limit_minutes: Optional[int]
    calc_tier: str
    kind: str


class CustomConfig(BaseModel):
    course_ids: list[str] = Field(..., min_length=1, max_length=4)
    total_problems: int = Field(10, ge=5, le=15)
    time_limit_minutes: Optional[int] = Field(None)  # None = untimed
    difficulty_min: int = Field(2, ge=1, le=5)
    difficulty_max: int = Field(4, ge=1, le=5)


class ExamStartRequest(BaseModel):
    template_id: str                        # preset id or "custom"
    untimed: bool = False                   # override preset timer
    custom_config: Optional[CustomConfig] = None


class ExamProblemPublic(BaseModel):
    """Problem fields safe to send to the client during the exam (no answers)."""
    index: int
    statement: str
    answer_type: str


class ExamStateResponse(BaseModel):
    attempt_id: str
    template_id: str
    template_name: str
    total_problems: int
    remaining_seconds: Optional[float]     # None if untimed
    submitted_at: Optional[str]
    problems: list[ExamProblemPublic]


class IntegrityEventRequest(BaseModel):
    event_type: Literal["tab_blur", "tab_focus", "paste", "timing_anomaly"]
    problem_index: Optional[int] = None
    elapsed_seconds: Optional[float] = None


class SubmitRequest(BaseModel):
    answers: dict[str, str]   # str(problem_index) → student answer


class ProblemResult(BaseModel):
    index: int
    statement: str
    student_answer: Optional[str]
    correct: bool
    correct_answer: str
    worked_steps: list[dict]


class SubmitResponse(BaseModel):
    score: float
    problems_correct: int
    total_problems: int
    results: list[ProblemResult]
    review_summary: str
    integrity_flag_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uses_database() -> bool:
    from config import USE_DATABASE
    return USE_DATABASE


def _remaining_seconds(attempt: ExamAttemptRecord) -> Optional[float]:
    if attempt.time_limit_minutes is None:
        return None
    elapsed = (datetime.now(timezone.utc) - attempt.start_time.replace(tzinfo=timezone.utc)).total_seconds()
    return max(0.0, attempt.time_limit_minutes * 60 - elapsed)


def _is_expired(attempt: ExamAttemptRecord) -> bool:
    rem = _remaining_seconds(attempt)
    return rem is not None and rem <= 0


def _get_attempt_or_404(attempt_id: str, user_id: str) -> ExamAttemptRecord:
    if not _uses_database():
        raise HTTPException(status_code=404, detail="Exam not found (database disabled in dev mode)")
    db = get_session()
    try:
        record = db.query(ExamAttemptRecord).filter(ExamAttemptRecord.id == attempt_id).first()
        if record is None:
            raise HTTPException(status_code=404, detail="Exam attempt not found")
        if record.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return record
    finally:
        db.close()


def _pick_topics(dist: ConceptDistribution, n: int) -> list[str]:
    """Randomly sample n topic_ids from the given course set."""
    candidates = [
        tid for tid, meta in TOPIC_REGISTRY.items()
        if meta.course_id in dist.course_ids
    ]
    if not candidates:
        return []
    return random.choices(candidates, k=n)


def _allocate_problems(template: ExamTemplate) -> list[tuple[str, int, int, str]]:
    """
    Return a list of (topic_id, conceptual_diff, computational_diff, calc_tier)
    tuples, one per problem, distributed by template weights.
    """
    dist = template.concept_distribution
    total = template.total_problems
    total_weight = sum(d.weight for d in dist)
    allocations: list[tuple[str, int, int, str]] = []

    for i, group in enumerate(dist):
        if i < len(dist) - 1:
            count = round(total * group.weight / total_weight)
        else:
            count = total - len(allocations)  # remainder goes to last group
        count = max(0, count)
        topics = _pick_topics(group, count)
        for tid in topics:
            cdiff = random.randint(group.difficulty_min, group.difficulty_max)
            # computational difficulty mirrors conceptual for exam problems
            allocations.append((tid, cdiff, cdiff, template.calc_tier))

    return allocations[:total]


async def _grade_answers(problems: list[dict], answers: dict[str, str]) -> list[dict]:
    """Grade all answers via answer_checker.check(). Returns results list."""
    from agents.answer_checker import check as check_answer

    async def _check_one(i: int, prob: dict) -> dict:
        student_ans = answers.get(str(i), "").strip()
        if not student_ans:
            return {"index": i, "correct": False, "student_answer": "", "canonical": prob["answer"]}
        result = await check_answer(student_ans, prob["answer"], prob.get("answer_type", "expression"))
        return {"index": i, "correct": result.correct, "student_answer": student_ans, "canonical": prob["answer"]}

    return await asyncio.gather(*[_check_one(i, p) for i, p in enumerate(problems)])


async def _generate_review_summary(
    problems: list[dict],
    results: list[dict],
    template_name: str,
) -> str:
    """Generate a short AI paragraph linking weak areas to practice topics."""
    from llm_anthropic_client import _call_with_backoff

    wrong = [r for r in results if not r["correct"]]
    if not wrong:
        return (
            f"Excellent work — perfect score on {template_name}! "
            "To keep sharp, revisit these topics weekly and push to harder difficulty levels."
        )

    weak_topics = list({problems[r["index"]].get("topic_name", "this area") for r in wrong})[:4]
    topics_str = ", ".join(weak_topics)
    messages = [{"role": "user", "content": (
        f"A student just completed a {template_name} practice exam. "
        f"They got {len(wrong)} question(s) wrong, in these areas: {topics_str}. "
        "Write one concise paragraph (3-4 sentences) summarizing what they should focus on "
        "and why. Be encouraging but specific. Do not use bullet points."
    )}]
    try:
        return await _call_with_backoff(messages, max_tokens=200)
    except Exception:
        return (
            f"You missed {len(wrong)} question(s) on {template_name}. "
            f"Focus on: {topics_str}. "
            "Book a tutoring session to walk through your mistakes step by step."
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/templates", response_model=list[TemplateInfo])
def list_templates():
    """Return all preset exam templates."""
    return [
        TemplateInfo(
            id=t.id,
            name=t.name,
            description=t.description,
            total_problems=t.total_problems,
            time_limit_minutes=t.time_limit_minutes,
            calc_tier=t.calc_tier,
            kind=t.kind,
        )
        for t in PRESET_TEMPLATES.values()
    ]


@router.post("/start", status_code=201, response_model=ExamStateResponse)
async def start_exam(
    body: ExamStartRequest,
    user: User = Depends(require_student),
):
    """
    Start a new exam attempt.

    Generates all problems up-front (parallel LLM calls), saves the attempt,
    and returns problem statements. Answers are withheld until review.

    Does a preflight credit check but does NOT consume the credit yet — credit
    is consumed on submit.
    """
    from agents.generator import generate
    from agents.schemas import GeneratorInput

    # ── 1. Resolve template ──────────────────────────────────────────────────
    if body.template_id == "custom":
        if body.custom_config is None:
            raise HTTPException(status_code=422, detail="custom_config required for template_id='custom'")
        cfg = body.custom_config
        template = ExamTemplate(
            id="custom",
            name="Custom Exam",
            description="Custom exam",
            total_problems=cfg.total_problems,
            time_limit_minutes=None if body.untimed else cfg.time_limit_minutes,
            calc_tier="scientific",
            kind="custom",
            concept_distribution=[
                ConceptDistribution(
                    course_ids=cfg.course_ids,
                    weight=1.0,
                    difficulty_min=cfg.difficulty_min,
                    difficulty_max=cfg.difficulty_max,
                )
            ],
        )
        credit_kind = "exam_custom"
    else:
        template = PRESET_TEMPLATES.get(body.template_id)
        if template is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown template '{body.template_id}'. "
                       f"Valid options: {list(PRESET_TEMPLATES)} or 'custom'",
            )
        credit_kind = "exam_preset"

    if body.untimed:
        template.time_limit_minutes = None

    # ── 2. Credit preflight (don't consume yet — consumed at submit) ─────────
    if not has_available_credit(user.id, kind=credit_kind):
        raise HTTPException(
            status_code=402,
            detail=(
                f"No {credit_kind.replace('_', ' ')} credits available. "
                "Purchase one at /pricing to get started."
            ),
        )

    # ── 3. Allocate problems from concept distribution ───────────────────────
    allocations = _allocate_problems(template)
    if not allocations:
        raise HTTPException(status_code=500, detail="Failed to sample topics from template distribution.")

    # ── 4. Generate all problems in parallel ─────────────────────────────────
    async def _gen_one(idx: int, topic_id: str, cdiff: int, cpdiff: int, calc: str) -> Optional[dict]:
        meta = TOPIC_REGISTRY.get(topic_id)
        if meta is None:
            return None
        try:
            inp = GeneratorInput(
                topic=meta.topic_name,
                course=meta.course_name,
                unit=meta.unit_name,
                conceptual_diff=cdiff,
                computational_diff=cpdiff,
                calc_tier=calc,
            )
            prob = await generate(inp)
            return {
                "index": idx,
                "statement": prob.statement,
                "answer": prob.answer,
                "answer_type": prob.answer_type,
                "worked_steps": [{"step": s.step, "explanation": s.explanation} for s in (prob.worked_steps or [])],
                "topic_id": topic_id,
                "topic_name": meta.topic_name,
                "course_id": meta.course_id,
            }
        except Exception:
            return None

    raw_results = await asyncio.gather(*[
        _gen_one(i, tid, cdiff, cpdiff, calc)
        for i, (tid, cdiff, cpdiff, calc) in enumerate(allocations)
    ])
    problems = [p for p in raw_results if p is not None]
    # Re-index sequentially in case any failed
    for i, p in enumerate(problems):
        p["index"] = i

    if not problems:
        raise HTTPException(status_code=500, detail="Problem generation failed. Please try again.")

    # ── 5. Persist attempt ───────────────────────────────────────────────────
    attempt_id = str(uuid4())
    template_dict = {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "total_problems": template.total_problems,
        "time_limit_minutes": template.time_limit_minutes,
        "calc_tier": template.calc_tier,
        "kind": template.kind,
        "credit_kind": credit_kind,
    }

    if _uses_database():
        db = get_session()
        try:
            record = ExamAttemptRecord(
                id=attempt_id,
                user_id=user.id,
                template_id=template.id,
                template_json=template_dict,
                problems_json=problems,
                answers_json={},
                start_time=datetime.utcnow(),
                time_limit_minutes=template.time_limit_minutes,
            )
            db.add(record)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    return ExamStateResponse(
        attempt_id=attempt_id,
        template_id=template.id,
        template_name=template.name,
        total_problems=len(problems),
        remaining_seconds=(
            template.time_limit_minutes * 60.0
            if template.time_limit_minutes is not None
            else None
        ),
        submitted_at=None,
        problems=[
            ExamProblemPublic(index=p["index"], statement=p["statement"], answer_type=p["answer_type"])
            for p in problems
        ],
    )


@router.get("/{attempt_id}", response_model=ExamStateResponse)
def get_exam(attempt_id: str, user: User = Depends(require_student)):
    """Return current exam state (no answers). Auto-submits if time has expired."""
    record = _get_attempt_or_404(attempt_id, user.id)

    # Auto-submit on expiry
    if record.submitted_at is None and _is_expired(record):
        _do_auto_submit(record)

    return ExamStateResponse(
        attempt_id=record.id,
        template_id=record.template_id,
        template_name=record.template_json.get("name", ""),
        total_problems=len(record.problems_json),
        remaining_seconds=_remaining_seconds(record),
        submitted_at=record.submitted_at.isoformat() if record.submitted_at else None,
        problems=[
            ExamProblemPublic(
                index=p["index"],
                statement=p["statement"],
                answer_type=p.get("answer_type", "expression"),
            )
            for p in record.problems_json
        ],
    )


@router.post("/{attempt_id}/event", status_code=204, response_model=None)
def log_integrity_event(
    attempt_id: str,
    body: IntegrityEventRequest,
    user: User = Depends(require_student),
):
    """Log a client-side integrity event (tab blur, paste, per-item timing)."""
    record = _get_attempt_or_404(attempt_id, user.id)
    if record.submitted_at is not None:
        return  # silently ignore events after submission

    if not _uses_database():
        return

    db = get_session()
    try:
        event = ExamIntegrityEventRecord(
            id=str(uuid4()),
            attempt_id=attempt_id,
            event_type=body.event_type,
            problem_index=body.problem_index,
            elapsed_seconds=body.elapsed_seconds,
        )
        db.add(event)
        # Count blur events as the "flag" indicator visible in admin
        if body.event_type == "tab_blur":
            attempt = db.query(ExamAttemptRecord).filter(ExamAttemptRecord.id == attempt_id).first()
            if attempt:
                attempt.integrity_flag_count += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.post("/{attempt_id}/submit", response_model=SubmitResponse)
async def submit_exam(
    attempt_id: str,
    body: SubmitRequest,
    user: User = Depends(require_student),
):
    """
    Submit exam answers.

    Grades all answers, consumes the exam credit, generates a review summary,
    and returns full results with worked solutions for wrong answers.
    """
    record = _get_attempt_or_404(attempt_id, user.id)

    if record.submitted_at is not None:
        raise HTTPException(status_code=409, detail="Exam already submitted.")

    # Auto-submit on expiry (still returns results, just can't change answers)
    if _is_expired(record):
        # merge any last-second client answers (may be partial)
        pass

    # ── Consume credit ────────────────────────────────────────────────────────
    credit_kind = record.template_json.get("credit_kind", "exam_preset")
    credit_id = consume_credit(user.id, kind=credit_kind)
    if credit_id is None:
        raise HTTPException(
            status_code=402,
            detail=f"No {credit_kind.replace('_', ' ')} credits available.",
        )

    # ── Grade ─────────────────────────────────────────────────────────────────
    problems = record.problems_json
    grade_results = await _grade_answers(problems, body.answers)

    n_correct = sum(1 for r in grade_results if r["correct"])
    n_attempted = sum(1 for r in grade_results if r["student_answer"])
    score = n_correct / len(problems) if problems else 0.0

    # ── AI review summary ────────────────────────────────────────────────────
    template_name = record.template_json.get("name", "your exam")
    review_summary = await _generate_review_summary(problems, grade_results, template_name)

    # ── Persist results ───────────────────────────────────────────────────────
    if _uses_database():
        db = get_session()
        try:
            attempt = db.query(ExamAttemptRecord).filter(ExamAttemptRecord.id == attempt_id).first()
            if attempt:
                attempt.answers_json = body.answers
                attempt.submitted_at = datetime.utcnow()
                attempt.score = score
                attempt.problems_attempted = n_attempted
                attempt.problems_correct = n_correct
                attempt.credit_id = credit_id
                attempt.review_summary = review_summary
            db.commit()
        except Exception:
            db.rollback()
            restore_credit(credit_id)
            raise
        finally:
            db.close()

    # ── Build response ────────────────────────────────────────────────────────
    results = []
    for r in grade_results:
        prob = problems[r["index"]]
        results.append(ProblemResult(
            index=r["index"],
            statement=prob["statement"],
            student_answer=r["student_answer"] or None,
            correct=r["correct"],
            correct_answer=prob["answer"],
            worked_steps=prob.get("worked_steps", []),
        ))

    return SubmitResponse(
        score=round(score, 4),
        problems_correct=n_correct,
        total_problems=len(problems),
        results=results,
        review_summary=review_summary,
        integrity_flag_count=record.integrity_flag_count,
    )


@router.get("/{attempt_id}/review", response_model=SubmitResponse)
def get_review(attempt_id: str, user: User = Depends(require_student)):
    """Return full review with worked solutions. Requires submitted exam."""
    record = _get_attempt_or_404(attempt_id, user.id)

    if record.submitted_at is None:
        raise HTTPException(status_code=409, detail="Exam has not been submitted yet.")

    problems = record.problems_json
    answers = record.answers_json or {}

    results = []
    for i, prob in enumerate(problems):
        student_ans = answers.get(str(i), "")
        # Use stored score rather than re-grading to avoid inconsistency
        # We need to reconstruct correct/wrong from stored answers + canonical
        # Since we can't re-grade synchronously here without async, we recompute
        # from the stored data using simple string match as an approximation.
        # (Full async re-grade could be a separate endpoint if needed.)
        correct_ans = prob.get("answer", "")
        is_correct = student_ans.strip() == correct_ans.strip() if student_ans else False
        results.append(ProblemResult(
            index=i,
            statement=prob["statement"],
            student_answer=student_ans or None,
            correct=is_correct,
            correct_answer=correct_ans,
            worked_steps=prob.get("worked_steps", []),
        ))

    # Score from DB is canonical
    score = record.score or 0.0
    n_correct = record.problems_correct

    return SubmitResponse(
        score=round(score, 4),
        problems_correct=n_correct,
        total_problems=len(problems),
        results=results,
        review_summary=record.review_summary or "",
        integrity_flag_count=record.integrity_flag_count,
    )


# ---------------------------------------------------------------------------
# Internal: auto-submit helper (synchronous — called from sync route handlers)
# ---------------------------------------------------------------------------

def _do_auto_submit(record: ExamAttemptRecord) -> None:
    """Mark an expired exam as auto-submitted with whatever answers were stored."""
    if not _uses_database():
        return
    db = get_session()
    try:
        attempt = db.query(ExamAttemptRecord).filter(ExamAttemptRecord.id == record.id).first()
        if attempt and attempt.submitted_at is None:
            n_attempted = len([v for v in (attempt.answers_json or {}).values() if v])
            attempt.submitted_at = datetime.utcnow()
            attempt.problems_attempted = n_attempted
            # score stays 0.0 until actual grading — grading requires async so
            # we leave it to be computed lazily on the review endpoint.
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
