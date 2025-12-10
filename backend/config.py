"""
Configuration and constants for the math problem generator.

Centralizes paths, settings, and configuration values to avoid
hard-coding and enable easy override for testing/deployment.
"""

from pathlib import Path

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
import os
DATABASE_URL: str | None = os.getenv("DATABASE_URL", None)

# Enable database backend (False = use JSONL, True = use database)
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

# ============================================================================
# LLM Settings
# ============================================================================

# Enable LLM integration (False = use DummyLLMClient, True = use real LLM)
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"

# LLM provider: "dummy", "openai", etc.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "dummy")

# OpenAI API key (for OpenAI provider)
# Must be set in environment if LLM_PROVIDER == "openai"
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY", None)

# LLM model name
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4-turbo-preview")

# LLM API timeout in seconds
LLM_API_TIMEOUT = 30

# Maximum tokens for LLM responses
LLM_MAX_TOKENS = 500

# ============================================================================
# Authentication Settings (Phase 7+)
# ============================================================================

# Teacher API key for protecting teacher-only endpoints
# If None, no authentication is required for teacher endpoints
TEACHER_API_KEY: str | None = os.getenv("TEACHER_API_KEY", None)

# Admin API key for admin-only endpoints
# If None, no authentication is required for admin endpoints
ADMIN_API_KEY: str | None = os.getenv("ADMIN_API_KEY", None)

# ============================================================================
# JWT Authentication Settings (Phase 9)
# ============================================================================

# Secret key for JWT token signing
# IMPORTANT: Set this in production to a strong random value
# Example: openssl rand -hex 32
JWT_SECRET_KEY: str = os.getenv(
    "JWT_SECRET_KEY",
    "dev-secret-key-change-in-production-do-not-use-this"
)

# JWT algorithm for token creation
JWT_ALGORITHM: str = "HS256"

# JWT token expiration time in minutes
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)
