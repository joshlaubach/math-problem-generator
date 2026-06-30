"""
Phase 4 gating tests: Clerk JWT verification and dual-auth behaviour.

All tests run with AUTH_PROVIDER=clerk and mock out verify_clerk_token
so no real Clerk instance is required in CI.

Covers:
- Valid Clerk token → 200, user JIT-provisioned
- Second request with same token → existing user returned (no duplicate)
- Age not confirmed → /me/stats returns 403
- /users/me/confirm-age sets age_confirmed=True
- After confirm-age → /me/stats returns 200
- Invalid / expired token → 401
- Inactive user → 403
- AUTH_PROVIDER=jwt falls back to legacy JWT (no regression)
"""

import pytest
from unittest.mock import patch
from datetime import datetime

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ADULT_DOB = {"date_of_birth": "1990-01-01"}  # age = 35+, always returns age_confirmed=True


def _make_clerk_payload(sub: str = "user_clerk_test_001") -> dict:
    """Minimal Clerk-style JWT payload for mocking."""
    return {
        "sub": sub,
        "iss": "https://test.clerk.accounts.dev",
        "iat": 1700000000,
        "exp": 9999999999,
        "sid": "sess_test",
        "azp": "http://localhost:3000",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clerk_client():
    """
    TestClient with AUTH_PROVIDER=clerk and a clean in-memory user repository.
    verify_clerk_token is patched so no real Clerk keys are needed.
    """
    import repo_factory
    import config
    import auth_dependencies

    # Set AUTH_PROVIDER directly on the module so runtime checks see it
    original_provider = config.AUTH_PROVIDER
    config.AUTH_PROVIDER = "clerk"

    repo_factory.reset_repositories()
    auth_dependencies._user_repo_instance = None

    from api import app
    client = TestClient(app, raise_server_exceptions=False)

    try:
        yield client
    finally:
        config.AUTH_PROVIDER = original_provider
        auth_dependencies._user_repo_instance = None
        repo_factory.reset_repositories()


# ---------------------------------------------------------------------------
# Test: valid Clerk token → 200 + JIT provisioning
# ---------------------------------------------------------------------------

class TestClerkJITProvisioning:

    def test_valid_clerk_token_provisions_user_and_returns_200_after_age_confirm(
        self, clerk_client
    ):
        payload = _make_clerk_payload("user_jit_001")

        with patch("clerk_auth.verify_clerk_token", return_value=payload), \
             patch("clerk_auth.fetch_clerk_user_email", return_value="jit@example.com"):

            # Confirm age first (bypasses age check)
            resp = clerk_client.post(
                "/users/me/confirm-age",
                json=_ADULT_DOB,
                headers={"Authorization": "Bearer fake-clerk-token"},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["age_confirmed"] is True

            # Now the regular endpoint should work
            resp2 = clerk_client.get(
                "/me/stats/alg1_linear_solve_one_var",
                headers={"Authorization": "Bearer fake-clerk-token"},
            )
            assert resp2.status_code == 200, resp2.text
            data = resp2.json()
            assert data["user_id"]  # some UUID was assigned

    def test_second_request_does_not_create_duplicate_user(self, clerk_client):
        payload = _make_clerk_payload("user_dedup_001")

        with patch("clerk_auth.verify_clerk_token", return_value=payload), \
             patch("clerk_auth.fetch_clerk_user_email", return_value="dedup@example.com"):

            # Confirm age
            clerk_client.post(
                "/users/me/confirm-age",
                json=_ADULT_DOB,
                headers={"Authorization": "Bearer fake-clerk-token"},
            )

            # Two calls to /me/stats should return the same user_id
            resp1 = clerk_client.get(
                "/me/stats/alg1_linear_solve_one_var",
                headers={"Authorization": "Bearer fake-clerk-token"},
            )
            resp2 = clerk_client.get(
                "/me/stats/alg1_linear_solve_one_var",
                headers={"Authorization": "Bearer fake-clerk-token"},
            )
            assert resp1.status_code == 200
            assert resp2.status_code == 200
            assert resp1.json()["user_id"] == resp2.json()["user_id"]


# ---------------------------------------------------------------------------
# Test: age gate
# ---------------------------------------------------------------------------

class TestAgeGate:

    def test_unconfirmed_age_blocks_me_stats(self, clerk_client):
        """Freshly provisioned user without age confirmation gets 403."""
        payload = _make_clerk_payload("user_unconfirmed_001")

        with patch("clerk_auth.verify_clerk_token", return_value=payload), \
             patch("clerk_auth.fetch_clerk_user_email", return_value="young@example.com"):

            resp = clerk_client.get(
                "/me/stats/alg1_linear_solve_one_var",
                headers={"Authorization": "Bearer fake-clerk-token"},
            )
            assert resp.status_code == 403
            assert "age" in resp.json()["detail"].lower()

    def test_confirm_age_endpoint_accessible_without_prior_age_confirmation(
        self, clerk_client
    ):
        """The confirm-age endpoint itself must NOT require age_confirmed."""
        payload = _make_clerk_payload("user_preconfirm_001")

        with patch("clerk_auth.verify_clerk_token", return_value=payload), \
             patch("clerk_auth.fetch_clerk_user_email", return_value="pre@example.com"):

            resp = clerk_client.post(
                "/users/me/confirm-age",
                json=_ADULT_DOB,
                headers={"Authorization": "Bearer fake-clerk-token"},
            )
            # Must succeed even though user has age_confirmed=False
            assert resp.status_code == 200
            assert resp.json()["age_confirmed"] is True

    def test_confirm_age_idempotent(self, clerk_client):
        """Calling confirm-age twice should not error."""
        payload = _make_clerk_payload("user_idem_001")

        with patch("clerk_auth.verify_clerk_token", return_value=payload), \
             patch("clerk_auth.fetch_clerk_user_email", return_value="idem@example.com"):

            for _ in range(2):
                resp = clerk_client.post(
                    "/users/me/confirm-age",
                    json=_ADULT_DOB,
                    headers={"Authorization": "Bearer fake-clerk-token"},
                )
                assert resp.status_code == 200
                assert resp.json()["age_confirmed"] is True


# ---------------------------------------------------------------------------
# Test: invalid / expired tokens
# ---------------------------------------------------------------------------

class TestInvalidClerkTokens:

    def test_invalid_token_returns_401(self, clerk_client):
        with patch("clerk_auth.verify_clerk_token", return_value=None):
            resp = clerk_client.get(
                "/me/stats/alg1_linear_solve_one_var",
                headers={"Authorization": "Bearer totally-invalid"},
            )
            assert resp.status_code == 401

    def test_missing_sub_claim_returns_401(self, clerk_client):
        payload_no_sub = {"iss": "https://test.clerk.accounts.dev", "exp": 9999999999}
        with patch("clerk_auth.verify_clerk_token", return_value=payload_no_sub):
            resp = clerk_client.get(
                "/me/stats/alg1_linear_solve_one_var",
                headers={"Authorization": "Bearer no-sub-token"},
            )
            assert resp.status_code == 401

    def test_no_authorization_header_returns_403(self, clerk_client):
        resp = clerk_client.get("/me/stats/alg1_linear_solve_one_var")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test: inactive user
# ---------------------------------------------------------------------------

class TestInactiveClerkUser:

    def test_inactive_user_returns_403(self, clerk_client):
        payload = _make_clerk_payload("user_inactive_001")

        with patch("clerk_auth.verify_clerk_token", return_value=payload), \
             patch("clerk_auth.fetch_clerk_user_email", return_value="inactive@example.com"):

            # Provision user and confirm age
            clerk_client.post(
                "/users/me/confirm-age",
                json=_ADULT_DOB,
                headers={"Authorization": "Bearer fake-token"},
            )

            # Deactivate the user directly via the repo
            import auth_dependencies
            repo = auth_dependencies.get_user_repository()
            user = repo.get_user_by_clerk_id("user_inactive_001")
            assert user is not None
            user.is_active = False
            repo.update_user(user)

            resp = clerk_client.get(
                "/me/stats/alg1_linear_solve_one_var",
                headers={"Authorization": "Bearer fake-token"},
            )
            assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test: JWT mode regression (AUTH_PROVIDER=jwt still works)
# ---------------------------------------------------------------------------

class TestJWTModeRegression:

    def test_jwt_mode_still_works(self):
        """With AUTH_PROVIDER=jwt (default), legacy JWT auth is unchanged."""
        import config
        import repo_factory
        import auth_dependencies

        original_provider = config.AUTH_PROVIDER
        config.AUTH_PROVIDER = "jwt"
        repo_factory.reset_repositories()
        auth_dependencies._user_repo_instance = None

        from api import app
        client = TestClient(app)

        try:
            resp = client.post(
                "/auth/register",
                json={
                    "email": "regression@example.com",
                    "password": "TestPassword123",
                    "role": "student",
                },
            )
            assert resp.status_code == 201
            token = resp.json()["access_token"]

            stats_resp = client.get(
                "/me/stats/alg1_linear_solve_one_var",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert stats_resp.status_code == 200
        finally:
            config.AUTH_PROVIDER = original_provider
            auth_dependencies._user_repo_instance = None
            repo_factory.reset_repositories()
