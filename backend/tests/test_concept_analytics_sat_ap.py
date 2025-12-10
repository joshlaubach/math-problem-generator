"""
Unit tests for concept-level analytics.

Tests the ConceptStats aggregation and filtering functions.
"""

import pytest
from datetime import datetime
from typing import Sequence

from models import Problem, SolutionStep, Solution
from tracking import Attempt
from repositories import ProblemRepository, AttemptRepository
from concept_analytics import (
    ConceptStats,
    get_user_concept_stats,
    get_course_concept_heatmap,
    get_course_concept_stats_for_topic,
)
from concepts import register_concept, Concept, CONCEPTS


# ============================================================================
# In-Memory Repositories for Testing
# ============================================================================


class InMemoryProblemRepository:
    """In-memory problem repository for testing."""
    
    def __init__(self):
        self.problems: dict[str, Problem] = {}
    
    def save_problem(self, problem: Problem) -> None:
        self.problems[problem.id] = problem
    
    def get_problem(self, problem_id: str) -> Problem | None:
        return self.problems.get(problem_id)
    
    def list_problems_by_topic(self, topic_id: str, limit: int = 50) -> Sequence[Problem]:
        result = [p for p in self.problems.values() if p.topic_id == topic_id]
        return result[:limit]
    
    def list_all_problems(self, limit: int = 100) -> Sequence[Problem]:
        all_problems = list(self.problems.values())
        return all_problems[:limit]


class InMemoryAttemptRepository:
    """In-memory attempt repository for testing."""
    
    def __init__(self):
        self.attempts: list[Attempt] = []
    
    def save_attempt(self, attempt: Attempt) -> None:
        self.attempts.append(attempt)
    
    def list_attempts_by_user_and_topic(
        self, user_id: str, topic_id: str
    ) -> Sequence[Attempt]:
        return [
            a for a in self.attempts
            if a.user_id == user_id and a.topic_id == topic_id
        ]
    
    def list_attempts_by_user(self, user_id: str) -> Sequence[Attempt]:
        return [a for a in self.attempts if a.user_id == user_id]
    
    def list_all_attempts(self, limit: int = 100) -> Sequence[Attempt]:
        return self.attempts[:limit]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def clear_concepts():
    """Clear the concept registry before and after each test."""
    original_concepts = CONCEPTS.copy()
    CONCEPTS.clear()
    yield
    CONCEPTS.clear()
    CONCEPTS.update(original_concepts)


@pytest.fixture
def sat_math_concepts(clear_concepts):
    """Register SAT Math concepts for testing."""
    register_concept(Concept(
        id="sat.algebra.linear_basics",
        name="Linear Equations and Inequalities",
        course_id="sat_math",
        unit_id="sat_algebra",
        topic_id="sat_linear",
        kind="definition",
        description="SAT linear equations",
        prerequisites=["alg1.linear_eq.one_step_int"],
    ))
    
    register_concept(Concept(
        id="sat.algebra.quadratic_solving",
        name="Quadratic Functions and Solving",
        course_id="sat_math",
        unit_id="sat_algebra",
        topic_id="sat_quadratic",
        kind="skill",
        description="SAT quadratic solving",
        prerequisites=["alg2.quadratic.solving_methods"],
    ))
    
    register_concept(Concept(
        id="sat.data.statistics",
        name="Statistics and Probability",
        course_id="sat_math",
        unit_id="sat_data",
        topic_id="sat_statistics",
        kind="skill",
        description="SAT statistics",
        prerequisites=[],
    ))
    
    register_concept(Concept(
        id="alg1.linear_eq.one_step_int",
        name="One-step equations with integers",
        course_id="alg1",
        unit_id="alg1_unit_linear",
        topic_id="alg1_linear_one_var",
        kind="skill",
        description="Solving one-step equations",
    ))


@pytest.fixture
def ap_calc_concepts(clear_concepts):
    """Register AP Calculus concepts for testing."""
    register_concept(Concept(
        id="ap_calc.derivatives.power_rule",
        name="Power Rule and Basic Derivative Rules",
        course_id="ap_calculus",
        unit_id="ap_derivatives",
        topic_id="ap_deriv_rules",
        kind="skill",
        description="Power rule for derivatives",
        prerequisites=["ap_calc.derivatives.definition"],
    ))
    
    register_concept(Concept(
        id="ap_calc.derivatives.definition",
        name="Derivative as a Limit",
        course_id="ap_calculus",
        unit_id="ap_derivatives",
        topic_id="ap_deriv_def",
        kind="definition",
        description="Derivative definition",
    ))
    
    register_concept(Concept(
        id="ap_calc.integrals.ftc",
        name="Fundamental Theorem of Calculus",
        course_id="ap_calculus",
        unit_id="ap_integrals",
        topic_id="ap_int_ftc",
        kind="theorem",
        description="FTC",
    ))


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
        metadata={},
    )


