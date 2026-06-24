"""
Referral code system — Phase 5.

Each user gets a unique 6-character referral code (lazy: created on first GET /referral/me).
New users call POST /referral/use to link themselves to a code.

Rewards (granted by the Stripe webhook in credit_router):
  - 5 paid tutoring sessions → 1 free 1hr credit (repeats at 10, 15, …)
  - 3 paid referrals          → 1 free 1hr credit (repeats at 6, 9, …)

Only tutoring session purchases (kind="1hr"|"2hr") count toward the 5-session milestone.
Any first Stripe payment by a referred user triggers the referral path.
"""
from __future__ import annotations

import secrets
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_dependencies import require_student
from users_models import User
from db_models import ReferralRecord, ReferralUsageRecord, RewardRecord, SessionCreditRecord
from db_session import get_session

router = APIRouter(prefix="/referral", tags=["referral"])

# 6-char uppercase alphanumeric; excludes 0/1/I/O to avoid transcription errors.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _gen_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


def _session_milestone_hit(paid_count: int) -> bool:
    """True when paid_count is a positive multiple of 5."""
    return paid_count > 0 and paid_count % 5 == 0


def _referral_milestone_hit(paid_referrals: int) -> bool:
    """True when paid_referrals is a positive multiple of 3."""
    return paid_referrals > 0 and paid_referrals % 3 == 0


def _get_or_create_code(user_id: str, db) -> ReferralRecord:
    record = db.query(ReferralRecord).filter(ReferralRecord.user_id == user_id).first()
    if record:
        return record
    for _ in range(10):
        code = _gen_code()
        if not db.query(ReferralRecord).filter(ReferralRecord.code == code).first():
            break
    record = ReferralRecord(id=str(uuid4()), user_id=user_id, code=code)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _uses_database() -> bool:
    from config import USE_DATABASE
    return USE_DATABASE


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ReferralStatsResponse(BaseModel):
    code: str
    referred_count: int       # signed up with your code
    paid_referrals: int       # of those, made their first payment
    paid_sessions: int        # your own paid tutoring-session purchases
    rewards_earned: int       # total reward records for this user
    next_session_reward_at: int   # next multiple of 5
    next_referral_reward_at: int  # next multiple of 3


class UseReferralRequest(BaseModel):
    code: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/me", response_model=ReferralStatsResponse)
def get_my_referral(user: User = Depends(require_student)):
    """Return the user's referral code and reward progress."""
    if not _uses_database():
        return ReferralStatsResponse(
            code="DEV123", referred_count=0, paid_referrals=0,
            paid_sessions=0, rewards_earned=0,
            next_session_reward_at=5, next_referral_reward_at=3,
        )
    db = get_session()
    try:
        ref = _get_or_create_code(user.id, db)

        usages = db.query(ReferralUsageRecord).filter(ReferralUsageRecord.code == ref.code).all()
        referred_count = len(usages)
        paid_referrals = sum(1 for u in usages if u.first_paid_at is not None)

        paid_rows = (
            db.query(SessionCreditRecord.purchase_id)
            .filter(
                SessionCreditRecord.user_id == user.id,
                SessionCreditRecord.kind.in_(["1hr", "2hr"]),
                SessionCreditRecord.purchase_id.isnot(None),
            )
            .distinct()
            .all()
        )
        paid_sessions = len(paid_rows)
        rewards_earned = db.query(RewardRecord).filter(RewardRecord.user_id == user.id).count()

        next_session = ((paid_sessions // 5) + 1) * 5
        next_referral = ((paid_referrals // 3) + 1) * 3

        return ReferralStatsResponse(
            code=ref.code,
            referred_count=referred_count,
            paid_referrals=paid_referrals,
            paid_sessions=paid_sessions,
            rewards_earned=rewards_earned,
            next_session_reward_at=next_session,
            next_referral_reward_at=next_referral,
        )
    finally:
        db.close()


@router.post("/use", status_code=200)
def use_referral_code(body: UseReferralRequest, user: User = Depends(require_student)):
    """
    Link the authenticated user to a referral code.
    One-time; must be called before the user's first Stripe payment.
    """
    if not _uses_database():
        return {"ok": True}

    db = get_session()
    try:
        existing = (
            db.query(ReferralUsageRecord)
            .filter(ReferralUsageRecord.referred_user_id == user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="You've already used a referral code.")

        already_paid = (
            db.query(SessionCreditRecord)
            .filter(
                SessionCreditRecord.user_id == user.id,
                SessionCreditRecord.purchase_id.isnot(None),
            )
            .first()
        )
        if already_paid:
            raise HTTPException(
                status_code=409,
                detail="Referral codes can only be used before your first purchase.",
            )

        code = body.code.upper().strip()
        ref_record = db.query(ReferralRecord).filter(ReferralRecord.code == code).first()
        if not ref_record:
            raise HTTPException(status_code=404, detail="Referral code not found.")

        if ref_record.user_id == user.id:
            raise HTTPException(status_code=400, detail="You cannot use your own referral code.")

        db.add(ReferralUsageRecord(
            id=str(uuid4()),
            code=code,
            referred_user_id=user.id,
        ))
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
