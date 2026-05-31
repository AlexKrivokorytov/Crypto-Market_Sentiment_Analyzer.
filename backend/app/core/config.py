"""
Configuration settings for the Market Sentiment Analyzer backend.

All secrets must be injected via environment variables, never hard-coded.
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

    # ── Database ──────────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "sentiment_db"

    # ── LLM / OpenRouter ──────────────────────────────────────────────────
    LLM_API_URL: Optional[str] = None
    LLM_MODEL: str = "google/gemini-2.0-flash-exp"
    LLM_API_KEY: Optional[str] = None
    # Comma-separated fallback chain tried in order after primary model fails.
    LLM_FALLBACK_MODELS: str = (
        "google/gemini-2.5-flash:free,"
        "meta-llama/llama-3-8b-instruct:free,"
        "mistralai/mistral-7b-instruct:free"
    )
    # Max background LLM requests per 60-second window (preserves free-tier budget)
    LLM_MAX_BACKGROUND_RPM: int = 8

    # ── Circuit Breaker ───────────────────────────────────────────────────
    CB_FAILURE_THRESHOLD: int = 3
    CB_RECOVERY_TIMEOUT: float = 60.0

    # ── RSS Parser ────────────────────────────────────────────────────────
    RSS_MAX_ARTICLES_PER_SWEEP: int = 15
    RSS_MAX_AAPL_ARTICLES: int = 3

    # ── Task Supervisor (exponential backoff) ──────────────────────────────
    TASK_BACKOFF_START: float = 5.0
    TASK_BACKOFF_MAX: float = 300.0
    TASK_HEALTHY_RUN_SECONDS: float = 60.0

    # ── CORS (comma-separated allowed origins) ────────────────────────────
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://localhost:4173,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:4173,"
        "http://localhost:8080,"
        "http://127.0.0.1:8080,"
        "https://crypto-market-sentiment-analyzer-1.onrender.com"
    )

    # ── Auth ──────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_ENV_VAR"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── External APIs ─────────────────────────────────────────────────────
    ALCHEMY_API_KEY: Optional[str] = None

    # ── Computed properties ───────────────────────────────────────────────
    @property
    def llm_fallback_models_list(self) -> list[str]:
        """Returns the parsed, deduplicated fallback model chain."""
        seen: set[str] = set()
        result: list[str] = []
        for model in [self.LLM_MODEL] + [
            m.strip() for m in self.LLM_FALLBACK_MODELS.split(",") if m.strip()
        ]:
            if model not in seen:
                seen.add(model)
                result.append(model)
        return result

    @property
    def cors_origins_list(self) -> list[str]:
        """Returns the parsed list of allowed CORS origins."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
