"""MySQL 8.0.16+ compatibility checks for enforced CHECKs and VIRTUAL generated columns."""

import re
from typing import Any, Tuple

from sqlalchemy import text

# MySQL 8.0.0-8.0.15 parse CHECK syntax but silently ignore CHECK enforcement.
MIN_MYSQL_VERSION: Tuple[int, int, int] = (8, 0, 16)
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def parse_mysql_version(version_string: str) -> Tuple[int, int, int]:
    """Parse a MySQL SELECT VERSION() string into a semantic (major, minor, patch) tuple."""
    if not version_string or not isinstance(version_string, str):
        raise ValueError("Empty MySQL version string received.")

    lowered = version_string.lower()
    if "mariadb" in lowered:
        raise RuntimeError(
            f"Unsupported database engine '{version_string}': NEXORA requires MySQL >= 8.0.16 "
            "for InnoDB enforced CHECK constraints and VIRTUAL generated column indexes."
        )

    match = _VERSION_RE.match(version_string.strip())
    if not match:
        raise ValueError(f"Could not parse MySQL version string: '{version_string}'.")

    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def ensure_mysql_min_version(connection: Any) -> Tuple[int, int, int]:
    """Verify the target connection runs MySQL >= 8.0.16 before executing DDL migrations."""
    dialect_name = getattr(getattr(connection, "dialect", None), "name", "")
    if dialect_name != "mysql":
        raise RuntimeError(
            f"Unsupported SQL dialect '{dialect_name}': NEXORA migrations target MySQL >= 8.0.16 only."
        )

    raw_version = connection.execute(text("SELECT VERSION()")).scalar_one()
    parsed = parse_mysql_version(str(raw_version))
    if parsed < MIN_MYSQL_VERSION:
        raise RuntimeError(
            f"MySQL version {parsed[0]}.{parsed[1]}.{parsed[2]} is below the required minimum "
            f"{MIN_MYSQL_VERSION[0]}.{MIN_MYSQL_VERSION[1]}.{MIN_MYSQL_VERSION[2]} "
            "(required for enforced CHECK constraints, VIRTUAL generated columns, and DATETIME(6))."
        )
    return parsed
