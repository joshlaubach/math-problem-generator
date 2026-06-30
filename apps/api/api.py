"""
HTTP API for the math problem generator.

Exposes endpoints for:
- Listing available topics
- Generating problems
- Tracking student attempts
- Recommending adaptive difficulty
- Generating hints with LLM
"""

import os
import re
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Depends, Header, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import DEFAULT_ATTEMPT_JSONL_PATH, USE_DATABASE, TEACHER_API_KEY, ADMIN_API_KEY, FRONTEND_URL
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
from llm_factory import get_cached_sync_llm_client, get_cached_llm_client
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
from ws_router import router as ws_router
from calc_router import router as calc_router
from admin_router import router as admin_router
from session_quota import (
    check_problem_quota,
    record_problem,
    get_tutor_hours_used,
    get_problems_used,
    get_problems_used_today,
    get_reset_date,
    ABUSE_CEILING_HOURS_PER_MONTH,
    PROBLEM_MONTH_LIMITS,
    FREE_DAILY_PROBLEM_LIMIT,
)
from auth_dependencies import (
    get_current_user,
    get_unverified_clerk_user,
    optional_current_user,
    require_student,
    require_teacher,
    require_admin,
    get_user_repository,
)
from users_models import User as AuthUser
from abuse_guard import check_and_record as _abuse_check


def _rate_key(request: Request) -> str:
    """Rate-limit by user ID extracted from the Bearer token, falling back to IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import jwt as _pyjwt
            payload = _pyjwt.decode(
                auth[7:],
                options={"verify_signature": False, "verify_exp": False},
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return request.client.host if request.client else "unknown"


# SECURITY (H4): back the limiter with Redis when available so limits are shared
# across Railway replicas and survive restarts; falls back to in-memory storage
# (dev/test, or if Redis is unreachable).
limiter = Limiter(
    key_func=_rate_key,
    storage_uri=os.getenv("REDIS_URL") or "memory://",
    enabled=not os.getenv("TESTING", "").lower() in ("1", "true", "yes"),
)


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
    problem_latex: str = Field(..., max_length=2000)
    hint_index: int = Field(default=0, ge=0, le=3, description="Which hint to generate (0=first, 3=fourth)")
    current_step_latex: Optional[str] = Field(default=None, max_length=2000)
    error_description: Optional[str] = Field(default=None, max_length=2000)
    context_tags: Optional[str] = Field(default=None, max_length=2000)


class HintResponse(BaseModel):
    """Response containing a generated hint."""

    problem_id: str
    hint: str
    hint_type: str = Field(default="educational", description="Type of hint (educational, strategic, etc.)")


class CheckAnswerRequest(BaseModel):
    """Request to grade a student's answer against the canonical answer."""

    student_answer: str = Field(..., max_length=2000)
    correct_answer: str = Field(..., max_length=2000)
    answer_type: Optional[str] = Field(default=None, description="numeric | expression")
    problem_id: Optional[str] = Field(default=None, max_length=200)


class CheckAnswerResponse(BaseModel):
    """Grading verdict. `is_correct` is decided by SymPy equivalence, not a
    string compare, so equivalent forms (1/2 == 0.5 == \\frac{1}{2}) are
    accepted and non-equivalent forms (\\sqrt{2} != 2) are not."""

    is_correct: bool
    correct_answer: str


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


def _validate_production_config() -> None:
    """
    Fail-loud production readiness checks, run once at startup.

    When USE_DATABASE=true (i.e., production):
    - the database must be reachable and the schema present (hard fail), and
    - the lesson store should not be empty (loud warning — sessions would
      silently regenerate all 866 lessons at LLM cost and latency; run
      scripts/migrate_lessons_to_db.py).
    Also warns when REDIS_URL is unset in DB mode: live sessions then reside
    in process memory only and every deploy drops active tutoring sessions.
    """
    import logging
    import os
    from config import USE_DATABASE

    log = logging.getLogger("startup")

    # SECURITY: API keys that fail open (unauthenticated access) when unset.
    # Warn whenever RAILWAY_ENVIRONMENT is present — that's the production indicator.
    if os.getenv("RAILWAY_ENVIRONMENT"):
        if TEACHER_API_KEY is None:
            log.warning(
                "TEACHER_API_KEY is not set — teacher endpoints are unauthenticated in production"
            )
        if ADMIN_API_KEY is None:
            log.warning(
                "ADMIN_API_KEY is not set — admin endpoints are unauthenticated in production"
            )

    if not USE_DATABASE:
        return

    # 1. Create any missing tables (idempotent), then verify the DB is usable.
    #    SQLAlchemy owns the schema — the Prisma schema is not applied at runtime.
    try:
        from db_session import init_db, get_session
        from db_models import TopicLessonRecord
        init_db()
        db = get_session()
        try:
            db.query(TopicLessonRecord).count()
        finally:
            db.close()
    except Exception as exc:
        raise RuntimeError(
            "USE_DATABASE=true but the database is unreachable or could not be "
            f"initialised — refusing to serve traffic: {exc}"
        ) from exc

    # 2. Lesson store must not be empty in prod
    from agents.lesson_store import lesson_count
    db_lessons, file_lessons = lesson_count()
    if db_lessons == 0:
        log.error(
            "LESSON STORE EMPTY: 0 lessons in Postgres (%d on local disk). "
            "Production will regenerate every lesson on demand at LLM cost. "
            "Run: python scripts/migrate_lessons_to_db.py", file_lessons,
        )
    else:
        log.info("Lesson store: %d lessons in DB (%d on disk)", db_lessons, file_lessons)

    # 3. Redis strongly recommended in prod
    if not os.getenv("REDIS_URL"):
        log.warning(
            "REDIS_URL not set with USE_DATABASE=true: live tutor sessions are "
            "in-memory only — every deploy/restart drops active sessions, and "
            "rate limits are per-process rather than shared across replicas."
        )

    # 4. SECURITY: refuse to boot prod without secrets that fail OPEN if unset.
    #    Stripe webhook secret (C1) — without it the webhook would be forgeable.
    if not os.getenv("STRIPE_WEBHOOK_SECRET"):
        raise RuntimeError(
            "STRIPE_WEBHOOK_SECRET is not set. The Stripe webhook would be "
            "unverifiable (forgeable payment events) — refusing to serve traffic."
        )

    # 5. SECURITY (L3): FRONTEND_URL must be a real origin in prod, otherwise CORS
    #    silently falls back to localhost and the deployed app can't call the API.
    frontend = os.getenv("FRONTEND_URL", "")
    if not frontend or frontend.startswith("http://localhost") or frontend.startswith("http://127.0.0.1"):
        raise RuntimeError(
            "FRONTEND_URL must be set to the production origin (got "
            f"{frontend!r}) — refusing to serve traffic with a localhost CORS origin."
        )

    # 6. SECURITY (M5): Clerk auth in prod requires issuer/JWKS configuration.
    if os.getenv("AUTH_PROVIDER") == "clerk" and not (
        os.getenv("CLERK_FRONTEND_API") or os.getenv("CLERK_JWKS_URL")
    ):
        raise RuntimeError(
            "AUTH_PROVIDER=clerk but neither CLERK_FRONTEND_API nor CLERK_JWKS_URL "
            "is set — cannot verify tokens. Refusing to serve traffic."
        )


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
    _validate_production_config()
    # Initialise Redis session store (no-op if REDIS_URL not set)
    from ws_session import init_redis
    await init_redis()
    # Sweep orphaned upload directories older than 24 h (Phase 3)
    _sweep_orphaned_uploads()
    yield
    # Shutdown: graceful session cleanup on SIGTERM / Railway deploy restart
    try:
        from ws_session import _sessions
        from ws_router import _end_session as _ws_end_session
        active_sessions = list(_sessions.values())
        if active_sessions:
            async def _shutdown_sessions() -> None:
                for sess in active_sessions:
                    try:
                        await _ws_end_session(None, sess, reason="server_restart")
                    except Exception:
                        pass
            await asyncio.wait_for(_shutdown_sessions(), timeout=5.0)
    except Exception:
        pass


