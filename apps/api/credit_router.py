"""
Session credit management — purchase, balance, and Stripe webhook.

Session products (pay-per-session, no subscription):
  1hr   → 1 credit  @ $20  (1-hour session)
  2hr   → 1 credit  @ $35  (2-hour session)
  5x1hr → 5 credits @ $90  (five 1-hour sessions, best value)

Credits are typed — a 1hr credit can only start a 1hr session and vice versa.
Credits expire 6 months after purchase.
One credit is consumed at the start of each tutor session.
If a session fails within 2 minutes, the credit is automatically restored.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from pydantic import BaseModel

from auth_dependencies import require_student, get_user_repository
from users_models import User
from db_models import SessionCreditRecord
from db_session import get_session

router = APIRouter(prefix="/credits", tags=["credits"])

# ---------------------------------------------------------------------------
# Bundle config
# ---------------------------------------------------------------------------

BUNDLES: dict[str, dict] = {
    # Tutoring session credits
    "1hr":         {"credits": 1, "price_usd": 20, "kind": "1hr",         "tiers": "all"},
    "2hr":         {"credits": 1, "price_usd": 35, "kind": "2hr",         "tiers": "all"},
    "5x1hr":       {"credits": 5, "price_usd": 90, "kind": "1hr",         "tiers": "all"},
    # Exam credits (consumed at submit)
    "exam_custom": {"credits": 1, "price_usd": 5,  "kind": "exam_custom", "tiers": "all"},
    "exam_preset": {"credits": 1, "price_usd": 8,  "kind": "exam_preset", "tiers": "all"},
}

CREDIT_EXPIRY_DAYS = 183  # ~6 months

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_stripe():
    import stripe as _stripe
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured. Set STRIPE_SECRET_KEY.",
        )
    _stripe.api_key = key
    return _stripe


def _available_credits(
    user_id: str, session, kind: Optional[str] = None
) -> list[SessionCreditRecord]:
    """Return all unused, non-expired credits for a user, oldest first.

    Pass kind="1hr" or kind="2hr" to filter by session type.
    """
    now = datetime.now(timezone.utc)
    q = (
        session.query(SessionCreditRecord)
        .filter(
            SessionCreditRecord.user_id == user_id,
            SessionCreditRecord.used_at.is_(None),
            SessionCreditRecord.expires_at > now,
        )
    )
    if kind is not None:
        q = q.filter(SessionCreditRecord.kind == kind)
    return q.order_by(SessionCreditRecord.expires_at.asc()).all()


def _expiring_soon(credits: list[SessionCreditRecord]) -> int:
    """Count credits expiring within 30 days."""
    cutoff = datetime.now(timezone.utc) + timedelta(days=30)
    return sum(1 for c in credits if c.expires_at <= cutoff)


def _next_expiry(credits: list[SessionCreditRecord]) -> Optional[str]:
    if not credits:
        return None
    return credits[0].expires_at.isoformat()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class BalanceResponse(BaseModel):
    available: int          # total across all kinds (backward compat)
    available_1hr: int
    available_2hr: int
    expiring_soon: int      # within 30 days, across all kinds
    next_expiry: Optional[str]


class CheckoutRequest(BaseModel):
    bundle: str          # "1hr" | "2hr" | "5x1hr"
    success_url: str     # redirect after payment
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


@router.get("/balance", response_model=BalanceResponse)
def get_balance(
    user: User = Depends(require_student),
):
    """Return the authenticated student's current session credit balance."""
    if not _uses_database():
        return BalanceResponse(available=0, available_1hr=0, available_2hr=0, expiring_soon=0, next_expiry=None)

    session = get_session()
    try:
        credits_1hr = _available_credits(user.id, session, kind="1hr")
        credits_2hr = _available_credits(user.id, session, kind="2hr")
        all_credits = sorted(credits_1hr + credits_2hr, key=lambda c: c.expires_at)
        return BalanceResponse(
            available=len(all_credits),
            available_1hr=len(credits_1hr),
            available_2hr=len(credits_2hr),
            expiring_soon=_expiring_soon(all_credits),
            next_expiry=_next_expiry(all_credits),
        )
    finally:
        session.close()


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(require_student),
):
    """Create a Stripe Checkout Session for a session credit bundle."""
    bundle = BUNDLES.get(body.bundle)
    if not bundle:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown bundle: {body.bundle}. Must be one of {list(BUNDLES)}",
        )

    price_id_env = {
        "1hr":         "STRIPE_SESSION_1HR_PRICE_ID",
        "2hr":         "STRIPE_SESSION_2HR_PRICE_ID",
        "5x1hr":       "STRIPE_SESSION_5X1HR_PRICE_ID",
        "exam_custom": "STRIPE_EXAM_CUSTOM_PRICE_ID",
        "exam_preset": "STRIPE_EXAM_PRESET_PRICE_ID",
    }[body.bundle]

    price_id = os.getenv(price_id_env, "")
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Price not configured. Set {price_id_env} in your environment.",
        )

    stripe = _get_stripe()
    checkout = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=body.cancel_url,
        metadata={
            "user_id": user.id,
            "bundle": body.bundle,
            "credits": str(bundle["credits"]),
            "kind": bundle["kind"],
        },
        customer_email=user.email,
    )
    return CheckoutResponse(checkout_url=checkout.url, session_id=checkout.id)


