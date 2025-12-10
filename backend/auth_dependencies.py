"""
Authentication dependencies and role-based guards for FastAPI.

Provides:
- JWT token verification
- Current user extraction from token
- Role-based access control
- Optional bearer decoding (no implicit allow)
"""

from typing import Optional, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from auth_utils import decode_access_token
from config import JWT_SECRET_KEY, JWT_ALGORITHM, USE_DATABASE
from users_models import User
from users_repository import DBUserRepository, InMemoryUserRepository
from db_session import get_session


# Singleton instance for user repository (persists during tests/app lifetime)
_user_repo_instance: Optional[Union[DBUserRepository, InMemoryUserRepository]] = None


# OAuth2 scheme for token-based authentication
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


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo=Depends(get_user_repository),
) -> User:
    """Extract and verify current user from JWT token."""
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