def _sweep_orphaned_uploads() -> None:
    """
    Delete session_uploads/ subdirs that are more than 24 h old.
    This catches uploads whose sessions ended abnormally before _end_session ran.
    Silently swallowed — never blocks startup.
    """
    import shutil
    import time
    from config import DATA_DIR
    upload_root = DATA_DIR / "session_uploads"
    if not upload_root.exists():
        return
    cutoff = time.time() - 86400  # 24 hours
    try:
        for child in upload_root.iterdir():
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
    except Exception:
        pass


# ============================================================================
# Error Tracking (Sentry)
# ============================================================================

_SENTRY_DSN = os.getenv("SENTRY_DSN")
if _SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
    )

# ============================================================================
# Structured logging — JSON output for Railway log ingestion
# ============================================================================

try:
    from pythonjsonlogger import jsonlogger as _jsonlogger
    _log_handler = logging.StreamHandler()
    _log_handler.setFormatter(
        _jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    _log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, _log_level, logging.INFO),
        handlers=[_log_handler],
        force=True,
    )
except ImportError:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("api")

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Math Problem Generator API",
    description="Generate and track math problems with adaptive difficulty.",
    version="3.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: lock to FRONTEND_URL in production; localhost fallback for dev.
_is_prod_origin = (
    FRONTEND_URL
    and not FRONTEND_URL.startswith("http://localhost")
    and not FRONTEND_URL.startswith("http://127.0.0.1")
)
_cors_origins = (
    [FRONTEND_URL]
    if _is_prod_origin
    else [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    """SECURITY (M1): defense-in-depth response headers on the API too."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
    )
    return response


@app.exception_handler(Exception)
async def _generic_exception_handler(request: Request, exc: Exception):
    """
    SECURITY (L2): catch-all so an unhandled error returns a generic 500 with no
    stack trace, file path, or internal message. HTTPExceptions are handled by
    FastAPI's own handler and keep their intended status/detail.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Default: teacher endpoints open when TEACHER_API_KEY is None; can be tightened per-client
app.state.allow_public_teacher_endpoints = True

# Mount auth router (Phase 10)
app.include_router(
    auth_router,
    prefix="",
    tags=["auth"],
)

# WebSocket tutor router
app.include_router(ws_router)

# CAS calculator router
app.include_router(calc_router)

# Admin panel router
app.include_router(admin_router)

# Session credits + Stripe checkout
from credit_router import router as credit_router
app.include_router(credit_router)

# Tutor utilities (scratchpad validation, dispute, voice)
from tutor_router import router as tutor_router
app.include_router(tutor_router)

# Voice WebSocket — Deepgram streaming STT proxy
from voice_ws import router as voice_ws_router
app.include_router(voice_ws_router)

# Email (session reports + reminders)
from email_router import router as email_router
app.include_router(email_router)

# Parent monitoring
from parent_router import router as parent_router
app.include_router(parent_router)

# Exam Mode (Phase 4)
from exam_router import router as exam_router
app.include_router(exam_router)

# Rewards / Referral (Phase 5)
from referral_router import router as referral_router
app.include_router(referral_router)


@app.get("/me/quota")
async def get_my_quota(user: AuthUser = Depends(require_student)):
    """Return the authenticated user's current quota usage for tutor hours and problem generation."""
    from datetime import datetime, timezone
    year_month = datetime.now(timezone.utc).strftime("%Y-%m")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    problems_used = get_problems_used(user.id, year_month)
    problem_limit = PROBLEM_MONTH_LIMITS.get(user.tier, PROBLEM_MONTH_LIMITS["free"])
    problems_today = get_problems_used_today(user.id, today) if user.tier == "free" else None

    # Tutor access is credits-only (see /credits/balance for purchasable credits).
    # Hours here report only the flat anti-abuse ceiling, same for every tier.
    hours_used = get_tutor_hours_used(user.id, year_month)
    tutor_info = {
        "used_hours": round(hours_used, 2),
        "limit_hours": ABUSE_CEILING_HOURS_PER_MONTH,
        "allowed": hours_used < ABUSE_CEILING_HOURS_PER_MONTH,
    }

    return {
        "tier": user.tier,
        "resets_at": get_reset_date(),
        "tutor": tutor_info,
        "problems": {
            "used": problems_used,
            "limit": problem_limit,
            "used_today": problems_today,
            "daily_limit": FREE_DAILY_PROBLEM_LIMIT if user.tier == "free" else None,
            "allowed": problems_used < problem_limit and (
                user.tier != "free" or (problems_today or 0) < FREE_DAILY_PROBLEM_LIMIT
            ),
        },
    }


@app.get("/me/reviews")
async def get_my_reviews(user: AuthUser = Depends(require_student)):
    """
    Spaced-repetition topics due for review (next_review_at <= now), soonest
    first. Surfaces the SRS schedule the adaptive engine writes at session end.
    """
    from progress_store import due_for_review
    from topic_registry import TOPIC_REGISTRY

    due = due_for_review(user.id, limit=20)
    for item in due:
        meta = TOPIC_REGISTRY.get(item["topic_id"])
        item["topic_name"] = meta.topic_name if meta else item["topic_id"]
    return {"due": due, "count": len(due)}


@app.get("/me/progress")
async def get_my_progress(user: AuthUser = Depends(require_student)):
    """
    Return goal-calibrated progress for the authenticated student.

    Computes per-topic completion status against the student's learning goal.
    Goal thresholds:
      pass    → 65% accuracy at difficulty 2-3
      b       → 75% accuracy at difficulty 3-4
      a       → 85% accuracy at difficulty 4-5
      mastery → 90%+ accuracy at difficulty 5-6
    """
    GOAL_THRESHOLDS = {
        "pass":    {"accuracy": 0.65, "min_difficulty": 2},
        "b":       {"accuracy": 0.75, "min_difficulty": 3},
        "a":       {"accuracy": 0.85, "min_difficulty": 4},
        "mastery": {"accuracy": 0.90, "min_difficulty": 5},
    }

    goal = getattr(user, "learning_goal", None) or "b"
    threshold = GOAL_THRESHOLDS.get(goal, GOAL_THRESHOLDS["b"])

    # Load this user's attempts via the repository (handles DB vs JSONL).
    try:
        user_attempts = list(get_attempt_repository().list_attempts_by_user(user.id))
    except Exception:
        user_attempts = []

    # Group by topic_id → compute accuracy on recent 10 attempts at threshold difficulty
    from collections import defaultdict
    topic_stats: dict[str, dict] = defaultdict(lambda: {"correct": 0, "total": 0, "at_level": 0})

    for attempt in user_attempts:
        tid = attempt.topic_id
        if not tid:
            continue
        topic_stats[tid]["total"] += 1
        if attempt.is_correct:
            topic_stats[tid]["correct"] += 1
        if attempt.difficulty >= threshold["min_difficulty"]:
            topic_stats[tid]["at_level"] += 1

    # Build per-topic progress
    topics_progress = []
    for tid, stats in topic_stats.items():
        total = stats["total"]
        if total == 0:
            continue
        accuracy = stats["correct"] / total
        complete = (
            accuracy >= threshold["accuracy"]
            and stats["at_level"] >= 2
        )
        needs_review = total >= 3 and accuracy < 0.60

        topics_progress.append({
            "topic_id": tid,
            "total_attempts": total,
            "accuracy": round(accuracy, 3),
            "complete": complete,
            "needs_review": needs_review,
        })

    complete_count = sum(1 for t in topics_progress if t["complete"])
    needs_review_count = sum(1 for t in topics_progress if t["needs_review"])

    return {
        "goal": goal,
        "threshold": threshold,
        "summary": {
            "topics_attempted": len(topics_progress),
            "topics_complete": complete_count,
            "topics_needing_review": needs_review_count,
        },
        "topics": topics_progress,
        "session_credits": _get_credit_balance(user.id),
        "streak": _compute_day_streak(user_attempts),
    }


def _compute_day_streak(attempts) -> dict:
    """Consecutive-day practice streak from attempt timestamps (UTC).

    Returns {current, longest, active_today}. The current streak counts back
    from today, or from yesterday if the student hasn't practiced yet today
    (so an active streak isn't shown as broken until a full day is missed).
    Never raises.
    """
    from datetime import timezone, timedelta

    dates = set()
    for a in attempts:
        ts = getattr(a, "timestamp", None)
        if ts is None:
            continue
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                continue
        try:
            dates.add(ts.date())
        except AttributeError:
            continue

    if not dates:
        return {"current": 0, "longest": 0, "active_today": False}

    today = datetime.now(timezone.utc).date()
    active_today = today in dates

    ordered = sorted(dates)
    longest = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)

    current = 0
    cursor = today if active_today else today - timedelta(days=1)
    while cursor in dates:
        current += 1
        cursor -= timedelta(days=1)

    return {"current": current, "longest": longest, "active_today": active_today}


def _get_credit_balance(user_id: str) -> dict:
    """Return session credit balance for dashboard display."""
    try:
        from credit_router import _uses_database, _available_credits, _expiring_soon, _next_expiry
        if not _uses_database():
            return {"available": None, "expiring_soon": 0, "next_expiry": None}
        from db_session import get_session as _get_db
        db = _get_db()
        try:
            credits = _available_credits(user_id, db)
            return {
                "available": len(credits),
                "expiring_soon": _expiring_soon(credits),
                "next_expiry": _next_expiry(credits),
            }
        finally:
            db.close()
    except Exception:
        return {"available": None, "expiring_soon": 0, "next_expiry": None}


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
            "calculator_mode": t.calculator_mode,
            "is_honors": t.is_honors,
        }
        for t in topics
    ]


