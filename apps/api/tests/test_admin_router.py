"""
Tests for admin panel API endpoints (Section 1: Users, Section 2: Flagged Problems).

Runs in AUTH_PROVIDER=jwt + USE_DATABASE=false mode. All endpoints call
_require_db() which returns 503 without a real DB — so each test verifies
the correct 503 response plus the auth guard layer (401/403).

Dependency overrides via app.dependency_overrides bypass the Clerk JWT
check and inject a synthetic admin user directly.
"""

import os
import pytest
from datetime import datetime

os.environ["AUTH_PROVIDER"] = "jwt"
os.environ["USE_DATABASE"] = "false"


# ── helpers ──────────────────────────────────────────────────────────────────

def _admin_user():
    from users_models import User
    return User(
        id="admin-001",
        email="admin@example.com",
        password_hash="",
        role="admin",
        created_at=datetime.utcnow(),
    )


def _make_token(sub: str, role: str) -> str:
    from auth_utils import create_access_token
    from config import JWT_SECRET_KEY, JWT_ALGORITHM
    return create_access_token(
        {"sub": sub, "role": role},
        secret_key=JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


# ── Section 1: User Management ────────────────────────────────────────────────

class TestAdminUsersAuthGuard:
    """Unauthenticated and non-admin users must be rejected."""

    def test_unauthenticated_returns_401(self, client):
        res = client.get("/admin/users")
        assert res.status_code in (401, 403)

    def test_student_token_rejected(self, client):
        token = _make_token("student-001", "student")
        res = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code in (401, 403)

    def test_teacher_token_rejected(self, client):
        token = _make_token("teacher-001", "teacher")
        res = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code in (401, 403)


class TestAdminUsersNoDb:
    """With an admin override but no DB, endpoints return 503."""

    @pytest.fixture(autouse=True)
    def override_admin(self, client):
        from auth_dependencies import require_admin
        from api import app
        admin = _admin_user()
        app.dependency_overrides[require_admin] = lambda: admin
        yield
        app.dependency_overrides.pop(require_admin, None)

    def test_list_users_requires_db(self, client):
        res = client.get("/admin/users", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503
        assert "USE_DATABASE" in res.json()["detail"]

    def test_patch_user_requires_db(self, client):
        res = client.patch(
            "/admin/users/some-user-id",
            json={"role": "teacher"},
            headers={"Authorization": "Bearer fake"},
        )
        assert res.status_code == 503

    def test_patch_user_invalid_role_rejected(self, client):
        """Invalid role is caught before the DB check → 422."""
        res = client.patch(
            "/admin/users/some-user-id",
            json={"role": "superuser"},
            headers={"Authorization": "Bearer fake"},
        )
        assert res.status_code == 422
        assert "Invalid role" in res.json()["detail"]

    def test_patch_user_invalid_tier_rejected(self, client):
        res = client.patch(
            "/admin/users/some-user-id",
            json={"tier": "platinum"},
            headers={"Authorization": "Bearer fake"},
        )
        assert res.status_code == 422
        assert "Invalid tier" in res.json()["detail"]

    def test_reset_quota_only_requires_db(self, client):
        res = client.patch(
            "/admin/users/some-user-id",
            json={"reset_quota": True},
            headers={"Authorization": "Bearer fake"},
        )
        assert res.status_code == 503

    def test_patch_active_status_requires_db(self, client):
        res = client.patch(
            "/admin/users/some-user-id",
            json={"is_active": False},
            headers={"Authorization": "Bearer fake"},
        )
        assert res.status_code == 503


# ── Section 2: Flagged Problems ───────────────────────────────────────────────

class TestAdminFlaggedAuthGuard:
    """Flagged endpoints require admin role."""

    def test_list_flagged_unauthenticated(self, client):
        res = client.get("/admin/flagged")
        assert res.status_code in (401, 403)

    def test_list_flagged_resolved_unauthenticated(self, client):
        res = client.get("/admin/flagged?resolved=true")
        assert res.status_code in (401, 403)

    def test_dismiss_unauthenticated(self, client):
        res = client.post("/admin/flagged/flag-001/dismiss")
        assert res.status_code in (401, 403)

    def test_delete_unauthenticated(self, client):
        res = client.delete("/admin/flagged/flag-001")
        assert res.status_code in (401, 403)

    def test_edit_unauthenticated(self, client):
        res = client.patch("/admin/flagged/flag-001", json={"statement": "x"})
        assert res.status_code in (401, 403)


class TestAdminFlaggedNoDb:
    """With admin override but no DB, all flagged endpoints return 503."""

    @pytest.fixture(autouse=True)
    def override_admin(self, client):
        from auth_dependencies import require_admin
        from api import app
        admin = _admin_user()
        app.dependency_overrides[require_admin] = lambda: admin
        yield
        app.dependency_overrides.pop(require_admin, None)

    def test_list_flagged_requires_db(self, client):
        res = client.get("/admin/flagged", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503
        assert "USE_DATABASE" in res.json()["detail"]

    def test_list_flagged_resolved_filter_requires_db(self, client):
        res = client.get("/admin/flagged?resolved=true", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503

    def test_dismiss_requires_db(self, client):
        res = client.post("/admin/flagged/flag-001/dismiss", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503

    def test_delete_requires_db(self, client):
        res = client.delete("/admin/flagged/flag-001", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503

    def test_edit_requires_db(self, client):
        res = client.patch(
            "/admin/flagged/flag-001",
            json={"statement": "Fixed statement", "answer": "42"},
            headers={"Authorization": "Bearer fake"},
        )
        assert res.status_code == 503

    def test_edit_empty_body_requires_db(self, client):
        """PATCH with no fields still hits the DB (still returns 503)."""
        res = client.patch(
            "/admin/flagged/flag-001",
            json={},
            headers={"Authorization": "Bearer fake"},
        )
        assert res.status_code == 503


# ── Routing / mount ──────────────────────────────────────────────────────────

class TestAdminRouterMounted:
    """Verify /admin prefix is registered — auth failures not 404s."""

    def test_users_route_exists(self, client):
        assert client.get("/admin/users").status_code != 404

    def test_patch_user_route_exists(self, client):
        assert client.patch("/admin/users/x", json={}).status_code != 404

    def test_flagged_list_route_exists(self, client):
        assert client.get("/admin/flagged").status_code != 404

    def test_flagged_dismiss_route_exists(self, client):
        assert client.post("/admin/flagged/x/dismiss").status_code != 404

    def test_flagged_delete_route_exists(self, client):
        assert client.delete("/admin/flagged/x").status_code != 404

    def test_flagged_edit_route_exists(self, client):
        assert client.patch("/admin/flagged/x", json={}).status_code != 404

    def test_analytics_route_exists(self, client):
        assert client.get("/admin/analytics/overview").status_code != 404


# ── Section 3: Analytics ──────────────────────────────────────────────────────

class TestAdminAnalyticsAuthGuard:
    def test_unauthenticated(self, client):
        assert client.get("/admin/analytics/overview").status_code in (401, 403)

    def test_student_rejected(self, client):
        token = _make_token("student-001", "student")
        res = client.get("/admin/analytics/overview", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code in (401, 403)


class TestAdminAnalyticsNoDb:
    @pytest.fixture(autouse=True)
    def override_admin(self, client):
        from auth_dependencies import require_admin
        from api import app
        admin = _admin_user()
        app.dependency_overrides[require_admin] = lambda: admin
        yield
        app.dependency_overrides.pop(require_admin, None)

    def test_requires_db(self, client):
        res = client.get("/admin/analytics/overview", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503
        assert "USE_DATABASE" in res.json()["detail"]

    def test_bust_param_also_requires_db(self, client):
        res = client.get("/admin/analytics/overview?bust=true", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503


# ── Section 4: Quotas ─────────────────────────────────────────────────────────

class TestAdminQuotasAuthGuard:
    def test_unauthenticated(self, client):
        assert client.get("/admin/quotas/overview").status_code in (401, 403)

    def test_student_rejected(self, client):
        token = _make_token("student-001", "student")
        res = client.get("/admin/quotas/overview", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code in (401, 403)


class TestAdminQuotasNoDb:
    @pytest.fixture(autouse=True)
    def override_admin(self, client):
        from auth_dependencies import require_admin
        from api import app
        admin = _admin_user()
        app.dependency_overrides[require_admin] = lambda: admin
        yield
        app.dependency_overrides.pop(require_admin, None)

    def test_requires_db(self, client):
        res = client.get("/admin/quotas/overview", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503

    def test_only_active_filter_requires_db(self, client):
        res = client.get("/admin/quotas/overview?only_active=false", headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503


class TestAdminQuotaOverrideValidation:
    """Override limit validation runs before the DB check."""

    @pytest.fixture(autouse=True)
    def override_admin(self, client):
        from auth_dependencies import require_admin
        from api import app
        admin = _admin_user()
        app.dependency_overrides[require_admin] = lambda: admin
        yield
        app.dependency_overrides.pop(require_admin, None)

    def test_zero_override_rejected(self, client):
        res = client.patch("/admin/users/x", json={"daily_limit_override": 0},
                           headers={"Authorization": "Bearer fake"})
        assert res.status_code == 422

    def test_negative_override_rejected(self, client):
        res = client.patch("/admin/users/x", json={"daily_limit_override": -5},
                           headers={"Authorization": "Bearer fake"})
        assert res.status_code == 422

    def test_valid_override_reaches_db_check(self, client):
        res = client.patch("/admin/users/x", json={"daily_limit_override": 25},
                           headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503  # got past validation, hit DB check

    def test_clear_override_reaches_db_check(self, client):
        res = client.patch("/admin/users/x", json={"clear_limit_override": True},
                           headers={"Authorization": "Bearer fake"})
        assert res.status_code == 503


class TestAdminRouterMountedQuotas:
    def test_quotas_route_exists(self, client):
        assert client.get("/admin/quotas/overview").status_code != 404
