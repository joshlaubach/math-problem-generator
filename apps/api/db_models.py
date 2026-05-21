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
        Index("idx_topic_course_id", "course_id", "id"),
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

    # Spec-aligned fields (populated by agents in Phase 3+; NULL for legacy pre-generated problems)
    statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    worked_steps_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: {step, explanation}[]
    hint_ladder_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON: string[] (4 hints)
    distractors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON: {answer, mistake}[]
    conceptual_diff: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # 1-5
    computational_diff: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 1-5
    calc_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flag_resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (
        Index("idx_topic_difficulty", "topic_id", "difficulty"),
        Index("idx_course_topic", "course_id", "topic_id"),
        Index("idx_free_verified", "is_free", "verified"),
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
    Includes Clerk auth fields added in Phase 4 migration.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID (legacy) or Clerk user ID
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), index=True, default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Clerk auth fields (populated in Phase 4)
    clerk_user_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Platform tier fields (Prisma User model alignment)
    tier: Mapped[str] = mapped_column(String(30), default="free", index=True)  # 'free'|'basic'|'student'|'honors'|'classroom-student'
    is_teacher: Mapped[bool] = mapped_column(Boolean, default=False)
    age_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Daily usage tracking
    daily_problems_generated: Mapped[int] = mapped_column(Integer, default=0)
    last_reset_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # ISO date "YYYY-MM-DD"

    # Per-user quota override (NULL = use tier default)
    daily_limit_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Tutor / learning goal fields
    learning_goal: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'pass'|'b'|'a'|'mastery'
    parent_monitor: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<UserRecord(id={self.id}, email={self.email}, role={self.role}, tier={self.tier})>"


class AdminActionRecord(Base):
    """Audit log for admin panel actions (role changes, tier overrides, deactivations, etc.)."""

    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[str] = mapped_column(String(36), index=True)
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[str] = mapped_column(String(255), index=True)
    changes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AdminActionRecord(admin={self.admin_id[:8]}..., action={self.action_type}, target={self.target_id[:8]}...)>"


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
        clerk_user_id=record.clerk_user_id,
        age_confirmed=record.age_confirmed,
        tier=record.tier,
        is_teacher=record.is_teacher,
        learning_goal=record.learning_goal,
        parent_monitor=record.parent_monitor,
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
        clerk_user_id=user.clerk_user_id,
        age_confirmed=user.age_confirmed,
        tier=user.tier,
        is_teacher=user.is_teacher,
        learning_goal=getattr(user, "learning_goal", None),
        parent_monitor=getattr(user, "parent_monitor", False),
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


# ============================================================================
# New platform models (Phase 1+) — mirror the Prisma schema in schema.prisma
# ============================================================================

class VideoLinkRecord(Base):
    """Curated video links (3Blue1Brown, Professor Leonard) for topics."""

    __tablename__ = "video_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(2000))
    channel: Mapped[str] = mapped_column(String(50))  # '3blue1brown'|'professor-leonard'|'other'
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    def __repr__(self) -> str:
        return f"<VideoLinkRecord(id={self.id}, topic_id={self.topic_id}, channel={self.channel})>"


class ProgressRecord(Base):
    """
    Per-user, per-topic mastery tracking with spaced repetition scheduling.

    nextReviewAt = lastReviewedAt + timedelta(days=masteryScore * 7)
    """

    __tablename__ = "progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    topic_id: Mapped[str] = mapped_column(String(100), index=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    current_conceptual_diff: Mapped[int] = mapped_column(Integer, default=1)
    current_computational_diff: Mapped[int] = mapped_column(Integer, default=1)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_progress_user_topic", "user_id", "topic_id", unique=True),
        Index("idx_progress_review", "user_id", "next_review_at"),
    )

    def __repr__(self) -> str:
        return f"<ProgressRecord(user_id={self.user_id}, topic_id={self.topic_id}, mastery={self.mastery_score:.2f})>"


