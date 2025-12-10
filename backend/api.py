"""
HTTP API for the math problem generator.

Exposes endpoints for:
- Listing available topics
- Generating problems
- Tracking student attempts
- Recommending adaptive difficulty
- Generating hints with LLM
"""

from __future__ import annotations
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Depends, Header, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import DEFAULT_ATTEMPT_JSONL_PATH, USE_DATABASE, TEACHER_API_KEY, ADMIN_API_KEY
from generators import get_generator_for_topic, list_registered_topics
from repositories import AttemptRepository, ProblemRepository
from repo_factory import get_attempt_repository as factory_get_attempt_repository, get_problem_repository as factory_get_problem_repository
from repositories_assignments import DBAssignmentRepository, InMemoryAssignmentRepository
from assignments_models import Assignment, AssignmentProblemLink, generate_assignment_code
from db_session import get_session
from storage import problem_to_dict, dict_to_problem
from tracking import (
    User,
    Attempt,
    save_attempt,
    load_attempts,
    clear_attempts_file,
    get_user_topic_stats,
)
from adaptive import recommend_difficulty_for_user, get_difficulty_range_for_user
from word_problem import wrap_problem_as_word_problem
from taxonomy import get_algebra1_course
from llm_factory import get_cached_sync_llm_client
from concept_analytics import (
    get_user_concept_stats,
    get_course_concept_heatmap,
    ConceptStats,
)
from concepts import (
    get_concept as get_concept_obj,
    get_prerequisites_recursive,
    get_dependents_recursive,
    CONCEPTS,
)

# Phase 10: Authentication and authorization
from auth_router import router as auth_router
from auth_dependencies import (
    get_current_user,
    optional_current_user,
    require_student,
    require_teacher,
    require_admin,
)
from users_models import User as AuthUser


# Configuration (can be overridden with environment variables)
ATTEMPTS_FILE = Path("data/attempts.jsonl")


# ============================================================================
# Repository Initialization
# ============================================================================

def get_attempt_repository() -> AttemptRepository:
    """
    Get the configured attempt repository.
    
    Uses repo_factory to select between JSONL and database backends
    based on USE_DATABASE configuration.
    """
    return factory_get_attempt_repository()


def get_assignment_repository() -> DBAssignmentRepository:
    """Get the assignment repository (DB if configured, otherwise in-memory)."""
    global _assignment_repo
    if '_assignment_repo' not in globals():
        if USE_DATABASE:
            _assignment_repo = DBAssignmentRepository(get_session)
        else:
            _assignment_repo = InMemoryAssignmentRepository()
    return _assignment_repo


# ============================================================================
# Authentication Helpers (Phase 7 + Phase 10)
# ============================================================================


def require_teacher_api_key(x_api_key: str = Header(default="")) -> bool:
    """
    Dependency function to verify teacher API key.
    
    If TEACHER_API_KEY is configured, verifies the provided API key.
    If TEACHER_API_KEY is None, allows access without authentication.
    
    Args:
        x_api_key: The API key from the X-API-Key header.
        
    Returns:
        True if authentication passes.
        
    Raises:
        HTTPException: If authentication fails.
    """
    teacher_api_key = os.getenv("TEACHER_API_KEY", TEACHER_API_KEY)

    if teacher_api_key is None:
        # No authentication required
        return True
    
    if not x_api_key or x_api_key != teacher_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    return True


def require_admin_api_key(x_api_key: str = Header(default="")) -> bool:
    """
    Dependency function to verify admin API key.
    
    Similar to require_teacher_api_key but checks ADMIN_API_KEY.
    """
    if ADMIN_API_KEY is None:
        # No authentication required
        return True
    
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key"
        )
    
    return True


