"""
Admin API endpoints — gated by require_admin.

All write operations perform a dual write: FastAPI DB + Clerk publicMetadata.
Every mutation is appended to the admin_actions audit table.
"""

from __future__ import annotations

import json
import time as _time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, cast as sa_cast
from sqlalchemy.types import Integer as SAInt, Date as SADate

from auth_dependencies import require_admin
from db_models import AdminActionRecord, AttemptRecord, FlaggedProblemRecord, ProblemRecord, UserRecord
from db_session import get_session
from users_models import User

router = APIRouter(prefix="/admin", tags=["admin"])

_VALID_ROLES = {"student", "teacher", "admin"}
_VALID_TIERS = {"free", "basic", "student", "honors", "classroom-student"}


# ─── Response / request models ────────────────────────────────────────────────

class AdminUserResponse(BaseModel):
    id: str
    email: str
    role: str
    tier: str
    is_active: bool
    clerk_user_id: Optional[str]
    created_at: datetime
    daily_problems_generated: int
    display_name: Optional[str]
    daily_limit_override: Optional[int] = None


class AdminUserListResponse(BaseModel):
    users: List[AdminUserResponse]
    total: int
    page: int
    per_page: int


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    reset_quota: bool = False
    daily_limit_override: Optional[int] = None  # positive int sets override
    clear_limit_override: bool = False           # True removes the override


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _require_db() -> None:
    """Raise 503 when the database is not configured (USE_DATABASE=false)."""
    try:
        from db_session import get_engine
        get_engine()
    except ValueError:
        raise HTTPException(
            status_code=503,
            detail="Admin panel requires a database. Set USE_DATABASE=true and DATABASE_URL.",
        )


def _record_to_response(r: UserRecord) -> AdminUserResponse:
    return AdminUserResponse(
        id=r.id,
        email=r.email,
        role=r.role,
        tier=r.tier,
        is_active=r.is_active,
        clerk_user_id=r.clerk_user_id,
        created_at=r.created_at,
        daily_problems_generated=r.daily_problems_generated,
        display_name=r.display_name,
        daily_limit_override=r.daily_limit_override,
    )


