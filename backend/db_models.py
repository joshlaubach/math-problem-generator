"""
SQLAlchemy ORM models for database-backed persistence.

Provides table definitions for problems, attempts, assignments, and users
with JSON serialization for complex fields.
"""

from datetime import datetime
from typing import Optional, Literal
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, Float, DateTime, Text, Index, ForeignKey


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ============================================================================
# Curriculum Schema: Education Levels, Courses, Units, Topics, Concepts
# ============================================================================

EducationLevel = Literal["high_school", "college_university", "test_prep"]


class EducationLevelRecord(Base):
    """
    ORM model for education levels (High School, College/University, Test Prep).
    
    Top-level categorization of the curriculum hierarchy.
    """
    __tablename__ = "education_levels"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EducationLevelRecord(id={self.id}, name={self.name})>"


class CourseRecord(Base):
    """
    ORM model for courses within an education level.
    
    Examples: Algebra 1, Calculus I, SAT Math
    """
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    education_level_id: Mapped[str] = mapped_column(String(50), ForeignKey("education_levels.id"), index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "ALG1", "CALC1"
    credits: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For college courses
    prerequisites_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of course IDs
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_education_level_order", "education_level_id", "display_order"),
        Index("idx_education_level_active", "education_level_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<CourseRecord(id={self.id}, name={self.name}, level={self.education_level_id})>"


class UnitRecord(Base):
    """
    ORM model for units within a course.
    
    Examples: "Linear Equations and Inequalities", "Limits and Continuity"
    """
    __tablename__ = "units"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    course_id: Mapped[str] = mapped_column(String(100), ForeignKey("courses.id"), index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_course_order", "course_id", "display_order"),
        Index("idx_course_active", "course_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<UnitRecord(id={self.id}, name={self.name}, course={self.course_id})>"


class TopicRecord(Base):
    """
    ORM model for topics within a unit.
    
    Topics are the specific skills or subject areas that students practice.
    Examples: "Solving one-variable linear equations", "Derivative rules"
    """
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_id: Mapped[str] = mapped_column(String(100), ForeignKey("units.id"), index=True)
    course_id: Mapped[str] = mapped_column(String(100), ForeignKey("courses.id"), index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    prerequisites_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of topic IDs
    difficulty_min: Mapped[int] = mapped_column(Integer, default=1)  # 1-10 scale
    difficulty_max: Mapped[int] = mapped_column(Integer, default=10)  # 1-10 scale
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_unit_order", "unit_id", "display_order"),
        Index("idx_unit_active", "unit_id", "is_active"),
        Index("idx_course_topic", "course_id", "id"),
    )

    def __repr__(self) -> str:
        return f"<TopicRecord(id={self.id}, name={self.name}, unit={self.unit_id})>"


class ConceptRecord(Base):
    """
    ORM model for granular concepts within topics.
    
    Concepts are atomic learning objectives that form a prerequisite DAG.
    Examples: "One-step equations with integers", "Power rule for derivatives"
    """
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    topic_id: Mapped[str] = mapped_column(String(100), ForeignKey("topics.id"), index=True)
    unit_id: Mapped[str] = mapped_column(String(100), ForeignKey("units.id"), index=True)
    course_id: Mapped[str] = mapped_column(String(100), ForeignKey("courses.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50), default="skill")  # skill, definition, strategy, representation
    difficulty_min: Mapped[int] = mapped_column(Integer, default=1)  # 1-6 scale for concepts
    difficulty_max: Mapped[int] = mapped_column(Integer, default=6)  # 1-6 scale for concepts
    prerequisites_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of concept IDs
    examples_latex_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of LaTeX examples
    tags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of searchable tags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    version: Mapped[str] = mapped_column(String(20), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_topic_concept", "topic_id", "id"),
        Index("idx_unit_concept", "unit_id", "id"),
        Index("idx_course_concept", "course_id", "id"),
        Index("idx_concept_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ConceptRecord(id={self.id}, name={self.name}, topic={self.topic_id})>"


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

