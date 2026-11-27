"""Alembic migration environment for NEXORA (MySQL 8.0.16+ enforced)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.mysql_compat import ensure_mysql_min_version
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """Resolve URL from explicit Alembic `-x db_url=...`, programmatic config, or Settings."""
    x_args = context.get_x_argument(as_dictionary=True)
    if x_args.get("db_url"):
        return str(x_args["db_url"])
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url
    return settings.sqlalchemy_database_uri


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode targeting MySQL dialect."""
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode after verifying MySQL >= 8.0.16 compatibility."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _resolve_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        ensure_mysql_min_version(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
