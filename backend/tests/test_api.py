"""
Tests for the FastAPI application.
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import app, ATTEMPTS_FILE
from tracking import save_attempt, Attempt
from datetime import datetime


@pytest.fixture(autouse=True)
def temp_attempts_file():
    """Use a temporary attempts file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        api_module = __import__("api")
        old_path = api_module.ATTEMPTS_FILE
        api_module.ATTEMPTS_FILE = Path(tmpdir) / "attempts.jsonl"
        # Reset factories to ensure fresh state
        from repo_factory import reset_repositories
        reset_repositories()
        yield
        api_module.ATTEMPTS_FILE = old_path
        # Reset again after test
        reset_repositories()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestListTopics:
    """Tests for GET /topics endpoint."""

    def test_list_topics_returns_list(self, client):
        """Test that /topics returns a non-empty list."""
        response = client.get("/topics")
        assert response.status_code == 200
        topics = response.json()
        assert isinstance(topics, list)
        assert len(topics) > 0

    def test_topic_has_required_fields(self, client):
        """Test that each topic has required fields."""
        response = client.get("/topics")
        topics = response.json()
        for topic in topics:
            assert "topic_id" in topic
            assert "course_id" in topic
            assert "unit_id" in topic

    def test_linear_equation_topic_present(self, client):
        """Test that linear equation topic is in the list."""
        response = client.get("/topics")
        topics = response.json()
        topic_ids = [t["topic_id"] for t in topics]
        assert "alg1_linear_solve_one_var" in topic_ids


class TestGenerateProblem:
    """Tests for GET /generate endpoint."""

    def test_generate_with_valid_topic(self, client):
        """Test generating a problem with a valid topic."""
        response = client.get(
            "/generate?topic_id=alg1_linear_solve_one_var&difficulty=2"
        )
        assert response.status_code == 200
        problem = response.json()
        assert problem["topic_id"] == "alg1_linear_solve_one_var"
        assert problem["difficulty"] == 2
        assert "prompt_latex" in problem
        assert "final_answer" in problem
        assert "solution" in problem

    def test_generate_with_invalid_topic(self, client):
        """Test that invalid topic returns 404."""
        response = client.get(
            "/generate?topic_id=nonexistent_topic&difficulty=2"
        )
        assert response.status_code == 404

    def test_generate_with_invalid_difficulty(self, client):
        """Test that invalid difficulty returns 422 (validation error)."""
        response = client.get(
            "/generate?topic_id=alg1_linear_solve_one_var&difficulty=99"
        )
        # FastAPI validates ge=1, le=6, so invalid difficulty is 422
        assert response.status_code == 422

    def test_generate_with_calculator_mode(self, client):
        """Test generating with different calculator modes."""
        for mode in ["none", "scientific", "graphing"]:
            response = client.get(
                f"/generate?topic_id=alg1_linear_solve_one_var&difficulty=2&calculator_mode={mode}"
            )
            assert response.status_code == 200
            problem = response.json()
            assert problem["calculator_mode"] == mode

    def test_generate_with_invalid_calculator_mode(self, client):
        """Test that invalid calculator mode returns 422."""
        response = client.get(
            "/generate?topic_id=alg1_linear_solve_one_var&difficulty=2&calculator_mode=invalid"
        )
        assert response.status_code == 422

    def test_generate_word_problem(self, client):
        """Test generating a word problem."""
        response = client.get(
            "/generate?topic_id=alg1_linear_solve_one_var&difficulty=2&word_problem=true&reading_level=grade_8"
        )
        assert response.status_code == 200
        problem = response.json()
        # Word problem wrapper should add word_problem_prompt
        assert "word_problem_prompt" in problem

    def test_generate_word_problem_with_context_tags(self, client):
        """Test generating word problem with context tags."""
        response = client.get(
            "/generate?topic_id=alg1_linear_solve_one_var&difficulty=2&word_problem=true&context_tags=money,distance"
        )
        assert response.status_code == 200
        problem = response.json()
        assert "word_problem_prompt" in problem

    def test_problem_response_has_solution_structure(self, client):
        """Test that solution is returned in response."""
        response = client.get(
            "/generate?topic_id=alg1_linear_solve_one_var&difficulty=2"
        )
        problem = response.json()
        solution = problem["solution"]
        assert isinstance(solution, dict)
        # Solution should have steps or other structure
        assert len(solution) > 0


