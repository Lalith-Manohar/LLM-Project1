"""Database package exposing lazy SQLAlchemy engine/session helpers and Declarative Base."""

from app.db.base import Base
from app.db.mysql_compat import MIN_MYSQL_VERSION, ensure_mysql_min_version, parse_mysql_version
from app.db.session import get_db, get_engine, get_session_factory, reset_engine, session_scope

__all__ = [
    "Base",
    "MIN_MYSQL_VERSION",
    "ensure_mysql_min_version",
    "get_db",
    "get_engine",
    "get_session_factory",
    "parse_mysql_version",
    "reset_engine",
    "session_scope",
]
