"""Read-only activity log."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.db import get_db
from app.models.identity import AuditEvent, User
from pydantic import BaseModel

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditOut(BaseModel):
    id: int
    created_at: datetime
    actor_id: int | None
    actor_label: str | None
    role_label: str | None
    action: str
    target_type: str | None
    target_id: str | None
    company_id: int | None


@router.get("", response_model=list[AuditOut])
def list_events(
    action: str | None = None,
    actor_id: int | None = None,
    company_id: int | None = None,
    limit: int = Query(default=200, le=1000),
    _: User = Depends(require("audit:view")),
    db: Session = Depends(get_db),
) -> list[AuditOut]:
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if company_id:
        stmt = stmt.where(AuditEvent.company_id == company_id)
    rows = db.execute(stmt.order_by(AuditEvent.id.desc()).limit(limit)).scalars().all()
    return [AuditOut.model_validate(r, from_attributes=True) for r in rows]