# Internal QA / bookkeeping fields that must never be sent to the client — they
# leak the answer machinery and would render as raw "SYMPY_VERIFIED" rows in the
# student solution panel.
_SOLUTION_INTERNAL_KEYS = frozenset({
    "final_answer_latex",      # duplicates the separately-shown final_answer
    "full_solution_latex",     # flattened raw string; `steps` is the clean form
    "sympy_verified",
    "verification_details",
})


def _student_facing_solution(solution: Optional[dict]) -> dict:
    """Strip internal verification metadata from a solution dict, leaving only
    the student-facing worked steps. Returns {} when there is no solution."""
    if not solution:
        return {}
    return {
        k: v for k, v in solution.items()
        if k not in _SOLUTION_INTERNAL_KEYS and v is not None
    }


_APPROX_RE = re.compile(r"^\$?\\?approx\s*|^≈\s*")

def _strip_approx(s: str) -> str:
    """Remove leading \\approx / ≈ markers from a final_answer string.

    LLMs sometimes prefix decimal answers with \\approx (e.g. '$\\approx 3.14$').
    This makes the answer unparseable by SymPy and looks wrong in the UI.
    """
    s = _APPROX_RE.sub("", s.strip()).strip("$").strip()
    return s


@app.get("/generate", response_model=ProblemResponse)
@limiter.limit("5/minute")
async def generate_problem(
    request: Request,
    topic_id: Optional[str] = Query(None, description="Topic ID from /topics"),
    topic: Optional[str] = Query(None, description="Alias for topic_id"),
    difficulty: int = Query(
        ..., ge=1, le=6, description="Difficulty level (1-6)"
    ),
    calculator_mode: str = Query(
        "none",
        pattern="^(none|scientific|graphing|cas)$",
        description="Calculator mode",
    ),
    word_problem: bool = Query(False, description="Wrap as word problem"),
    reading_level: Optional[str] = Query(None, description="Reading level (for word problems)"),
    context_tags: Optional[str] = Query(None, description="Comma-separated context tags"),
    user: AuthUser = Depends(require_student),
    user_repo=Depends(get_user_repository),
):
    """
    Generate a math problem. Requires authentication.

    Uses SymPy-backed generators when available; falls back to LLM (Mode B)
    for any topic not in the static registry. All 818 curriculum topics are
    supported via the LLM fallback when ANTHROPIC_API_KEY is set.
    """
    from topic_registry import TOPIC_REGISTRY
    from agents.generator import generate as agent_generate
    from agents.schemas import GeneratorInput
    from uuid import uuid4

    _abuse_check(user.id, user.role, user_repo)

    allowed, used, limit = check_problem_quota(user.id, user.tier)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly problem limit reached ({used}/{limit}). Resets on {get_reset_date()}.",
        )

    effective_topic_id = topic_id or topic
    if not effective_topic_id:
        raise HTTPException(status_code=422, detail="topic_id (or topic) is required")

    # Try SymPy-backed registry first
    try:
        generator = get_generator_for_topic(effective_topic_id)
        try:
            problem = generator.generate(difficulty, calculator_mode)
        except Exception as e:
            logger.exception("Problem generation failed for topic %s", effective_topic_id)
            raise HTTPException(status_code=400, detail="Problem generation failed. Please try again.")

        if word_problem:
            tags = [t.strip() for t in context_tags.split(",")] if context_tags else []
            problem = wrap_problem_as_word_problem(
                problem, reading_level=reading_level or "grade_8", context_tags=tags
            )

        problem_dict = problem_to_dict(problem)
        student_solution = _student_facing_solution(problem_dict.get("solution"))
        word_problem_prompt = problem.metadata.get("word_problem_prompt") if hasattr(problem, 'metadata') else None
        if user is not None:
            record_problem(user.id, problem.id, source="bank")
        return ProblemResponse(
            id=problem.id,
            topic_id=problem.topic_id,
            course_id=problem.course_id,
            difficulty=problem.difficulty,
            prompt_latex=problem.prompt_latex,
            answer_type=problem.answer_type,
            final_answer=_strip_approx(str(problem.final_answer)),
            solution=student_solution,
            calculator_mode=problem.calculator_mode,
            word_problem_prompt=word_problem_prompt,
            concept_ids=problem.concept_ids,
            primary_concept_id=problem.primary_concept_id,
        )

    except KeyError:
        pass  # no SymPy generator — fall through to LLM agent

    # LLM fallback (Mode B): works for any topic in the curriculum registry
    topic_meta = TOPIC_REGISTRY.get(effective_topic_id)
    if not topic_meta:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {effective_topic_id}")

    # Map difficulty 1-6 → conceptual/computational 1-5
    diff5 = max(1, min(5, round(difficulty * 5 / 6)))
    _calc_map = {"none": "none", "scientific": "scientific", "graphing": "graphing", "cas": "cas"}
    calc_tier = _calc_map.get(calculator_mode, "none")

    try:
        generated = await agent_generate(GeneratorInput(
            topic=topic_meta.topic_name,
            course=topic_meta.course_name,
            unit=topic_meta.unit_name,
            conceptual_diff=diff5,
            computational_diff=diff5,
            calc_tier=calc_tier,
        ))
    except Exception as e:
        logger.exception("Problem generation (Mode B) failed for topic %s", effective_topic_id)
        raise HTTPException(status_code=400, detail="Problem generation failed. Please try again.")

    problem_id = str(uuid4())
    if user is not None:
        record_problem(user.id, problem_id, source="live")
    return ProblemResponse(
        id=problem_id,
        topic_id=effective_topic_id,
        course_id=topic_meta.course_id,
        difficulty=difficulty,
        prompt_latex=generated.statement,
        answer_type=generated.answer_type,
        final_answer=_strip_approx(generated.answer),
        solution={
            "steps": [{"expression_latex": s.step, "description_latex": s.explanation} for s in generated.worked_steps],
            **({"proof_rows": generated.proof_rows} if generated.proof_rows else {}),
        },
        calculator_mode=calculator_mode,
        word_problem_prompt=None,
        concept_ids=[],
        primary_concept_id=None,
    )


