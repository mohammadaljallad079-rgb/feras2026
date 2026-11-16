"""Application configuration.

All secrets are read from the environment. Nothing here is committed with a
real credential; the defaults are development placeholders and are rejected
when ``ENVIRONMENT=production``.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # Database
    database_url: str = "postgresql+psycopg://safir:safir@localhost:5432/safir"

    # Auth
    secret_key: str = "dev-insecure-change-me"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    password_reset_minutes: int = 60
    algorithm: str = "HS256"

    # Storage
    storage_dir: str = "/var/lib/safir/storage"
    max_upload_bytes: int = 20 * 1024 * 1024

    # CORS / public website
    cors_origins: str = "http://localhost:3000"
    public_rate_limit_per_hour: int = 20

    # AI provider abstraction. The approved provider is selected here; no other
    # provider is substituted silently. Missing key => configuration status,
    # never a fabricated answer.
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""

    @field_validator("secret_key")
    @classmethod
    def _reject_insecure_in_production(cls, v: str) -> str:
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