# ============================================================================
# Tests for get_user_concept_stats
# ============================================================================


def test_user_concept_stats_no_attempts(sat_math_concepts):
    """Test concept stats when user has no attempts."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    stats = get_user_concept_stats(
        "user123",
        "sat.algebra.linear_basics",
        attempt_repo,
        problem_repo,
    )
    
    assert stats.concept_id == "sat.algebra.linear_basics"
    assert stats.total_attempts == 0
    assert stats.correct_attempts == 0
    assert stats.success_rate is None
    assert stats.average_difficulty is None


def test_user_concept_stats_with_attempts(sat_math_concepts):
    """Test concept stats with correct and incorrect attempts."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    # Create two problems tagged with sat.algebra.linear_basics
    p1 = create_test_problem(
        "p1", "sat_math", "sat_linear", "sat_algebra", 2,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    p2 = create_test_problem(
        "p2", "sat_math", "sat_linear", "sat_algebra", 3,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    problem_repo.save_problem(p1)
    problem_repo.save_problem(p2)
    
    # Create attempts: 1 correct on p1, 1 incorrect on p2
    attempt_repo.save_attempt(Attempt(
        user_id="user123",
        problem_id="p1",
        topic_id="sat_linear",
        course_id="sat_math",
        difficulty=2,
        is_correct=True,
        timestamp=datetime(2024, 1, 1),
        time_taken_seconds=120.0,
    ))
    attempt_repo.save_attempt(Attempt(
        user_id="user123",
        problem_id="p2",
        topic_id="sat_linear",
        course_id="sat_math",
        difficulty=3,
        is_correct=False,
        timestamp=datetime(2024, 1, 2),
        time_taken_seconds=180.0,
    ))
    
    stats = get_user_concept_stats(
        "user123",
        "sat.algebra.linear_basics",
        attempt_repo,
        problem_repo,
    )
    
    assert stats.concept_id == "sat.algebra.linear_basics"
    assert stats.total_attempts == 2
    assert stats.correct_attempts == 1
    assert stats.success_rate == 0.5
    assert stats.average_difficulty == 2.5
    assert stats.average_time_seconds == 150.0


def test_user_concept_stats_filters_by_concept(sat_math_concepts):
    """Test that stats only include problems tagged with the concept."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    # Create problems: one for linear_basics, one for quadratic
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
        user_id="user123", problem_id="p1", topic_id="sat_linear",
        course_id="sat_math", difficulty=2, is_correct=True,
        timestamp=datetime(2024, 1, 1),
    ))
    attempt_repo.save_attempt(Attempt(
        user_id="user123", problem_id="p2", topic_id="sat_quadratic",
        course_id="sat_math", difficulty=3, is_correct=True,
        timestamp=datetime(2024, 1, 2),
    ))
    
    # Get stats for linear_basics only
    stats = get_user_concept_stats(
        "user123",
        "sat.algebra.linear_basics",
        attempt_repo,
        problem_repo,
    )
    
    # Should only count the p1 attempt
    assert stats.total_attempts == 1
    assert stats.correct_attempts == 1
    assert stats.average_difficulty == 2.0


def test_user_concept_stats_nonexistent_concept(sat_math_concepts):
    """Test that KeyError is raised for nonexistent concept."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    with pytest.raises(KeyError):
        get_user_concept_stats(
            "user123",
            "nonexistent.concept.id",
            attempt_repo,
            problem_repo,
        )


# ============================================================================
# Tests for get_course_concept_heatmap
# ============================================================================


def test_course_concept_heatmap_no_attempts(sat_math_concepts):
    """Test heatmap when user has no attempts."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    heatmap = get_course_concept_heatmap(
        "user123",
        "sat_math",
        attempt_repo,
        problem_repo,
    )
    
    # Should include all sat_math concepts even with no attempts
    concept_ids = {s.concept_id for s in heatmap}
    assert "sat.algebra.linear_basics" in concept_ids
    assert "sat.algebra.quadratic_solving" in concept_ids
    assert "sat.data.statistics" in concept_ids


def test_course_concept_heatmap_multiple_concepts(sat_math_concepts):
    """Test heatmap aggregates multiple concepts for a course."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    # Create problems for different SAT Math concepts
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
        user_id="user123", problem_id="p1", topic_id="sat_linear",
        course_id="sat_math", difficulty=2, is_correct=True,
        timestamp=datetime(2024, 1, 1),
    ))
    attempt_repo.save_attempt(Attempt(
        user_id="user123", problem_id="p2", topic_id="sat_quadratic",
        course_id="sat_math", difficulty=3, is_correct=False,
        timestamp=datetime(2024, 1, 2),
    ))
    
    heatmap = get_course_concept_heatmap(
        "user123",
        "sat_math",
        attempt_repo,
        problem_repo,
    )
    
    # Find stats for the two concepts we attempted
    linear_stats = next(
        (s for s in heatmap if s.concept_id == "sat.algebra.linear_basics"),
        None
    )
    quad_stats = next(
        (s for s in heatmap if s.concept_id == "sat.algebra.quadratic_solving"),
        None
    )
    
    assert linear_stats is not None
    assert linear_stats.total_attempts == 1
    assert linear_stats.correct_attempts == 1
    
    assert quad_stats is not None
    assert quad_stats.total_attempts == 1
    assert quad_stats.correct_attempts == 0