@app.post("/attempt", response_model=AttemptResponse)
async def record_attempt(
    request: AttemptRequest,
    user: AuthUser = Depends(require_student),
):
    """
    Record a student attempt on a problem. Requires authentication.

    Args:
        request: AttemptRequest with problem and correctness info.
        user: Authenticated user from JWT.

    Returns:
        AttemptResponse confirming the attempt was saved.
    """
    effective_user_id = user.id
    
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
        logger.exception("Failed to save attempt for user %s", attempt.user_id)
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    return AttemptResponse(
        user_id=attempt.user_id,
        problem_id=attempt.problem_id,
        topic_id=attempt.topic_id,
        timestamp=attempt.timestamp,
        is_correct=attempt.is_correct,
    )


@app.post("/check-answer", response_model=CheckAnswerResponse)
@limiter.limit("30/minute")
async def check_answer(
    request: Request,
    body: CheckAnswerRequest,
    user: AuthUser = Depends(require_student),
):
    """Grade a student's answer with SymPy equivalence.

    This is the source of truth for correctness — the client must not decide
    it with a string compare. CAS verification is cheap and synchronous (no
    LLM), so the practice loop can call it on every submission.
    """
    from answer_check import answers_equivalent

    is_correct = answers_equivalent(
        body.student_answer, body.correct_answer, body.answer_type
    )
    return CheckAnswerResponse(is_correct=is_correct, correct_answer=body.correct_answer)


# ── Public landing-page demo (no auth, no quota) ────────────────────────────────
# Lets a prospective student solve one real, CAS-graded problem before signing up.
# Rate-limited per IP; no problem is persisted.

