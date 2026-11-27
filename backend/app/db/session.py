"""Lazy SQLAlchemy 2.x engine and session lifecycle management."""

from contextlib import contextmanager
from typing import Generator, Optional, Union

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def get_engine(database_url: Optional[Union[str, URL]] = None) -> Engine:
    """Return the cached SQLAlchemy Engine, creating it lazily on first database use."""
    global _engine
    if database_url is not None:
        return create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            echo=settings.DB_ECHO,
            future=True,
        )

    if _engine is None:
        _engine = create_engine(
            settings.get_database_url(),
            pool_pre_ping=True,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            echo=settings.DB_ECHO,
            future=True,
        )
    return _engine


def get_session_factory(database_url: Optional[Union[str, URL]] = None) -> sessionmaker[Session]:
    """Return a configured SQLAlchemy 2.x sessionmaker without opening a DB connection."""
    global _SessionLocal
    if database_url is not None:
        engine = get_engine(database_url)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped Session and closing it cleanly after use."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope(
    database_url: Optional[Union[str, URL]] = None,
) -> Generator[Session, None, None]:
    """Transactional context manager committing on success and rolling back on error."""
    session = get_session_factory(database_url)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose and clear cached engine/sessionmaker state (used in tests/shutdown)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
