"""
Tests for Phase 5 — Rewards / Referral.

Covers:
  - Code generation (alphabet, length, uniqueness)
  - Milestone logic (pure functions — no DB required)
  - Dev-mode GET /referral/me (returns stub when USE_DATABASE=false)
  - POST /referral/use validation (self-referral, duplicate, code not found)
"""
import pytest
from unittest.mock import patch, MagicMock

import referral_router
from referral_router import (
    _gen_code,
    _CODE_ALPHABET,
    _session_milestone_hit,
    _referral_milestone_hit,
    _get_or_create_code,
    get_my_referral,
    use_referral_code,
    UseReferralRequest,
    ReferralStatsResponse,
)
from users_models import User
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Code generation
# ─────────────────────────────────────────────────────────────────────────────

class TestCodeGeneration:
    def test_code_length(self):
        assert len(_gen_code()) == 6

    def test_code_uses_allowed_alphabet(self):
        for _ in range(50):
            code = _gen_code()
            assert all(c in _CODE_ALPHABET for c in code), f"Bad char in {code!r}"

    def test_code_uppercase(self):
        code = _gen_code()
        assert code == code.upper()

    def test_excluded_chars_absent(self):
        """0, 1, I, O must never appear — they're transcription-error-prone."""
        for _ in range(200):
            code = _gen_code()
            for bad in "01IO":
                assert bad not in code, f"Found {bad!r} in {code!r}"

    def test_codes_differ(self):
        codes = {_gen_code() for _ in range(30)}
        assert len(codes) > 1  # extremely unlikely to be all equal


# ─────────────────────────────────────────────────────────────────────────────
# Milestone logic (pure, no DB)
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionMilestone:
    def test_zero_is_not_milestone(self):
        assert _session_milestone_hit(0) is False

    def test_four_is_not_milestone(self):
        assert _session_milestone_hit(4) is False

    def test_five_is_milestone(self):
        assert _session_milestone_hit(5) is True

    def test_six_is_not_milestone(self):
        assert _session_milestone_hit(6) is False

    def test_ten_is_milestone(self):
        assert _session_milestone_hit(10) is True

    def test_fifteen_is_milestone(self):
        assert _session_milestone_hit(15) is True

    def test_negative_is_not_milestone(self):
        assert _session_milestone_hit(-5) is False


class TestReferralMilestone:
    def test_zero_is_not_milestone(self):
        assert _referral_milestone_hit(0) is False

    def test_two_is_not_milestone(self):
        assert _referral_milestone_hit(2) is False

    def test_three_is_milestone(self):
        assert _referral_milestone_hit(3) is True

    def test_four_is_not_milestone(self):
        assert _referral_milestone_hit(4) is False

    def test_six_is_milestone(self):
        assert _referral_milestone_hit(6) is True

    def test_nine_is_milestone(self):
        assert _referral_milestone_hit(9) is True


# ─────────────────────────────────────────────────────────────────────────────
# Dev-mode (USE_DATABASE=false)
# ─────────────────────────────────────────────────────────────────────────────

