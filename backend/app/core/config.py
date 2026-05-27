"""
Configuration settings for the Market Sentiment Analyzer backend.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "sentiment_db"

    LLM_API_URL: Optional[str] = None
    LLM_MODEL: str = "local-model"


settings = Settings()