@router.post("/webhook", status_code=200)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="stripe-signature"),
):
    """
    Stripe webhook handler.

    Grants session credits on checkout.session.completed.
    Must be registered in the Stripe dashboard pointing to /credits/webhook.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        # SECURITY (C1): never accept an unsigned webhook. Without the secret we
        # cannot verify the event came from Stripe, so an attacker could forge a
        # checkout.session.completed to mint credits. Fail closed.
        raise HTTPException(
            status_code=503,
            detail="Webhook processing is not configured (STRIPE_WEBHOOK_SECRET unset).",
        )

    payload = await request.body()
    stripe = _get_stripe()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        _handle_checkout_completed(event["data"]["object"])

    return {"received": True}


def _handle_checkout_completed(checkout_session) -> None:
    """Grant typed credits to the user after a successful checkout."""
    if not _uses_database():
        return

    meta = checkout_session.get("metadata", {})
    user_id = meta.get("user_id")
    credits_count = int(meta.get("credits", 0))
    kind = meta.get("kind", "1hr")  # default "1hr" for legacy webhooks
    purchase_id = checkout_session.get("id")

    if not user_id or credits_count <= 0:
        return

    expires_at = datetime.now(timezone.utc) + timedelta(days=CREDIT_EXPIRY_DAYS)
    db = get_session()
    try:
        # SECURITY (M6): Stripe redelivers events; granting per-delivery would
        # double-credit. Idempotency key is the checkout/purchase id — if any
        # credit row already exists for it, this delivery is a replay; no-op.
        if purchase_id:
            already = (
                db.query(SessionCreditRecord)
                .filter(SessionCreditRecord.purchase_id == purchase_id)
                .first()
            )
            if already is not None:
                return
        for _ in range(credits_count):
            record = SessionCreditRecord(
                id=str(uuid4()),
                user_id=user_id,
                kind=kind,
                expires_at=expires_at,
                purchase_id=purchase_id,
            )
            db.add(record)
        db.commit()
        # Check for loyalty and referral reward milestones.
        _maybe_grant_rewards(user_id, kind, db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _maybe_grant_rewards(user_id: str, kind: str, db) -> None:
    """
    After a purchase is persisted, check whether the user has crossed a
    loyalty or referral reward milestone and grant a free 1hr credit if so.

    Loyalty   — every 5 paid tutoring-session purchases (kind 1hr|2hr)
    Referral  — after 3 paid referrals, the referrer earns a free session
    Both are idempotent: the RewardRecord unique index blocks double-grants.
    """
    from db_models import ReferralRecord, ReferralUsageRecord, RewardRecord

    def _grant(recipient_id: str, reason: str, milestone: int) -> None:
        from db_models import RewardRecord as _R
        existing = (
            db.query(_R)
            .filter(_R.user_id == recipient_id, _R.reason == reason, _R.milestone == milestone)
            .first()
        )
        if existing:
            return
        credit_id = str(uuid4())
        free_expires = datetime.now(timezone.utc) + timedelta(days=CREDIT_EXPIRY_DAYS)
        db.add(SessionCreditRecord(
            id=credit_id,
            user_id=recipient_id,
            kind="1hr",
            expires_at=free_expires,
            purchase_id=None,
        ))
        db.add(_R(
            id=str(uuid4()),
            user_id=recipient_id,
            reason=reason,
            milestone=milestone,
            credit_id=credit_id,
        ))

    # ── Loyalty: every 5 paid tutoring-session purchases ─────────────────────
    if kind in ("1hr", "2hr"):
        paid_count = (
            db.query(SessionCreditRecord.purchase_id)
            .filter(
                SessionCreditRecord.user_id == user_id,
                SessionCreditRecord.kind.in_(["1hr", "2hr"]),
                SessionCreditRecord.purchase_id.isnot(None),
            )
            .distinct()
            .count()
        )
        if paid_count > 0 and paid_count % 5 == 0:
            _grant(user_id, "paid_5", paid_count)

    # ── Referral: mark referred user's first payment, check referrer ──────────
    usage = (
        db.query(ReferralUsageRecord)
        .filter(
            ReferralUsageRecord.referred_user_id == user_id,
            ReferralUsageRecord.first_paid_at.is_(None),
        )
        .first()
    )
    if usage:
        usage.first_paid_at = datetime.now(timezone.utc)
        ref_record = (
            db.query(ReferralRecord)
            .filter(ReferralRecord.code == usage.code)
            .first()
        )
        if ref_record and ref_record.user_id != user_id:
            paid_referrals = (
                db.query(ReferralUsageRecord)
                .filter(
                    ReferralUsageRecord.code == usage.code,
                    ReferralUsageRecord.first_paid_at.isnot(None),
                )
                .count()
            )
            if paid_referrals > 0 and paid_referrals % 3 == 0:
                _grant(ref_record.user_id, "referral_3", paid_referrals)


# ---------------------------------------------------------------------------
# Internal helpers used by ws_router / tutor_router
# ---------------------------------------------------------------------------

def has_available_credit(user_id: str, kind: str = "1hr") -> bool:
    """
    Preflight: does the user have at least one unused, unexpired credit of the
    given kind?

    Used by /tutor/session/create for a friendly intake-form error. Does NOT
    consume anything — consumption happens at WebSocket connect. Returns True
    when the database is disabled (dev/test), mirroring consume_credit's mock.
    """
    if not _uses_database():
        return True

    db = get_session()
    try:
        return len(_available_credits(user_id, db, kind=kind)) > 0
    finally:
        db.close()


def consume_credit(user_id: str, kind: str = "1hr") -> Optional[str]:
    """
    Soft-lock the oldest available credit of the given kind for a session.

    Returns the credit ID on success, None if no matching credit is available.
    Sets used_at to NOW — call restore_credit() if session fails within 2 min.
    """
    if not _uses_database():
        return "no-db-mock-credit"

    db = get_session()
    try:
        credits = _available_credits(user_id, db, kind=kind)
        if not credits:
            return None
        credit = credits[0]
        credit.used_at = datetime.now(timezone.utc)
        db.commit()
        return credit.id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def restore_credit(credit_id: str) -> None:
    """Undo a credit consumption — called if session fails within 2 minutes."""
    if not _uses_database() or credit_id == "no-db-mock-credit":
        return

    db = get_session()
    try:
        record = db.query(SessionCreditRecord).filter(
            SessionCreditRecord.id == credit_id
        ).first()
        if record:
            record.used_at = None
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _uses_database() -> bool:
    from config import USE_DATABASE
    return USE_DATABASE
