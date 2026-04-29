"""
Authentication utilities including password hashing and JWT token generation.

Uses passlib for secure password hashing with pbkdf2_sha256 algorithm.
Uses python-jose for JWT token handling.
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Dict

from passlib.context import CryptContext
from jose import JWTError, jwt

# Password hashing context using PBKDF2-SHA256
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(plaintext_password: str) -> str:
    """
    Hash a plaintext password using bcrypt with salt.

    Args:
        plaintext_password: The raw password from user input

    Returns:
        Salted + hashed password string (safe to store in database)
    """
    return pwd_context.hash(plaintext_password)


def verify_password(plaintext_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Args:
        plaintext_password: Raw password from login attempt
        hashed_password: Stored hash from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plaintext_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload to encode in token (typically {"sub": user_id, "role": role})
        secret_key: Secret key for signing (from config)
        algorithm: JWT algorithm (default: HS256)
        expires_delta: Token expiration time (default: 60 minutes)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=60)

    # JWT libraries prefer numeric (POSIX) timestamps for exp
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT token to decode
        secret_key: Secret key for validation
        algorithm: JWT algorithm (must match creation)

    Returns:
        Decoded payload dict if valid, None if expired or invalid
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        return None

    # Enforce expiration manually to be explicit
    exp = payload.get("exp")
    if exp is not None:
        now_ts = int(datetime.utcnow().timestamp())
        if now_ts >= int(exp):
            return None

    return payload