def test_course_concept_heatmap_sorted(sat_math_concepts):
    """Test that heatmap is sorted by concept_id."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    # Create problems for all concepts
    p1 = create_test_problem(
        "p1", "sat_math", "sat_linear", "sat_algebra", 2,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    p2 = create_test_problem(
        "p2", "sat_math", "sat_quadratic", "sat_algebra", 3,
        "sat.algebra.quadratic_solving", ["sat.algebra.quadratic_solving"]
    )
    p3 = create_test_problem(
        "p3", "sat_math", "sat_statistics", "sat_data", 2,
        "sat.data.statistics", ["sat.data.statistics"]
    )
    problem_repo.save_problem(p1)
    problem_repo.save_problem(p2)
    problem_repo.save_problem(p3)
    
    # Create attempt on each
    for p in [p1, p2, p3]:
        attempt_repo.save_attempt(Attempt(
            user_id="user123", problem_id=p.id, topic_id=p.topic_id,
            course_id="sat_math", difficulty=p.difficulty, is_correct=True,
            timestamp=datetime(2024, 1, 1),
        ))
    
    heatmap = get_course_concept_heatmap(
        "user123",
        "sat_math",
        attempt_repo,
        problem_repo,
    )
    
    # Extract concept IDs in order
    concept_ids = [s.concept_id for s in heatmap]
    
    # Check they are sorted
    assert concept_ids == sorted(concept_ids)


# ============================================================================
# Tests for get_course_concept_stats_for_topic
# ============================================================================


def test_topic_concept_stats(sat_math_concepts):
    """Test that topic filtering works correctly."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    # Create problems for same topic but different concepts
    p1 = create_test_problem(
        "p1", "sat_math", "sat_linear", "sat_algebra", 2,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    p2 = create_test_problem(
        "p2", "sat_math", "sat_linear", "sat_algebra", 3,
        "sat.algebra.linear_basics", ["sat.algebra.linear_basics"]
    )
    problem_repo.save_problem(p1)
    problem_repo.save_problem(p2)
    
    # Create attempts on both
    attempt_repo.save_attempt(Attempt(
        user_id="user123", problem_id="p1", topic_id="sat_linear",
        course_id="sat_math", difficulty=2, is_correct=True,
        timestamp=datetime(2024, 1, 1),
    ))
    attempt_repo.save_attempt(Attempt(
        user_id="user123", problem_id="p2", topic_id="sat_linear",
        course_id="sat_math", difficulty=3, is_correct=True,
        timestamp=datetime(2024, 1, 2),
    ))
    
    stats = get_course_concept_stats_for_topic(
        "user123",
        "sat_linear",
        attempt_repo,
        problem_repo,
    )
    
    # Should return stats for concepts in this topic
    assert len(stats) > 0
    linear_stats = next(
        (s for s in stats if s.concept_id == "sat.algebra.linear_basics"),
        None
    )
    assert linear_stats is not None
    assert linear_stats.total_attempts == 2
    assert linear_stats.correct_attempts == 2


def test_topic_concept_stats_mixed_primary_and_secondary(sat_math_concepts):
    """Test topic stats includes both primary and secondary concepts."""
    attempt_repo = InMemoryAttemptRepository()
    problem_repo = InMemoryProblemRepository()
    
    # Create a problem with multiple concept tags
    p = create_test_problem(
        "p1", "sat_math", "sat_linear", "sat_algebra", 2,
        "sat.algebra.linear_basics",
        ["sat.algebra.linear_basics", "alg1.linear_eq.one_step_int"]
    )
    problem_repo.save_problem(p)
    
    attempt_repo.save_attempt(Attempt(
        user_id="user123", problem_id="p1", topic_id="sat_linear",
        course_id="sat_math", difficulty=2, is_correct=True,
        timestamp=datetime(2024, 1, 1),
    ))
    
    stats = get_course_concept_stats_for_topic(
        "user123",
        "sat_linear",
        attempt_repo,
        problem_repo,
    )
    
    concept_ids = {s.concept_id for s in stats}
    assert "sat.algebra.linear_basics" in concept_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
