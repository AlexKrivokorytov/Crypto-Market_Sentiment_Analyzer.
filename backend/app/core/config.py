"""
Configuration settings for the Market Sentiment Analyzer backend.

All secrets must be injected via environment variables, never hard-coded.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.

    JWT settings:
        JWT_SECRET_KEY: Secret used to sign access tokens. Generate with:
            `python -c "import secrets; print(secrets.token_hex(32))"`
        JWT_ALGORITHM: Algorithm used for encoding. Default: HS256.
        ACCESS_TOKEN_EXPIRE_MINUTES: Token lifetime in minutes. Default: 60.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "sentiment_db"

    LLM_API_URL: Optional[str] = None
    LLM_MODEL: str = "google/gemini-2.0-flash-exp"
    LLM_API_KEY: Optional[str] = None

    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_ENV_VAR"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Alchemy Web3 / Price API Key
    ALCHEMY_API_KEY: Optional[str] = None


settings = Settings()