class TestRecordAttempt:
    """Tests for POST /attempt endpoint."""

    def test_record_correct_attempt(self, client):
        """Test recording a correct attempt."""
        request_data = {
            "user_id": "student_1",
            "problem_id": "prob_001",
            "topic_id": "alg1_linear_solve_one_var",
            "course_id": "alg1",
            "difficulty": 2,
            "is_correct": True,
            "time_taken_seconds": 45.5,
        }
        response = client.post("/attempt", json=request_data)
        assert response.status_code == 200
        result = response.json()
        assert result["user_id"] == "student_1"
        assert result["problem_id"] == "prob_001"
        assert result["is_correct"] is True

    def test_record_incorrect_attempt(self, client):
        """Test recording an incorrect attempt."""
        request_data = {
            "user_id": "student_2",
            "problem_id": "prob_002",
            "topic_id": "alg1_linear_solve_one_var",
            "course_id": "alg1",
            "difficulty": 3,
            "is_correct": False,
        }
        response = client.post("/attempt", json=request_data)
        assert response.status_code == 200
        result = response.json()
        assert result["is_correct"] is False

    def test_record_attempt_without_time(self, client):
        """Test recording attempt without time_taken_seconds."""
        request_data = {
            "user_id": "student_3",
            "problem_id": "prob_003",
            "topic_id": "alg1_linear_solve_one_var",
            "course_id": "alg1",
            "difficulty": 1,
            "is_correct": True,
        }
        response = client.post("/attempt", json=request_data)
        assert response.status_code == 200

    def test_multiple_attempts_recorded(self, client):
        """Test that multiple attempts are recorded independently."""
        for i in range(3):
            request_data = {
                "user_id": "student_1",
                "problem_id": f"prob_{i:03d}",
                "topic_id": "alg1_linear_solve_one_var",
                "course_id": "alg1",
                "difficulty": 2,
                "is_correct": i % 2 == 0,
            }
            response = client.post("/attempt", json=request_data)
            assert response.status_code == 200


class TestUserStats:
    """Tests for GET /user/{user_id}/stats/{topic_id} endpoint."""

    def test_stats_for_user_with_no_attempts(self, client):
        """Test stats endpoint when user has no attempts."""
        response = client.get(
            "/user/unknown_user/stats/alg1_linear_solve_one_var"
        )
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_attempts"] == 0
        assert stats["correct_attempts"] == 0
        assert stats["success_rate"] == 0.0

    def test_stats_after_recording_attempts(self, client):
        """Test stats after recording some attempts."""
        # Record some attempts
        for is_correct in [True, False, True]:
            request_data = {
                "user_id": "student_1",
                "problem_id": f"prob_{is_correct}",
                "topic_id": "alg1_linear_solve_one_var",
                "course_id": "alg1",
                "difficulty": 2,
                "is_correct": is_correct,
            }
            client.post("/attempt", json=request_data)

        # Get stats
        response = client.get(
            "/user/student_1/stats/alg1_linear_solve_one_var"
        )
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_attempts"] == 3
        assert stats["correct_attempts"] == 2
        assert abs(stats["success_rate"] - 0.667) < 0.01

    def test_stats_correct_fields(self, client):
        """Test that stats response has all required fields."""
        response = client.get(
            "/user/some_user/stats/alg1_linear_solve_one_var"
        )
        stats = response.json()
        assert "user_id" in stats
        assert "topic_id" in stats
        assert "total_attempts" in stats
        assert "correct_attempts" in stats
        assert "success_rate" in stats
        assert "average_difficulty" in stats


class TestDifficultyRecommendation:
    """Tests for GET /user/{user_id}/recommend/{topic_id} endpoint."""

    def test_recommend_for_new_user(self, client):
        """Test recommendation for user with no history."""
        response = client.get(
            "/user/new_user/recommend/alg1_linear_solve_one_var"
        )
        assert response.status_code == 200
        rec = response.json()
        assert rec["user_id"] == "new_user"
        assert rec["topic_id"] == "alg1_linear_solve_one_var"
        assert "recommended_difficulty" in rec
        assert "difficulty_range" in rec
        assert "reason" in rec

    def test_recommend_after_successes(self, client):
        """Test that recommendation increases after successes."""
        # Record successful attempts
        for i in range(5):
            request_data = {
                "user_id": "student_1",
                "problem_id": f"prob_{i}",
                "topic_id": "alg1_linear_solve_one_var",
                "course_id": "alg1",
                "difficulty": 2,
                "is_correct": True,
            }
            client.post("/attempt", json=request_data)

        # Get recommendation
        response = client.get(
            "/user/student_1/recommend/alg1_linear_solve_one_var"
        )
        assert response.status_code == 200
        rec = response.json()
        # Should increase from 2 to 3
        assert rec["recommended_difficulty"] == 3

    def test_recommend_after_failures(self, client):
        """Test that recommendation decreases after failures."""
        # Record failed attempts at difficulty 3
        for i in range(5):
            request_data = {
                "user_id": "student_2",
                "problem_id": f"prob_{i}",
                "topic_id": "alg1_linear_solve_one_var",
                "course_id": "alg1",
                "difficulty": 3,
                "is_correct": False,
            }
            client.post("/attempt", json=request_data)

        # Get recommendation
        response = client.get(
            "/user/student_2/recommend/alg1_linear_solve_one_var"
        )
        assert response.status_code == 200
        rec = response.json()
        # Should decrease from 3 to 2
        assert rec["recommended_difficulty"] == 2

    def test_recommendation_includes_reason(self, client):
        """Test that recommendation response includes a reason."""
        response = client.get(
            "/user/some_user/recommend/alg1_linear_solve_one_var"
        )
        rec = response.json()
        assert isinstance(rec["reason"], str)
        assert len(rec["reason"]) > 0


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
