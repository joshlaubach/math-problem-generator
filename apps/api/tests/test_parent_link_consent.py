"""
Regression tests for the parent-link consent path (audit Blocker F1).

Before the fix, redeem_parent_link crashed with a NameError on
ConsentLogRecord whenever the linked student had age_confirmed=False —
the one flow that records parental consent could never complete. A second
latent bug (DBUserRepository(lambda: db) closing the live session mid-
transaction) silently rolled back the link confirmation itself.

These tests drive the endpoint function directly against an in-memory
sqlite database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db_models import Base, ConsentLogRecord, ParentLinkRecord, UserRecord
from users_models import User


@pytest.fixture()
def db_factory():
    """In-memory sqlite shared across sessions (StaticPool keeps one conn)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture()
def fake_request():
    return SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.7"),
        headers={"user-agent": "pytest"},
    )


def _parent_user() -> User:
    return User(
        id="parent-1",
        email="parent@example.com",
        password_hash="",
        role="student",
        created_at=datetime.now(timezone.utc),
        is_active=True,
        age_confirmed=True,
        tier="free",
    )


def _seed(db, *, age_confirmed: bool) -> str:
    """Insert a student + an unconfirmed link code; return the code."""
    code = "test-code-" + uuid4().hex[:8]
    db.add(UserRecord(
        id="student-1",
        email="student@example.com",
        role="student",
        age_confirmed=age_confirmed,
    ))
    db.add(ParentLinkRecord(
        id=str(uuid4()),
        parent_id="",
        student_id="student-1",
        link_code=code,
        confirmed=False,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    ))
    db.commit()
    return code


@pytest.mark.asyncio
async def test_redeem_unlocks_unconfirmed_minor(monkeypatch, db_factory, fake_request):
    """The unconfirmed-minor branch must complete, log consent, and unlock."""
    import parent_router
    import rate_limit

    seed_db = db_factory()
    code = _seed(seed_db, age_confirmed=False)
    seed_db.close()

    monkeypatch.setattr(parent_router, "_uses_database", lambda: True)
    monkeypatch.setattr(parent_router, "_get_db", db_factory)
    monkeypatch.setattr(rate_limit, "hit", lambda *a, **k: (True, 0))

    result = await parent_router.redeem_parent_link(code, fake_request, _parent_user())
    assert result["ok"] is True
    assert result["student_email"] == "student@example.com"

    check = db_factory()
    try:
        link = check.query(ParentLinkRecord).filter_by(link_code=code).one()
        assert link.confirmed is True
        assert link.parent_id == "parent-1"

        student = check.query(UserRecord).filter_by(id="student-1").one()
        assert student.age_confirmed is True

        consent = check.query(ConsentLogRecord).filter_by(user_id="student-1").all()
        assert len(consent) == 1
        assert consent[0].event == "parent_consent_granted"
        assert consent[0].ip_address == "203.0.113.7"
    finally:
        check.close()


@pytest.mark.asyncio
async def test_redeem_already_confirmed_student_no_extra_consent_row(
    monkeypatch, db_factory, fake_request
):
    """Adult/already-confirmed student: link confirms, no consent row written."""
    import parent_router
    import rate_limit

    seed_db = db_factory()
    code = _seed(seed_db, age_confirmed=True)
    seed_db.close()

    monkeypatch.setattr(parent_router, "_uses_database", lambda: True)
    monkeypatch.setattr(parent_router, "_get_db", db_factory)
    monkeypatch.setattr(rate_limit, "hit", lambda *a, **k: (True, 0))

    result = await parent_router.redeem_parent_link(code, fake_request, _parent_user())
    assert result["ok"] is True

    check = db_factory()
    try:
        link = check.query(ParentLinkRecord).filter_by(link_code=code).one()
        assert link.confirmed is True
        assert check.query(ConsentLogRecord).count() == 0
    finally:
        check.close()


@pytest.mark.asyncio
async def test_redeem_invalid_code_404(monkeypatch, db_factory, fake_request):
    import parent_router
    import rate_limit
    from fastapi import HTTPException

    monkeypatch.setattr(parent_router, "_uses_database", lambda: True)
    monkeypatch.setattr(parent_router, "_get_db", db_factory)
    monkeypatch.setattr(rate_limit, "hit", lambda *a, **k: (True, 0))

    with pytest.raises(HTTPException) as exc:
        await parent_router.redeem_parent_link("nope", fake_request, _parent_user())
    assert exc.value.status_code == 404
