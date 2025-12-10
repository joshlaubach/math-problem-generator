"""
Repository factory for selecting between JSONL and database backends.

Provides factory functions that select the appropriate repository
implementation based on configuration settings.
"""

from typing import Callable, Optional
from repositories import (
    ProblemRepository,
    AttemptRepository,
    JSONLProblemRepository,
    JSONLAttemptRepository,
    DBProblemRepository,
    DBAttemptRepository,
)
from config import USE_DATABASE, DEFAULT_PROBLEM_JSONL_PATH, DEFAULT_ATTEMPT_JSONL_PATH


def create_problem_repository() -> ProblemRepository:
    """
    Create and return the appropriate problem repository.
    
    Returns JSONLProblemRepository if USE_DATABASE is False,
    otherwise returns DBProblemRepository.
    
    Returns:
        A ProblemRepository instance (JSONL or DB backend)
        
    Raises:
        ValueError: If database backend is requested but DATABASE_URL is not configured
    """
    if USE_DATABASE:
        from db_session import get_session_factory
        return DBProblemRepository(get_session_factory())
    else:
        return JSONLProblemRepository(str(DEFAULT_PROBLEM_JSONL_PATH))


def create_attempt_repository() -> AttemptRepository:
    """
    Create and return the appropriate attempt repository.
    
    Returns JSONLAttemptRepository if USE_DATABASE is False,
    otherwise returns DBAttemptRepository.
    
    Returns:
        An AttemptRepository instance (JSONL or DB backend)
        
    Raises:
        ValueError: If database backend is requested but DATABASE_URL is not configured
    """
    if USE_DATABASE:
        from db_session import get_session_factory
        return DBAttemptRepository(get_session_factory())
    else:
        # Try to get the attempts file path from api module (for testing),
        # fall back to config default
        try:
            import api
            attempts_path = api.ATTEMPTS_FILE
        except (ImportError, AttributeError):
            attempts_path = DEFAULT_ATTEMPT_JSONL_PATH
        return JSONLAttemptRepository(str(attempts_path))


# Cached repository instances to avoid recreating on each call
_problem_repo: Optional[ProblemRepository] = None
_attempt_repo: Optional[AttemptRepository] = None


def get_problem_repository() -> ProblemRepository:
    """
    Get the cached problem repository instance.
    
    Creates the repository on first call, then returns the cached instance
    for subsequent calls to avoid repeated initialization.
    
    Returns:
        The configured ProblemRepository instance
    """
    global _problem_repo
    if _problem_repo is None:
        _problem_repo = create_problem_repository()
    return _problem_repo


def get_attempt_repository() -> AttemptRepository:
    """
    Get the cached attempt repository instance.
    
    Creates the repository on first call, then returns the cached instance
    for subsequent calls to avoid repeated initialization.
    
    Returns:
        The configured AttemptRepository instance
    """
    global _attempt_repo
    if _attempt_repo is None:
        _attempt_repo = create_attempt_repository()
    return _attempt_repo


def reset_repositories() -> None:
    """
    Reset cached repository instances.
    
    Useful for testing when configuration changes or when switching backends.
    After calling this, the next get_*_repository() call will create fresh instances.
    """
    global _problem_repo, _attempt_repo
    _problem_repo = None
    _attempt_repo = None
