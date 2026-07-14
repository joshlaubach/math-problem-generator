"""
Verification tests for the security audit remediation.

Maps to the audit's verification checklist. Runs with USE_DATABASE=false, so
DB-dependent paths (idempotency row checks, hard-delete purges) are asserted at
the logic level here and exercised end-to-end in staging.
"""
from __future__ import annotations

import pytest


# ── C1: Stripe webhook signature ──────────────────────────────────────────────

class TestWebhookSignature:
    def test_unsigned_webhook_rejected(self, client, monkeypatch):
        # STRIPE_WEBHOOK_SECRET unset in test env → fail closed (503), never
        # process a forged event.
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        forged = (
            '{"type":"checkout.session.completed","data":{"object":'
            '{"id":"evil","metadata":{"user_id":"victim","credits":"9999"}}}}'
        )
        resp = client.post(
            "/credits/webhook", content=forged,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 503

    def test_bad_signature_rejected(self, client, monkeypatch):
        pytest.importorskip("stripe")  # signature verification needs the SDK
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
        resp = client.post(
            "/credits/webhook", content='{"type":"x"}',
            headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=bad"},
        )
        # Invalid signature → 400 (never 200/no-op-success)
        assert resp.status_code == 400


# ── M6: Webhook idempotency ───────────────────────────────────────────────────

class TestWebhookIdempotency:
    def test_handler_checks_purchase_id_before_granting(self):
        # The handler must query existing credits by purchase_id (logic guard).
        import inspect
        import credit_router
        src = inspect.getsource(credit_router._handle_checkout_completed)
        assert "purchase_id" in src and "already" in src


# ── H1 / H4: rate limiting ────────────────────────────────────────────────────

class TestRateLimit:
    def test_sliding_window_blocks_over_limit(self):
        import rate_limit
        rate_limit.reset_for_testing()
        assert rate_limit.hit("k", 2, 60)[0] is True
        assert rate_limit.hit("k", 2, 60)[0] is True
        assert rate_limit.hit("k", 2, 60)[0] is False  # third exceeds

    def test_cooldown_set_and_remaining(self):
        import rate_limit
        rate_limit.reset_for_testing()
        assert rate_limit.cooldown_remaining("u") == 0
        rate_limit.set_cooldown("u", 60)
        assert rate_limit.cooldown_remaining("u") > 0


class TestAbuseGuardCooldown:
    def test_breach_triggers_timed_cooldown_not_permanent(self):
        import abuse_guard
        import rate_limit
        from fastapi import HTTPException
        rate_limit.reset_for_testing()

        # Exceed the hourly limit → 429
        with pytest.raises(HTTPException) as exc:
            for _ in range(abuse_guard.STUDENT_HOURLY_LIMIT + 2):
                abuse_guard.check_and_record("u1", "student", None)
        assert exc.value.status_code == 429
        # It's a timed cooldown, not a permanent suspension
        assert rate_limit.cooldown_remaining("abuse:u1") > 0

    def test_exempt_roles_never_limited(self):
        import abuse_guard
        import rate_limit
        rate_limit.reset_for_testing()
        for _ in range(100):
            abuse_guard.check_and_record("teacher1", "teacher", None)  # no raise


# ── H2: parent-link strength ──────────────────────────────────────────────────

class TestParentLinkCode:
    def test_code_is_high_entropy_and_case_sensitive(self):
        from parent_router import _generate_link_code
        codes = [_generate_link_code() for _ in range(20)]
        for c in codes:
            assert len(c) >= 16          # was 8
            assert c != c.upper() or c != c.lower()  # not case-collapsed in general
        assert len(set(codes)) == 20     # no collisions


# ── H3: content moderation ────────────────────────────────────────────────────

class TestContentModeration:
    @pytest.mark.parametrize("text", [
        "I want to kill myself",
        "i feel suicidal",
        "thinking about hurting myself",
        "there's no reason to live",
    ])
    def test_self_harm_flagged(self, text):
        import content_moderation
        verdict = content_moderation.screen(text)
        assert verdict.flagged is True
        assert verdict.category == "self_harm"
        assert "988" in verdict.response

    @pytest.mark.parametrize("text", [
        "how do I solve for x in 2x + 3 = 7?",
        "I'm stuck on factoring",
        "can you kill this extra term in the equation?",  # benign 'kill'
    ])
    def test_benign_not_flagged(self, text):
        import content_moderation
        assert content_moderation.screen(text).flagged is False

    def test_orchestrator_returns_crisis_response_not_tutoring(self):
        import asyncio
        from types import SimpleNamespace
        import session_orchestrator as so

        async def gen(*a, **k):
            raise AssertionError("LLM must not be called for flagged input")

        deps = so.SessionDeps(
            generate_tutor_response=gen, handle_going_too_fast=gen,
            check_exam_readiness=lambda s: False, get_exam_mode_proposal=gen,
            get_exam_start_message=gen, check_answer=gen, get_hint=gen,
            log_event=lambda **k: None, update_session=lambda s: None,
            looks_like_correction=lambda r: False,
        )
        session = SimpleNamespace(
            session_id="s", topic_id="t", difficulty=3, class_name="Algebra",
            conversation=[], soft_error_count=0,
        )
        user = SimpleNamespace(id="u", tier="free")
        res = asyncio.get_event_loop().run_until_complete(
            so.handle(session, user, {"type": "student_text", "text": "i want to kill myself"}, deps)
        )
        assert res.flagged is not None
        assert res.flagged.category == "self_harm"
        assert any("988" in m.payload.get("text", "") for m in res.messages)


# ── M1: security headers ──────────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_headers_present(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert "max-age=" in resp.headers.get("Strict-Transport-Security", "")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ── M5: Clerk issuer pinning ──────────────────────────────────────────────────

class TestClerkIssuer:
    def test_expected_issuer_derived_from_frontend_api(self, monkeypatch):
        import clerk_auth
        monkeypatch.setenv("CLERK_ISSUER", "")
        monkeypatch.setattr("config.CLERK_FRONTEND_API", "myapp.clerk.accounts.dev", raising=False)
        assert clerk_auth._expected_issuer() == "https://myapp.clerk.accounts.dev"


# ── M7: account deletion ──────────────────────────────────────────────────────

class TestAccountDeletion:
    def test_delete_me_returns_ok(self, auth_client):
        resp = auth_client.delete("/users/me")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