class FlaggedProblemRecord(Base):
    """Student-flagged problems awaiting teacher/admin review."""

    __tablename__ = "flagged_problems"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    problem_id: Mapped[str] = mapped_column(String(50), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    reason: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FlaggedProblemRecord(problem_id={self.problem_id}, resolved={self.resolved})>"


class ClassroomRecord(Base):
    """Teacher-owned classroom with 8-char join code."""

    __tablename__ = "classrooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    teacher_id: Mapped[str] = mapped_column(String(255), index=True)
    join_code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    course_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ClassroomRecord(id={self.id}, name={self.name}, join_code={self.join_code})>"


class ClassroomMembershipRecord(Base):
    """Student membership in a classroom."""

    __tablename__ = "classroom_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    classroom_id: Mapped[str] = mapped_column(String(36), index=True)
    student_id: Mapped[str] = mapped_column(String(255), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_membership_unique", "classroom_id", "student_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ClassroomMembershipRecord(classroom_id={self.classroom_id}, student_id={self.student_id})>"


class NewAssignmentRecord(Base):
    """
    Platform assignment record aligned with Prisma Assignment model.

    Replaces legacy AssignmentRecord in Phase 9+. Kept separate to avoid
    breaking existing AssignmentRecord tests during Phase 1.
    """

    __tablename__ = "platform_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    classroom_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(500))
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic_ids_json: Mapped[str] = mapped_column(Text, default="[]")   # JSON string[]
    problem_ids_json: Mapped[str] = mapped_column(Text, default="[]") # JSON string[]
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    calc_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    conceptual_diff: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    computational_diff: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    allow_hints: Mapped[bool] = mapped_column(Boolean, default=True)
    max_hints: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_assignment_classroom", "classroom_id", "due_at"),
    )

    def __repr__(self) -> str:
        return f"<NewAssignmentRecord(id={self.id}, title={self.title}, classroom_id={self.classroom_id})>"


class AssignmentSubmissionRecord(Base):
    """Student submission for a platform assignment."""

    __tablename__ = "assignment_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(String(36), index=True)
    student_id: Mapped[str] = mapped_column(String(255), index=True)
    attempt_ids_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON string[]
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_submission_unique", "assignment_id", "student_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<AssignmentSubmissionRecord(assignment_id={self.assignment_id}, student_id={self.student_id})>"


# ============================================================================
# Tutor Session Credits & Sessions (Phase: AI Tutor)
# ============================================================================


class SessionCreditRecord(Base):
    """One purchasable tutor session credit. Expires after 6 months."""

    __tablename__ = "session_credits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    purchase_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SessionCreditRecord(id={self.id}, user_id={self.user_id}, used={self.used_at is not None})>"


class TutorSessionRecord(Base):
    """Persisted record of a completed or in-progress tutor session."""

    __tablename__ = "tutor_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    credit_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    topic_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mode: Mapped[str] = mapped_column(String(20), default="practice")  # concept|homework|practice
    summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # {bullets: str[]}
    transcript_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # only if parent_monitor
    parent_monitor: Mapped[bool] = mapped_column(Boolean, default=False)
    problems_attempted: Mapped[int] = mapped_column(Integer, default=0)
    problems_solved: Mapped[int] = mapped_column(Integer, default=0)
    credit_restored: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<TutorSessionRecord(id={self.id}, user_id={self.user_id}, topic={self.topic_id})>"


class ScrapbookEntryRecord(Base):
    """One scratchpad entry (reasoning or expression) from a tutor session."""

    __tablename__ = "scrapbook_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    box: Mapped[str] = mapped_column(String(20))  # 'reasoning'|'expression'
    content: Mapped[str] = mapped_column(Text)
    sympy_result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # valid|invalid|unknown
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ScrapbookEntryRecord(session_id={self.session_id}, box={self.box})>"


class ValidationDisputeRecord(Base):
    """Disputed SymPy validation — queued for human review when Claude and SymPy disagree."""

    __tablename__ = "validation_disputes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    expression: Mapped[str] = mapped_column(Text)
    expected: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sympy_loose: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    claude_verdict: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    accepted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ValidationDisputeRecord(id={self.id}, accepted={self.accepted})>"


class ParentLinkRecord(Base):
    """Links a parent account to a student account for session monitoring."""

    __tablename__ = "parent_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parent_id: Mapped[str] = mapped_column(String(255), index=True)
    student_id: Mapped[str] = mapped_column(String(255), index=True)
    link_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_parent_student_unique", "parent_id", "student_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ParentLinkRecord(parent_id={self.parent_id}, student_id={self.student_id})>"




class StudentConceptError(Base):
    """Tracks how many times a student has made an error tagged with a given concept label."""

    __tablename__ = "student_concept_errors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    concept_id: Mapped[str] = mapped_column(String(255), index=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_student_concept_unique", "user_id", "concept_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<StudentConceptError(user_id={self.user_id}, concept_id={self.concept_id}, count={self.count})>"
