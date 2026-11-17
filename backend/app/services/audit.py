"""Audit logging. Records *who did what to which record*, never secret values."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.identity import AuditEvent, User


def record(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    company_id: int | None = None,
    meta: dict | None = None,
) -> AuditEvent:
    role_label = None
    if actor is not None and getattr(actor, "roles", None):
        role_label = ", ".join(sorted(r.role.slug for r in actor.roles if r.role))
    event = AuditEvent(
        actor_id=actor.id if actor else None,
        actor_label=actor.email if actor else None,
        role_label=role_label,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        company_id=company_id,
        request_meta=json.dumps(meta, ensure_ascii=False) if meta else None,
    )
    db.add(event)
    return event
