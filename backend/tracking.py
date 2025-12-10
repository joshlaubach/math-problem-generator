"""
Student and teacher user tracking, and attempt recording.

This module manages users, their roles, and their attempt history on problems.
Attempts are stored in JSONL format for easy streaming and analysis.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Literal, Optional
import json
from pathlib import Path

UserRole = Literal["student", "teacher"]


@dataclass
class User:
    """Represents a user (student or teacher)."""

    id: str
    role: UserRole
    name: Optional[str] = None


@dataclass
class Attempt:
    """Represents a student attempt at a single problem."""

    user_id: str
    problem_id: str
    topic_id: str
    course_id: str
    difficulty: int
    is_correct: bool
    timestamp: datetime
    time_taken_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Attempt":
        """Reconstruct from dict."""
        data_copy = dict(data)
        data_copy["timestamp"] = datetime.fromisoformat(data_copy["timestamp"])
        return cls(**data_copy)


def save_attempt(attempt: Attempt, path: str) -> None:
    """
    Append an attempt to a JSONL file.

    Args:
        attempt: The Attempt to save.
        path: Path to JSONL file (created if doesn't exist).
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(attempt.to_dict()) + "\n")


def load_attempts(path: str) -> list[Attempt]:
    """
    Load all attempts from a JSONL file.

    Args:
        path: Path to JSONL file.

    Returns:
        List of Attempt objects.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Attempts file not found: {path}")

    attempts: list[Attempt] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                attempts.append(Attempt.from_dict(data))

    return attempts


def save_attempts_batch(attempts: list[Attempt], path: str) -> None:
    """
    Save multiple attempts to a JSONL file (overwrites existing file).

    Args:
        attempts: List of attempts to save.
        path: Path to JSONL file.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        for attempt in attempts:
            f.write(json.dumps(attempt.to_dict()) + "\n")


def get_user_topic_stats(
    user_id: str, topic_id: str, attempts: list[Attempt]
) -> dict:
    """
    Compute statistics for a user on a specific topic.

    Args:
        user_id: The user ID.
        topic_id: The topic ID.
        attempts: List of all attempts (will be filtered).

    Returns:
        A dict with keys:
            * total_attempts: int
            * correct_attempts: int
            * success_rate: float (0.0 to 1.0)
            * average_difficulty: float
            * average_time_seconds: float | None
    """
    topic_attempts = [
        a for a in attempts if a.user_id == user_id and a.topic_id == topic_id
    ]

    if not topic_attempts:
        return {
            "total_attempts": 0,
            "correct_attempts": 0,
            "success_rate": 0.0,
            "average_difficulty": 0.0,
            "average_time_seconds": None,
        }

    correct = sum(1 for a in topic_attempts if a.is_correct)
    success_rate = correct / len(topic_attempts)
    avg_difficulty = sum(a.difficulty for a in topic_attempts) / len(
        topic_attempts
    )

    times = [a.time_taken_seconds for a in topic_attempts if a.time_taken_seconds]
    avg_time = sum(times) / len(times) if times else None

    return {
        "total_attempts": len(topic_attempts),
        "correct_attempts": correct,
        "success_rate": success_rate,
        "average_difficulty": avg_difficulty,
        "average_time_seconds": avg_time,
    }


def clear_attempts_file(path: str) -> None:
    """Delete the attempts file."""
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()
