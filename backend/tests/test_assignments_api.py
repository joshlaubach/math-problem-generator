"""
Tests for assignment endpoints.

Tests creation, retrieval, and analytics for assignments.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from api import app
from assignments_models import Assignment, AssignmentProblemLink
from db_session import get_session
from db_models import Base, AssignmentRecord, AssignmentProblemRecord
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_session():
    """Override get_session for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with overridden dependencies."""
    from fastapi.testclient import TestClient
    
    # Override get_session
    def get_test_session():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_session] = get_test_session
    
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestAssignmentCreation:
    """Tests for assignment creation endpoint."""

    def test_create_assignment_success(self, client):
        """Test successful assignment creation."""
        response = client.post(
            "/teacher/assignments",
            json={
                "name": "Algebra Fundamentals",
                "description": "Basic algebra problems",
                "topic_id": "algebra",
                "num_questions": 5,
                "min_difficulty": 1,
                "max_difficulty": 3,
                "calculator_mode": "none",
            },
            headers={"X-API-Key": ""},  # Mock auth
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Algebra Fundamentals"
        assert data["topic_id"] == "algebra"
        assert data["num_questions"] == 5
        assert data["status"] == "active"
        assert "id" in data
        assert len(data["id"]) > 0

    def test_create_assignment_with_defaults(self, client):
        """Test assignment creation with default values."""
        response = client.post(
            "/teacher/assignments",
            json={
                "name": "Quick Quiz",
                "topic_id": "geometry",
            },
            headers={"X-API-Key": ""},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["num_questions"] == 10  # default
        assert data["min_difficulty"] == 1  # default
        assert data["max_difficulty"] == 4  # default

    def test_create_assignment_generates_code(self, client):
        """Test that assignment code is properly formatted."""
        response1 = client.post(
            "/teacher/assignments",
            json={
                "name": "Test 1",
                "topic_id": "algebra",
            },
            headers={"X-API-Key": ""},
        )

        response2 = client.post(
            "/teacher/assignments",
            json={
                "name": "Test 2",
                "topic_id": "algebra",
            },
            headers={"X-API-Key": ""},
        )

        id1 = response1.json()["id"]
        id2 = response2.json()["id"]

        # Both should be valid codes
        assert "-" in id1
        assert "-" in id2
        # They should be different
        assert id1 != id2


class TestAssignmentRetrieval:
    """Tests for student-facing assignment endpoints."""

    def test_get_assignment_summary(self, client):
        """Test retrieving assignment summary."""
        # Create assignment
        create_response = client.post(
            "/teacher/assignments",
            json={
                "name": "Test Assignment",
                "topic_id": "algebra",
                "num_questions": 5,
            },
            headers={"X-API-Key": ""},
        )
        assignment_id = create_response.json()["id"]

        # Get summary
        response = client.get(f"/assignments/{assignment_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == assignment_id
        assert data["name"] == "Test Assignment"
        assert data["num_questions"] == 5
        assert data["status"] == "active"

    def test_get_assignment_not_found(self, client):
        """Test retrieving non-existent assignment."""
        response = client.get("/assignments/INVALID-CODE")
        assert response.status_code == 404

    def test_get_assignment_problem(self, client):
        """Test retrieving a specific problem from an assignment."""
        # Create assignment
        create_response = client.post(
            "/teacher/assignments",
            json={
                "name": "Test",
                "topic_id": "algebra",
                "num_questions": 3,
            },
            headers={"X-API-Key": ""},
        )
        assignment_id = create_response.json()["id"]

        # Get first problem
        response = client.get(f"/assignments/{assignment_id}/problem/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["assignment_id"] == assignment_id
        assert data["index"] == 1
        assert data["total"] == 3
        assert "problem" in data
        assert "prompt_latex" in data["problem"]

    def test_get_assignment_problem_invalid_index(self, client):
        """Test retrieving invalid problem index."""
        create_response = client.post(
            "/teacher/assignments",
            json={
                "name": "Test",
                "topic_id": "algebra",
                "num_questions": 3,
            },
            headers={"X-API-Key": ""},
        )
        assignment_id = create_response.json()["id"]

        # Try to get non-existent problem
        response = client.get(f"/assignments/{assignment_id}/problem/10")
        assert response.status_code == 404


class TestAssignmentStats:
    """Tests for assignment analytics endpoints."""

    def test_get_assignment_stats(self, client):
        """Test retrieving assignment statistics."""
        # Create assignment
        create_response = client.post(
            "/teacher/assignments",
            json={
                "name": "Stats Test",
                "topic_id": "algebra",
                "num_questions": 5,
            },
            headers={"X-API-Key": ""},
        )
        assignment_id = create_response.json()["id"]

        # Get stats
        response = client.get(
            f"/teacher/assignments/{assignment_id}/stats",
            headers={"X-API-Key": ""},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["assignment_id"] == assignment_id
        assert data["num_questions"] == 5
        assert "total_students" in data
        assert "total_attempts" in data
        assert "avg_score" in data

    def test_assignment_stats_not_found(self, client):
        """Test stats for non-existent assignment."""
        response = client.get(
            "/teacher/assignments/INVALID-CODE/stats",
            headers={"X-API-Key": ""},
        )
        assert response.status_code == 404


class TestAssignmentSequence:
    """Tests for complete assignment workflow."""

    def test_full_assignment_workflow(self, client):
        """Test complete student workflow through an assignment."""
        # 1. Teacher creates assignment
        create_response = client.post(
            "/teacher/assignments",
            json={
                "name": "Full Test",
                "topic_id": "algebra",
                "num_questions": 2,
                "min_difficulty": 1,
                "max_difficulty": 2,
            },
            headers={"X-API-Key": ""},
        )
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]

        # 2. Student gets assignment summary
        summary_response = client.get(f"/assignments/{assignment_id}")
        assert summary_response.status_code == 200
        assert summary_response.json()["num_questions"] == 2

        # 3. Student retrieves first problem
        problem1_response = client.get(f"/assignments/{assignment_id}/problem/1")
        assert problem1_response.status_code == 200
        assert problem1_response.json()["index"] == 1

        # 4. Student retrieves second problem
        problem2_response = client.get(f"/assignments/{assignment_id}/problem/2")
        assert problem2_response.status_code == 200
        assert problem2_response.json()["index"] == 2

        # 5. Teacher retrieves stats
        stats_response = client.get(
            f"/teacher/assignments/{assignment_id}/stats",
            headers={"X-API-Key": ""},
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["num_questions"] == 2