_DEMO_FALLBACK = {
    "id": "demo-fallback",
    "prompt_latex": "Solve for $x$: $2x + 3 = 11$",
    "answer_type": "numeric",
    "final_answer": "4",
    "solution": {"steps": [
        {"description_latex": "Subtract $3$ from both sides", "expression_latex": "2 x = 8"},
        {"description_latex": "Divide both sides by $2$", "expression_latex": "x = 4"},
    ]},
}


@app.get("/demo/problem")
@limiter.limit("30/minute")
async def demo_problem(request: Request):
    """Return one public sample problem for the landing page. No auth, no quota."""
    import random
    try:
        generator = get_generator_for_topic("alg1_linear_solve_one_var")
        problem = generator.generate(random.choice([1, 2]), "none")
        problem_dict = problem_to_dict(problem)
        return {
            "id": problem.id,
            "prompt_latex": problem.prompt_latex,
            "answer_type": problem.answer_type,
            "final_answer": _strip_approx(str(problem.final_answer)),
            "solution": _student_facing_solution(problem_dict.get("solution")),
        }
    except Exception:
        return _DEMO_FALLBACK


@app.post("/demo/check-answer", response_model=CheckAnswerResponse)
@limiter.limit("30/minute")
async def demo_check_answer(request: Request, body: CheckAnswerRequest):
    """Public CAS grading for the landing-page demo. Same engine as /check-answer."""
    from answer_check import answers_equivalent

    is_correct = answers_equivalent(
        body.student_answer, body.correct_answer, body.answer_type
    )
    return CheckAnswerResponse(is_correct=is_correct, correct_answer=body.correct_answer)


@app.get("/user/{user_id}/stats/{topic_id}", response_model=UserStatsResponse)
def get_user_stats(user_id: str, topic_id: str, user: AuthUser = Depends(require_student)):
    """
    Get performance statistics for a user on a topic.

    Args:
        user_id: The user ID.
        topic_id: The topic ID.

    Returns:
        UserStatsResponse with aggregated performance metrics.
    """
    if user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
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
def recommend_difficulty(user_id: str, topic_id: str, user: AuthUser = Depends(require_student)):
    """
    Get recommended difficulty for a user on a topic.

    Args:
        user_id: The user ID.
        topic_id: The topic ID.

    Returns:
        DifficultyRecommendationResponse with recommended difficulty.
    """
    if user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
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


class AgeConfirmRequest(BaseModel):
    date_of_birth: str  # ISO date "YYYY-MM-DD"


def _compute_age(dob_str: str) -> Optional[int]:
    """Return age in years from ISO date string, or None if unparseable."""
    from datetime import date
    try:
        dob = date.fromisoformat(dob_str)
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        return None


@app.post("/users/me/confirm-age", status_code=status.HTTP_200_OK)
async def confirm_age(
    body: AgeConfirmRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: AuthUser = Depends(get_unverified_clerk_user),
    user_repo=Depends(get_user_repository),
):
    """
    Enforce DOB-based age gate:
    - <13: hard block (400); account stays locked
    - 13–17: store DOB, keep age_confirmed=False; parent consent required
    - 18+: store DOB, set age_confirmed=True

    Writes an immutable consent-log entry (M4) in all cases.
    Uses get_unverified_clerk_user so users who haven't confirmed yet can reach this.
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    age = _compute_age(body.date_of_birth)
    if age is None:
        raise HTTPException(status_code=422, detail="Invalid date_of_birth format. Use YYYY-MM-DD.")

    if age < 13:
        # COPPA compliance: write audit log first, then erase all PII.
        _log_consent_event(user.id, "age_blocked_under_13", ip, ua)
        # Hard-delete the UserRecord (contains name, email, DOB, IP from provisioning).
        # ConsentLogRecord is intentionally retained — it has no PII beyond user_id.
        from config import USE_DATABASE as _USE_DB
        if _USE_DB:
            from db_models import UserRecord as _UserRecord
            from db_session import get_session as _get_db
            _db = _get_db()
            try:
                _db.query(_UserRecord).filter(_UserRecord.id == user.id).delete(synchronize_session=False)
                _db.commit()
            except Exception:
                _db.rollback()
                logger.exception("COPPA: failed to delete UserRecord for %s", user.id)
            finally:
                _db.close()
        # Async Clerk account deletion (non-blocking — fires after 400 response is sent).
        if user.clerk_user_id:
            background_tasks.add_task(_delete_clerk_account, user.clerk_user_id)
        raise HTTPException(
            status_code=400,
            detail={"status": "blocked", "reason": "too_young",
                    "message": "You must be 13 or older to use Gradient."},
        )

    # Store DOB temporarily for age calculation, then null it out after confirmation
    user.date_of_birth = body.date_of_birth  # type: ignore[attr-defined]
    if age >= 18:
        user.age_confirmed = True
        user.date_of_birth = None  # DOB no longer needed once confirmed
        user_repo.update_user(user)
        _log_consent_event(user.id, "age_confirmed_adult", ip, ua)
        return {"ok": True, "status": "confirmed", "age_confirmed": True}
    else:
        # 13–17: retain DOB temporarily for parent consent; nulled after parent confirms
        user_repo.update_user(user)
        _log_consent_event(user.id, "age_confirmed_minor_pending_parent", ip, ua)
        return {"ok": True, "status": "minor", "age_confirmed": False, "parent_required": True}


@app.delete("/users/me", status_code=status.HTTP_200_OK)
async def delete_my_account(user: AuthUser = Depends(require_student)):
    """
    SECURITY/PRIVACY (M7): permanently hard-delete the authenticated user's
    account and all associated data — transcripts, progress, credits, parent
    links (both directions), quota/served events, flagged content — and the
    user row itself. This is a real DELETE, not a soft-delete flag.

    The immutable consent_log is intentionally retained (compliance record of
    the age attestation), keyed by user_id; it contains no tutoring content.
    Documented in the privacy policy.
    """
    from config import USE_DATABASE
    if not USE_DATABASE:
        return {"ok": True, "deleted": True, "note": "dev mode (no database)"}

    from db_session import get_session as _get_db
    from db_models import (
        TutorSessionRecord, ProgressRecord, SessionCreditRecord,
        ParentLinkRecord, QuotaEventRecord, FlaggedContentRecord, UserRecord,
        AttemptRecord, ExamAttemptRecord, ClassroomMembershipRecord,
        AssignmentSubmissionRecord, ReferralUsageRecord,
    )
    from sqlalchemy import or_

    db = _get_db()
    try:
        uid = user.id
        db.query(TutorSessionRecord).filter(TutorSessionRecord.user_id == uid).delete(synchronize_session=False)
        db.query(ProgressRecord).filter(ProgressRecord.user_id == uid).delete(synchronize_session=False)
        db.query(SessionCreditRecord).filter(SessionCreditRecord.user_id == uid).delete(synchronize_session=False)
        db.query(QuotaEventRecord).filter(QuotaEventRecord.user_id == uid).delete(synchronize_session=False)
        db.query(FlaggedContentRecord).filter(FlaggedContentRecord.user_id == uid).delete(synchronize_session=False)
        db.query(ParentLinkRecord).filter(
            or_(ParentLinkRecord.student_id == uid, ParentLinkRecord.parent_id == uid)
        ).delete(synchronize_session=False)
        db.query(AttemptRecord).filter(AttemptRecord.user_id == uid).delete(synchronize_session=False)
        db.query(ExamAttemptRecord).filter(ExamAttemptRecord.user_id == uid).delete(synchronize_session=False)
        db.query(ClassroomMembershipRecord).filter(ClassroomMembershipRecord.student_id == uid).delete(synchronize_session=False)
        db.query(AssignmentSubmissionRecord).filter(AssignmentSubmissionRecord.student_id == uid).delete(synchronize_session=False)
        db.query(ReferralUsageRecord).filter(ReferralUsageRecord.referred_user_id == uid).delete(synchronize_session=False)
        db.query(UserRecord).filter(UserRecord.id == uid).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # Delete from Clerk (best-effort, non-blocking)
    if user.clerk_user_id:
        _delete_clerk_account(user.clerk_user_id)

    return {"ok": True, "deleted": True}


def _log_consent_event(user_id: str, event: str, ip: Optional[str], user_agent: Optional[str]) -> None:
    """Write an immutable consent attestation row (M4). Best-effort."""
    from config import USE_DATABASE
    if not USE_DATABASE:
        return
    try:
        from db_models import ConsentLogRecord
        from db_session import get_session as _get_db
        from uuid import uuid4
        db = _get_db()
        try:
            db.add(ConsentLogRecord(
                id=str(uuid4()), user_id=user_id, event=event,
                ip_address=ip, user_agent=(user_agent or "")[:255],
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to write consent log for %s", user_id)


def _delete_clerk_account(clerk_user_id: str) -> None:
    """Best-effort background deletion of a Clerk account. Called after COPPA block."""
    import httpx
    import os as _os
    secret = _os.getenv("CLERK_SECRET_KEY")
    if not secret or not clerk_user_id:
        return
    try:
        resp = httpx.delete(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=10,
        )
        if resp.status_code not in (200, 404):
            logger.warning(
                "Clerk account deletion returned %s for %s", resp.status_code, clerk_user_id
            )
    except Exception:
        logger.exception("Clerk account deletion failed for %s", clerk_user_id)


class GoalRequest(BaseModel):
    goal: str  # 'pass'|'b'|'a'|'mastery'


@app.post("/users/me/goal", status_code=status.HTTP_200_OK)
async def set_learning_goal(
    body: GoalRequest,
    user: AuthUser = Depends(require_student),
    user_repo=Depends(get_user_repository),
):
    """Set the student's learning goal, used to calibrate progress thresholds."""
    valid_goals = {"pass", "b", "a", "mastery"}
    if body.goal not in valid_goals:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid goal '{body.goal}'. Must be one of {sorted(valid_goals)}.",
        )
    user.learning_goal = body.goal
    user_repo.update_user(user)
    return {"ok": True, "learning_goal": body.goal}


