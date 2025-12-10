"""
Adaptive difficulty recommendation logic.

Provides pure functions to recommend the next difficulty level for a user
based on their attempt history on a topic.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tracking import Attempt


def recommend_difficulty_for_user(
    user_id: str,
    topic_id: str,
    attempts: list["Attempt"],
    min_difficulty: int = 1,
    max_difficulty: int = 6,
    default_difficulty: int = 2,
) -> int:
    """
    Recommend the next difficulty for a user on a topic.

    Uses a simple heuristic:
    - If no history, return default difficulty.
    - If recent attempts are mostly correct (>80%), increase difficulty.
    - If recent attempts are mostly incorrect (<60%), decrease difficulty.
    - Otherwise, maintain current difficulty.

    Args:
        user_id: The user ID.
        topic_id: The topic ID.
        attempts: List of all attempts (will be filtered).
        min_difficulty: Minimum allowed difficulty (default 1).
        max_difficulty: Maximum allowed difficulty (default 6).
        default_difficulty: Default for new users (default 2).

    Returns:
        Recommended difficulty level (int).
    """
    # Filter to relevant attempts
    topic_attempts = [
        a for a in attempts if a.user_id == user_id and a.topic_id == topic_id
    ]

    # No history: return default
    if not topic_attempts:
        return max(min_difficulty, min(default_difficulty, max_difficulty))

    # Consider only the last N attempts
    recent_attempts = topic_attempts[-5:]

    # Calculate success rate
    correct_count = sum(1 for a in recent_attempts if a.is_correct)
    success_rate = correct_count / len(recent_attempts)

    # Get the most recent difficulty
    current_difficulty = recent_attempts[-1].difficulty

    # Heuristic decision
    if success_rate > 0.8:
        # Very successful: increase difficulty
        recommended = current_difficulty + 1
    elif success_rate < 0.6:
        # Struggling: decrease difficulty
        recommended = current_difficulty - 1
    else:
        # On track: maintain difficulty
        recommended = current_difficulty

    # Clamp to valid range
    return max(min_difficulty, min(recommended, max_difficulty))


def get_difficulty_range_for_user(
    user_id: str,
    topic_id: str,
    attempts: list["Attempt"],
    min_difficulty: int = 1,
    max_difficulty: int = 6,
    default_difficulty: int = 2,
) -> tuple[int, int]:
    """
    Get a recommended range of difficulties for a user on a topic.

    Useful for presenting options to students.

    Args:
        user_id: The user ID.
        topic_id: The topic ID.
        attempts: List of all attempts.
        min_difficulty: Minimum allowed difficulty.
        max_difficulty: Maximum allowed difficulty.
        default_difficulty: Default for new users.

    Returns:
        A tuple (min_rec, max_rec) of recommended difficulty range.
    """
    recommended = recommend_difficulty_for_user(
        user_id, topic_id, attempts, min_difficulty, max_difficulty, default_difficulty
    )

    # Range is ±1 from recommended, clamped
    min_rec = max(min_difficulty, recommended - 1)
    max_rec = min(max_difficulty, recommended + 1)

    return (min_rec, max_rec)
