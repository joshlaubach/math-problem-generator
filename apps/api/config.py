"""
Configuration and constants for the math problem generator.

Centralizes paths, settings, and configuration values to avoid
hard-coding and enable easy override for testing/deployment.
"""

import os
from pathlib import Path
from typing import Optional

# Load .env file from the same directory as this file (apps/api/.env)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            os.environ.setdefault(_key.strip(), _val.strip())

# ============================================================================
# File Paths
# ============================================================================

# Data directory for JSONL storage
DATA_DIR = Path("data")

# Problem storage
DEFAULT_PROBLEM_JSONL_PATH = DATA_DIR / "problems.jsonl"

# Attempt/tracking storage
DEFAULT_ATTEMPT_JSONL_PATH = DATA_DIR / "attempts.jsonl"

# ============================================================================
# Adaptive Difficulty Settings
# ============================================================================

# Default difficulty for new users
ADAPTIVE_DEFAULT_DIFFICULTY = 2

# Minimum difficulty level
ADAPTIVE_MIN_DIFFICULTY = 1

# Maximum difficulty level
ADAPTIVE_MAX_DIFFICULTY = 6

# Success rate threshold for increasing difficulty (>80%)
ADAPTIVE_SUCCESS_THRESHOLD_INCREASE = 0.80

# Success rate threshold for decreasing difficulty (<60%)
ADAPTIVE_SUCCESS_THRESHOLD_DECREASE = 0.60

# Number of recent attempts to consider for adaptive recommendation
ADAPTIVE_RECENT_ATTEMPTS_WINDOW = 5

# ============================================================================
# Problem Generation Settings
# ============================================================================

# Default calculator mode
DEFAULT_CALCULATOR_MODE = "none"

# ============================================================================
# API Settings
# ============================================================================

# API host and port (default, can be overridden via uvicorn CLI)
API_HOST = "0.0.0.0"
API_PORT = 8000

# ============================================================================
# Database Settings
# ============================================================================

# Database URL for PostgreSQL or other SQL backends
# Example: "postgresql://user:password@localhost/mathgen"
# If None, JSONL storage is used
# Can be set via DATABASE_URL environment variable
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", None)

# Enable database backend (False = use JSONL, True = use database)
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

# ============================================================================
# LLM Settings
# ============================================================================

# Enable LLM integration (False = use DummyLLMClient, True = use real LLM)
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"

# LLM provider: "dummy", "openai", "anthropic"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "dummy")

# OpenAI API key (Phase 12: deprecated; kept for emergency fallback)
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)

# LLM model name (legacy OpenAI)
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4-turbo-preview")

# Anthropic Claude API key
ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", None)

# Claude model for all agents (see ADR-002)
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Clerk secret key (for server-side Clerk API calls)
CLERK_SECRET_KEY: Optional[str] = os.getenv("CLERK_SECRET_KEY", None)

# Clerk frontend API hostname, e.g. "your-instance.clerk.accounts.dev"
# Used to derive JWKS URL for Clerk JWT verification.
CLERK_FRONTEND_API: str = os.getenv("CLERK_FRONTEND_API", "")

# Override JWKS URL directly (takes precedence over CLERK_FRONTEND_API if set)
CLERK_JWKS_URL: str = os.getenv("CLERK_JWKS_URL", "")

# Frontend origin for CORS (Next.js dev default is localhost:3000)
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ============================================================================
# Auth Provider Selection (dual-auth window)
# ============================================================================

# "jwt"   — legacy local JWT (default, keeps existing tests green)
# "clerk" — Clerk-issued JWTs via JWKS (set in production after migration)
AUTH_PROVIDER: str = os.getenv("AUTH_PROVIDER", "jwt")

# LLM API timeout in seconds
LLM_API_TIMEOUT = 30

# Maximum tokens for LLM responses
LLM_MAX_TOKENS = 500

# Per-session output token budget (protects against runaway sessions)
SESSION_TOKEN_BUDGET: int = int(os.getenv("SESSION_TOKEN_BUDGET", "50000"))

# Fallback model after 3 primary failures
ANTHROPIC_FALLBACK_MODEL: str = os.getenv("ANTHROPIC_FALLBACK_MODEL", "claude-haiku-4-5-20251001")

# ============================================================================
# Observability
# ============================================================================

# Sentry DSN — set in production via environment variable; empty = Sentry disabled
SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN", None)

# Deployment environment label surfaced in Sentry issues and structured logs
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

# ============================================================================
# MCP Backends (Phase 3 — verification & visualization routing)
# ============================================================================

# Wolfram|Alpha verification fallback: set WOLFRAM_MCP_URL to speak MCP, or
# just WOLFRAM_APP_ID to use the REST LLM API. Both empty = SymPy-only.
WOLFRAM_APP_ID: Optional[str] = os.getenv("WOLFRAM_APP_ID", None)
WOLFRAM_MCP_URL: Optional[str] = os.getenv("WOLFRAM_MCP_URL", None)

# GeoGebra visualization backend (MCP). Empty = every scene renders locally
# via Mafs — the designed default; the flow never depends on this.
GEOGEBRA_MCP_URL: Optional[str] = os.getenv("GEOGEBRA_MCP_URL", None)

# ============================================================================
# Authentication Settings (Phase 7+)
# ============================================================================

# Teacher API key for protecting teacher-only endpoints
# If None, no authentication is required for teacher endpoints
TEACHER_API_KEY: Optional[str] = os.getenv("TEACHER_API_KEY", None)

# Admin API key for admin-only endpoints
# If None, no authentication is required for admin endpoints
ADMIN_API_KEY: Optional[str] = os.getenv("ADMIN_API_KEY", None)

# ============================================================================
# Admin / Super-User Settings
# ============================================================================

# Emails that automatically receive the maximum tier (classroom-student) with
# unlimited problem generation. Used for developer accounts.
_admin_emails_env = os.getenv("ADMIN_EMAILS", "josh.laubach1@gmail.com")
ADMIN_EMAILS: list[str] = [e.strip() for e in _admin_emails_env.split(",") if e.strip()]

# ============================================================================
# Daily Problem Limit Settings
# ============================================================================

# Problems per day per tier (enforced by /generate endpoint)
DAILY_PROBLEM_LIMITS: dict[str, int] = {
    "free":               5,
    "basic":             30,
    "student":          100,
    "honors":           300,
    "classroom-student": 500,
}

# Lesson notes cache directory
LESSON_NOTES_DIR = DATA_DIR / "lesson_notes"

# ============================================================================
# JWT Authentication Settings (Phase 9)
# ============================================================================

# Secret key for JWT token signing — MUST be set to a strong random value.
# Generate one with: openssl rand -hex 32
_jwt_secret_env = os.getenv("JWT_SECRET_KEY", "")
_INSECURE_JWT_DEFAULT = "dev-secret-key-change-in-production-do-not-use-this"
if not _jwt_secret_env or _jwt_secret_env == _INSECURE_JWT_DEFAULT:
    raise RuntimeError(
        "JWT_SECRET_KEY must be set to a strong random secret. "
        "Generate one with: openssl rand -hex 32"
    )
JWT_SECRET_KEY: str = _jwt_secret_env

# JWT algorithm for token creation
JWT_ALGORITHM: str = "HS256"

# JWT token expiration time in minutes
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)
