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

    openai_api_key: str | None = None
    llm_model_generate: str = "gpt-6.1-sol"
    llm_model_evaluate: str = "gpt-6.1-sol"
    llm_model_verify: str = "gpt-5.6-terra"

    content_dir: str = "/srv/content"  # generated JSON + media (repo-root content/)


@lru_cache
def get_settings() -> Settings:
    return Settings()
