"""
Concept-level analytics for student performance tracking.

Provides aggregation functions to derive statistics at the concept level
by joining Attempts with Problems and their concept tags.
"""

from dataclasses import dataclass, field
from typing import Optional, Sequence

from models import Problem
from tracking import Attempt
from repositories import ProblemRepository, AttemptRepository
from concepts import get_concept, CONCEPTS


@dataclass
class ConceptStats:
    """
    Aggregated statistics for a concept.
    
    Attributes:
        concept_id: The concept identifier
        concept_name: Human-readable concept name
        total_attempts: Total number of attempts on problems with this concept
        correct_attempts: Number of correct attempts
        success_rate: Fraction of attempts that were correct (0.0-1.0), or None if no attempts
        average_difficulty: Mean difficulty of problems attempted, or None if no attempts
        average_time_seconds: Mean time taken per attempt, or None if no attempts or all None
    """
    concept_id: str
    concept_name: str
    total_attempts: int
    correct_attempts: int
    success_rate: Optional[float] = None
    average_difficulty: Optional[float] = None
    average_time_seconds: Optional[float] = None


def get_user_concept_stats(
    user_id: str,
    concept_id: str,
    attempt_repo: AttemptRepository,
    problem_repo: ProblemRepository,
) -> ConceptStats:
    """
    Get aggregated statistics for a user on a specific concept.
    
    Joins attempts with problems to find all attempts where the concept_id
    appears in the problem's concept_ids or is the primary_concept_id.
    
    Args:
        user_id: The user ID
        concept_id: The concept identifier (e.g., "sat.algebra.linear_basics")
        attempt_repo: Attempt repository implementation
        problem_repo: Problem repository implementation
        
    Returns:
        ConceptStats with aggregated metrics
        
    Raises:
        KeyError: If concept_id does not exist in registry
    """
    # Validate concept exists
    concept = get_concept(concept_id)
    
    # Load all attempts for user
    user_attempts = attempt_repo.list_attempts_by_user(user_id)
    
    # Filter to attempts where problem has this concept
    matching_attempts: list[Attempt] = []
    
    for attempt in user_attempts:
        problem = problem_repo.get_problem(attempt.problem_id)
        if problem is None:
            continue
        
        # Check if concept is tagged on this problem
        if (problem.primary_concept_id == concept_id or 
            concept_id in problem.concept_ids):
            matching_attempts.append(attempt)
    
    # Aggregate statistics
    total_attempts = len(matching_attempts)
    correct_attempts = sum(1 for a in matching_attempts if a.is_correct)
    
    success_rate = None
    if total_attempts > 0:
        success_rate = correct_attempts / total_attempts
    
    average_difficulty = None
    if total_attempts > 0:
        avg_diff = sum(a.difficulty for a in matching_attempts) / total_attempts
        average_difficulty = avg_diff
    
    average_time_seconds = None
    if total_attempts > 0:
        times = [a.time_taken_seconds for a in matching_attempts if a.time_taken_seconds is not None]
        if times:
            average_time_seconds = sum(times) / len(times)
    
    return ConceptStats(
        concept_id=concept_id,
        concept_name=concept.name,
        total_attempts=total_attempts,
        correct_attempts=correct_attempts,
        success_rate=success_rate,
        average_difficulty=average_difficulty,
        average_time_seconds=average_time_seconds,
    )


def get_course_concept_heatmap(
    user_id: str,
    course_id: str,
    attempt_repo: AttemptRepository,
    problem_repo: ProblemRepository,
) -> list[ConceptStats]:
    """
    Get concept-level stats for all concepts in a course.
    
    Aggregates attempts by concept for a user within a specific course.
    Returns a list of ConceptStats sorted by concept_id.
    
    Args:
        user_id: The user ID
        course_id: The course identifier (e.g., "sat_math", "ap_calculus")
        attempt_repo: Attempt repository implementation
        problem_repo: Problem repository implementation
        
    Returns:
        List of ConceptStats, one per concept in the course, sorted by concept_id
    """
    # Load all attempts for user
    user_attempts = attempt_repo.list_attempts_by_user(user_id)
    
    # Collect all unique concept IDs from problems attempted in this course
    concept_ids_in_course: set[str] = set()
    
    for attempt in user_attempts:
        problem = problem_repo.get_problem(attempt.problem_id)
        if problem is None or problem.course_id != course_id:
            continue
        
        # Add primary concept
        if problem.primary_concept_id:
            concept_ids_in_course.add(problem.primary_concept_id)
        
        # Add all other concepts
        for cid in problem.concept_ids:
            if cid.startswith(f"{course_id}."):
                concept_ids_in_course.add(cid)
    
    # If no attempts found, still include all concepts for this course
    if not concept_ids_in_course:
        # Fetch all registered concepts for this course
        for cid, concept in CONCEPTS.items():
            if concept.course_id == course_id:
                concept_ids_in_course.add(cid)
    
    # Compute stats for each concept
    stats_list: list[ConceptStats] = []
    
    for concept_id in concept_ids_in_course:
        try:
            stats = get_user_concept_stats(
                user_id, concept_id, attempt_repo, problem_repo
            )
            stats_list.append(stats)
        except KeyError:
            # Concept not in registry; skip
            continue
    
    # Sort by concept_id for consistency
    stats_list.sort(key=lambda s: s.concept_id)
    
    return stats_list


def get_course_concept_stats_for_topic(
    user_id: str,
    topic_id: str,
    attempt_repo: AttemptRepository,
    problem_repo: ProblemRepository,
) -> list[ConceptStats]:
    """
    Get concept-level stats for all concepts within a specific topic.
    
    Similar to get_course_concept_heatmap, but filters to a single topic.
    
    Args:
        user_id: The user ID
        topic_id: The topic identifier (e.g., "sat_linear", "ap_deriv_chain")
        attempt_repo: Attempt repository implementation
        problem_repo: Problem repository implementation
        
    Returns:
        List of ConceptStats for concepts in this topic, sorted by concept_id
    """
    # Load all attempts for user in this topic
    user_attempts = attempt_repo.list_attempts_by_user_and_topic(user_id, topic_id)
    
    # Collect all unique concept IDs from problems in this topic
    concept_ids_in_topic: set[str] = set()
    
    for attempt in user_attempts:
        problem = problem_repo.get_problem(attempt.problem_id)
        if problem is None or problem.topic_id != topic_id:
            continue
        
        # Add primary concept
        if problem.primary_concept_id:
            concept_ids_in_topic.add(problem.primary_concept_id)
        
        # Add all other concepts
        for cid in problem.concept_ids:
            concept_ids_in_topic.add(cid)
    
    # Compute stats for each concept
    stats_list: list[ConceptStats] = []
    
    for concept_id in concept_ids_in_topic:
        try:
            stats = get_user_concept_stats(
                user_id, concept_id, attempt_repo, problem_repo
            )
            stats_list.append(stats)
        except KeyError:
            # Concept not in registry; skip
            continue
    
    # Sort by concept_id
    stats_list.sort(key=lambda s: s.concept_id)
    
    return stats_list
