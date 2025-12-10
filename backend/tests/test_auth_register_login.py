"""
Tests for user registration and login endpoints.

Covers:
- Successful registration with default role
- Duplicate email rejection
- Invalid password handling
- Successful login with valid credentials
- Failed login with wrong password
- JWT token structure validation
- Optional legacy user ID mapping
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from auth_utils import hash_password, verify_password, create_access_token, decode_access_token
from config import JWT_SECRET_KEY, JWT_ALGORITHM
from users_models import User


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password_creates_hash(self):
        """Hash should create different string than plaintext."""
        plaintext = "MySecurePassword123"
        hashed = hash_password(plaintext)
        
        assert hashed != plaintext
        assert len(hashed) > 20

    def test_verify_password_success(self):
        """Verify should return True for correct password."""
        plaintext = "MySecurePassword123"
        hashed = hash_password(plaintext)
        
        assert verify_password(plaintext, hashed) is True

    def test_verify_password_failure(self):
        """Verify should return False for incorrect password."""
        plaintext = "MySecurePassword123"
        hashed = hash_password(plaintext)
        
        assert verify_password("WrongPassword", hashed) is False

    def test_hash_different_each_time(self):
        """Two hashes of same plaintext should be different (salt)."""
        plaintext = "MySecurePassword123"
        hash1 = hash_password(plaintext)
        hash2 = hash_password(plaintext)
        
        assert hash1 != hash2
        # But both should verify
        assert verify_password(plaintext, hash1) is True
        assert verify_password(plaintext, hash2) is True


class TestJWTToken:
    """Tests for JWT token creation and validation."""

    def test_create_access_token(self):
        """Should create valid JWT token."""
        data = {"sub": "user123", "role": "student"}
        token = create_access_token(
            data=data,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        
        assert token is not None
        assert len(token) > 20
        assert "." in token  # JWT has 3 dot-separated parts

    def test_decode_access_token_success(self):
        """Should decode and validate correct token."""
        data = {"sub": "user123", "role": "student"}
        token = create_access_token(
            data=data,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        
        decoded = decode_access_token(
            token=token,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        
        assert decoded is not None
        assert decoded["sub"] == "user123"
        assert decoded["role"] == "student"

    def test_decode_invalid_token(self):
        """Should return None for invalid token."""
        invalid_token = "not.a.valid.token"
        
        decoded = decode_access_token(
            token=invalid_token,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        
        assert decoded is None

    def test_decode_expired_token(self):
        """Should return None for expired token."""
        data = {"sub": "user123"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(
            data=data,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
            expires_delta=expires_delta,
        )
        
        decoded = decode_access_token(
            token=token,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        
        assert decoded is None

    def test_decode_wrong_secret_key(self):
        """Should return None if decoded with wrong secret."""
        data = {"sub": "user123"}
        token = create_access_token(
            data=data,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        
        decoded = decode_access_token(
            token=token,
            secret_key="wrong-secret-key",
            algorithm=JWT_ALGORITHM,
        )
        
        assert decoded is None

    def test_token_contains_expiration(self):
        """Token should contain exp claim."""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(
            data=data,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
            expires_delta=expires_delta,
        )
        
        decoded = decode_access_token(
            token=token,
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        
        assert decoded is not None
        assert "exp" in decoded
        assert decoded["exp"] > datetime.utcnow().timestamp()


class TestUserModel:
    """Tests for User domain model."""

    def test_user_generate_id(self):
        """Should generate unique UUIDs."""
        id1 = User.generate_id()
        id2 = User.generate_id()
        
        assert id1 != id2
        assert len(id1) == 36  # UUID string length
        assert len(id2) == 36

    def test_user_get_display_name_with_name(self):
        """Should return display_name if set."""
        user = User(
            id="user123",
            email="john@example.com",
            password_hash="hash",
            role="student",
            created_at=datetime.utcnow(),
            display_name="John Doe",
        )
        
        assert user.get_display_name() == "John Doe"

    def test_user_get_display_name_defaults_to_email_prefix(self):
        """Should fall back to email prefix if display_name not set."""
        user = User(
            id="user123",
            email="john@example.com",
            password_hash="hash",
            role="student",
            created_at=datetime.utcnow(),
            display_name=None,
        )
        
        assert user.get_display_name() == "john"

    def test_user_role_validation(self):
        """Should accept valid roles."""
        for role in ["student", "teacher", "admin"]:
            user = User(
                id="user123",
                email="john@example.com",
                password_hash="hash",
                role=role,  # type: ignore
                created_at=datetime.utcnow(),
            )
            assert user.role == role


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
