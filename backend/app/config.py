from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_ttl_days: int = 7
    cookie_secure: bool = True  # False only for local http dev
    default_monthly_ai_budget_usd: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