class TestDevMode:
    def _make_user(self):
        return User(
            id="user-dev", email="dev@test.com",
            password_hash="", role="student",
            created_at=datetime.utcnow(), age_confirmed=True,
        )

    def test_get_my_referral_returns_stub(self):
        user = self._make_user()
        with patch.object(referral_router, "_uses_database", return_value=False):
            result = get_my_referral(user=user)
        assert result.code == "DEV123"
        assert result.referred_count == 0
        assert result.paid_sessions == 0
        assert result.next_session_reward_at == 5
        assert result.next_referral_reward_at == 3

    def test_use_referral_noop_in_dev_mode(self):
        user = self._make_user()
        body = UseReferralRequest(code="ABCDEF")
        with patch.object(referral_router, "_uses_database", return_value=False):
            result = use_referral_code(body=body, user=user)
        assert result == {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# POST /referral/use validation (DB mocked)
# ─────────────────────────────────────────────────────────────────────────────

class TestUseReferralValidation:
    """Tests that exercise validation paths using a minimal SQLAlchemy session mock."""

    def _make_user(self, uid="user-123"):
        return User(
            id=uid, email=f"{uid}@test.com",
            password_hash="", role="student",
            created_at=datetime.utcnow(), age_confirmed=True,
        )

    def _mock_db(self, existing_usage=None, already_paid=None, ref_record=None):
        """Return a MagicMock db where .query(...).filter(...).first() is controlled."""
        db = MagicMock()

        def query_side_effect(model):
            q = MagicMock()
            q_filtered = MagicMock()
            q_filtered.first.return_value = None

            from db_models import ReferralUsageRecord, SessionCreditRecord, ReferralRecord
            if model is ReferralUsageRecord and existing_usage is not None:
                # First call: check existing usage for this user
                q_filtered.first.return_value = existing_usage
            elif model is SessionCreditRecord and already_paid is not None:
                q_filtered.first.return_value = already_paid
            elif model is ReferralRecord and ref_record is not None:
                q_filtered.first.return_value = ref_record

            q.filter.return_value = q_filtered
            return q

        db.query.side_effect = query_side_effect
        return db

    def test_self_referral_blocked(self):
        from fastapi import HTTPException
        from db_models import ReferralRecord
        user = self._make_user("owner-user")

        ref = MagicMock(spec=ReferralRecord)
        ref.user_id = "owner-user"
        ref.code = "ABCDEF"

        db = MagicMock()
        call_count = [0]

        def q_side(model):
            q = MagicMock()
            fil = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                fil.first.return_value = None   # no existing usage
            elif call_count[0] == 2:
                fil.first.return_value = None   # no existing payment
            else:
                fil.first.return_value = ref    # code found, same owner
            q.filter.return_value = fil
            return q

        db.query.side_effect = q_side

        with patch.object(referral_router, "_uses_database", return_value=True), \
             patch("referral_router.get_session", return_value=db):
            body = UseReferralRequest(code="ABCDEF")
            with pytest.raises(HTTPException) as exc_info:
                use_referral_code(body=body, user=user)
            assert exc_info.value.status_code == 400
            assert "own referral code" in exc_info.value.detail

    def test_unknown_code_raises_404(self):
        from fastapi import HTTPException
        user = self._make_user()
        call_count = [0]

        db = MagicMock()

        def q_side(model):
            q = MagicMock()
            fil = MagicMock()
            call_count[0] += 1
            if call_count[0] <= 2:
                fil.first.return_value = None   # no usage, no payment
            else:
                fil.first.return_value = None   # code not found
            q.filter.return_value = fil
            return q

        db.query.side_effect = q_side

        with patch.object(referral_router, "_uses_database", return_value=True), \
             patch("referral_router.get_session", return_value=db):
            body = UseReferralRequest(code="ZZZZZZ")
            with pytest.raises(HTTPException) as exc_info:
                use_referral_code(body=body, user=user)
            assert exc_info.value.status_code == 404

    def test_double_referral_blocked(self):
        from fastapi import HTTPException
        from db_models import ReferralUsageRecord
        user = self._make_user()

        existing = MagicMock(spec=ReferralUsageRecord)
        existing.referred_user_id = user.id

        db = MagicMock()

        def q_side(model):
            q = MagicMock()
            fil = MagicMock()
            fil.first.return_value = existing   # already has a usage
            q.filter.return_value = fil
            return q

        db.query.side_effect = q_side

        with patch.object(referral_router, "_uses_database", return_value=True), \
             patch("referral_router.get_session", return_value=db):
            body = UseReferralRequest(code="ABCDEF")
            with pytest.raises(HTTPException) as exc_info:
                use_referral_code(body=body, user=user)
            assert exc_info.value.status_code == 409
            assert "already used" in exc_info.value.detail

    def test_code_normalised_to_uppercase(self):
        """Lowercase input is normalised; a valid uppercase code is then looked up."""
        from db_models import ReferralRecord
        user = self._make_user("buyer")

        ref = MagicMock(spec=ReferralRecord)
        ref.user_id = "other-user"
        ref.code = "ABCDEF"

        call_count = [0]
        db = MagicMock()

        def q_side(model):
            q = MagicMock()
            fil = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                fil.first.return_value = None   # no existing usage
            elif call_count[0] == 2:
                fil.first.return_value = None   # no existing payment
            else:
                fil.first.return_value = ref    # code found
            q.filter.return_value = fil
            return q

        db.query.side_effect = q_side
        db.commit = MagicMock()
        db.close = MagicMock()

        with patch.object(referral_router, "_uses_database", return_value=True), \
             patch("referral_router.get_session", return_value=db):
            body = UseReferralRequest(code="abcdef")   # lowercase input
            result = use_referral_code(body=body, user=user)
        assert result == {"ok": True}
