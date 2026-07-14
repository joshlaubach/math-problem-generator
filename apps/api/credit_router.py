"""
Session credit management — purchase, balance, and Stripe webhook.

Bundles (any authenticated student can buy any bundle — tutor access is
credits-only as of 2026-06-12; subscription tiers gate practice, not tutoring):
  single  → 1 credit  @ $40
  3pack   → 3 credits @ $99
  5pack   → 5 credits @ $149

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
    "single": {"credits": 1, "price_usd": 40, "tiers": "all"},
    "3pack":  {"credits": 3, "price_usd": 99, "tiers": "all"},
    "5pack":  {"credits": 5, "price_usd": 149, "tiers": "all"},
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


def _available_credits(user_id: str, session) -> list[SessionCreditRecord]:
    """Return all unused, non-expired credits for a user, oldest first."""
    now = datetime.now(timezone.utc)
    return (
        session.query(SessionCreditRecord)
        .filter(
            SessionCreditRecord.user_id == user_id,
            SessionCreditRecord.used_at.is_(None),
            SessionCreditRecord.expires_at > now,
        )
        .order_by(SessionCreditRecord.expires_at.asc())
        .all()
    )


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
    available: int
    expiring_soon: int   # within 30 days
    next_expiry: Optional[str]


class CheckoutRequest(BaseModel):
    bundle: str          # "single" | "3pack" | "5pack"
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
        return BalanceResponse(available=0, expiring_soon=0, next_expiry=None)

    session = get_session()
    try:
        credits = _available_credits(user.id, session)
        return BalanceResponse(
            available=len(credits),
            expiring_soon=_expiring_soon(credits),
            next_expiry=_next_expiry(credits),
        )
    finally:
        session.close()


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(require_student),
):
    """Create a Stripe Checkout Session for a credit bundle."""
    bundle = BUNDLES.get(body.bundle)
    if not bundle:
        raise HTTPException(status_code=422, detail=f"Unknown bundle: {body.bundle}. Must be one of {list(BUNDLES)}")

    price_id_env = {
        "single": "STRIPE_TUTOR_SINGLE_PRICE_ID",
        "3pack":  "STRIPE_TUTOR_3PACK_PRICE_ID",
        "5pack":  "STRIPE_TUTOR_5PACK_PRICE_ID",
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
    """Grant credits to the user after a successful checkout."""
    if not _uses_database():
        return

    meta = checkout_session.get("metadata", {})
    user_id = meta.get("user_id")
    credits_count = int(meta.get("credits", 0))
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
                expires_at=expires_at,
                purchase_id=purchase_id,
            )
            db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Internal helpers used by ws_router / tutor_router
# ---------------------------------------------------------------------------

def has_available_credit(user_id: str) -> bool:
    """
    Preflight: does the user have at least one unused, unexpired credit?

    Used by /tutor/session/create for a friendly intake-form error. Does NOT
    consume anything — consumption happens at WebSocket connect. Returns True
    when the database is disabled (dev/test), mirroring consume_credit's mock.
    """
    if not _uses_database():
        return True

    db = get_session()
    try:
        return len(_available_credits(user_id, db)) > 0
    finally:
        db.close()


def consume_credit(user_id: str) -> Optional[str]:
    """
    Soft-lock the oldest available credit for a session.

    Returns the credit ID on success, None if no credits available.
    Sets used_at to NOW — call restore_credit() if session fails within 2 min.
    """
    if not _uses_database():
        return "no-db-mock-credit"

    db = get_session()
    try:
        credits = _available_credits(user_id, db)
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
