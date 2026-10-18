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

    tts_provider: str = "elevenlabs"  # or "kokoro" (free, local) or "fake" (tones), see scripts/content/tts.py
    elevenlabs_api_key: str | None = None
    elevenlabs_model: str = "eleven_multilingual_v2"  # the API's documented default; newer models via env
    kokoro_dir: str = "~/.cache/kokoro"
    whisper_model: str = "small.en"  # Speaking transcription (scripts.speaking); "medium.en" is slower but more exact

    exam_time_scale: float = 1.0  # dev only: 0.05 turns a 60-minute section into 3 minutes
    dev_clock_offset_days: float = 0  # dev only: 1 = the server lives one day ahead (to see reviews fall due)
    content_dir: str = "/srv/content"  # generated JSON + media (repo-root content/)
    frontend_dist: str = "/srv/frontend/dist"  # built SPA, present only in the prod image


@lru_cache
def get_settings() -> Settings:
    return Settings()
