"""
Integration tests for authentication + API endpoints.

Tests:
- Student registration -> login -> /me/stats endpoint
- Teacher registration -> login -> /teacher/topic_stats endpoint
- Role-based access control (403 when student tries teacher endpoints)
- Legacy API key flow still works
- Optional auth on /attempt endpoint
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from api import app
from auth_utils import hash_password
from users_models import User as AuthUser
from config import TEACHER_API_KEY


@pytest.fixture
def client():
    """FastAPI test client with enforced teacher auth and clean attempts file."""
    import os
    from pathlib import Path
    from config import DEFAULT_ATTEMPT_JSONL_PATH
    import repo_factory

    previous_public = getattr(app.state, "allow_public_teacher_endpoints", True)
    app.state.allow_public_teacher_endpoints = False
    os.environ["FORCE_TEACHER_AUTH"] = "1"

    repo_factory.reset_repositories()
    Path(DEFAULT_ATTEMPT_JSONL_PATH).unlink(missing_ok=True)
    Path("data/attempts.jsonl").unlink(missing_ok=True)
    try:
        Path(app.ATTEMPTS_FILE).unlink(missing_ok=True)  # type: ignore[attr-defined]
    except Exception:
        pass

    client = TestClient(app)
    try:
        yield client
    finally:
        app.state.allow_public_teacher_endpoints = previous_public
        os.environ.pop("FORCE_TEACHER_AUTH", None)
        repo_factory.reset_repositories()
        Path(DEFAULT_ATTEMPT_JSONL_PATH).unlink(missing_ok=True)
        Path("data/attempts.jsonl").unlink(missing_ok=True)
        try:
            Path(app.ATTEMPTS_FILE).unlink(missing_ok=True)  # type: ignore[attr-defined]
        except Exception:
            pass


@pytest.fixture
def student_token(client):
    """Register and login as a student, return JWT token."""
    # Register
    register_response = client.post(
        "/auth/register",
        json={
            "email": "student@example.com",
            "password": "TestPassword123",
            "role": "student",
            "display_name": "Test Student",
        }
    )
    assert register_response.status_code == 201
    return register_response.json()["access_token"]


@pytest.fixture
def teacher_token(client):
    """Register and login as a teacher, return JWT token."""
    # Register
    register_response = client.post(
        "/auth/register",
        json={
            "email": "teacher@example.com",
            "password": "TeacherPassword123",
            "role": "teacher",
            "display_name": "Test Teacher",
        }
    )
    assert register_response.status_code == 201
    return register_response.json()["access_token"]


@pytest.fixture
def admin_token(client):
    """Register and login as an admin, return JWT token."""
    # Register
    register_response = client.post(
        "/auth/register",
        json={
            "email": "admin@example.com",
            "password": "AdminPassword123",
            "role": "admin",
            "display_name": "Test Admin",
        }
    )
    assert register_response.status_code == 201
    return register_response.json()["access_token"]


class TestStudentAuthFlow:
    """Test student registration and authenticated endpoints."""

    def test_student_register_and_get_stats(self, client, student_token):
        """Student should be able to register and call /me/stats."""
        # Call /me/stats with the token
        response = client.get(
            "/me/stats/alg1_linear_solve_one_var",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        # Should succeed (even if no attempts yet)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["topic_id"] == "alg1_linear_solve_one_var"
        assert data["total_attempts"] == 0

    def test_student_register_and_get_recommendation(self, client, student_token):
        """Student should be able to call /me/recommend."""
        response = client.get(
            "/me/recommend/alg1_linear_solve_one_var",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "recommended_difficulty" in data
        assert "difficulty_range" in data

    def test_student_cannot_access_teacher_stats(self, client, student_token):
        """Student token should be rejected by teacher endpoints."""
        response = client.get(
            "/teacher/topic_stats",
            params={"topic_id": "alg1_linear_solve_one_var"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        # Should fail (student role not teacher/admin)
        assert response.status_code == 403
        assert "access required" in response.json()["detail"].lower()

    def test_student_cannot_access_admin_endpoints(self, client, student_token):
        """Student token should not have admin privileges."""
        # If there were admin-only endpoints, they should reject students
        # This is a placeholder for future admin endpoints
        pass


class TestTeacherAuthFlow:
    """Test teacher registration and authenticated endpoints."""

    def test_teacher_register_and_create_assignment(self, client, teacher_token):
        """Teacher should be able to register and create assignments."""
        response = client.post(
            "/teacher/assignments",
            json={
                "name": "Algebra Quiz 1",
                "description": "Basic linear equations",
                "topic_id": "alg1_linear_solve_one_var",
                "num_questions": 5,
                "min_difficulty": 1,
                "max_difficulty": 3,
            },
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Algebra Quiz 1"
        return data["id"]

    def test_teacher_can_access_topic_stats(self, client, teacher_token):
        """Teacher should be able to call /teacher/topic_stats."""
        response = client.get(
            "/teacher/topic_stats",
            params={"topic_id": "alg1_linear_solve_one_var"},
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["topic_id"] == "alg1_linear_solve_one_var"
        assert "success_rate" in data

    def test_teacher_can_access_user_overview(self, client, teacher_token):
        """Teacher should be able to call /teacher/user_overview."""
        # Use a fake user ID (doesn't need to exist)
        response = client.get(
            "/teacher/user_overview",
            params={"user_id": "test-user-id"},
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-id"

    def test_teacher_can_access_recent_attempts(self, client, teacher_token):
        """Teacher should be able to call /teacher/recent_attempts."""
        response = client.get(
            "/teacher/recent_attempts",
            params={"limit": 10},
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "attempts" in data
        assert "total_count" in data

    def test_student_cannot_create_assignment(self, client, student_token):
        """Student token should be rejected when creating assignments."""
        response = client.post(
            "/teacher/assignments",
            json={
                "name": "Unauthorized Quiz",
                "description": "This should fail",
                "topic_id": "alg1_linear_solve_one_var",
                "num_questions": 5,
            },
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        # Should fail (student role not teacher/admin)
        assert response.status_code == 403

    def test_student_cannot_access_user_overview(self, client, student_token):
        """Student token should be rejected by /teacher/user_overview."""
        response = client.get(
            "/teacher/user_overview",
            params={"user_id": "test-user"},
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 403


class TestAdminAuthFlow:
    """Test admin privileges."""

    def test_admin_can_access_teacher_endpoints(self, client, admin_token):
        """Admin should have access to all teacher endpoints."""
        response = client.get(
            "/teacher/topic_stats",
            params={"topic_id": "alg1_linear_solve_one_var"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200

    def test_admin_can_create_assignment(self, client, admin_token):
        """Admin should be able to create assignments."""
        response = client.post(
            "/teacher/assignments",
            json={
                "name": "Admin Assignment",
                "description": "Created by admin",
                "topic_id": "alg1_linear_solve_one_var",
                "num_questions": 3,
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        assert "id" in response.json()


class TestHybridAuthFlow:
    """Test fallback to API key when JWT fails or not provided."""

    def test_teacher_endpoint_with_api_key(self, client):
        """Teacher endpoints should still accept TEACHER_API_KEY."""
        if TEACHER_API_KEY is None:
            pytest.skip("TEACHER_API_KEY not configured")
        
        response = client.get(
            "/teacher/topic_stats",
            params={"topic_id": "alg1_linear_solve_one_var"},
            headers={"X-API-Key": TEACHER_API_KEY}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["topic_id"] == "alg1_linear_solve_one_var"

    def test_teacher_endpoint_rejects_invalid_api_key(self, client):
        """Teacher endpoints should reject invalid API key."""
        if TEACHER_API_KEY is None:
            pytest.skip("TEACHER_API_KEY not configured")
        
        response = client.get(
            "/teacher/topic_stats",
            params={"topic_id": "alg1_linear_solve_one_var"},
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 401

    def test_teacher_endpoint_prefers_jwt_over_api_key(self, client, teacher_token):
        """If both JWT and API key provided, JWT should be used."""
        if TEACHER_API_KEY is None:
            pytest.skip("TEACHER_API_KEY not configured")
        
        # Both valid token and API key
        response = client.get(
            "/teacher/topic_stats",
            params={"topic_id": "alg1_linear_solve_one_var"},
            headers={
                "Authorization": f"Bearer {teacher_token}",
                "X-API-Key": TEACHER_API_KEY,
            }
        )
        
        assert response.status_code == 200


class TestOptionalAuthOnAttempt:
    """Test optional auth on /attempt endpoint."""

    def test_attempt_with_authenticated_user(self, client, student_token):
        """Authenticated user's ID should be used in /attempt."""
        response = client.post(
            "/attempt",
            json={
                "user_id": "legacy-user-id",  # Should be ignored
                "problem_id": "prob123",
                "topic_id": "alg1_linear_solve_one_var",
                "course_id": "alg1",
                "difficulty": 2,
                "is_correct": True,
            },
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should use authenticated user's ID, not the legacy one
        assert data["user_id"] != "legacy-user-id"

    def test_attempt_with_legacy_user_id(self, client):
        """Legacy user_id should still work without auth."""
        response = client.post(
            "/attempt",
            json={
                "user_id": "legacy-user-123",
                "problem_id": "prob456",
                "topic_id": "alg1_linear_solve_one_var",
                "course_id": "alg1",
                "difficulty": 2,
                "is_correct": False,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "legacy-user-123"


class TestAuthTokenContent:
    """Test that auth tokens contain correct claims."""

    def test_student_token_has_role(self, client):
        """Student token should contain student role."""
        response = client.post(
            "/auth/register",
            json={
                "email": "claim_test_student@example.com",
                "password": "TestPassword123",
                "role": "student",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "student"

    def test_teacher_token_has_role(self, client):
        """Teacher token should contain teacher role."""
        response = client.post(
            "/auth/register",
            json={
                "email": "claim_test_teacher@example.com",
                "password": "TestPassword123",
                "role": "teacher",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "teacher"

    def test_token_contains_user_id(self, client):
        """Token response should contain user_id."""
        response = client.post(
            "/auth/register",
            json={
                "email": "claim_test_userid@example.com",
                "password": "TestPassword123",
                "role": "student",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert len(data["user_id"]) > 0


class TestMissingOrInvalidToken:
    """Test behavior with missing or invalid tokens."""

    def test_me_endpoint_without_token(self, client):
        """Calling /me without token should return 403."""
        response = client.get(
            "/me/stats/alg1_linear_solve_one_var"
        )
        
        assert response.status_code == 403

    def test_me_endpoint_with_invalid_token(self, client):
        """Calling /me with invalid token should return 401."""
        response = client.get(
            "/me/stats/alg1_linear_solve_one_var",
            headers={"Authorization": "Bearer invalid-token-here"}
        )
        
        assert response.status_code == 401

    def test_teacher_endpoint_without_auth(self, client):
        """Teacher endpoint without token or API key should return 401."""
        response = client.get(
            "/teacher/topic_stats",
            params={"topic_id": "alg1_linear_solve_one_var"}
        )
        
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
