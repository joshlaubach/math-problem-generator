"""
Tests for teacher authentication endpoints (Phase 7).

Verifies:
- Authentication is required when TEACHER_API_KEY is set.
- Authentication is optional when TEACHER_API_KEY is None.
- Teacher endpoints return 401 with invalid keys.
"""

import pytest
from fastapi.testclient import TestClient


def test_teacher_topic_stats_with_valid_key(monkeypatch):
    """Test /teacher/topic_stats with valid API key."""
    # Set teacher API key via environment
    monkeypatch.setenv("TEACHER_API_KEY", "secret-teacher-key")
    
    # Re-import to pick up new env
    import importlib
    import api
    importlib.reload(api)
    
    client = TestClient(api.app)
    
    # Request with valid key
    response = client.get(
        "/teacher/topic_stats?topic_id=alg1_linear_solve_one_var",
        headers={"X-API-Key": "secret-teacher-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "topic_id" in data
    assert data["topic_id"] == "alg1_linear_solve_one_var"


def test_teacher_topic_stats_with_invalid_key(monkeypatch):
    """Test /teacher/topic_stats with invalid API key returns 401."""
    monkeypatch.setenv("TEACHER_API_KEY", "secret-teacher-key")
    
    import importlib
    import api
    importlib.reload(api)
    
    client = TestClient(api.app)
    
    # Request with invalid key
    response = client.get(
        "/teacher/topic_stats?topic_id=alg1_linear_solve_one_var",
        headers={"X-API-Key": "wrong-key"}
    )
    
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]


def test_teacher_topic_stats_no_key_header(monkeypatch):
    """Test /teacher/topic_stats without API key header returns 401 if auth is enabled."""
    monkeypatch.setenv("TEACHER_API_KEY", "secret-teacher-key")
    
    import importlib
    import api
    importlib.reload(api)
    
    client = TestClient(api.app)
    
    # Request without X-API-Key header
    response = client.get(
        "/teacher/topic_stats?topic_id=alg1_linear_solve_one_var"
    )
    
    assert response.status_code == 401


def test_teacher_topic_stats_no_auth_required():
    """Test /teacher/topic_stats is accessible without auth when TEACHER_API_KEY is None."""
    # Assuming default config has TEACHER_API_KEY = None
    from api import app
    
    client = TestClient(app)
    
    response = client.get(
        "/teacher/topic_stats?topic_id=alg1_linear_solve_one_var"
    )
    
    # Should be 200 (not 401) if no auth is configured
    assert response.status_code == 200


def test_teacher_user_overview_requires_auth(monkeypatch):
    """Test /teacher/user_overview respects authentication."""
    monkeypatch.setenv("TEACHER_API_KEY", "secret-key")
    
    import importlib
    import api
    importlib.reload(api)
    
    client = TestClient(api.app)
    
    # Without key
    response = client.get("/teacher/user_overview?user_id=test-user")
    assert response.status_code == 401
    
    # With key
    response = client.get(
        "/teacher/user_overview?user_id=test-user",
        headers={"X-API-Key": "secret-key"}
    )
    assert response.status_code == 200


def test_teacher_recent_attempts_requires_auth(monkeypatch):
    """Test /teacher/recent_attempts respects authentication."""
    monkeypatch.setenv("TEACHER_API_KEY", "secret-key")
    
    import importlib
    import api
    importlib.reload(api)
    
    client = TestClient(api.app)
    
    # Without key
    response = client.get("/teacher/recent_attempts")
    assert response.status_code == 401
    
    # With key
    response = client.get(
        "/teacher/recent_attempts",
        headers={"X-API-Key": "secret-key"}
    )
    assert response.status_code == 200


def test_teacher_endpoints_respond_with_correct_models():
    """Test /teacher endpoints return correct response models."""
    from api import app
    
    client = TestClient(app)
    
    # /teacher/topic_stats
    response = client.get("/teacher/topic_stats?topic_id=alg1_linear_solve_one_var")
    assert response.status_code == 200
    data = response.json()
    assert "topic_id" in data
    assert "total_attempts" in data
    assert "correct_attempts" in data
    assert "success_rate" in data
    
    # /teacher/user_overview
    response = client.get("/teacher/user_overview?user_id=test-user")
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "topics" in data
    assert "total_attempts" in data
    assert "total_correct" in data
    assert "overall_success_rate" in data
    
    # /teacher/recent_attempts
    response = client.get("/teacher/recent_attempts")
    assert response.status_code == 200
    data = response.json()
    assert "attempts" in data
    assert "total_count" in data
    assert "limit" in data
    assert isinstance(data["attempts"], list)
