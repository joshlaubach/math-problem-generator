"""
Tests for database-backed repositories using in-memory SQLite.

These tests verify that DBProblemRepository and DBAttemptRepository
work correctly with SQLAlchemy ORM. Uses SQLite for portability.
"""

import pytest
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Problem
from tracking import Attempt
from repositories import DBProblemRepository, DBAttemptRepository
from db_models import Base
from storage import problem_to_dict, dict_to_problem


@pytest.fixture
def in_memory_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def session_factory(in_memory_engine):
    """Create a session factory for the in-memory database."""
    SessionLocal = sessionmaker(bind=in_memory_engine, expire_on_commit=False)
    return SessionLocal


@pytest.fixture
def problem_repo(session_factory):
    """Create a DBProblemRepository for testing."""
    return DBProblemRepository(session_factory)


@pytest.fixture
def attempt_repo(session_factory):
    """Create a DBAttemptRepository for testing."""
    return DBAttemptRepository(session_factory)


@pytest.fixture
def sample_problem() -> Problem:
    """Create a sample problem for testing."""
    return Problem(
        id="test_prob_1",
        course_id="algebra_1",
        unit_id="alg1_unit_1",
        topic_id="alg1_linear_solve_one_var",
        difficulty=2,
        calculator_mode="none",
        prompt_latex="x + 5 = 10",
        answer_type="numeric",
        final_answer="5",
        metadata={"generated_at": "2025-12-09T10:00:00"},
    )


@pytest.fixture
def sample_attempt() -> Attempt:
    """Create a sample attempt for testing."""
    return Attempt(
        user_id="student_1",
        problem_id="test_prob_1",
        topic_id="alg1_linear_solve_one_var",
        course_id="algebra_1",
        difficulty=2,
        is_correct=True,
        timestamp=datetime(2025, 12, 9, 10, 30, 0),
        time_taken_seconds=45.0,
    )


class TestDBProblemRepository:
    """Tests for DBProblemRepository."""

    def test_save_and_get_problem(self, problem_repo, sample_problem):
        """Test saving and retrieving a problem."""
        problem_repo.save_problem(sample_problem)
        retrieved = problem_repo.get_problem(sample_problem.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_problem.id
        assert retrieved.topic_id == sample_problem.topic_id
        assert retrieved.difficulty == sample_problem.difficulty

    def test_get_nonexistent_problem(self, problem_repo):
        """Test retrieving a non-existent problem returns None."""
        result = problem_repo.get_problem("nonexistent_id")
        assert result is None

    def test_list_problems_by_topic(self, problem_repo, sample_problem):
        """Test listing problems by topic."""
        # Save multiple problems
        problem1 = sample_problem
        problem_repo.save_problem(problem1)
        
        problem2 = Problem(
            id="test_prob_2",
            course_id="algebra_1",
            unit_id="alg1_unit_1",
            topic_id="alg1_linear_solve_one_var",
            difficulty=3,
            calculator_mode="none",
            prompt_latex="2x = 10",
            answer_type="numeric",
            final_answer="5",
            metadata={},
        )
        problem_repo.save_problem(problem2)
        
        # List by topic
        problems = problem_repo.list_problems_by_topic("alg1_linear_solve_one_var")
        assert len(problems) == 2
        assert all(p.topic_id == "alg1_linear_solve_one_var" for p in problems)

    def test_list_all_problems(self, problem_repo, sample_problem):
        """Test listing all problems."""
        problem_repo.save_problem(sample_problem)
        
        problems = problem_repo.list_all_problems(limit=10)
        assert len(problems) >= 1
        assert any(p.id == sample_problem.id for p in problems)

    def test_update_existing_problem(self, problem_repo, sample_problem):
        """Test that saving an existing problem updates it."""
        problem_repo.save_problem(sample_problem)
        
        # Modify and resave
        modified_problem = Problem(
            id=sample_problem.id,
            course_id=sample_problem.course_id,
            unit_id=sample_problem.unit_id,
            topic_id=sample_problem.topic_id,
            difficulty=4,  # Changed
            calculator_mode=sample_problem.calculator_mode,
            prompt_latex=sample_problem.prompt_latex,
            answer_type=sample_problem.answer_type,
            final_answer=sample_problem.final_answer,
            metadata=sample_problem.metadata,
        )
        problem_repo.save_problem(modified_problem)
        
        # Verify update
        retrieved = problem_repo.get_problem(sample_problem.id)
        assert retrieved.difficulty == 4


class TestDBAttemptRepository:
    """Tests for DBAttemptRepository."""

    def test_save_and_retrieve_attempt(self, attempt_repo, sample_attempt):
        """Test saving and retrieving an attempt."""
        attempt_repo.save_attempt(sample_attempt)
        
        attempts = attempt_repo.list_attempts_by_user(sample_attempt.user_id)
        assert len(attempts) == 1
        assert attempts[0].user_id == sample_attempt.user_id
        assert attempts[0].is_correct == sample_attempt.is_correct

    def test_list_attempts_by_user_and_topic(self, attempt_repo, sample_attempt):
        """Test listing attempts filtered by user and topic."""
        attempt_repo.save_attempt(sample_attempt)
        
        # Add attempt for different topic
        other_attempt = Attempt(
            user_id="student_1",
            problem_id="other_prob",
            topic_id="alg1_linear_inequalities_one_var",
            course_id="algebra_1",
            difficulty=2,
            is_correct=False,
            timestamp=datetime(2025, 12, 9, 11, 0, 0),
            time_taken_seconds=30.0,
        )
        attempt_repo.save_attempt(other_attempt)
        
        # List for specific topic
        attempts = attempt_repo.list_attempts_by_user_and_topic(
            "student_1", "alg1_linear_solve_one_var"
        )
        assert len(attempts) == 1
        assert attempts[0].topic_id == "alg1_linear_solve_one_var"

    def test_list_attempts_by_user(self, attempt_repo, sample_attempt):
        """Test listing all attempts for a user."""
        attempt_repo.save_attempt(sample_attempt)
        
        # Add second attempt
        attempt2 = Attempt(
            user_id="student_1",
            problem_id="prob_2",
            topic_id="alg1_linear_inequalities_one_var",
            course_id="algebra_1",
            difficulty=3,
            is_correct=False,
            timestamp=datetime(2025, 12, 9, 11, 0, 0),
            time_taken_seconds=60.0,
        )
        attempt_repo.save_attempt(attempt2)
        
        # List all
        attempts = attempt_repo.list_attempts_by_user("student_1")
        assert len(attempts) == 2

    def test_list_all_attempts(self, attempt_repo, sample_attempt):
        """Test listing all attempts."""
        attempt_repo.save_attempt(sample_attempt)
        
        attempts = attempt_repo.list_all_attempts(limit=100)
        assert len(attempts) >= 1

    def test_multiple_users(self, attempt_repo):
        """Test attempts for multiple users."""
        for user_id in ["student_1", "student_2", "student_3"]:
            attempt = Attempt(
                user_id=user_id,
                problem_id="prob_1",
                topic_id="alg1_linear_solve_one_var",
                course_id="algebra_1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
                time_taken_seconds=45.0,
            )
            attempt_repo.save_attempt(attempt)
        
        # Verify user1 isolation
        user1_attempts = attempt_repo.list_attempts_by_user("student_1")
        assert len(user1_attempts) == 1
        assert user1_attempts[0].user_id == "student_1"
