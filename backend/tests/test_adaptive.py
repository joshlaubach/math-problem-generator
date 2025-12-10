"""
Tests for the adaptive difficulty recommendation module.
"""

from datetime import datetime

import pytest

from adaptive import recommend_difficulty_for_user, get_difficulty_range_for_user
from tracking import Attempt


class TestRecommendDifficulty:
    """Tests for recommend_difficulty_for_user."""

    def test_no_history_returns_default(self):
        """Test that new users get the default difficulty."""
        recommended = recommend_difficulty_for_user(
            "new_user", "alg1_linear_solve_one_var", []
        )
        assert recommended == 2  # default

    def test_custom_default(self):
        """Test using a custom default difficulty."""
        recommended = recommend_difficulty_for_user(
            "new_user", "alg1_linear_solve_one_var", [], default_difficulty=3
        )
        assert recommended == 3

    def test_default_clamped_to_min(self):
        """Test that default is clamped to min_difficulty."""
        recommended = recommend_difficulty_for_user(
            "new_user", "alg1_linear_solve_one_var", [], min_difficulty=5
        )
        assert recommended == 5

    def test_all_correct_increases_difficulty(self):
        """Test that 100% success rate increases difficulty."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        recommended = recommend_difficulty_for_user(
            "student_1", "alg1_linear_solve_one_var", attempts
        )

        assert recommended == 3  # 2 + 1

    def test_high_success_rate_increases_difficulty(self):
        """Test that >80% success rate increases difficulty."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=i < 5,  # 5 correct, 0 incorrect = 100% (>80%)
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        recommended = recommend_difficulty_for_user(
            "student_1", "alg1_linear_solve_one_var", attempts
        )

        assert recommended == 3

    def test_low_success_rate_decreases_difficulty(self):
        """Test that <60% success rate decreases difficulty."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=3,
                is_correct=i == 0,  # 1 correct, 4 incorrect = 20%
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        recommended = recommend_difficulty_for_user(
            "student_1", "alg1_linear_solve_one_var", attempts
        )

        assert recommended == 2  # 3 - 1

    def test_moderate_success_maintains_difficulty(self):
        """Test that 60-80% success rate maintains difficulty."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=i < 3,  # 3 correct, 2 incorrect = 60%
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        recommended = recommend_difficulty_for_user(
            "student_1", "alg1_linear_solve_one_var", attempts
        )

        assert recommended == 2  # unchanged

    def test_considers_only_recent_5_attempts(self):
        """Test that only the last 5 attempts are considered."""
        # Old attempts: all correct at difficulty 2
        old_attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
            )
            for i in range(10)
        ]

        # New attempts: all incorrect at difficulty 4
        new_attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{10 + i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=4,
                is_correct=False,
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        all_attempts = old_attempts + new_attempts

        recommended = recommend_difficulty_for_user(
            "student_1", "alg1_linear_solve_one_var", all_attempts
        )

        # Should recommend decreasing from 4 due to the 5 recent failures
        assert recommended == 3

    def test_filtered_by_topic(self):
        """Test that recommendations are filtered by topic."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]
        # Add some failed attempts on a different topic
        attempts.extend(
            [
                Attempt(
                    user_id="student_1",
                    problem_id=f"prob_other_{i}",
                    topic_id="alg1_quadratic_solve",
                    course_id="alg1",
                    difficulty=3,
                    is_correct=False,
                    timestamp=datetime.now(),
                )
                for i in range(5)
            ]
        )

        # Recommendation for linear topic should be based on 5 successes
        recommended = recommend_difficulty_for_user(
            "student_1", "alg1_linear_solve_one_var", attempts
        )
        assert recommended == 3  # increased due to 100% success on linear

    def test_clamped_to_max_difficulty(self):
        """Test that recommendation is clamped to max_difficulty."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=5,
                is_correct=True,
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        recommended = recommend_difficulty_for_user(
            "student_1", "alg1_linear_solve_one_var", attempts, max_difficulty=5
        )

        assert recommended == 5  # clamped to max


class TestGetDifficultyRange:
    """Tests for get_difficulty_range_for_user."""

    def test_range_around_recommended(self):
        """Test that range is ±1 around recommended."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=i < 3,  # 60% success, maintain difficulty
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        min_rec, max_rec = get_difficulty_range_for_user(
            "student_1", "alg1_linear_solve_one_var", attempts
        )

        assert min_rec == 1
        assert max_rec == 3

    def test_range_respects_min_max(self):
        """Test that range respects global min/max bounds."""
        # Very successful at difficulty 1
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=1,
                is_correct=True,
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        min_rec, max_rec = get_difficulty_range_for_user(
            "student_1", "alg1_linear_solve_one_var", attempts, min_difficulty=1
        )

        # Recommended would be 2, so range is [1, 3]
        assert min_rec >= 1
        assert max_rec <= 3

    def test_range_for_new_user(self):
        """Test range for new user with no history."""
        min_rec, max_rec = get_difficulty_range_for_user(
            "new_user", "alg1_linear_solve_one_var", []
        )

        # Default is 2, so range is [1, 3]
        assert min_rec == 1
        assert max_rec == 3