# ── Honors toggle ─────────────────────────────────────────────────────────────

# Courses where teacher/parent must enable honors (younger students, foundational)
_HONORS_PERMISSION_REQUIRED_SLUGS = {"algebra-1", "geometry", "algebra-2", "algebra_1", "algebra_2"}


@app.post("/me/honors/{topic_id}/enable", status_code=status.HTTP_200_OK)
async def enable_honors(
    topic_id: str,
    request: Request,
    user: AuthUser = Depends(require_student),
    x_parent_token: Optional[str] = Header(default=None, alias="X-Parent-Token"),
):
    """
    Enable honors mode for a specific topic.

    For Algebra 1, Geometry, and Algebra 2: requires teacher role or X-Parent-Token header.
    For all other courses (Pre-Calc and above): student can self-enable with a disclaimer.

    Returns: {ok: true, honors_enabled: true, disclaimer: str|null}
    """
    from topic_registry import TOPIC_REGISTRY

    topic_meta = TOPIC_REGISTRY.get(topic_id)
    if not topic_meta:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id!r} not found")

    course_slug = topic_meta.course_id.lower().replace(" ", "-")
    requires_permission = any(s in course_slug for s in _HONORS_PERMISSION_REQUIRED_SLUGS)

    if requires_permission:
        # Must be teacher/admin or present a valid parent token
        is_teacher = user.role in ("teacher", "admin")
        has_parent_token = bool(x_parent_token)

        if not is_teacher and not has_parent_token:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Honors mode for this course requires parent or teacher approval. "
                    "Ask a parent or teacher to enable it for you."
                ),
            )
        disclaimer = None
    else:
        disclaimer = (
            "Honors mode activates significantly harder problems. "
            "These are designed for students aiming for advanced placement or competition math."
        )

    return {
        "ok": True,
        "honors_enabled": True,
        "topic_id": topic_id,
        "course": topic_meta.course_name,
        "required_permission": requires_permission,
        "disclaimer": disclaimer,
    }


@app.delete("/me/honors/{topic_id}", status_code=status.HTTP_200_OK)
async def disable_honors(
    topic_id: str,
    user: AuthUser = Depends(require_student),
):
    """Disable honors mode for a topic (always allowed by the student)."""
    return {"ok": True, "honors_enabled": False, "topic_id": topic_id}


@app.get("/me/honors/{topic_id}", status_code=status.HTTP_200_OK)
async def get_honors_status(
    topic_id: str,
    user: AuthUser = Depends(require_student),
):
    """Return honors gating info for a topic without enabling it."""
    from topic_registry import TOPIC_REGISTRY

    topic_meta = TOPIC_REGISTRY.get(topic_id)
    if not topic_meta:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id!r} not found")

    course_slug = topic_meta.course_id.lower().replace(" ", "-")
    requires_permission = any(s in course_slug for s in _HONORS_PERMISSION_REQUIRED_SLUGS)

    return {
        "topic_id": topic_id,
        "course": topic_meta.course_name,
        "requires_permission": requires_permission,
        "permission_reason": (
            "This course is for younger students. A parent or teacher must enable honors mode."
            if requires_permission else None
        ),
    }


