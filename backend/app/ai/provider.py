"""AI provider abstraction.

The approved provider is selected through configuration (``AI_PROVIDER``). No
other provider is substituted silently: if the configured provider has no API
key the assistant returns an explicit *configuration status* and never a
fabricated answer or invented financial figure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.config import settings


@dataclass
class GroundedContext:
    """Everything the model is allowed to see, already permission-filtered."""

    facts: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return bool(self.facts)


class AIProvider(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


class OpenAIProvider:
    name = "openai"

    def __init__(self, *, model: str | None = None, base_url: str | None = None, api_key: str | None = None) -> None:
        self.model = model or settings.ai_model
        self.base_url = base_url or settings.ai_base_url
        self.api_key = api_key or settings.openai_api_key

    def complete(self, system: str, user: str) -> str:
        resp = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.1,
            },
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


_PROVIDERS: dict[str, type] = {"openai": OpenAIProvider}


def get_provider(
    name: str | None = None, *, model: str | None = None, base_url: str | None = None, api_key: str | None = None
) -> AIProvider:
    provider_name = name or settings.ai_provider
    cls = _PROVIDERS.get(provider_name)
    if cls is None:
        raise ValueError(f"Unsupported AI provider: {provider_name}")
    return cls(model=model, base_url=base_url, api_key=api_key)


SYSTEM_PROMPT = (
    "You are the holding-company assistant. Answer ONLY from the FACTS block. "
    "Never invent financial values, dates, names, or document evidence. If the "
    "FACTS block does not contain the answer, say so plainly and state what is "
    "missing. Keep the answer concise and cite the source labels you used."
)


def build_answer(ctx: GroundedContext) -> tuple[str, str, str | None]:
    """Return ``(answer, confidence, note)``.

    The refusal/uncertainty paths are deterministic and never depend on the
    model, so a misconfigured provider can never produce a confident answer.
    """
    if not settings.ai_configured:
        return (
            "المساعد غير مهيأ: مفتاح مزوّد الذكاء الاصطناعي غير مُعد على الخادم.",
            "unconfigured",
            "ai_provider_not_configured",
        )
    if not ctx.has_data:
        return (
            "لا توجد سجلات مصرّح بها لديّ للإجابة على هذا السؤال. "
            "لم يتم اختلاق أي بيانات.",
            "no_data",
            "no_permitted_sources",
        )

    facts = "\n".join(f"- {f}" for f in ctx.facts)
    provider = get_provider()
    answer = provider.complete(SYSTEM_PROMPT, f"FACTS:\n{facts}\n\nQUESTION (from user): see below")
    confidence = "grounded" if len(ctx.facts) >= 2 else "low"
    return answer, confidence, None