def _log_action(session, admin_id: str, action_type: str, target_id: str, changes: dict) -> None:
    action = AdminActionRecord(
        admin_id=admin_id,
        action_type=action_type,
        target_id=target_id,
        changes_json=json.dumps(changes),
        timestamp=datetime.utcnow(),
    )
    session.add(action)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Filter by email (case-insensitive)"),
    role: Optional[str] = Query(None, description="Filter by role"),
    admin: User = Depends(require_admin),
) -> AdminUserListResponse:
    """List all users with optional search and role filter."""
    _require_db()
    session = get_session()
    try:
        q = session.query(UserRecord)
        if search:
            q = q.filter(UserRecord.email.ilike(f"%{search}%"))
        if role and role in _VALID_ROLES:
            q = q.filter(UserRecord.role == role)
        total = q.count()
        records = (
            q.order_by(UserRecord.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return AdminUserListResponse(
            users=[_record_to_response(r) for r in records],
            total=total,
            page=page,
            per_page=per_page,
        )
    finally:
        session.close()


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    admin: User = Depends(require_admin),
) -> AdminUserResponse:
    """Update a user's role, tier, active status, or reset their daily quota."""
    if body.role is not None and body.role not in _VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role: {body.role}")
    if body.tier is not None and body.tier not in _VALID_TIERS:
        raise HTTPException(status_code=422, detail=f"Invalid tier: {body.tier}")
    if body.daily_limit_override is not None and body.daily_limit_override < 1:
        raise HTTPException(status_code=422, detail="daily_limit_override must be ≥ 1")
    _require_db()

    session = get_session()
    try:
        record = session.query(UserRecord).filter_by(id=user_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")

        changes: dict = {}

        if body.role is not None:
            changes["role"] = {"from": record.role, "to": body.role}
            record.role = body.role

        if body.tier is not None:
            changes["tier"] = {"from": record.tier, "to": body.tier}
            record.tier = body.tier

        if body.is_active is not None:
            changes["is_active"] = {"from": record.is_active, "to": body.is_active}
            record.is_active = body.is_active

        if body.reset_quota:
            changes["daily_problems_generated"] = {"from": record.daily_problems_generated, "to": 0}
            record.daily_problems_generated = 0

        if body.clear_limit_override:
            changes["daily_limit_override"] = {"from": record.daily_limit_override, "to": None}
            record.daily_limit_override = None
        elif body.daily_limit_override is not None:
            changes["daily_limit_override"] = {"from": record.daily_limit_override, "to": body.daily_limit_override}
            record.daily_limit_override = body.daily_limit_override

        clerk_user_id = record.clerk_user_id
        _log_action(session, admin.id, "update_user", user_id, changes)
        session.commit()

        result = _record_to_response(record)
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    # Clerk sync outside the DB transaction (best-effort)
    if "role" in changes and clerk_user_id:
        from clerk_auth import update_clerk_user_metadata
        update_clerk_user_metadata(clerk_user_id, {"role": changes["role"]["to"]})

    return result


# ─── Flagged Problems ──────────────────────────────────────────────────────────

class AdminFlagResponse(BaseModel):
    flag_id: str
    problem_id: str
    user_id: str
    reason: str
    resolved: bool
    created_at: datetime
    statement: Optional[str]
    prompt_latex: Optional[str]
    answer: Optional[str]
    topic_id: str
    difficulty: int


class AdminFlagListResponse(BaseModel):
    flags: List[AdminFlagResponse]
    total: int
    page: int
    per_page: int


class FlagProblemEditRequest(BaseModel):
    statement: Optional[str] = None
    answer: Optional[str] = None


def _flag_to_response(flag: FlaggedProblemRecord, problem: Optional[ProblemRecord]) -> AdminFlagResponse:
    return AdminFlagResponse(
        flag_id=flag.id,
        problem_id=flag.problem_id,
        user_id=flag.user_id,
        reason=flag.reason,
        resolved=flag.resolved,
        created_at=flag.created_at,
        statement=problem.statement if problem else None,
        prompt_latex=problem.prompt_latex if problem else None,
        answer=problem.answer if problem else None,
        topic_id=problem.topic_id if problem else "",
        difficulty=problem.difficulty if problem else 0,
    )


@router.get("/flagged", response_model=AdminFlagListResponse)
async def list_flagged(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    resolved: Optional[bool] = Query(None, description="true=resolved only, false=unresolved only, omit=unresolved"),
    admin: User = Depends(require_admin),
) -> AdminFlagListResponse:
    """List flagged problems. Defaults to unresolved flags."""
    _require_db()
    session = get_session()
    try:
        q = session.query(FlaggedProblemRecord)
        show_resolved = resolved if resolved is not None else False
        q = q.filter(FlaggedProblemRecord.resolved == show_resolved)
        total = q.count()
        flags = (
            q.order_by(FlaggedProblemRecord.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        problem_ids = [f.problem_id for f in flags]
        problems: dict = {}
        if problem_ids:
            recs = session.query(ProblemRecord).filter(ProblemRecord.id.in_(problem_ids)).all()
            problems = {r.id: r for r in recs}
        return AdminFlagListResponse(
            flags=[_flag_to_response(f, problems.get(f.problem_id)) for f in flags],
            total=total,
            page=page,
            per_page=per_page,
        )
    finally:
        session.close()


@router.post("/flagged/{flag_id}/dismiss", response_model=AdminFlagResponse)
async def dismiss_flag(
    flag_id: str,
    admin: User = Depends(require_admin),
) -> AdminFlagResponse:
    """Mark a flag as resolved without modifying the problem."""
    _require_db()
    session = get_session()
    try:
        flag = session.query(FlaggedProblemRecord).filter_by(id=flag_id).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        flag.resolved = True
        problem = session.query(ProblemRecord).filter_by(id=flag.problem_id).first()
        if problem:
            problem.is_flagged = False
            problem.flag_resolved_at = datetime.utcnow()
        _log_action(session, admin.id, "dismiss_flag", flag_id, {"problem_id": flag.problem_id})
        session.commit()
        return _flag_to_response(flag, problem)
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.delete("/flagged/{flag_id}", status_code=204, response_model=None)
async def delete_flagged_problem(
    flag_id: str,
    admin: User = Depends(require_admin),
) -> None:
    """Delete the flagged problem and its flag record."""
    _require_db()
    session = get_session()
    try:
        flag = session.query(FlaggedProblemRecord).filter_by(id=flag_id).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        problem_id = flag.problem_id
        problem = session.query(ProblemRecord).filter_by(id=problem_id).first()
        _log_action(session, admin.id, "delete_problem", flag_id, {"problem_id": problem_id})
        session.delete(flag)
        if problem:
            session.delete(problem)
        session.commit()
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.patch("/flagged/{flag_id}", response_model=AdminFlagResponse)
async def edit_flagged_problem(
    flag_id: str,
    body: FlagProblemEditRequest,
    admin: User = Depends(require_admin),
) -> AdminFlagResponse:
    """Edit a flagged problem's statement and/or answer in-place, then auto-resolve the flag."""
    _require_db()
    session = get_session()
    try:
        flag = session.query(FlaggedProblemRecord).filter_by(id=flag_id).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        problem = session.query(ProblemRecord).filter_by(id=flag.problem_id).first()
        if not problem:
            raise HTTPException(status_code=404, detail="Problem not found")
        changes: dict = {}
        if body.statement is not None:
            changes["statement"] = {"from": problem.statement, "to": body.statement}
            problem.statement = body.statement
        if body.answer is not None:
            changes["answer"] = {"from": problem.answer, "to": body.answer}
            problem.answer = body.answer
        if changes:
            flag.resolved = True
            problem.is_flagged = False
            problem.flag_resolved_at = datetime.utcnow()
        _log_action(session, admin.id, "edit_problem", flag_id, {"problem_id": flag.problem_id, **changes})
        session.commit()
        return _flag_to_response(flag, problem)
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ─── Analytics ────────────────────────────────────────────────────────────────

_ANALYTICS_TTL = 300  # seconds
_analytics_store: Dict[str, dict] = {}


def _acache_get(key: str):
    entry = _analytics_store.get(key)
    if entry and _time.monotonic() < entry["expires"]:
        return entry["data"]
    _analytics_store.pop(key, None)
    return None


def _acache_set(key: str, value) -> None:
    _analytics_store[key] = {"data": value, "expires": _time.monotonic() + _ANALYTICS_TTL}


class DailyCount(BaseModel):
    date: str  # "YYYY-MM-DD"
    count: int


class TopicStat(BaseModel):
    topic_id: str
    attempts: int
    correct: int
    correct_rate: float


class AnalyticsOverview(BaseModel):
    cached_at: datetime
    cache_ttl_seconds: int
    total_users: int
    active_users: int
    new_users_7d: int
    users_by_role: Dict[str, int]
    users_by_tier: Dict[str, int]
    total_problems: int
    unresolved_flags: int
    total_attempts: int
    correct_attempts: int
    attempts_today: int
    correct_rate: float
    top_topics: List[TopicStat]
    daily_problems_7d: List[DailyCount]
    daily_attempts_7d: List[DailyCount]


@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    bust: bool = Query(False, description="Bypass cache and recompute"),
    admin: User = Depends(require_admin),
) -> AnalyticsOverview:
    """Platform analytics snapshot with a 5-minute in-memory TTL cache."""
    _require_db()

    cache_key = "analytics_overview"
    if not bust:
        cached = _acache_get(cache_key)
        if cached is not None:
            return cached

    session = get_session()
    try:
        now = datetime.utcnow()
        seven_ago = now - timedelta(days=7)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # ── Users ─────────────────────────────────────────────────────────────
        total_users = session.query(UserRecord).count()
        active_users = session.query(UserRecord).filter(UserRecord.is_active == True).count()  # noqa: E712
        new_users_7d = session.query(UserRecord).filter(UserRecord.created_at >= seven_ago).count()

        role_rows = (
            session.query(UserRecord.role, func.count(UserRecord.id))
            .group_by(UserRecord.role).all()
        )
        users_by_role: Dict[str, int] = {r: c for r, c in role_rows}

        tier_rows = (
            session.query(UserRecord.tier, func.count(UserRecord.id))
            .group_by(UserRecord.tier).all()
        )
        users_by_tier: Dict[str, int] = {t: c for t, c in tier_rows}

        # ── Problems ──────────────────────────────────────────────────────────
        total_problems = session.query(ProblemRecord).count()
        unresolved_flags = (
            session.query(FlaggedProblemRecord)
            .filter(FlaggedProblemRecord.resolved == False)  # noqa: E712
            .count()
        )

        daily_prob_rows = (
            session.query(
                sa_cast(ProblemRecord.created_at, SADate).label("day"),
                func.count(ProblemRecord.id).label("cnt"),
            )
            .filter(ProblemRecord.created_at >= seven_ago)
            .group_by("day")
            .order_by("day")
            .all()
        )
        daily_problems_7d = [DailyCount(date=str(r.day), count=r.cnt) for r in daily_prob_rows]

        # ── Attempts ──────────────────────────────────────────────────────────
        total_attempts = session.query(AttemptRecord).count()
        correct_attempts = session.query(AttemptRecord).filter(AttemptRecord.is_correct == True).count()  # noqa: E712
        attempts_today = session.query(AttemptRecord).filter(AttemptRecord.timestamp >= today_start).count()
        correct_rate = round(correct_attempts / total_attempts, 4) if total_attempts else 0.0

        topic_rows = (
            session.query(
                AttemptRecord.topic_id,
                func.count(AttemptRecord.id).label("attempts"),
                func.sum(sa_cast(AttemptRecord.is_correct, SAInt)).label("correct"),
            )
            .group_by(AttemptRecord.topic_id)
            .order_by(func.count(AttemptRecord.id).desc())
            .limit(10)
            .all()
        )
        top_topics = [
            TopicStat(
                topic_id=r.topic_id,
                attempts=r.attempts,
                correct=int(r.correct or 0),
                correct_rate=round(int(r.correct or 0) / r.attempts, 4) if r.attempts else 0.0,
            )
            for r in topic_rows
        ]

        daily_att_rows = (
            session.query(
                sa_cast(AttemptRecord.timestamp, SADate).label("day"),
                func.count(AttemptRecord.id).label("cnt"),
            )
            .filter(AttemptRecord.timestamp >= seven_ago)
            .group_by("day")
            .order_by("day")
            .all()
        )
        daily_attempts_7d = [DailyCount(date=str(r.day), count=r.cnt) for r in daily_att_rows]

        result = AnalyticsOverview(
            cached_at=now,
            cache_ttl_seconds=_ANALYTICS_TTL,
            total_users=total_users,
            active_users=active_users,
            new_users_7d=new_users_7d,
            users_by_role=users_by_role,
            users_by_tier=users_by_tier,
            total_problems=total_problems,
            unresolved_flags=unresolved_flags,
            total_attempts=total_attempts,
            correct_attempts=correct_attempts,
            attempts_today=attempts_today,
            correct_rate=correct_rate,
            top_topics=top_topics,
            daily_problems_7d=daily_problems_7d,
            daily_attempts_7d=daily_attempts_7d,
        )
        _acache_set(cache_key, result)
        return result

    finally:
        session.close()


# ─── Quotas ───────────────────────────────────────────────────────────────────

# Tier defaults surfaced to the frontend so the API is the single source of truth
_TIER_DAILY_DEFAULTS: Dict[str, Optional[int]] = {
    "free": 3,
    "basic": 10,
    "student": None,       # no daily cap
    "honors": None,
    "classroom-student": None,
}

_TIER_MONTHLY_LIMITS: Dict[str, Optional[int]] = {
    "free": 10,
    "basic": 30,
    "student": 100,
    "honors": 250,
    "classroom-student": 150,
}


class TierLimitRow(BaseModel):
    tier: str
    daily_limit: Optional[int]    # None = unlimited
    monthly_limit: Optional[int]  # None = unlimited


class UserQuotaRow(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    tier: str
    daily_problems_generated: int
    daily_limit_override: Optional[int]
    effective_daily_limit: Optional[int]  # override ?? tier default, None = unlimited
    last_reset_date: Optional[str]


class QuotasOverview(BaseModel):
    tier_limits: List[TierLimitRow]
    users: List[UserQuotaRow]
    total: int
    page: int
    per_page: int


@router.get("/quotas/overview", response_model=QuotasOverview)
async def quotas_overview(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    only_active: bool = Query(True, description="Only show users with usage > 0 or an override set"),
    admin: User = Depends(require_admin),
) -> QuotasOverview:
    """Quota overview: tier defaults + per-user usage and overrides."""
    _require_db()
    session = get_session()
    try:
        q = session.query(UserRecord)
        if only_active:
            q = q.filter(
                (UserRecord.daily_problems_generated > 0) |
                (UserRecord.daily_limit_override != None)  # noqa: E711
            )
        total = q.count()
        records = (
            q.order_by(UserRecord.daily_problems_generated.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        def _effective(r: UserRecord) -> Optional[int]:
            if r.daily_limit_override is not None:
                return r.daily_limit_override
            return _TIER_DAILY_DEFAULTS.get(r.tier)

        users = [
            UserQuotaRow(
                id=r.id,
                email=r.email,
                display_name=r.display_name,
                tier=r.tier,
                daily_problems_generated=r.daily_problems_generated,
                daily_limit_override=r.daily_limit_override,
                effective_daily_limit=_effective(r),
                last_reset_date=r.last_reset_date,
            )
            for r in records
        ]

        tier_limits = [
            TierLimitRow(
                tier=t,
                daily_limit=_TIER_DAILY_DEFAULTS[t],
                monthly_limit=_TIER_MONTHLY_LIMITS[t],
            )
            for t in ["free", "basic", "student", "honors", "classroom-student"]
        ]

        return QuotasOverview(
            tier_limits=tier_limits,
            users=users,
            total=total,
            page=page,
            per_page=per_page,
        )
    finally:
        session.close()
