"""
SQLAlchemy ORM models for database-backed persistence.

Provides table definitions for problems, attempts, assignments, and users
with JSON serialization for complex fields.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, Float, DateTime, Text, Index


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class ProblemRecord(Base):
    """
    ORM model for storing generated math problems.
    
    Complex fields (final_answer, solution, metadata) are stored as JSON
    to allow flexibility in structure while maintaining relational structure
    for indexing and querying.
    """
    __tablename__ = "problems"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(100), index=True)
    unit_id: Mapped[str] = mapped_column(String(100), index=True)
    topic_id: Mapped[str] = mapped_column(String(100), index=True)
    difficulty: Mapped[int] = mapped_column(Integer, index=True)
    calculator_mode: Mapped[str] = mapped_column(String(20), index=True)
    prompt_latex: Mapped[str] = mapped_column(Text)
    answer_type: Mapped[str] = mapped_column(String(50))
    final_answer_json: Mapped[str] = mapped_column(Text)
    solution_json: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_topic_difficulty", "topic_id", "difficulty"),
        Index("idx_course_topic", "course_id", "topic_id"),
    )

    def __repr__(self) -> str:
        return f"<ProblemRecord(id={self.id}, topic_id={self.topic_id}, difficulty={self.difficulty})>"


class AttemptRecord(Base):
    """
    ORM model for storing student attempt records.
    
    Tracks which problems students attempt, whether they got them correct,
    time taken, and related metadata for adaptive difficulty algorithms.
    """
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    problem_id: Mapped[str] = mapped_column(String(50), index=True)
    topic_id: Mapped[str] = mapped_column(String(100), index=True)
    course_id: Mapped[str] = mapped_column(String(100), index=True)
    difficulty: Mapped[int] = mapped_column(Integer, index=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, index=True)
    time_taken_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_topic", "user_id", "topic_id"),
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_topic_timestamp", "topic_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<AttemptRecord(user_id={self.user_id}, problem_id={self.problem_id}, "
            f"is_correct={self.is_correct})>"
        )


class AssignmentRecord(Base):
    """
    ORM model for storing assignments created by teachers.
    
    Each assignment has a unique code, metadata, and links to its problems.
    """
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    teacher_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    topic_id: Mapped[str] = mapped_column(String(100), index=True)
    num_questions: Mapped[int] = mapped_column(Integer)
    min_difficulty: Mapped[int] = mapped_column(Integer)
    max_difficulty: Mapped[int] = mapped_column(Integer)
    calculator_mode: Mapped[str] = mapped_column(String(20), default="none")

    __table_args__ = (
        Index("idx_teacher_status", "teacher_id", "status"),
        Index("idx_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AssignmentRecord(id={self.id}, name={self.name}, topic_id={self.topic_id})>"


class AssignmentProblemRecord(Base):
    """
    ORM model linking problems to assignments.
    
    Maintains the order of problems within an assignment.
    """
    __tablename__ = "assignment_problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[str] = mapped_column(String(50), index=True)
    problem_id: Mapped[str] = mapped_column(String(50), index=True)
    index: Mapped[int] = mapped_column(Integer)  # 1-based position

    __table_args__ = (
        Index("idx_assignment_index", "assignment_id", "index"),
    )

    def __repr__(self) -> str:
        return f"<AssignmentProblemRecord(assignment_id={self.assignment_id}, index={self.index})>"


class UserRecord(Base):
    """
    ORM model for system users with role-based access control.

    Stores user accounts with email, hashed password, role, and account metadata.
    Roles: "student", "teacher", "admin".
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    def __repr__(self) -> str:
        return f"<UserRecord(id={self.id}, email={self.email}, role={self.role})>"


class LegacyUserLinkRecord(Base):
    """
    ORM model mapping old anonymous user IDs to new authenticated accounts.

    Used for backward compatibility when users with existing anonymous history
    create accounts. Allows gradual migration of past attempts and data.
    """

    __tablename__ = "legacy_user_links"

    legacy_user_id: Mapped[str] = mapped_column(String(36), primary_key=True)  # Old UUID
    new_user_id: Mapped[str] = mapped_column(String(36), index=True)  # New user ID
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_new_user_id", "new_user_id"),
    )

    def __repr__(self) -> str:
        return f"<LegacyUserLinkRecord(legacy={self.legacy_user_id[:8]}..., new={self.new_user_id[:8]}...)>"


# ============================================================================
# Mapping functions: ORM <-> Domain models
# ============================================================================

from users_models import User, LegacyUserLink


def user_record_to_model(record: UserRecord) -> User:
    """Convert UserRecord ORM to User domain model."""
    return User(
        id=record.id,
        email=record.email,
        password_hash=record.password_hash,
        role=record.role,  # type: ignore
        created_at=record.created_at,
        display_name=record.display_name,
        is_active=record.is_active,
    )


def user_model_to_record(user: User) -> UserRecord:
    """Convert User domain model to UserRecord ORM."""
    return UserRecord(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        role=user.role,
        created_at=user.created_at,
        display_name=user.display_name,
        is_active=user.is_active,
    )


def legacy_link_record_to_model(record: LegacyUserLinkRecord) -> LegacyUserLink:
    """Convert LegacyUserLinkRecord ORM to LegacyUserLink domain model."""
    return LegacyUserLink(
        legacy_user_id=record.legacy_user_id,
        new_user_id=record.new_user_id,
        linked_at=record.linked_at,
    )


def legacy_link_model_to_record(link: LegacyUserLink) -> LegacyUserLinkRecord:
    """Convert LegacyUserLink domain model to LegacyUserLinkRecord ORM."""
    return LegacyUserLinkRecord(
        legacy_user_id=link.legacy_user_id,
        new_user_id=link.new_user_id,
        linked_at=link.linked_at,
    )

