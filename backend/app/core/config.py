"""Core configuration module for NEXORA backend."""

import os
from pathlib import Path
from typing import Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    PROJECT_NAME: str = "NEXORA Retail Management & Intelligence System"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Union[bool, str, int]) -> bool:
        """Coerce common string values (e.g. 'release', 'prod', 'debug') into a boolean."""
        if isinstance(v, str):
            val = v.strip().lower()
            if val in ("true", "1", "yes", "debug", "dev", "development"):
                return True
            if val in ("false", "0", "no", "release", "prod", "production"):
                return False
        return bool(v)

    # MySQL Database Settings (populated from environment variables; no live connection at import time)
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "nexora_db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 1800

    # Explicit integration test database URL (never falls back silently to DB_NAME)
    TEST_DATABASE_URL: Optional[str] = None

    def get_database_url(self) -> URL:
        """Build a PyMySQL utf8mb4 connection URL safely without exposing credentials in logs."""
        return URL.create(
            drivername="mysql+pymysql",
            username=self.DB_USER,
            password=self.DB_PASSWORD or None,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={"charset": "utf8mb4"},
        )

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Render the full SQLAlchemy URI for engine creation or Alembic configuration."""
        return self.get_database_url().render_as_string(hide_password=False)

    # ML Artifacts path relative to backend root directory (backend/ml/models)
    MODELS_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "ml" / "models")

    # Task 12 Experimental ML Artifacts path relative to backend root directory (backend/ml/models_task12)
    EXPERIMENTAL_MODELS_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "ml" / "models_task12")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