@app.post("/hint", response_model=HintResponse)
@limiter.limit("5/minute")
async def generate_hint(
    request: Request,
    body: HintRequest,
    user: AuthUser = Depends(require_student),
    user_repo=Depends(get_user_repository),
):
    """
    Generate a hint for a problem using the configured LLM. Requires authentication.

    Args:
        body: HintRequest with problem context and optional error information.

    Returns:
        HintResponse with the generated hint.

    Raises:
        HTTPException: If hint generation fails.
    """
    _abuse_check(user.id, user.role, user_repo)

    try:
        llm_client = get_cached_llm_client()

        _hint_guidance = [
            "Give a very gentle nudge — help the student identify the relevant concept or formula WITHOUT revealing the method.",
            "Be more specific than hint 1. Point the student toward the right approach or first step, but do NOT show the calculation.",
            "Give the key method or first calculation step. The student should still need to complete the work themselves.",
            "Give a near-complete walkthrough of the method, stopping just before the final numerical answer.",
        ]
        guidance = _hint_guidance[min(body.hint_index, 3)]

        problem_context = (
            f"Hint {body.hint_index + 1} of 4 — {guidance}\n\n"
            f"Problem: {body.problem_latex}"
        )
        if body.current_step_latex:
            problem_context += f"\nStudent's current step: {body.current_step_latex}"
        if body.error_description:
            problem_context += f"\nDescribed error: {body.error_description}"

        hint = await llm_client.generate_hint(problem_context)

        return HintResponse(
            problem_id=body.problem_id,
            hint=hint,
            hint_type="educational",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Hint generation failed")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


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
        logger.exception("Error fetching concept stats for student")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


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
        logger.exception("Error fetching concept stats for teacher")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


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
    """Health check with DB and Redis depth checks."""
    from sqlalchemy import text as _text
    db_ok = False
    try:
        db = get_session()
        db.execute(_text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    from ws_session import _redis_client
    redis_ok = _redis_client is not None

    status = "ok" if (db_ok and redis_ok) else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok}


@app.get("/topics/{topic_id}/lesson")
async def get_topic_lesson(topic_id: str):
    """
    Return a structured JSON lesson for a topic, generating on first request.

    Cache lives in the lesson store (Postgres in prod, data/topic_lessons/
    files in dev — see agents/lesson_store.py).
    Returns the 8-section schema: hook, concept, anatomy, worked_example,
    partial_example, practice_problems, common_mistakes, untested_variants.
    """
    from datetime import datetime, timezone
    from topic_registry import TOPIC_REGISTRY, COURSE_REGISTRY
    from agents.lesson_store import get_lesson, save_lesson

    cached = get_lesson(topic_id)
    if cached is not None:
        return cached

    topic_meta = TOPIC_REGISTRY.get(topic_id)
    if not topic_meta:
        raise HTTPException(status_code=404, detail=f"Topic not found: {topic_id}")

    # Resolve unit_name from COURSE_REGISTRY
    unit_name = topic_meta.unit_name

    from agents.topic_lesson_writer import write_topic_lesson
    try:
        lesson = await write_topic_lesson(
            topic_id=topic_id,
            topic_name=topic_meta.topic_name,
            unit_name=unit_name,
            course_name=topic_meta.course_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lesson generation failed: {exc}")

    result = {
        "topic_id": topic_id,
        "topic_name": topic_meta.topic_name,
        "course_name": topic_meta.course_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **lesson,
    }
    save_lesson(topic_id, result)
    return result


@app.get("/units/{unit_id}/intro")
async def get_unit_intro(unit_id: str):
    """
    Return a structured unit introduction (hook + concept + topic_roadmap).

    Topics are passed to Claude in taxonomy order; Claude writes descriptions only.
    Caches to apps/api/data/unit_intros/{unit_id}.json.
    """
    import json
    from datetime import datetime, timezone
    from config import DATA_DIR
    from topic_registry import COURSE_REGISTRY

    intros_dir = DATA_DIR / "unit_intros"
    intros_dir.mkdir(parents=True, exist_ok=True)
    cache_path = intros_dir / f"{unit_id}.json"

    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except Exception:
            pass

    # Resolve unit from registry
    unit_info = None
    for course_data in COURSE_REGISTRY.values():
        if unit_id in course_data["units"]:
            unit_info = {**course_data["units"][unit_id], "course_name": course_data["course_name"]}
            break

    if not unit_info:
        raise HTTPException(status_code=404, detail=f"Unit not found: {unit_id}")

    # Topics in taxonomy order (dict preserves insertion order in Python 3.7+)
    topics = [
        {"topic_id": t.topic_id, "topic_name": t.topic_name}
        for t in unit_info["topics"].values()
    ]

    from agents.unit_intro_writer import write_unit_intro
    try:
        intro = await write_unit_intro(
            unit_id=unit_id,
            unit_name=unit_info["unit_name"],
            course_name=unit_info["course_name"],
            topics=topics,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Intro generation failed: {exc}")

    result = {
        "unit_id": unit_id,
        "unit_name": unit_info["unit_name"],
        "course_name": unit_info["course_name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **intro,
    }
    cache_path.write_text(json.dumps(result, indent=2))
    return result


# Retired: GET /units/{unit_id}/notes (replaced by /topics/{id}/lesson + /units/{id}/intro)
# Kept as a tombstone returning 410 Gone so old clients get a clear error.
@app.get("/units/{unit_id}/notes")
async def unit_notes_retired(unit_id: str):
    raise HTTPException(
        status_code=410,
        detail="This endpoint has been retired. Use GET /units/{unit_id}/intro and GET /topics/{topic_id}/lesson instead.",
    )


# ============================================================================
# Curriculum Database Endpoints
# ============================================================================


class EducationLevelResponse(BaseModel):
    """Response model for education level."""
    id: str
    name: str
    description: Optional[str]
    display_order: int
    is_active: bool


class CourseResponse(BaseModel):
    """Response model for course."""
    id: str
    name: str
    description: Optional[str]
    education_level_id: str
    display_order: int
    is_active: bool
    code: Optional[str]
    credits: Optional[float]
    prerequisites: list[str] = Field(default_factory=list)


class UnitResponse(BaseModel):
    """Response model for unit."""
    id: str
    name: str
    description: Optional[str]
    course_id: str
    display_order: int
    is_active: bool


class TopicResponse(BaseModel):
    """Response model for topic."""
    id: str
    name: str
    description: Optional[str]
    unit_id: str
    course_id: str
    display_order: int
    is_active: bool
    prerequisites: list[str] = Field(default_factory=list)
    difficulty_min: int
    difficulty_max: int


class ConceptDbResponse(BaseModel):
    """Response model for concept from database."""
    id: str
    name: str
    description: str
    topic_id: str
    unit_id: str
    course_id: str
    kind: str
    difficulty_min: int
    difficulty_max: int
    prerequisites: list[str] = Field(default_factory=list)
    examples_latex: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_active: bool
    version: str


@app.get("/curriculum/education-levels", response_model=list[EducationLevelResponse])
def get_education_levels():
    """
    Get all education levels (High School, College/University, Test Prep).
    
    Returns:
        List of education levels ordered by display_order
    """
    from db_models import EducationLevelRecord
    from db_session import get_session
    
    with get_session() as session:
        records = session.query(EducationLevelRecord).filter_by(is_active=True).order_by(EducationLevelRecord.display_order).all()
        return [
            EducationLevelResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                display_order=r.display_order,
                is_active=r.is_active,
            )
            for r in records
        ]


@app.get("/curriculum/courses", response_model=list[CourseResponse])
def get_courses(
    education_level_id: Optional[str] = Query(None, description="Filter by education level")
):
    """
    Get all courses, optionally filtered by education level.
    
    Query Parameters:
        education_level_id: Optional filter (high_school, college_university, test_prep)
    
    Returns:
        List of courses ordered by education level and display order
    """
    import json
    from db_models import CourseRecord
    from db_session import get_session
    
    with get_session() as session:
        query = session.query(CourseRecord).filter_by(is_active=True)
        
        if education_level_id:
            query = query.filter_by(education_level_id=education_level_id)
        
        records = query.order_by(CourseRecord.education_level_id, CourseRecord.display_order).all()
        
        return [
            CourseResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                education_level_id=r.education_level_id,
                display_order=r.display_order,
                is_active=r.is_active,
                code=r.code,
                credits=r.credits,
                prerequisites=json.loads(r.prerequisites_json) if r.prerequisites_json else [],
            )
            for r in records
        ]


@app.get("/curriculum/courses/{course_id}", response_model=CourseResponse)
def get_course(course_id: str):
    """
    Get a specific course by ID.
    
    Path Parameters:
        course_id: The course ID (e.g., "algebra_1", "calculus_1")
    
    Returns:
        Course details
        
    Raises:
        HTTPException: 404 if course not found
    """
    import json
    from db_models import CourseRecord
    from db_session import get_session
    
    with get_session() as session:
        record = session.query(CourseRecord).filter_by(id=course_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail=f"Course not found: {course_id}")
        
        return CourseResponse(
            id=record.id,
            name=record.name,
            description=record.description,
            education_level_id=record.education_level_id,
            display_order=record.display_order,
            is_active=record.is_active,
            code=record.code,
            credits=record.credits,
            prerequisites=json.loads(record.prerequisites_json) if record.prerequisites_json else [],
        )


@app.get("/curriculum/units", response_model=list[UnitResponse])
def get_units(
    course_id: Optional[str] = Query(None, description="Filter by course ID")
):
    """
    Get all units, optionally filtered by course.
    
    Query Parameters:
        course_id: Optional filter by course
    
    Returns:
        List of units ordered by course and display order
    """
    from db_models import UnitRecord
    from db_session import get_session
    
    with get_session() as session:
        query = session.query(UnitRecord).filter_by(is_active=True)
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        records = query.order_by(UnitRecord.course_id, UnitRecord.display_order).all()
        
        return [
            UnitResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                course_id=r.course_id,
                display_order=r.display_order,
                is_active=r.is_active,
            )
            for r in records
        ]


@app.get("/curriculum/topics", response_model=list[TopicResponse])
def get_curriculum_topics(
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    unit_id: Optional[str] = Query(None, description="Filter by unit ID")
):
    """
    Get all topics from database, optionally filtered by course or unit.
    
    Query Parameters:
        course_id: Optional filter by course
        unit_id: Optional filter by unit
    
    Returns:
        List of topics ordered by unit and display order
    """
    import json
    from db_models import TopicRecord
    from db_session import get_session
    
    with get_session() as session:
        query = session.query(TopicRecord).filter_by(is_active=True)
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        if unit_id:
            query = query.filter_by(unit_id=unit_id)
        
        records = query.order_by(TopicRecord.unit_id, TopicRecord.display_order).all()
        
        return [
            TopicResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                unit_id=r.unit_id,
                course_id=r.course_id,
                display_order=r.display_order,
                is_active=r.is_active,
                prerequisites=json.loads(r.prerequisites_json) if r.prerequisites_json else [],
                difficulty_min=r.difficulty_min,
                difficulty_max=r.difficulty_max,
            )
            for r in records
        ]


