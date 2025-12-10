"""
Tests for teacher analytics API endpoints (Phase 7).

Verifies:
- Topic stats aggregation across users.
- User overview across topics.
- Recent attempts listing.
"""

from datetime import datetime
import pytest
from fastapi.testclient import TestClient

from api import app
from tracking import Attempt


@pytest.fixture
def client():
    """Fixture for FastAPI test client."""
    return TestClient(app)


def test_topic_stats_empty_topic(client):
    """Test /teacher/topic_stats with a topic that has no attempts."""
    response = client.get("/teacher/topic_stats?topic_id=nonexistent_topic")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["topic_id"] == "nonexistent_topic"
    assert data["total_attempts"] == 0
    assert data["correct_attempts"] == 0
    assert data["success_rate"] == 0.0
    assert data["average_difficulty"] is None
    assert data["average_time_seconds"] is None
    assert data["num_unique_students"] == 0


def test_user_overview_new_user(client):
    """Test /teacher/user_overview for a user with no attempts."""
    response = client.get("/teacher/user_overview?user_id=brand_new_user")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["user_id"] == "brand_new_user"
    assert data["topics"] == []
    assert data["total_attempts"] == 0
    assert data["total_correct"] == 0
    assert data["overall_success_rate"] == 0.0


def test_recent_attempts_empty(client):
    """Test /teacher/recent_attempts when no attempts exist."""
    response = client.get("/teacher/recent_attempts?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["attempts"] == []
    assert data["total_count"] == 0
    assert data["limit"] == 10


def test_recent_attempts_limit_parameter(client):
    """Test /teacher/recent_attempts respects limit parameter."""
    response = client.get("/teacher/recent_attempts?limit=5")
    
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    
    # Test default limit
    response = client.get("/teacher/recent_attempts")
    assert response.status_code == 200
    assert response.json()["limit"] == 50


def test_recent_attempts_invalid_limit(client):
    """Test /teacher/recent_attempts rejects invalid limit values."""
    # limit too high
    response = client.get("/teacher/recent_attempts?limit=1000")
    assert response.status_code == 422  # Validation error
    
    # limit too low
    response = client.get("/teacher/recent_attempts?limit=0")
    assert response.status_code == 422


def test_topic_stats_response_model(client):
    """Test /teacher/topic_stats response model has correct fields."""
    response = client.get("/teacher/topic_stats?topic_id=alg1_linear_solve_one_var")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = [
        "topic_id",
        "total_attempts",
        "correct_attempts",
        "success_rate",
        "num_unique_students",
    ]
    
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


def test_user_overview_response_model(client):
    """Test /teacher/user_overview response model has correct fields."""
    response = client.get("/teacher/user_overview?user_id=test_user")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = [
        "user_id",
        "topics",
        "total_attempts",
        "total_correct",
        "overall_success_rate",
    ]
    
    for field in required_fields:
        assert field in data, f"Missing field: {field}"
    
    # Check topics is a list
    assert isinstance(data["topics"], list)


def test_recent_attempts_response_model(client):
    """Test /teacher/recent_attempts response model has correct fields."""
    response = client.get("/teacher/recent_attempts?limit=20")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = ["attempts", "total_count", "limit"]
    
    for field in required_fields:
        assert field in data, f"Missing field: {field}"
    
    # Check attempts is a list
    assert isinstance(data["attempts"], list)


def test_recent_attempt_item_structure(client):
    """Test that recent attempts have correct item structure."""
    response = client.get("/teacher/recent_attempts?limit=50")
    
    assert response.status_code == 200
    data = response.json()
    
    # If there are attempts, check their structure
    if data["attempts"]:
        item = data["attempts"][0]
        
        required_fields = [
            "user_id",
            "topic_id",
            "difficulty",
            "is_correct",
            "timestamp",
        ]
        
        for field in required_fields:
            assert field in item, f"Missing field in attempt item: {field}"
