"""
Assignment and practice set data models.

Assignments are containers for pre-generated problems that teachers can create
and distribute to students via codes. Each assignment has:
- A set of questions (pre-generated on creation)
- Metadata (name, description, topic, difficulty range)
- Status (draft, active, closed)
- Analytics tracking per student
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4

AssignmentStatus = Literal["draft", "active", "closed"]
CalculatorMode = Literal["none", "scientific", "graphing"]


@dataclass
class Assignment:
    """An assignment that students can access via a code."""

    id: str  # short code like "ALG1-XYZ123"
    name: str
    description: str | None = None
    teacher_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: AssignmentStatus = "active"
    topic_id: str = "algebra"
    num_questions: int = 10
    min_difficulty: int = 1
    max_difficulty: int = 4
    calculator_mode: CalculatorMode = "none"


@dataclass
class AssignmentProblemLink:
    """Links a problem to an assignment at a specific position."""

    assignment_id: str
    problem_id: str
    index: int  # 1-based position in the assignment


@dataclass
class AssignmentAttempt:
    """Tracks a student's attempt at an assignment problem."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    assignment_id: str = ""
    problem_index: int = 0  # position in the assignment (1-based)
    problem_id: str = ""
    submitted_answer: str = ""
    is_correct: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    time_spent_seconds: int = 0


def generate_assignment_code() -> str:
    """Generate a short assignment code like 'ALG1-XYZ123'."""
    import random
    import string

    topic_codes = {
        "algebra": "ALG",
        "geometry": "GEO",
        "calculus": "CAL",
        "statistics": "STA",
    }
    topic_code = topic_codes.get("algebra", "MAT")
    difficulty = random.randint(1, 4)
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{topic_code}{difficulty}-{random_part}"
