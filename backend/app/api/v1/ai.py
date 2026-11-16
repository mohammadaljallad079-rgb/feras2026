"""Assistant endpoint: grounded answers with sources, or an explicit config status."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.provider import GroundedContext, build_answer
from app.ai.retrieval import gather_context
from app.api.deps import require
from app.core.config import settings
from app.core.db import get_db
from app.models.identity import User
from app.models.operations import AiQuery
from app.schemas import AiAnswer, AiAskRequest, AiSource
from app.services import audit

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
def status(_: User = Depends(require("ai:use"))) -> dict:
    """A missing key yields a clear configuration status, not a fake success."""
    return {
        "provider": settings.ai_provider,
        "model": settings.ai_model,
        "configured": settings.ai_configured,
        "message_ar": (
            "المساعد مهيأ."
            if settings.ai_configured
            else "المساعد غير مهيأ: مفتاح مزوّد الذكاء الاصطناعي غير مُعد."
        ),
    }


@router.post("/ask", response_model=AiAnswer)
def ask(
    payload: AiAskRequest,
    actor: User = Depends(require("ai:use")),
    db: Session = Depends(get_db),
) -> AiAnswer:
    ctx: GroundedContext = gather_context(db, actor, company_id=payload.company_id, period_id=payload.period_id)

    note = None
    if settings.ai_configured and ctx.has_data:
        try:
            answer, confidence, note = build_answer_with_prompt(ctx, payload.prompt)
        except Exception as exc:  # provider/network failure must be visible, not faked
            raise HTTPException(status_code=502, detail={"error": "ai_provider_failed", "detail": str(exc)})
    else:
        answer, confidence, note = build_answer(ctx)

    record = AiQuery(
        user_id=actor.id,
        prompt=payload.prompt,
        answer=answer,
        provider=settings.ai_provider,
        model=settings.ai_model,
        confidence=confidence,
        sources=json.dumps(ctx.sources, ensure_ascii=False),
        company_id=payload.company_id,
        period_id=payload.period_id,
    )
    db.add(record)
    audit.record(db, action="ai.ask", actor=actor, target_type="ai_query", target_id=record.id, company_id=payload.company_id)
    db.commit()

    return AiAnswer(
        answer=answer,
        confidence=confidence,
        sources=[AiSource(**s) for s in ctx.sources],
        provider=settings.ai_provider,
        model=settings.ai_model,
        configured=settings.ai_configured,
        note=note,
    )


def build_answer_with_prompt(ctx: GroundedContext, prompt: str) -> tuple[str, str, str | None]:
    from app.ai.provider import SYSTEM_PROMPT, get_provider

    facts = "\n".join(f"- {f}" for f in ctx.facts)
    provider = get_provider()
    answer = provider.complete(SYSTEM_PROMPT, f"FACTS:\n{facts}\n\nQUESTION: {prompt}")
    confidence = "grounded" if len(ctx.facts) >= 2 else "low"
    return answer, confidence, None
