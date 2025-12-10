"""
Authentication routes for user registration and login.

Provides endpoints for:
- User registration (POST /auth/register)
- User login (POST /auth/login)
- Token-based authentication for subsequent API calls
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field

from auth_utils import hash_password, verify_password, create_access_token
from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from users_models import User, UserRole
from auth_dependencies import get_user_repository
from users_repository import UserRepository

# Create router for auth endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================


class UserRegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=8, description="Password (minimum 8 characters)"
    )
    role: UserRole = Field(
        default="student", description="User role (student or teacher)"
    )
    display_name: Optional[str] = Field(
        default=None, description="Optional display name"
    )
    legacy_user_id: Optional[str] = Field(
        default=None, description="Optional old anonymous user ID for data migration"
    )


class UserLoginRequest(BaseModel):
    """Request model for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class AuthTokenResponse(BaseModel):
    """Response model for successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: str = Field(..., description="Authenticated user ID")
    role: UserRole = Field(..., description="User's role")
    email: str = Field(..., description="User's email")
    display_name: Optional[str] = Field(
        default=None, description="User's display name"
    )


class AuthErrorResponse(BaseModel):
    """Response model for authentication errors."""

    detail: str = Field(..., description="Error message")


# ============================================================================
# Auth Endpoints
# ============================================================================


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": AuthErrorResponse, "description": "Email already exists"},
        422: {"description": "Invalid input"},
    },
)
async def register(
    request: UserRegisterRequest,
    user_repo = Depends(get_user_repository),
) -> AuthTokenResponse:
    """
    Register a new user account.

    Creates a new user account with email/password authentication.
    Returns a JWT token for immediate use.

    Args:
        request: Registration request with email, password, and optional role
        user_repo: User repository dependency

    Returns:
        AuthTokenResponse with JWT token and user info

    Raises:
        HTTPException 400: If email already registered
        HTTPException 422: If invalid input
    """
    # Check if email already exists
    existing_user = user_repo.get_user_by_email(request.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        id=User.generate_id(),
        email=request.email,
        password_hash=hash_password(request.password),
        role=request.role,
        created_at=datetime.utcnow(),
        display_name=request.display_name,
        is_active=True,
    )

    # Persist user
    try:
        user_repo.create_user(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # Link legacy user ID if provided
    if request.legacy_user_id:
        try:
            legacy_link = LegacyUserLink.create(
                request.legacy_user_id, user.id
            )
            user_repo.create_legacy_link(legacy_link)
        except Exception:
            # Log but don't fail registration if legacy linking fails
            pass

    # Generate JWT token
    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role},
        secret_key=JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
        expires_delta=access_token_expires,
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role,
        email=user.email,
        display_name=user.display_name,
    )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    responses={
        401: {"model": AuthErrorResponse, "description": "Invalid credentials"},
        404: {"model": AuthErrorResponse, "description": "User not found"},
    },
)
async def login(
    request: UserLoginRequest,
    user_repo = Depends(get_user_repository),
) -> AuthTokenResponse:
    """
    Authenticate a user and return JWT token.

    Verifies email and password, then returns JWT token for API access.

    Args:
        request: Login request with email and password
        user_repo: User repository dependency

    Returns:
        AuthTokenResponse with JWT token and user info

    Raises:
        HTTPException 404: If user not found
        HTTPException 401: If password incorrect
    """
    # Find user by email
    user = user_repo.get_user_by_email(request.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    # Generate JWT token
    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role},
        secret_key=JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
        expires_delta=access_token_expires,
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role,
        email=user.email,
        display_name=user.display_name,
    )


# Import at end to avoid circular imports
from datetime import datetime
from users_models import LegacyUserLink
