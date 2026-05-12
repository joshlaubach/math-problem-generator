"""
Authentication dependencies and role-based guards for FastAPI.

Supports two auth providers (controlled by AUTH_PROVIDER env var):
  "jwt"   — legacy local JWT (default; keeps existing tests green)
  "clerk" — Clerk-issued JWTs via JWKS (production path)

The public interface — get_current_user, optional_current_user,
require_student, require_teacher, require_admin — is identical for both
providers so no call sites need to change.
"""

from typing import Optional, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from auth_utils import decode_access_token
from config import JWT_SECRET_KEY, JWT_ALGORITHM, USE_DATABASE
from users_models import User
from users_repository import DBUserRepository, InMemoryUserRepository
from db_session import get_session


_user_repo_instance: Optional[Union[DBUserRepository, InMemoryUserRepository]] = None

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scopes={
        "student": "Student access",
        "teacher": "Teacher access",
        "admin": "Admin access",
    },
)


def get_user_repository():
    """Get the user repository dependency (DB if available, otherwise in-memory)."""
    global _user_repo_instance
    if _user_repo_instance is None:
        if USE_DATABASE:
            try:
                _user_repo_instance = DBUserRepository(get_session)
            except ValueError:
                _user_repo_instance = InMemoryUserRepository()
        else:
            _user_repo_instance = InMemoryUserRepository()
    return _user_repo_instance


# ---------------------------------------------------------------------------
# Primary dependency — used everywhere via Depends(get_current_user)
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo=Depends(get_user_repository),
) -> User:
    """Extract and verify current user from JWT or Clerk token."""
    import config  # runtime check so AUTH_PROVIDER env changes take effect without restart
    if config.AUTH_PROVIDER == "clerk":
        return await _get_current_user_clerk(token, user_repo, require_age=True)
    return await _get_current_user_jwt(token, user_repo)


async def get_unverified_clerk_user(
    token: str = Depends(oauth2_scheme),
    user_repo=Depends(get_user_repository),
) -> User:
    """
    Clerk-mode only: verify token and provision user but skip age_confirmed check.

    Used exclusively on the /users/me/confirm-age endpoint so a freshly
    signed-up user can complete onboarding without hitting a 403 loop.
    Falls back to JWT verification when AUTH_PROVIDER != "clerk".
    """
    import config
    if config.AUTH_PROVIDER == "clerk":
        # Skip both age and email-verified checks — this endpoint is reached
        # during onboarding before either confirmation can be complete.
        return await _get_current_user_clerk(token, user_repo, require_age=False, require_email_verified=False)
    return await _get_current_user_jwt(token, user_repo)


# ---------------------------------------------------------------------------
# JWT path (unchanged from legacy implementation)
# ---------------------------------------------------------------------------

async def _get_current_user_jwt(token: str, user_repo) -> User:
    payload = decode_access_token(token, secret_key=JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_repo.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


# ---------------------------------------------------------------------------
# Clerk path
# ---------------------------------------------------------------------------

async def _get_current_user_clerk(token: str, user_repo, *, require_age: bool, require_email_verified: bool = True) -> User:
    from clerk_auth import verify_clerk_token, fetch_clerk_user_email

    payload = verify_clerk_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Clerk token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clerk_user_id: Optional[str] = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # email_verified absent → Clerk enforced verification at login; only block if explicitly False.
    if require_email_verified and payload.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email address before continuing.",
        )

    user = user_repo.get_user_by_clerk_id(clerk_user_id)
    if user is None:
        user = _provision_clerk_user(clerk_user_id, user_repo, fetch_clerk_user_email)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    if require_age and not user.age_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Age verification required. Please complete onboarding.",
        )

    return user


def _provision_clerk_user(clerk_user_id: str, user_repo, fetch_email_fn) -> User:
    """Create a new User from Clerk user ID (just-in-time provisioning)."""
    from datetime import datetime
    from config import ADMIN_EMAILS

    email = fetch_email_fn(clerk_user_id) or f"{clerk_user_id}@clerk.users"
    is_admin = email in ADMIN_EMAILS
    user = User(
        id=User.generate_id(),
        email=email,
        password_hash="",
        role="admin" if is_admin else "student",
        created_at=datetime.utcnow(),
        clerk_user_id=clerk_user_id,
        age_confirmed=True if is_admin else False,
        tier="classroom-student" if is_admin else "free",
        is_active=True,
    )
    user_repo.create_user(user)
    return user


# ---------------------------------------------------------------------------
# Optional auth (for endpoints that work with or without auth)
# ---------------------------------------------------------------------------

async def optional_current_user(
    request: Request,
    user_repo=Depends(get_user_repository),
) -> Optional[User]:
    """Return User if a valid bearer token is provided, else None.

    Missing header -> None
    Present but invalid/expired/malformed -> 401
    Present and valid -> User
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    scheme, token = auth_header.split(" ", 1) if " " in auth_header else (None, None)
    if scheme is None or scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    import config
    if config.AUTH_PROVIDER == "clerk":
        try:
            return await _get_current_user_clerk(token, user_repo, require_age=True)
        except HTTPException:
            raise

    payload = decode_access_token(token, secret_key=JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_repo.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


# ---------------------------------------------------------------------------
# Role guards (unchanged — work for both providers)
# ---------------------------------------------------------------------------

async def require_student(user: Optional[User] = Depends(optional_current_user)) -> User:
    """Require a student (or higher) role; 403 if missing/invalid auth."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role not in ("student", "teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have student access",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


async def require_teacher(user: User = Depends(get_current_user)) -> User:
    """Require teacher or admin role."""
    if user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
