"""AI provider configuration: masked reads, environment fallback, no key leaks.

The owner may set provider, model class, base URL and API key. The key is stored
server-side and is never returned by any endpoint — only ``has_api_key`` and a
short masked hint. The environment remains the authoritative source for the key
when one is set there, so a deployment secret is never overwritten by a row.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.operations import AiProviderSetting


def get_or_create(db: Session) -> AiProviderSetting:
    row = db.execute(select(AiProviderSetting).order_by(AiProviderSetting.id)).scalars().first()
    if row is None:
        row = AiProviderSetting(
            provider=settings.ai_provider,
            model=settings.ai_model,
            base_url=settings.ai_base_url,
        )
        db.add(row)
        db.flush()
    return row


def effective(row: AiProviderSetting) -> tuple[str, str, str, str]:
    """Return ``(provider, model, base_url, api_key)`` with the env key winning."""
    provider = row.provider or settings.ai_provider
    model = row.model or settings.ai_model
    base_url = row.base_url or settings.ai_base_url
    api_key = settings.openai_api_key or (row.api_key_encrypted or "")
    return provider, model, base_url, api_key


def is_configured(row: AiProviderSetting) -> bool:
    return bool(effective(row)[3])


def mask(key: str) -> str | None:
    """A short, non-reversible hint. Never the key itself."""
    if not key:
        return None
    digest = hashlib.sha256(key.encode()).hexdigest()[:6]
    return f"sk-…{digest}"