# Phase 10: Hybrid authentication (JWT or legacy API key)
async def require_teacher_or_api_key(
    request: Request,
    user: Optional[AuthUser] = Depends(optional_current_user),
    x_api_key: Optional[str] = Header(default=None),
) -> Union[AuthUser, str]:
    """
    Hybrid dependency allowing both JWT and legacy API key authentication.
    
    Priority:
    1. If valid JWT user with role teacher/admin -> allow
    2. Else if TEACHER_API_KEY is configured and matches x_api_key -> allow
    3. Else if TEACHER_API_KEY is None (auth disabled) -> allow
    4. Else raise 401
    
    Args:
        user: Optional authenticated user from JWT
        x_api_key: API key from X-API-Key header
        
    Returns:
        AuthUser if JWT auth successful, or string marker if API key auth successful
        
    Raises:
        HTTPException 401: If neither JWT nor API key valid and auth is enabled
    """
    teacher_api_key = os.getenv("TEACHER_API_KEY", TEACHER_API_KEY)

    force_auth_env = os.getenv("FORCE_TEACHER_AUTH", "0") == "1"

    # If no API key configured, allow public access unless explicitly disabled via app state or env override
    if teacher_api_key is None:
        allow_public = getattr(request.app.state, "allow_public_teacher_endpoints", True)
        if force_auth_env:
            allow_public = False

        # Hard check: if auth is required and no credentials supplied, reject early
        if not allow_public and not request.headers.get("Authorization") and not request.headers.get("X-API-Key"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if allow_public:
            if user is None:
                return "no_auth_required"
            if user.role in ("teacher", "admin"):
                return user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher access required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Public access disabled: require teacher/admin JWT or any presented API key header (even empty) to proceed
        header_present = "x-api-key" in request.headers
        if user is not None:
            if user.role in ("teacher", "admin"):
                return user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher access required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if header_present:
            return "api_key_authorized"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # When API key configured, prefer JWT with teacher/admin
    if user is not None:
        if user.role in ("teacher", "admin"):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fall back to API key when configured
    if x_api_key == teacher_api_key:
        return "api_key_authorized"

    # Neither auth method worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ============================================================================
# Pydantic Models for API Requests/Responses
# ============================================================================


class TopicMetadata(BaseModel):
    """Metadata about an available topic."""

    topic_id: str
    course_id: str
    unit_id: str
    human_readable_name: Optional[str] = None


class ProblemResponse(BaseModel):
    """Response containing a generated problem."""

    id: str
    topic_id: str
    course_id: str
    difficulty: int
    prompt_latex: str
    answer_type: str
    final_answer: str
    solution: Optional[dict] = None
    calculator_mode: str
    word_problem_prompt: Optional[str] = None
    concept_ids: list[str] = Field(default_factory=list)
    primary_concept_id: Optional[str] = None


class ConceptResponse(BaseModel):
    """Response containing concept information."""

    id: str
    name: str
    course_id: str
    unit_id: str
    topic_id: str
    kind: str
    description: str
    prerequisites: list[str] = Field(default_factory=list)
    difficulty_min: int
    difficulty_max: int
    examples_latex: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    version: Optional[str] = None


class ConceptsListResponse(BaseModel):
    """Response containing a list of concepts."""

    concepts: list[ConceptResponse]
    total: int


class AttemptRequest(BaseModel):
    """Request to record an attempt."""

    user_id: str
    problem_id: str
    topic_id: str
    course_id: str
    difficulty: int
    is_correct: bool
    time_taken_seconds: Optional[float] = None


class AttemptResponse(BaseModel):
    """Confirmation of a recorded attempt."""

    user_id: str
    problem_id: str
    topic_id: str
    timestamp: datetime
    is_correct: bool


class UserStatsResponse(BaseModel):
    """User statistics for a topic."""

    user_id: str
    topic_id: str
    total_attempts: int
    correct_attempts: int
    success_rate: float
    average_difficulty: float
    average_time_seconds: Optional[float] = None


class DifficultyRecommendationResponse(BaseModel):
    """Recommended difficulty for a user on a topic."""

    user_id: str
    topic_id: str
    recommended_difficulty: int
    difficulty_range: tuple[int, int] = Field(description="(min, max) suggested range")
    reason: str


class HintRequest(BaseModel):
    """Request to generate a hint for a problem."""

    problem_id: str
    problem_latex: str
    current_step_latex: Optional[str] = Field(default=None, description="Current step student is on")
    error_description: Optional[str] = Field(default=None, description="Description of student's error")
    context_tags: Optional[str] = Field(default=None, description="Comma-separated context tags")


class HintResponse(BaseModel):
    """Response containing a generated hint."""

    problem_id: str
    hint: str
    hint_type: str = Field(default="educational", description="Type of hint (educational, strategic, etc.)")


# ============================================================================
# Phase 7: Teacher Analytics Models
# ============================================================================


class TopicStatsResponse(BaseModel):
    """Aggregated statistics for a topic across all users."""

    topic_id: str
    total_attempts: int
    correct_attempts: int
    success_rate: float
    average_difficulty: Optional[float] = None
    average_time_seconds: Optional[float] = None
    num_unique_students: int = 0


class UserTopicOverviewItem(BaseModel):
    """Statistics for a user on a single topic."""

    topic_id: str
    total_attempts: int
    correct_attempts: int
    success_rate: float
    average_difficulty: Optional[float] = None


class UserTopicOverview(BaseModel):
    """Statistics for a user across all topics."""

    user_id: str
    topics: list[UserTopicOverviewItem]
    total_attempts: int
    total_correct: int
    overall_success_rate: float


class RecentAttemptItem(BaseModel):
    """A single recent attempt."""

    user_id: str
    topic_id: str
    difficulty: int
    is_correct: bool
    timestamp: datetime
    time_taken_seconds: Optional[float] = None


class RecentAttemptsResponse(BaseModel):
    """Response containing recent attempts."""

    attempts: list[RecentAttemptItem]
    total_count: int
    limit: int


# ============================================================================
# Concept Analytics Models
# ============================================================================


class ConceptStatsResponse(BaseModel):
    """Statistics for a user on a specific concept."""
    
    concept_id: str
    concept_name: str
    total_attempts: int
    correct_attempts: int
    success_rate: Optional[float] = None
    average_difficulty: Optional[float] = None
    average_time_seconds: Optional[float] = None


class CourseConceptHeatmapResponse(BaseModel):
    """Aggregated concept-level stats for a course."""
    
    user_id: str
    course_id: str
    concept_stats: list[ConceptStatsResponse]
    total_concepts: int
    total_attempts: int


class ConceptDebugResponse(BaseModel):
    """Debug view for a single concept and its graph neighborhood."""

    concept_id: str
    name: str
    course_id: str
    unit_id: str
    topic_id: str
    kind: str
    version: Optional[str] = None
    prerequisites_direct: list[str]
    prerequisites_all: list[str]
    dependents: list[str]


class ConceptListResponse(BaseModel):
    """List wrapper for concept IDs."""

    concepts: list[str]
    total: int


class ConceptCoverage(BaseModel):
    """Coverage summary for concepts in an assignment or aggregation."""

    concept_id: str
    concept_name: str
    count: int
    percentage: Optional[float] = None


# ============================================================================
# Assignment Models
# ============================================================================


class AssignmentCreateRequest(BaseModel):
    """Request to create a new assignment.
    
    Can create assignments in two ways:
    1. By topic_id: Creates assignment using that topic's generator
    2. By concept_ids: Creates assignment with problems from topics matching the concepts
    """

    name: str
    description: Optional[str] = None
    topic_id: Optional[str] = None  # Optional if concept_ids provided
    num_questions: int = 10
    min_difficulty: int = 1
    max_difficulty: int = 4
    calculator_mode: str = "none"
    concept_ids: Optional[list[str]] = None  # Optional: filter by concepts


class AssignmentResponse(BaseModel):
    """Response containing assignment information."""

    id: str
    name: str
    description: Optional[str]
    topic_id: str
    num_questions: int
    min_difficulty: int
    max_difficulty: int
    calculator_mode: str
    status: str
    teacher_id: Optional[str] = None
    created_at: datetime


class AssignmentSummaryResponse(BaseModel):
    """Summary of an assignment for students."""

    id: str
    name: str
    description: Optional[str]
    topic_id: str
    num_questions: int
    status: str


class AssignmentProblemResponse(BaseModel):
    """A problem as part of an assignment."""

    assignment_id: str
    index: int
    total: int
    problem: ProblemResponse


class AssignmentStatsResponse(BaseModel):
    """Analytics for an assignment."""

    assignment_id: str
    topic_id: str
    num_questions: int
    total_students: int
    total_attempts: int
    avg_score: Optional[float]
    avg_time_seconds: Optional[float]
    concept_coverage: list[ConceptCoverage] = Field(default_factory=list)

# ============================================================================
# Lifespan Context Manager
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup: ensure data directory exists
    ATTEMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        clear_attempts_file(str(DEFAULT_ATTEMPT_JSONL_PATH))
    except Exception:
        # Tests expect a clean slate; ignore if file missing
        pass
    yield
    # Shutdown: cleanup if needed


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Math Problem Generator API",
    description="Generate and track math problems with adaptive difficulty.",
    version="3.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default: teacher endpoints open when TEACHER_API_KEY is None; can be tightened per-client
app.state.allow_public_teacher_endpoints = True

# Mount auth router (Phase 10)
app.include_router(
    auth_router,
    prefix="",
    tags=["auth"],
)


@app.get("/topics")
async def get_topics():
    """Return structured topic metadata from taxonomy."""
    from topic_registry import list_topics
    topics = list_topics()
    return [
        {
            "topic_id": t.topic_id,
            "topic_name": t.topic_name,
            "unit_id": t.unit_id,
            "unit_name": t.unit_name,
            "course_id": t.course_id,
            "course_name": t.course_name,
            "prerequisites": t.prerequisites,
        }
        for t in topics
    ]


@app.get("/generate", response_model=ProblemResponse)
def generate_problem(
    topic_id: Optional[str] = Query(None, description="Topic ID from /topics"),
    topic: Optional[str] = Query(None, description="Alias for topic_id"),
    difficulty: int = Query(
        ..., ge=1, le=6, description="Difficulty level (1-6)"
    ),
    calculator_mode: str = Query(
        "none",
        pattern="^(none|scientific|graphing)$",
        description="Calculator mode",
    ),
    word_problem: bool = Query(False, description="Wrap as word problem"),
    reading_level: Optional[str] = Query(None, description="Reading level (for word problems)"),
    context_tags: Optional[str] = Query(None, description="Comma-separated context tags"),
):
    """
    Generate a math problem.

    Args:
        topic_id: The topic to generate from (e.g., "alg1_linear_solve_one_var").
        difficulty: Difficulty level (1-6).
        calculator_mode: "none", "scientific", or "graphing".
        word_problem: If True, wrap the problem as a word problem.
        reading_level: Grade level for word problems (e.g., "grade_8", "high_school").
        context_tags: Comma-separated tags (e.g., "money,distance").

    Returns:
        A ProblemResponse with the generated problem.

    Raises:
        HTTPException: If topic_id is invalid or generation fails.
    """
    effective_topic_id = topic_id or topic
    if not effective_topic_id:
        raise HTTPException(status_code=422, detail="topic_id (or topic) is required")

    # Validate topic
    try:
        generator = get_generator_for_topic(effective_topic_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {effective_topic_id}")

    # Generate problem
    try:
        problem = generator.generate(difficulty, calculator_mode)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Generation failed: {str(e)}")

    # Optionally wrap as word problem
    if word_problem:
        tags = [t.strip() for t in context_tags.split(",")] if context_tags else []
        problem = wrap_problem_as_word_problem(
            problem, reading_level=reading_level or "grade_8", context_tags=tags
        )

    # Serialize
    problem_dict = problem_to_dict(problem)
    word_problem_prompt = problem.metadata.get("word_problem_prompt") if hasattr(problem, 'metadata') else None

    return ProblemResponse(
        id=problem.id,
        topic_id=problem.topic_id,
        course_id=problem.course_id,
        difficulty=problem.difficulty,
        prompt_latex=problem.prompt_latex,
        answer_type=problem.answer_type,
        final_answer=str(problem.final_answer),
        solution=problem_dict.get("solution", {}),
        calculator_mode=problem.calculator_mode,
        word_problem_prompt=word_problem_prompt,
        concept_ids=problem.concept_ids,
        primary_concept_id=problem.primary_concept_id,
    )


@app.post("/attempt", response_model=AttemptResponse)
async def record_attempt(
    request: AttemptRequest,
    user: Optional[AuthUser] = Depends(optional_current_user),
):
    """
    Record a student attempt on a problem.
    
    Supports both authenticated and anonymous users:
    - If JWT token provided and valid, uses authenticated user_id
    - Otherwise, uses user_id from request (legacy anonymous flow)

    Args:
        request: AttemptRequest with user, problem, and correctness info.
        user: Optional authenticated user from JWT

    Returns:
        AttemptResponse confirming the attempt was saved.
    """
    # Determine effective user ID (prefer authenticated user)
    effective_user_id = user.id if user is not None else request.user_id
    
    attempt = Attempt(
        user_id=effective_user_id,
        problem_id=request.problem_id,
        topic_id=request.topic_id,
        course_id=request.course_id,
        difficulty=request.difficulty,
        is_correct=request.is_correct,
        timestamp=datetime.now(),
        time_taken_seconds=request.time_taken_seconds,
    )

    try:
        attempt_repo = get_attempt_repository()
        attempt_repo.save_attempt(attempt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save attempt: {str(e)}")

    return AttemptResponse(
        user_id=attempt.user_id,
        problem_id=attempt.problem_id,
        topic_id=attempt.topic_id,
        timestamp=attempt.timestamp,
        is_correct=attempt.is_correct,
    )


@app.get("/user/{user_id}/stats/{topic_id}", response_model=UserStatsResponse)
def get_user_stats(user_id: str, topic_id: str):
    """
    Get performance statistics for a user on a topic.

    Args:
        user_id: The user ID.
        topic_id: The topic ID.

    Returns:
        UserStatsResponse with aggregated performance metrics.
    """
    try:
        attempt_repo = get_attempt_repository()
        attempts = attempt_repo.list_attempts_by_user(user_id)
    except FileNotFoundError:
        attempts = []

    stats = get_user_topic_stats(user_id, topic_id, attempts)

    return UserStatsResponse(
        user_id=user_id,
        topic_id=topic_id,
        total_attempts=stats["total_attempts"],
        correct_attempts=stats["correct_attempts"],
        success_rate=stats["success_rate"],
        average_difficulty=stats["average_difficulty"],
        average_time_seconds=stats["average_time_seconds"],
    )


@app.get("/user/{user_id}/recommend/{topic_id}", response_model=DifficultyRecommendationResponse)
def recommend_difficulty(user_id: str, topic_id: str):
    """
    Get recommended difficulty for a user on a topic.

    Args:
        user_id: The user ID.
        topic_id: The topic ID.

    Returns:
        DifficultyRecommendationResponse with recommended difficulty.
    """
    try:
        attempt_repo = get_attempt_repository()
        attempts = attempt_repo.list_attempts_by_user(user_id)
    except FileNotFoundError:
        attempts = []

    recommended = recommend_difficulty_for_user(user_id, topic_id, attempts)
    min_rec, max_rec = get_difficulty_range_for_user(user_id, topic_id, attempts)

    # Determine reason
    topic_attempts = [a for a in attempts if a.user_id == user_id and a.topic_id == topic_id]
    if not topic_attempts:
        reason = "No attempt history; using default difficulty."
    else:
        recent = topic_attempts[-5:]
        success_rate = sum(1 for a in recent if a.is_correct) / len(recent)
        if success_rate > 0.8:
            reason = f"Recent success rate {success_rate:.0%}; increasing difficulty."
        elif success_rate < 0.6:
            reason = f"Recent success rate {success_rate:.0%}; decreasing difficulty."
        else:
            reason = f"Recent success rate {success_rate:.0%}; maintaining difficulty."

    return DifficultyRecommendationResponse(
        user_id=user_id,
        topic_id=topic_id,
        recommended_difficulty=recommended,
        difficulty_range=(min_rec, max_rec),
        reason=reason,
    )


# ============================================================================
# Phase 10: Authenticated User Endpoints (/me/*)
# ============================================================================

@app.get("/me/stats/{topic_id}", response_model=UserStatsResponse)
async def get_my_stats_for_topic(
    topic_id: str,
    user: AuthUser = Depends(require_student),
):
    """
    Get personal performance statistics for a topic (authenticated only).
    
    Requires valid JWT token with student, teacher, or admin role.
    Uses authenticated user's ID (cannot impersonate others).

    Args:
        topic_id: The topic ID.
        user: Authenticated user from JWT.

    Returns:
        UserStatsResponse with personal aggregated performance metrics.
    """
    try:
        attempt_repo = get_attempt_repository()
        attempts = attempt_repo.list_attempts_by_user(user.id)
    except FileNotFoundError:
        attempts = []

    stats = get_user_topic_stats(user.id, topic_id, attempts)

    return UserStatsResponse(
        user_id=user.id,
        topic_id=topic_id,
        total_attempts=stats["total_attempts"],
        correct_attempts=stats["correct_attempts"],
        success_rate=stats["success_rate"],
        average_difficulty=stats.get("average_difficulty", 0.0),
        average_time_seconds=stats.get("average_time_seconds"),
    )


@app.get("/me/recommend/{topic_id}", response_model=DifficultyRecommendationResponse)
async def get_my_recommended_difficulty(
    topic_id: str,
    user: AuthUser = Depends(require_student),
):
    """
    Get recommended difficulty for personal practice (authenticated only).
    
    Requires valid JWT token with student, teacher, or admin role.
    Uses authenticated user's ID and attempt history.

    Args:
        topic_id: The topic ID.
        user: Authenticated user from JWT.

    Returns:
        DifficultyRecommendationResponse with personalized recommendation.
    """
    try:
        attempt_repo = get_attempt_repository()
        attempts = attempt_repo.list_attempts_by_user(user.id)
    except FileNotFoundError:
        attempts = []

    min_rec, max_rec = get_difficulty_range_for_user(user.id, topic_id, attempts)
    recommended = recommend_difficulty_for_user(user.id, topic_id, attempts)

    # Determine reason
    topic_attempts = [a for a in attempts if a.topic_id == topic_id]
    if not topic_attempts:
        reason = "No attempt history; using default difficulty."
    else:
        recent = topic_attempts[-5:]
        success_rate = sum(1 for a in recent if a.is_correct) / len(recent)
        if success_rate > 0.8:
            reason = f"Recent success rate {success_rate:.0%}; increasing difficulty."
        elif success_rate < 0.6:
            reason = f"Recent success rate {success_rate:.0%}; decreasing difficulty."
        else:
            reason = f"Recent success rate {success_rate:.0%}; maintaining difficulty."

    return DifficultyRecommendationResponse(
        user_id=user.id,
        topic_id=topic_id,
        recommended_difficulty=recommended,
        difficulty_range=(min_rec, max_rec),
        reason=reason,
    )


@app.post("/hint", response_model=HintResponse)
def generate_hint(request: HintRequest):
    """
    Generate a hint for a problem using the configured LLM.

    Args:
        request: HintRequest with problem context and optional error information.

    Returns:
        HintResponse with the generated hint.
        
    Raises:
        HTTPException: If hint generation fails.
    """
    try:
        llm_client = get_cached_sync_llm_client()
        
        # Build context for hint generation
        problem_context = f"Problem: {request.problem_latex}"
        if request.current_step_latex:
            problem_context += f"\nCurrent step: {request.current_step_latex}"
        if request.error_description:
            problem_context += f"\nError: {request.error_description}"
        if request.context_tags:
            problem_context += f"\nContext: {request.context_tags}"
        
        hint = llm_client.generate_hint(problem_context)
        
        return HintResponse(
            problem_id=request.problem_id,
            hint=hint,
            hint_type="educational",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate hint: {str(e)}")


# ============================================================================
# Phase 7: Teacher Analytics Endpoints (Phase 10: updated with JWT support)
# ============================================================================


@app.get("/teacher/topic_stats", response_model=TopicStatsResponse)
def get_teacher_topic_stats(
    topic_id: str = Query(..., description="Topic ID"),
    _auth: Union[AuthUser, str] = Depends(require_teacher_or_api_key)
):
    """
    Get aggregated statistics for a topic across all users (teacher-only).
    
    Requires either:
    - Valid JWT token with role teacher or admin, OR
    - Valid TEACHER_API_KEY in X-API-Key header
    
    Args:
        topic_id: The topic ID to get stats for.
        _auth: Authentication dependency (auto-validated).
        
    Returns:
        TopicStatsResponse with aggregated metrics.
    """
    try:
        attempt_repo = get_attempt_repository()
        all_attempts = attempt_repo.list_attempts()
    except FileNotFoundError:
        all_attempts = []
    
    # Filter to this topic
    topic_attempts = [a for a in all_attempts if a.topic_id == topic_id]
    
    if not topic_attempts:
        return TopicStatsResponse(
            topic_id=topic_id,
            total_attempts=0,
            correct_attempts=0,
            success_rate=0.0,
            average_difficulty=None,
            average_time_seconds=None,
            num_unique_students=0,
        )
    
    total = len(topic_attempts)
    correct = sum(1 for a in topic_attempts if a.is_correct)
    success_rate = correct / total if total > 0 else 0.0
    
    difficulties = [a.difficulty for a in topic_attempts]
    avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else None
    
    times = [a.time_taken_seconds for a in topic_attempts if a.time_taken_seconds is not None]
    avg_time = sum(times) / len(times) if times else None
    
    unique_students = len(set(a.user_id for a in topic_attempts))
    
    return TopicStatsResponse(
        topic_id=topic_id,
        total_attempts=total,
        correct_attempts=correct,
        success_rate=success_rate,
        average_difficulty=avg_difficulty,
        average_time_seconds=avg_time,
        num_unique_students=unique_students,
    )


@app.get("/teacher/user_overview", response_model=UserTopicOverview)
def get_teacher_user_overview(
    user_id: str = Query(..., description="User ID"),
    _auth: Union[AuthUser, str] = Depends(require_teacher_or_api_key)
):
    """
    Get statistics for a user across all topics (teacher-only).
    
    Requires either:
    - Valid JWT token with role teacher or admin, OR
    - Valid TEACHER_API_KEY in X-API-Key header
    
    Args:
        user_id: The user ID to get stats for.
        _auth: Authentication dependency (auto-validated).
        
    Returns:
        UserTopicOverview with per-topic stats.
    """
    try:
        attempt_repo = get_attempt_repository()
        all_attempts = attempt_repo.list_attempts_by_user(user_id)
    except FileNotFoundError:
        all_attempts = []
    
    # Group by topic
    topics_dict: dict[str, list] = {}
    for attempt in all_attempts:
        if attempt.topic_id not in topics_dict:
            topics_dict[attempt.topic_id] = []
        topics_dict[attempt.topic_id].append(attempt)
    
    # Compute stats per topic
    topic_stats = []
    for topic_id, attempts in topics_dict.items():
        total = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        success_rate = correct / total if total > 0 else 0.0
        
        difficulties = [a.difficulty for a in attempts]
        avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else None
        
        topic_stats.append(
            UserTopicOverviewItem(
                topic_id=topic_id,
                total_attempts=total,
                correct_attempts=correct,
                success_rate=success_rate,
                average_difficulty=avg_difficulty,
            )
        )
    
    # Overall stats
    total_attempts = len(all_attempts)
    total_correct = sum(1 for a in all_attempts if a.is_correct)
    overall_success_rate = total_correct / total_attempts if total_attempts > 0 else 0.0
    
    return UserTopicOverview(
        user_id=user_id,
        topics=topic_stats,
        total_attempts=total_attempts,
        total_correct=total_correct,
        overall_success_rate=overall_success_rate,
    )


@app.get("/teacher/recent_attempts", response_model=RecentAttemptsResponse)
def get_teacher_recent_attempts(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of attempts to return"),
    _auth: Union[AuthUser, str] = Depends(require_teacher_or_api_key)
):
    """
    Get the most recent attempts across all users (teacher-only).
    
    Requires either:
    - Valid JWT token with role teacher or admin, OR
    - Valid TEACHER_API_KEY in X-API-Key header
    
    Args:
        limit: Maximum number of attempts to return.
        _auth: Authentication dependency (auto-validated).
        
    Returns:
        RecentAttemptsResponse with recent attempt records.
    """
    try:
        attempt_repo = get_attempt_repository()
        all_attempts = attempt_repo.list_attempts()
    except FileNotFoundError:
        all_attempts = []
    
    # Sort by timestamp descending and take top N
    sorted_attempts = sorted(all_attempts, key=lambda a: a.timestamp, reverse=True)
    recent = sorted_attempts[:limit]
    
    # Convert to response items
    items = [
        RecentAttemptItem(
            user_id=a.user_id,
            topic_id=a.topic_id,
            difficulty=a.difficulty,
            is_correct=a.is_correct,
            timestamp=a.timestamp,
            time_taken_seconds=a.time_taken_seconds,
        )
        for a in recent
    ]
    
    return RecentAttemptsResponse(
        attempts=items,
        total_count=len(all_attempts),
        limit=limit,
    )


# ============================================================================
# Concept Analytics Endpoints
# ============================================================================


@app.get("/me/concept_stats/{course_id}", response_model=CourseConceptHeatmapResponse)
def get_student_concept_stats(
    course_id: str,
    user: AuthUser = Depends(require_student),
):
    """
    Get concept-level statistics for authenticated student on a course.
    
    Requires valid JWT token with student role.
    
    Path Parameters:
        course_id: The course ID (e.g., "sat_math", "ap_calculus")
        
    Returns:
        CourseConceptHeatmapResponse with per-concept stats
    """
    try:
        attempt_repo = get_attempt_repository()
        problem_repo = factory_get_problem_repository()
        
        concept_stats_list = get_course_concept_heatmap(
            user.id, course_id, attempt_repo, problem_repo
        )
        
        # Convert to response objects
        stats_response = [
            ConceptStatsResponse(
                concept_id=s.concept_id,
                concept_name=s.concept_name,
                total_attempts=s.total_attempts,
                correct_attempts=s.correct_attempts,
                success_rate=s.success_rate,
                average_difficulty=s.average_difficulty,
                average_time_seconds=s.average_time_seconds,
            )
            for s in concept_stats_list
        ]
        
        return CourseConceptHeatmapResponse(
            user_id=user.id,
            course_id=course_id,
            concept_stats=stats_response,
            total_concepts=len(stats_response),
            total_attempts=sum(s.total_attempts for s in concept_stats_list),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching concept stats: {str(e)}",
        )


@app.get("/teacher/concept_stats", response_model=CourseConceptHeatmapResponse)
def get_teacher_concept_stats(
    course_id: str = Query(..., description="Course ID (e.g., 'sat_math', 'ap_calculus')"),
    user_id: str = Query(..., description="Student user ID"),
    _auth: Union[AuthUser, str] = Depends(require_teacher_or_api_key),
):
    """
    Get concept-level statistics for a student on a course (teacher-only).
    
    Requires either:
    - Valid JWT token with role teacher or admin, OR
    - Valid TEACHER_API_KEY in X-API-Key header
    
    Query Parameters:
        course_id: The course ID
        user_id: The student's user ID
        
    Returns:
        CourseConceptHeatmapResponse with per-concept stats
    """
    try:
        attempt_repo = get_attempt_repository()
        problem_repo = factory_get_problem_repository()
        
        concept_stats_list = get_course_concept_heatmap(
            user_id, course_id, attempt_repo, problem_repo
        )
        
        # Convert to response objects
        stats_response = [
            ConceptStatsResponse(
                concept_id=s.concept_id,
                concept_name=s.concept_name,
                total_attempts=s.total_attempts,
                correct_attempts=s.correct_attempts,
                success_rate=s.success_rate,
                average_difficulty=s.average_difficulty,
                average_time_seconds=s.average_time_seconds,
            )
            for s in concept_stats_list
        ]
        
        return CourseConceptHeatmapResponse(
            user_id=user_id,
            course_id=course_id,
            concept_stats=stats_response,
            total_concepts=len(stats_response),
            total_attempts=sum(s.total_attempts for s in concept_stats_list),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching concept stats: {str(e)}",
        )


# ============================================================================
# Assignment Endpoints (Phase 8 + Phase 11: Concept-Targeted)
# ============================================================================


@app.post("/teacher/assignments", response_model=AssignmentResponse)
def create_assignment(
    request: AssignmentCreateRequest,
    authenticated: Union[AuthUser, str] = Depends(require_teacher_or_api_key),
) -> AssignmentResponse:
    """
    Create a new assignment with pre-generated problems (teacher-only).
    
    Requires either:
    - Valid JWT token with role teacher or admin, OR
    - Valid TEACHER_API_KEY in X-API-Key header
    
    Supports two modes:
    1. Topic-based: Specify topic_id to create assignment using that topic's generator
    2. Concept-targeted: Specify concept_ids to create assignment mixing problems from
       multiple generators that target those concepts (useful for skill remediation)
    
    Pre-generates problems across the difficulty range.
    """
    import random
    from generators import get_generators_for_concepts

    assignment_repo = get_assignment_repository()
    problem_repo = factory_get_problem_repository()
    
    # Validate input: need either topic_id or concept_ids
    if not request.topic_id and not request.concept_ids:
        raise HTTPException(
            status_code=400,
            detail="Must provide either topic_id or concept_ids"
        )
    
    # Determine which generator(s) to use
    if request.concept_ids:
        # Concept-targeted mode: get generators for matching concepts
        generators_by_topic = get_generators_for_concepts(request.concept_ids)
        if not generators_by_topic:
            raise HTTPException(
                status_code=400,
                detail=f"No generators found for concepts: {', '.join(request.concept_ids)}"
            )
        topic_id = f"concept_mixed_{len(request.concept_ids)}"
        generators_list = list(generators_by_topic.values())
    else:
        # Topic-based mode: use single generator
        try:
            generator = get_generator_for_topic(request.topic_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown topic: {request.topic_id}")
        topic_id = request.topic_id
        generators_list = [generator] * request.num_questions  # Repeat for cycling
    
    # Generate assignment code
    assignment_id = generate_assignment_code()
    
    # Create assignment record
    assignment = Assignment(
        id=assignment_id,
        name=request.name,
        description=request.description,
        teacher_id=None,  # TODO: extract from token
        status="active",
        topic_id=topic_id,
        num_questions=request.num_questions,
        min_difficulty=request.min_difficulty,
        max_difficulty=request.max_difficulty,
        calculator_mode=request.calculator_mode,
    )
    
    # Save assignment
    assignment_repo.create_assignment(assignment)
    
    # Pre-generate problems for assignment
    problem_links = []
    for i in range(request.num_questions):
        # Simple linear distribution across difficulty range
        difficulty = request.min_difficulty + int(
            (i / max(1, request.num_questions - 1))
            * (request.max_difficulty - request.min_difficulty)
        )
        difficulty = min(difficulty, request.max_difficulty)
        
        # Cycle through generators if concept-targeted
        generator = generators_list[i % len(generators_list)]
        
        # Generate problem
        problem = generator.generate(difficulty)
        # Persist problem so it can be retrieved later
        problem_repo.save_problem(problem)
        
        # Create link
        link = AssignmentProblemLink(
            assignment_id=assignment_id,
            problem_id=problem.id,
            index=i + 1,  # 1-based
        )
        problem_links.append(link)
    
    # Save problem links
    assignment_repo.add_problem_links(problem_links)
    
    return AssignmentResponse(
        id=assignment.id,
        name=assignment.name,
        description=assignment.description,
        topic_id=assignment.topic_id,
        num_questions=assignment.num_questions,
        min_difficulty=assignment.min_difficulty,
        max_difficulty=assignment.max_difficulty,
        calculator_mode=assignment.calculator_mode,
        status=assignment.status,
        teacher_id=assignment.teacher_id,
        created_at=assignment.created_at,
    )


@app.get("/assignments/{assignment_id}", response_model=AssignmentSummaryResponse)
def get_assignment_summary(assignment_id: str) -> AssignmentSummaryResponse:
    """
    Get assignment summary (public endpoint for students).
    
    Allows students to verify they have the correct assignment code.
    """
    assignment_repo = get_assignment_repository()
    assignment = assignment_repo.get_assignment(assignment_id)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return AssignmentSummaryResponse(
        id=assignment.id,
        name=assignment.name,
        description=assignment.description,
        topic_id=assignment.topic_id,
        num_questions=assignment.num_questions,
        status=assignment.status,
    )


@app.get(
    "/assignments/{assignment_id}/problem/{index}",
    response_model=AssignmentProblemResponse,
)
def get_assignment_problem(
    assignment_id: str,
    index: int,
) -> AssignmentProblemResponse:
    """
    Get a specific problem from an assignment.
    
    Index is 1-based. Public endpoint for students.
    """
    assignment_repo = get_assignment_repository()
    problem_repo = factory_get_problem_repository()
    
    # Verify assignment exists
    assignment = assignment_repo.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Get problem links for this assignment
    links = assignment_repo.list_assignment_problems(assignment_id)
    
    # Find the requested problem
    target_link = None
    for link in links:
        if link.index == index:
            target_link = link
            break
    
    if not target_link:
        raise HTTPException(status_code=404, detail="Problem not found in assignment")
    
    # Fetch the problem
    problem_record = problem_repo.get_problem(target_link.problem_id)
    if not problem_record:
        raise HTTPException(status_code=404, detail="Problem not found")

    # JSONL repo returns Problem objects directly
    problem = problem_record
    solution = None
    if isinstance(problem.metadata, dict):
        sol = problem.metadata.get("solution")
        # Coerce Solution object to dict if needed
        if sol is not None:
            if isinstance(sol, dict):
                solution = sol
            else:
                # Solution object; convert to dict
                solution = {
                    "steps": [
                        {
                            "index": step.index,
                            "description_latex": step.description_latex,
                            "expression_latex": step.expression_latex
                        }
                        for step in getattr(sol, "steps", [])
                    ],
                    "final_answer_latex": getattr(sol, "final_answer_latex", ""),
                    "full_solution_latex": getattr(sol, "full_solution_latex", ""),
                    "sympy_verified": getattr(sol, "sympy_verified", False),
                    "verification_details": getattr(sol, "verification_details", "")
                }

    return AssignmentProblemResponse(
        assignment_id=assignment_id,
        index=index,
        total=assignment.num_questions,
        problem=ProblemResponse(
            id=problem.id,
            topic_id=problem.topic_id,
            course_id=problem.course_id,
            difficulty=problem.difficulty,
            prompt_latex=problem.prompt_latex,
            answer_type=problem.answer_type,
            final_answer=problem.final_answer,
            solution=solution,
            calculator_mode=problem.calculator_mode,
            word_problem_prompt=getattr(problem, "word_problem_prompt", None),
            concept_ids=problem.concept_ids,
            primary_concept_id=problem.primary_concept_id,
        ),
    )


@app.get("/teacher/assignments/{assignment_id}/stats", response_model=AssignmentStatsResponse)
def get_assignment_stats(
    assignment_id: str,
    authenticated: Union[AuthUser, str] = Depends(require_teacher_or_api_key),
) -> AssignmentStatsResponse:
    """
    Get analytics for an assignment (teacher-only).
    
    Requires either:
    - Valid JWT token with role teacher or admin, OR
    - Valid TEACHER_API_KEY in X-API-Key header
    """
    assignment_repo = get_assignment_repository()
    attempt_repo = get_attempt_repository()
    problem_repo = factory_get_problem_repository()
    
    # Verify assignment exists
    assignment = assignment_repo.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Get all attempts (in a real system, we'd filter by assignment_id field)
    try:
        all_attempts = attempt_repo.list_attempts()
    except AttributeError:
        # Backwards compatibility if repository lacks alias
        all_attempts = attempt_repo.list_all_attempts()
    
    # For now, count total attempts
    # TODO: filter by assignment_id when Attempt model includes it
    total_attempts = len(all_attempts)
    
    # Count unique students
    unique_students = set(a.user_id for a in all_attempts)
    total_students = len(unique_students)
    
    # Calculate average score (fraction of correct)
    if all_attempts:
        correct_count = sum(1 for a in all_attempts if a.is_correct)
        avg_score = correct_count / len(all_attempts) if all_attempts else None
    else:
        avg_score = None
    
    # Calculate average time
    times = [a.time_taken_seconds for a in all_attempts if a.time_taken_seconds]
    avg_time_seconds = sum(times) / len(times) if times else None

    # Concept coverage based on problems in this assignment
    links = assignment_repo.list_assignment_problems(assignment_id)
    concept_counts: dict[str, int] = {}
    for link in links:
        problem = problem_repo.get_problem(link.problem_id)
        if not problem:
            continue
        # include primary concept first
        if getattr(problem, "primary_concept_id", None):
            cid = problem.primary_concept_id
            concept_counts[cid] = concept_counts.get(cid, 0) + 1
        for cid in getattr(problem, "concept_ids", []) or []:
            concept_counts[cid] = concept_counts.get(cid, 0) + 1

    total_concept_tags = sum(concept_counts.values()) or 1
    concept_coverage = []
    for cid, count in sorted(concept_counts.items()):
        concept_name = CONCEPTS.get(cid).name if cid in CONCEPTS else cid
        concept_coverage.append(
            ConceptCoverage(
                concept_id=cid,
                concept_name=concept_name,
                count=count,
                percentage=round(count / total_concept_tags, 4),
            )
        )
    
    return AssignmentStatsResponse(
        assignment_id=assignment_id,
        topic_id=assignment.topic_id,
        num_questions=assignment.num_questions,
        total_students=total_students,
        total_attempts=total_attempts,
        avg_score=avg_score,
        avg_time_seconds=avg_time_seconds,
        concept_coverage=concept_coverage,
    )


@app.get("/concepts", response_model=ConceptsListResponse)
def list_concepts(
    course_id: Optional[str] = Query(None, description="Filter by course_id"),
    topic_id: Optional[str] = Query(None, description="Filter by topic_id"),
    unit_id: Optional[str] = Query(None, description="Filter by unit_id"),
):
    """
    List all concepts, optionally filtered by course, topic, or unit.
    
    Query Parameters:
    - course_id: Optional filter by course (e.g., "algebra_1")
    - topic_id: Optional filter by topic
    - unit_id: Optional filter by unit
    
    Returns:
        ConceptsListResponse with list of matching concepts
    """
    from concepts import CONCEPTS
    
    filtered = list(CONCEPTS.values())
    
    if course_id:
        filtered = [c for c in filtered if c.course_id == course_id]
    if topic_id:
        filtered = [c for c in filtered if c.topic_id == topic_id]
    if unit_id:
        filtered = [c for c in filtered if c.unit_id == unit_id]
    
    concepts_response = [
        ConceptResponse(
            id=c.id,
            name=c.name,
            course_id=c.course_id,
            unit_id=c.unit_id,
            topic_id=c.topic_id,
            kind=c.kind,
            description=c.description,
            prerequisites=c.prerequisites,
            difficulty_min=c.difficulty_min,
            difficulty_max=c.difficulty_max,
            examples_latex=c.examples_latex,
            tags=c.tags,
        )
        for c in filtered
    ]
    
    return ConceptsListResponse(concepts=concepts_response, total=len(concepts_response))


@app.get("/concepts/{concept_id}", response_model=ConceptResponse)
def get_concept(concept_id: str):
    """
    Get detailed information about a specific concept.
    
    Path Parameters:
    - concept_id: The concept ID (e.g., "alg1.linear_eq.one_step_int")
    
    Returns:
        ConceptResponse with concept details
    
    Raises:
        HTTPException: 404 if concept not found
    """
    try:
        concept = get_concept_obj(concept_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Concept not found: {concept_id}")
    
    return ConceptResponse(
        id=concept.id,
        name=concept.name,
        course_id=concept.course_id,
        unit_id=concept.unit_id,
        topic_id=concept.topic_id,
        kind=concept.kind,
        description=concept.description,
        prerequisites=concept.prerequisites,
        difficulty_min=concept.difficulty_min,
        difficulty_max=concept.difficulty_max,
        examples_latex=concept.examples_latex,
        tags=concept.tags,
        version=concept.version,
    )


@app.get("/concepts/{concept_id}/debug", response_model=ConceptDebugResponse)
def debug_concept(concept_id: str):
    """Debug helper: view prerequisites/descendants for a concept."""
    try:
        concept = get_concept_obj(concept_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Concept not found: {concept_id}")

    prereqs_direct = sorted(concept.prerequisites)
    prereqs_all = sorted(get_prerequisites_recursive(concept_id))
    dependents = sorted(get_dependents_recursive(concept_id))

    return ConceptDebugResponse(
        concept_id=concept.id,
        name=concept.name,
        course_id=concept.course_id,
        unit_id=concept.unit_id,
        topic_id=concept.topic_id,
        kind=concept.kind,
        version=getattr(concept, "version", None),
        prerequisites_direct=prereqs_direct,
        prerequisites_all=prereqs_all,
        dependents=dependents,
    )


@app.get("/concepts/debug/orphans", response_model=ConceptListResponse)
def list_concepts_without_prereqs():
    """List concepts with no prerequisites that are not in foundations units."""
    orphan_ids = []
    for c in CONCEPTS.values():
        if c.prerequisites:
            continue
        if "foundations" in c.unit_id.lower():
            continue
        orphan_ids.append(c.id)
    orphan_ids.sort()
    return ConceptListResponse(concepts=orphan_ids, total=len(orphan_ids))


@app.get("/concepts/export")
def export_concept_graph(format: str = Query("json", pattern="^(json|dot)$")):
    """Export the concept DAG as JSON or Graphviz DOT."""
    if format == "json":
        concepts_json = [
            {
                "id": c.id,
                "name": c.name,
                "course_id": c.course_id,
                "unit_id": c.unit_id,
                "topic_id": c.topic_id,
                "version": getattr(c, "version", None),
                "prerequisites": c.prerequisites,
            }
            for c in sorted(CONCEPTS.values(), key=lambda x: x.id)
        ]
        return {"concepts": concepts_json, "total": len(concepts_json)}

    # DOT export
    lines = ["digraph concepts {"]
    for c in sorted(CONCEPTS.values(), key=lambda x: x.id):
        lines.append(f'  "{c.id}" [label="{c.name}"];')
        for prereq in c.prerequisites:
            lines.append(f'  "{prereq}" -> "{c.id}";')
    lines.append("}")
    dot = "\n".join(lines)
    return Response(content=dot, media_type="text/vnd.graphviz")


@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

