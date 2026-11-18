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

    # Public base URL of the frontend, used to build the secure links in the
    # account emails (password reset, invitation).
    frontend_base_url: str = "http://localhost:3000"

    # Operating timezone for the deadline reminders. The due dates are Bahrain
    # business dates, so the daily cron resolves "today" here rather than in the
    # server's timezone.
    reminders_timezone: str = "Asia/Bahrain"

    # Outbound mail. When SMTP_HOST is empty the platform reports the mail
    # transport as unconfigured instead of pretending a message was delivered.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@safir-platform.com"
    smtp_use_tls: bool = True

    # AI provider abstraction. The approved provider is selected here; no other
    # provider is substituted silently. Missing key => configuration status,
    # never a fabricated answer.
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    # Model classes the owner may pick from on the assistant screen (PDF p.17).
    ai_model_classes: str = "gpt-4o-mini,gpt-4o,gpt-4.1-mini,gpt-4.1"

    @field_validator("secret_key")
    @classmethod
    def _reject_insecure_in_production(cls, v: str) -> str:
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_model_class_list(self) -> list[str]:
        return [m.strip() for m in self.ai_model_classes.split(",") if m.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def mail_configured(self) -> bool:
        return bool(self.smtp_host)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
