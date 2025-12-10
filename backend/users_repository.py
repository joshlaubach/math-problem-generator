"""
User repository for data access abstraction.

Provides Protocol-based interface and SQLAlchemy implementation
for user CRUD operations and queries.
"""

from typing import Optional, Protocol, Sequence
from sqlalchemy.orm import Session

from db_models import UserRecord, LegacyUserLinkRecord, user_record_to_model, user_model_to_record
from users_models import User, LegacyUserLink, UserRole


class UserRepository(Protocol):
    """
    Interface for user data access.

    Defines all operations needed for user management without
    specifying implementation details.
    """

    def create_user(self, user: User) -> None:
        """Create and persist a new user account."""
        ...

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve user by ID, or None if not found."""
        ...

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email address, or None if not found."""
        ...

    def list_users_by_role(self, role: UserRole) -> Sequence[User]:
        """Get all users with a specific role."""
        ...

    def create_legacy_link(self, link: LegacyUserLink) -> None:
        """Create a mapping between old and new user IDs."""
        ...

    def get_legacy_link(self, legacy_user_id: str) -> Optional[LegacyUserLink]:
        """Retrieve legacy link by old user ID."""
        ...

    def get_legacy_link_by_new_user(self, new_user_id: str) -> Optional[LegacyUserLink]:
        """Retrieve legacy link by new user ID."""
        ...


class DBUserRepository:
    """
    SQLAlchemy-based implementation of UserRepository.

    Manages user accounts and legacy user ID mappings using
    the database as persistent storage.
    """

    def __init__(self, get_session):
        """
        Initialize repository with session factory.

        Args:
            get_session: Callable that returns a SQLAlchemy Session
        """
        self._get_session = get_session

    def create_user(self, user: User) -> None:
        """Create and persist a new user account."""
        session: Session = self._get_session()
        try:
            record = user_model_to_record(user)
            session.add(record)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve user by ID, or None if not found."""
        session: Session = self._get_session()
        try:
            record = session.query(UserRecord).filter(UserRecord.id == user_id).first()
            if record is None:
                return None
            return user_record_to_model(record)
        finally:
            session.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email address, or None if not found."""
        session: Session = self._get_session()
        try:
            record = session.query(UserRecord).filter(UserRecord.email == email).first()
            if record is None:
                return None
            return user_record_to_model(record)
        finally:
            session.close()

    def list_users_by_role(self, role: UserRole) -> Sequence[User]:
        """Get all users with a specific role."""
        session: Session = self._get_session()
        try:
            records = (
                session.query(UserRecord)
                .filter(UserRecord.role == role)
                .order_by(UserRecord.created_at.desc())
                .all()
            )
            return [user_record_to_model(record) for record in records]
        finally:
            session.close()

    def create_legacy_link(self, link: LegacyUserLink) -> None:
        """Create a mapping between old and new user IDs."""
        session: Session = self._get_session()
        try:
            record = LegacyUserLinkRecord(
                legacy_user_id=link.legacy_user_id,
                new_user_id=link.new_user_id,
                linked_at=link.linked_at,
            )
            session.add(record)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_legacy_link(self, legacy_user_id: str) -> Optional[LegacyUserLink]:
        """Retrieve legacy link by old user ID."""
        session: Session = self._get_session()
        try:
            record = (
                session.query(LegacyUserLinkRecord)
                .filter(LegacyUserLinkRecord.legacy_user_id == legacy_user_id)
                .first()
            )
            if record is None:
                return None
            return LegacyUserLink(
                legacy_user_id=record.legacy_user_id,
                new_user_id=record.new_user_id,
                linked_at=record.linked_at,
            )
        finally:
            session.close()

    def get_legacy_link_by_new_user(self, new_user_id: str) -> Optional[LegacyUserLink]:
        """Retrieve legacy link by new user ID."""
        session: Session = self._get_session()
        try:
            record = (
                session.query(LegacyUserLinkRecord)
                .filter(LegacyUserLinkRecord.new_user_id == new_user_id)
                .first()
            )
            if record is None:
                return None
            return LegacyUserLink(
                legacy_user_id=record.legacy_user_id,
                new_user_id=record.new_user_id,
                linked_at=record.linked_at,
            )
        finally:
            session.close()


class InMemoryUserRepository:
    """
    In-memory implementation of UserRepository for testing.

    Stores users in dictionaries (not persistent).
    Useful when DATABASE_URL is not configured.
    """

    def __init__(self):
        """Initialize empty user and link stores."""
        self._users: dict[str, User] = {}
        self._legacy_links: dict[str, LegacyUserLink] = {}

    def create_user(self, user: User) -> None:
        """Create and store a new user in memory."""
        if user.id in self._users:
            raise ValueError(f"User with ID {user.id} already exists")
        self._users[user.id] = user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve user by ID from memory."""
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email from memory."""
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def list_users_by_role(self, role: UserRole) -> Sequence[User]:
        """Get all users with a specific role from memory."""
        return [u for u in self._users.values() if u.role == role]

    def create_legacy_link(self, link: LegacyUserLink) -> None:
        """Create a legacy link mapping in memory."""
        if link.legacy_user_id in self._legacy_links:
            raise ValueError(f"Legacy link for {link.legacy_user_id} already exists")
        self._legacy_links[link.legacy_user_id] = link

    def get_legacy_link(self, legacy_user_id: str) -> Optional[LegacyUserLink]:
        """Retrieve legacy link by old user ID from memory."""
        return self._legacy_links.get(legacy_user_id)

    def get_legacy_link_by_new_user(self, new_user_id: str) -> Optional[LegacyUserLink]:
        """Retrieve legacy link by new user ID from memory."""
        for link in self._legacy_links.values():
            if link.new_user_id == new_user_id:
                return link
        return None

