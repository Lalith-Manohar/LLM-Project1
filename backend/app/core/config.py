"""Core configuration module for NEXORA backend."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "NEXORA Retail Management & Intelligence System"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Future MySQL Database Settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "nexora_db"

    # ML Artifacts path relative to backend directory
    MODELS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "models")

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


settings = Settings()
