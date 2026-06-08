"""
Pytest configuration and shared fixtures.
"""

import os
import sys
from pathlib import Path
import pytest

# Must be set before config.py is imported (which happens when test files are collected).
# Force these for test isolation — override whatever is in .env
os.environ["AUTH_PROVIDER"] = "jwt"
os.environ["USE_DATABASE"] = "false"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-not-for-production")

# Add parent directory to path so tests can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True, scope="function")
def reset_rate_limiter():
    """Reset rate limiter and abuse guard before each test to prevent 429 cross-test bleed."""
    try:
        from abuse_guard import reset_for_testing
        from api import limiter
        reset_for_testing()
        limiter._storage.reset()
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True, scope="function")
def reset_user_repo():
    """Reset the in-memory user repository before each test function."""
    import auth_dependencies

    # Reset the singleton before each test
    auth_dependencies._user_repo_instance = None
    yield
    # Cleanup after test
    auth_dependencies._user_repo_instance = None


@pytest.fixture(scope="function")
def client(reset_user_repo):
    """FastAPI test client with fresh user repo per test."""
    from fastapi.testclient import TestClient
    from api import app
    # Reset attempts storage for each test client

    # Reset cached repositories and attempts file for isolation
    try:
        import repo_factory
        repo_factory.reset_repositories()
    except Exception:
        pass

    from pathlib import Path
    from config import DEFAULT_ATTEMPT_JSONL_PATH
    try:
        Path(DEFAULT_ATTEMPT_JSONL_PATH).unlink(missing_ok=True)
        Path("data/attempts.jsonl").unlink(missing_ok=True)
        try:
            import api
            Path(api.ATTEMPTS_FILE).unlink(missing_ok=True)
        except Exception:
            pass
    except Exception:
        pass

    try:
        from abuse_guard import reset_for_testing
        from api import limiter
        reset_for_testing()
        limiter._storage.reset()
    except Exception:
        pass

    return TestClient(app)


def _make_default_student():
    """Return a default student user for tests that require auth."""
    from datetime import datetime
    from users_models import User
    return User(
        id="test-student-default",
        email="student@test.com",
        password_hash="",
        role="student",
        created_at=datetime.utcnow(),
        is_active=True,
        tier="classroom-student",
    )


@pytest.fixture(scope="function")
def auth_client(reset_user_repo):
    """
    FastAPI test client with require_student dependency overridden.

    Use this for tests that call endpoints requiring authentication
    (e.g. /generate, /attempt, /hint after the security hardening phase).
    """
    from fastapi.testclient import TestClient
    from api import app
    from auth_dependencies import require_student, get_user_repository
    from abuse_guard import reset_for_testing
    from api import limiter

    try:
        import repo_factory
        repo_factory.reset_repositories()
    except Exception:
        pass

    from pathlib import Path
    from config import DEFAULT_ATTEMPT_JSONL_PATH
    try:
        Path(DEFAULT_ATTEMPT_JSONL_PATH).unlink(missing_ok=True)
    except Exception:
        pass

    reset_for_testing()
    limiter._storage.reset()
    app.dependency_overrides[require_student] = _make_default_student
    yield TestClient(app)
    app.dependency_overrides.pop(require_student, None)
