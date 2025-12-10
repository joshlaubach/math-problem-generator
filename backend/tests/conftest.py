"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path
import pytest

# Add parent directory to path so tests can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))


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
        # Also clear the API module path if different
        try:
            import api
            Path(api.ATTEMPTS_FILE).unlink(missing_ok=True)
        except Exception:
            pass
    except Exception:
        pass

    return TestClient(app)
