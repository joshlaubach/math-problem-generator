"""
Tests for the tracking module (user and attempt tracking).
"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from tracking import (
    User,
    Attempt,
    save_attempt,
    load_attempts,
    save_attempts_batch,
    get_user_topic_stats,
    clear_attempts_file,
)


class TestUser:
    """Tests for the User model."""

    def test_user_creation_student(self):
        """Test creating a student user."""
        user = User(id="student_1", role="student", name="Alice")
        assert user.id == "student_1"
        assert user.role == "student"
        assert user.name == "Alice"

    def test_user_creation_teacher(self):
        """Test creating a teacher user."""
        user = User(id="teacher_1", role="teacher", name="Mr. Smith")
        assert user.role == "teacher"

    def test_user_without_name(self):
        """Test creating a user without a name."""
        user = User(id="student_2", role="student")
        assert user.name is None


class TestAttempt:
    """Tests for the Attempt model."""

    def test_attempt_creation(self):
        """Test creating an attempt."""
        now = datetime.now()
        attempt = Attempt(
            user_id="student_1",
            problem_id="prob_001",
            topic_id="alg1_linear_solve_one_var",
            course_id="alg1",
            difficulty=2,
            is_correct=True,
            timestamp=now,
            time_taken_seconds=45.5,
        )
        assert attempt.user_id == "student_1"
        assert attempt.is_correct is True
        assert attempt.time_taken_seconds == 45.5

    def test_attempt_without_time(self):
        """Test attempt without time_taken_seconds."""
        now = datetime.now()
        attempt = Attempt(
            user_id="student_1",
            problem_id="prob_001",
            topic_id="alg1_linear_solve_one_var",
            course_id="alg1",
            difficulty=2,
            is_correct=False,
            timestamp=now,
        )
        assert attempt.time_taken_seconds is None

    def test_attempt_to_dict(self):
        """Test serialization to dict."""
        now = datetime.now()
        attempt = Attempt(
            user_id="student_1",
            problem_id="prob_001",
            topic_id="alg1_linear_solve_one_var",
            course_id="alg1",
            difficulty=2,
            is_correct=True,
            timestamp=now,
            time_taken_seconds=45.5,
        )
        data = attempt.to_dict()
        assert data["user_id"] == "student_1"
        assert data["is_correct"] is True
        assert isinstance(data["timestamp"], str)  # ISO format

    def test_attempt_from_dict(self):
        """Test deserialization from dict."""
        now = datetime.now()
        original = Attempt(
            user_id="student_1",
            problem_id="prob_001",
            topic_id="alg1_linear_solve_one_var",
            course_id="alg1",
            difficulty=2,
            is_correct=True,
            timestamp=now,
            time_taken_seconds=45.5,
        )
        data = original.to_dict()
        restored = Attempt.from_dict(data)

        assert restored.user_id == original.user_id
        assert restored.problem_id == original.problem_id
        assert restored.is_correct == original.is_correct
        assert restored.timestamp == original.timestamp


class TestAttemptStorage:
    """Tests for saving and loading attempts."""

    def test_save_and_load_single_attempt(self):
        """Test saving and loading a single attempt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = str(Path(tmpdir) / "attempts.jsonl")

            attempt = Attempt(
                user_id="student_1",
                problem_id="prob_001",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
            )

            save_attempt(attempt, file_path)
            loaded = load_attempts(file_path)

            assert len(loaded) == 1
            assert loaded[0].user_id == "student_1"
            assert loaded[0].problem_id == "prob_001"

    def test_load_nonexistent_file_raises_error(self):
        """Test loading from a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_attempts("/nonexistent/path/attempts.jsonl")

    def test_save_multiple_attempts_sequentially(self):
        """Test appending multiple attempts to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = str(Path(tmpdir) / "attempts.jsonl")

            for i in range(3):
                attempt = Attempt(
                    user_id=f"student_{i}",
                    problem_id=f"prob_{i:03d}",
                    topic_id="alg1_linear_solve_one_var",
                    course_id="alg1",
                    difficulty=1 + (i % 3),
                    is_correct=i % 2 == 0,
                    timestamp=datetime.now(),
                )
                save_attempt(attempt, file_path)

            loaded = load_attempts(file_path)
            assert len(loaded) == 3
            assert loaded[0].user_id == "student_0"
            assert loaded[2].user_id == "student_2"

    def test_save_batch(self):
        """Test batch saving of attempts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = str(Path(tmpdir) / "attempts.jsonl")

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

            save_attempts_batch(attempts, file_path)
            loaded = load_attempts(file_path)

            assert len(loaded) == 5

    def test_clear_attempts_file(self):
        """Test clearing the attempts file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = str(Path(tmpdir) / "attempts.jsonl")

            attempt = Attempt(
                user_id="student_1",
                problem_id="prob_001",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
            )
            save_attempt(attempt, file_path)

            assert Path(file_path).exists()
            clear_attempts_file(file_path)
            assert not Path(file_path).exists()