@app.get("/curriculum/concepts", response_model=list[ConceptDbResponse])
def get_curriculum_concepts(
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    unit_id: Optional[str] = Query(None, description="Filter by unit ID"),
    topic_id: Optional[str] = Query(None, description="Filter by topic ID")
):
    """
    Get all concepts from database, optionally filtered.
    
    Query Parameters:
        course_id: Optional filter by course
        unit_id: Optional filter by unit
        topic_id: Optional filter by topic
    
    Returns:
        List of concepts
    """
    import json
    from db_models import ConceptRecord
    from db_session import get_session
    
    with get_session() as session:
        query = session.query(ConceptRecord).filter_by(is_active=True)
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        if unit_id:
            query = query.filter_by(unit_id=unit_id)
        if topic_id:
            query = query.filter_by(topic_id=topic_id)
        
        records = query.all()
        
        return [
            ConceptDbResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                topic_id=r.topic_id,
                unit_id=r.unit_id,
                course_id=r.course_id,
                kind=r.kind,
                difficulty_min=r.difficulty_min,
                difficulty_max=r.difficulty_max,
                prerequisites=json.loads(r.prerequisites_json) if r.prerequisites_json else [],
                examples_latex=json.loads(r.examples_latex_json) if r.examples_latex_json else [],
                tags=json.loads(r.tags_json) if r.tags_json else [],
                is_active=r.is_active,
                version=r.version,
            )
            for r in records
        ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

