"""
Database session management and initialization.

Provides session factory, engine creation, and database initialization helpers.
"""

from typing import Callable, Generator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from config import DATABASE_URL


def create_db_engine() -> Engine:
    """
    Create and return the SQLAlchemy engine.
    
    Uses DATABASE_URL from config. For production, ensure:
    - Connection pooling is configured
    - Echo is False
    - Future=True for SQLAlchemy 2.0 compatibility
    
    Returns:
        SQLAlchemy Engine instance
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set to use database-backed repositories")
    
    return create_engine(
        DATABASE_URL,
        future=True,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before using
    )


# Lazy engine initialization
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Get or create the shared database engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def create_session_factory(engine: Optional[Engine] = None) -> Callable[[], Session]:
    """
    Create a session factory function.
    
    Args:
        engine: Optional SQLAlchemy Engine. If None, uses get_engine().
    
    Returns:
        A callable that returns a new Session when called.
    """
    if engine is None:
        engine = get_engine()
    
    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )
    
    return lambda: session_factory()


# Default session factory
_session_factory: Optional[Callable[[], Session]] = None


def get_session_factory() -> Callable[[], Session]:
    """Get the default session factory, creating if needed."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory()
    return _session_factory


def get_session() -> Session:
    """
    Get a new database session.
    
    Convenience function using the default session factory.
    
    Returns:
        A new SQLAlchemy Session instance
    """
    return get_session_factory()()


def session_context() -> Generator[Session, None, None]:
    """
    Context manager for automatic session cleanup.
    
    Usage:
        with session_context() as session:
            # Use session
            pass
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Optional[Engine] = None) -> None:
    """
    Initialize all tables in the database.
    
    Creates tables based on ORM models if they don't exist.
    Safe to call multiple times.
    
    Args:
        engine: Optional SQLAlchemy Engine. If None, uses get_engine().
    """
    if engine is None:
        engine = get_engine()
    
    from db_models import Base
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine: Optional[Engine] = None) -> None:
    """
    Drop all tables from the database.
    
    WARNING: This is destructive! Only use in development/testing.
    
    Args:
        engine: Optional SQLAlchemy Engine. If None, uses get_engine().
    """
    if engine is None:
        engine = get_engine()
    
    from db_models import Base
    Base.metadata.drop_all(bind=engine)
