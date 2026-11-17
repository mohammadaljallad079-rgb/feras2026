"""FastAPI application entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router, public_router
from app.core.config import settings
from app.core.db import engine

logger = logging.getLogger("safir")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Safir Holding Platform API",
    version="1.0.0",
    description="Arabic-first holding-company management platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(public_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def ready() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:  # pragma: no cover - exercised only on failure
        return {"status": "degraded", "database": str(exc)}


@app.get("/api/v1/config/ai-status", tags=["config"])
def ai_status() -> dict:
    """Public, secret-free view of the AI provider configuration state."""
    return {
        "provider": settings.ai_provider,
        "model": settings.ai_model,
        "configured": settings.ai_configured,
    }
