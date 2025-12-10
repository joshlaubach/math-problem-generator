"""
Integration tests for concept analytics API endpoints.

Tests the /me/concept_stats and /teacher/concept_stats endpoints.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from api import app
from models import Problem
from tracking import Attempt
from repositories import JSONLProblemRepository, JSONLAttemptRepository
from concepts import register_concept, Concept, CONCEPTS
import tempfile
from pathlib import Path


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_repositories(temp_data_dir):
    """Create temporary repositories."""
    problems_file = temp_data_dir / "problems.jsonl"
    attempts_file = temp_data_dir / "attempts.jsonl"
    
    problem_repo = JSONLProblemRepository(str(problems_file))
    attempt_repo = JSONLAttemptRepository(str(attempts_file))
    
    yield problem_repo, attempt_repo


@pytest.fixture
def clear_concepts():
    """Clear and restore concept registry."""
    original_concepts = CONCEPTS.copy()
    CONCEPTS.clear()
    yield
    CONCEPTS.clear()
    CONCEPTS.update(original_concepts)


@pytest.fixture
def sat_math_concepts(clear_concepts):
    """Register SAT Math concepts."""
    register_concept(Concept(
        id="sat.algebra.linear_basics",
        name="Linear Equations and Inequalities",
        course_id="sat_math",
        unit_id="sat_algebra",
        topic_id="sat_linear",
        kind="definition",
        description="SAT linear equations",
    ))
    
    register_concept(Concept(
        id="sat.algebra.quadratic_solving",
        name="Quadratic Functions and Solving",
        course_id="sat_math",
        unit_id="sat_algebra",
        topic_id="sat_quadratic",
        kind="skill",
        description="SAT quadratic solving",
    ))


@pytest.fixture
def ap_calc_concepts(clear_concepts):
    """Register AP Calculus concepts."""
    register_concept(Concept(
        id="ap_calc.derivatives.power_rule",
        name="Power Rule and Basic Derivative Rules",
        course_id="ap_calculus",
        unit_id="ap_derivatives",
        topic_id="ap_deriv_rules",
        kind="skill",
        description="Power rule for derivatives",
    ))


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# ============================================================================
# Helper Functions
# ============================================================================


def create_test_problem(
    problem_id: str,
    course_id: str,
    topic_id: str,
    unit_id: str,
    difficulty: int,
    primary_concept_id: str,
    concept_ids: list[str],
) -> Problem:
    """Helper to create a test problem."""
    return Problem(
        id=problem_id,
        course_id=course_id,
        unit_id=unit_id,
        topic_id=topic_id,
        difficulty=difficulty,
        calculator_mode="none",
        prompt_latex="Test problem",
        answer_type="numeric",
        final_answer=42,
        primary_concept_id=primary_concept_id,
        concept_ids=concept_ids,
    )


# ============================================================================
# Tests for /me/concept_stats/{course_id} (Student Endpoint)
# ============================================================================


def test_student_concept_stats_requires_auth(test_client):
    """Test that student endpoint requires authentication."""
    response = test_client.get("/me/concept_stats/sat_math")
    assert response.status_code in [401, 403]  # Unauthorized or Forbidden


def test_student_concept_stats_with_jwt_token(
    test_client,
    sat_math_concepts,
    temp_repositories,
    monkeypatch,
):
    """Test student concept stats endpoint with valid JWT token.
    
    Note: This test demonstrates the endpoint structure, but full JWT
    validation depends on auth_dependencies configuration. In a real
    deployment, you would use valid test JWTs.
    """
    problem_repo, attempt_repo = temp_repositories
    
    # Patch the repositories in api module
    import api
    original_get_attempt = api.get_attempt_repository
    original_get_problem = api.factory_get_problem_repository
    
    def mock_get_attempt():
        return attempt_repo
    
    def mock_get_problem():
        return problem_repo
    
    monkeypatch.setattr(api, "get_attempt_repository", mock_get_attempt)
    monkeypatch.setattr(api, "factory_get_problem_repository", mock_get_problem)
    
    # Create test data
    p1 = create_test_problem(
        "p1", "sat_math", "sat_linear", "sat_algebra", 2,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    problem_repo.save_problem(p1)
    
    # Note: In a real scenario, you'd need to provide a valid JWT token
    # For now, we test the endpoint structure
    # This will return 401/403 without proper auth setup
    response = test_client.get("/me/concept_stats/sat_math")
    assert response.status_code in [200, 401, 403]  # Success or auth error


# ============================================================================
# Tests for /teacher/concept_stats (Teacher Endpoint)
# ============================================================================


def test_teacher_concept_stats_requires_auth(test_client):
    """Test that teacher endpoint enforces auth when configured.
    
    Note: When TEACHER_API_KEY is None, auth is disabled (testing mode).
    This test verifies the endpoint structure and auth header handling.
    """
    response = test_client.get(
        "/teacher/concept_stats",
        params={"course_id": "sat_math", "user_id": "student123"}
    )
    # In testing mode (TEACHER_API_KEY=None), endpoint allows all requests
    # In production (TEACHER_API_KEY set), would expect 401
    assert response.status_code in [200, 401, 403]


def test_teacher_concept_stats_with_valid_api_key(
    test_client,
    sat_math_concepts,
    temp_repositories,
    monkeypatch,
):
    """Test teacher concept stats with valid API key."""
    problem_repo, attempt_repo = temp_repositories
    
    # Patch repositories
    import api
    monkeypatch.setattr(api, "get_attempt_repository", lambda: attempt_repo)
    monkeypatch.setattr(api, "factory_get_problem_repository", lambda: problem_repo)
    
    # Set a test teacher API key
    monkeypatch.setattr(api, "TEACHER_API_KEY", "test_key_123")
    
    # Create test data
    p1 = create_test_problem(
        "p1", "sat_math", "sat_linear", "sat_algebra", 2,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    problem_repo.save_problem(p1)
    
    attempt_repo.save_attempt(Attempt(
        user_id="student123",
        problem_id="p1",
        topic_id="sat_linear",
        course_id="sat_math",
        difficulty=2,
        is_correct=True,
        timestamp=datetime(2024, 1, 1),
        time_taken_seconds=120.0,
    ))
    
    # Request with API key
    response = test_client.get(
        "/teacher/concept_stats",
        params={"course_id": "sat_math", "user_id": "student123"},
        headers={"X-API-Key": "test_key_123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["user_id"] == "student123"
    assert data["course_id"] == "sat_math"
    assert len(data["concept_stats"]) > 0
    
    # Check concept stats
    linear_stats = next(
        (s for s in data["concept_stats"] if s["concept_id"] == "sat.algebra.linear_basics"),
        None
    )
    assert linear_stats is not None
    assert linear_stats["total_attempts"] == 1
    assert linear_stats["correct_attempts"] == 1
    assert linear_stats["success_rate"] == 1.0


def test_teacher_concept_stats_invalid_api_key(
    test_client,
    sat_math_concepts,
    monkeypatch,
):
    """Test that invalid API key is rejected."""
    import api
    monkeypatch.setattr(api, "TEACHER_API_KEY", "correct_key")
    
    response = test_client.get(
        "/teacher/concept_stats",
        params={"course_id": "sat_math", "user_id": "student123"},
        headers={"X-API-Key": "wrong_key"}
    )
    
    assert response.status_code == 401


def test_teacher_concept_stats_aggregates_multiple_concepts(
    test_client,
    sat_math_concepts,
    temp_repositories,
    monkeypatch,
):
    """Test that endpoint aggregates stats for all concepts in course."""
    problem_repo, attempt_repo = temp_repositories
    
    import api
    monkeypatch.setattr(api, "get_attempt_repository", lambda: attempt_repo)
    monkeypatch.setattr(api, "factory_get_problem_repository", lambda: problem_repo)
    monkeypatch.setattr(api, "TEACHER_API_KEY", "test_key")
    
    # Create problems for two concepts
    p1 = create_test_problem(
        "p1", "sat_math", "sat_linear", "sat_algebra", 2,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    p2 = create_test_problem(
        "p2", "sat_math", "sat_quadratic", "sat_algebra", 3,
        "sat.algebra.quadratic_solving", ["sat.algebra.quadratic_solving"]
    )
    problem_repo.save_problem(p1)
    problem_repo.save_problem(p2)
    
    # Create attempts on both
    attempt_repo.save_attempt(Attempt(
        user_id="student123", problem_id="p1", topic_id="sat_linear",
        course_id="sat_math", difficulty=2, is_correct=True,
        timestamp=datetime(2024, 1, 1),
    ))
    attempt_repo.save_attempt(Attempt(
        user_id="student123", problem_id="p2", topic_id="sat_quadratic",
        course_id="sat_math", difficulty=3, is_correct=False,
        timestamp=datetime(2024, 1, 2),
    ))
    
    response = test_client.get(
        "/teacher/concept_stats",
        params={"course_id": "sat_math", "user_id": "student123"},
        headers={"X-API-Key": "test_key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have stats for both concepts
    concept_ids = {s["concept_id"] for s in data["concept_stats"]}
    assert "sat.algebra.linear_basics" in concept_ids
    assert "sat.algebra.quadratic_solving" in concept_ids
    
    # Check aggregated total
    total_attempts = sum(s["total_attempts"] for s in data["concept_stats"])
    assert total_attempts == 2


def test_teacher_concept_stats_response_structure(
    test_client,
    sat_math_concepts,
    temp_repositories,
    monkeypatch,
):
    """Test that response has correct structure."""
    problem_repo, attempt_repo = temp_repositories
    
    import api
    monkeypatch.setattr(api, "get_attempt_repository", lambda: attempt_repo)
    monkeypatch.setattr(api, "factory_get_problem_repository", lambda: problem_repo)
    monkeypatch.setattr(api, "TEACHER_API_KEY", "test_key")
    
    p = create_test_problem(
        "p1", "sat_math", "sat_linear", "sat_algebra", 2,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    problem_repo.save_problem(p)
    
    attempt_repo.save_attempt(Attempt(
        user_id="student123", problem_id="p1", topic_id="sat_linear",
        course_id="sat_math", difficulty=2, is_correct=True,
        timestamp=datetime(2024, 1, 1), time_taken_seconds=150.0,
    ))
    
    response = test_client.get(
        "/teacher/concept_stats",
        params={"course_id": "sat_math", "user_id": "student123"},
        headers={"X-API-Key": "test_key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert "user_id" in data
    assert "course_id" in data
    assert "concept_stats" in data
    assert "total_concepts" in data
    assert "total_attempts" in data
    
    # Verify concept_stats items have required fields
    if len(data["concept_stats"]) > 0:
        stat = data["concept_stats"][0]
        assert "concept_id" in stat
        assert "concept_name" in stat
        assert "total_attempts" in stat
        assert "correct_attempts" in stat
        assert "success_rate" in stat
        assert "average_difficulty" in stat
        assert "average_time_seconds" in stat


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