class TestUserTopicStats:
    """Tests for statistics computation."""

    def test_stats_for_user_with_no_attempts(self):
        """Test stats for a user with no attempts."""
        stats = get_user_topic_stats("unknown_user", "alg1_linear_solve_one_var", [])

        assert stats["total_attempts"] == 0
        assert stats["correct_attempts"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["average_difficulty"] == 0.0
        assert stats["average_time_seconds"] is None

    def test_stats_for_user_all_correct(self):
        """Test stats for a user who got all problems correct."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id=f"prob_{i}",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2 + i,
                is_correct=True,
                timestamp=datetime.now(),
                time_taken_seconds=30.0 + i * 5,
            )
            for i in range(3)
        ]

        stats = get_user_topic_stats("student_1", "alg1_linear_solve_one_var", attempts)

        assert stats["total_attempts"] == 3
        assert stats["correct_attempts"] == 3
        assert stats["success_rate"] == 1.0
        assert stats["average_difficulty"] == 3.0  # (2 + 3 + 4) / 3
        assert stats["average_time_seconds"] == 35.0  # (30 + 35 + 40) / 3

    def test_stats_for_user_mixed_results(self):
        """Test stats for a user with mixed correctness."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id="prob_0",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
            ),
            Attempt(
                user_id="student_1",
                problem_id="prob_1",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=False,
                timestamp=datetime.now(),
            ),
            Attempt(
                user_id="student_1",
                problem_id="prob_2",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=3,
                is_correct=True,
                timestamp=datetime.now(),
            ),
        ]

        stats = get_user_topic_stats("student_1", "alg1_linear_solve_one_var", attempts)

        assert stats["total_attempts"] == 3
        assert stats["correct_attempts"] == 2
        assert abs(stats["success_rate"] - 0.667) < 0.01
        assert abs(stats["average_difficulty"] - 2.333) < 0.01

    def test_stats_filtered_by_topic(self):
        """Test that stats are filtered by topic."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id="prob_0",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
            ),
            Attempt(
                user_id="student_1",
                problem_id="prob_1",
                topic_id="alg1_quadratic_solve",
                course_id="alg1",
                difficulty=3,
                is_correct=False,
                timestamp=datetime.now(),
            ),
        ]

        stats = get_user_topic_stats("student_1", "alg1_linear_solve_one_var", attempts)

        assert stats["total_attempts"] == 1
        assert stats["correct_attempts"] == 1

    def test_stats_without_time_data(self):
        """Test stats when some attempts have no time recorded."""
        attempts = [
            Attempt(
                user_id="student_1",
                problem_id="prob_0",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
                time_taken_seconds=None,
            ),
            Attempt(
                user_id="student_1",
                problem_id="prob_1",
                topic_id="alg1_linear_solve_one_var",
                course_id="alg1",
                difficulty=2,
                is_correct=True,
                timestamp=datetime.now(),
                time_taken_seconds=30.0,
            ),
        ]

        stats = get_user_topic_stats("student_1", "alg1_linear_solve_one_var", attempts)

        assert stats["total_attempts"] == 2
        assert stats["average_time_seconds"] == 30.0  # Only the one with time
