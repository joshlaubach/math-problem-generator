"""
User models and role definitions for authentication system.

Supports role-based access control with three roles:
- "student": Regular user solving problems
- "teacher": Can create assignments and view analytics
- "admin": Full system access

All IDs are UUIDs for consistency with existing system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

# User roles in the system
UserRole = Literal["student", "teacher", "admin"]


@dataclass
class User:
    """
    Domain model for system users.

    Attributes:
        id: Unique user identifier (UUID string)
        email: User's email address (unique)
        password_hash: Salted + hashed password (not the plaintext password)
        role: User's role for access control (student, teacher, or admin)
        created_at: Account creation timestamp
        display_name: Optional user display name (defaults to email prefix)
        is_active: Whether account is active (defaults to True)
    """

    id: str
    email: str
    password_hash: str
    role: UserRole
    created_at: datetime
    display_name: Optional[str] = None
    is_active: bool = True

    @staticmethod
    def generate_id() -> str:
        """Generate a new user ID."""
        return str(uuid4())

    def get_display_name(self) -> str:
        """Get display name, falling back to email prefix if not set."""
        if self.display_name:
            return self.display_name
        return self.email.split("@")[0]


@dataclass
class LegacyUserLink:
    """
    Maps old anonymous user IDs to new authenticated user accounts.

    Used for backward compatibility when users with existing anonymous history
    create accounts. Allows migration of past attempts and data.

    Attributes:
        legacy_user_id: Old UUID-based user ID from localStorage
        new_user_id: New authenticated user account ID
        linked_at: When the link was created
    """

    legacy_user_id: str
    new_user_id: str
    linked_at: datetime

    @staticmethod
    def create(legacy_user_id: str, new_user_id: str) -> "LegacyUserLink":
        """Create a new legacy user link."""
        return LegacyUserLink(
            legacy_user_id=legacy_user_id,
            new_user_id=new_user_id,
            linked_at=datetime.utcnow(),
        )
