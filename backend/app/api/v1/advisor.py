"""External advisor messaging: recommendations, reports, suggestions."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.db import get_db
from app.models.enums import AdvisorCategory, AdvisorMessageStatus
from app.models.identity import User
from app.models.operations import AdvisorMessage
from app.schemas import AdvisorMessageCreate, AdvisorMessageOut
from app.services import audit

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.get("/messages", response_model=list[AdvisorMessageOut])
def list_messages(
    box: str = "all",
    actor: User = Depends(require("advisor:view")),
    db: Session = Depends(get_db),
) -> list[AdvisorMessageOut]:
    stmt = select(AdvisorMessage)
    if box == "inbox":
        stmt = stmt.where(AdvisorMessage.recipient_id == actor.id)
    elif box == "sent":
        stmt = stmt.where(AdvisorMessage.author_id == actor.id)
    else:
        stmt = stmt.where(
            or_(AdvisorMessage.recipient_id == actor.id, AdvisorMessage.author_id == actor.id)
        )
    rows = db.execute(stmt.order_by(AdvisorMessage.id.desc())).scalars().all()
    return [AdvisorMessageOut.model_validate(m) for m in rows]


@router.post("/messages", response_model=AdvisorMessageOut, status_code=status.HTTP_201_CREATED)
def create_message(
    payload: AdvisorMessageCreate,
    actor: User = Depends(require("advisor:submit")),
    db: Session = Depends(get_db),
) -> AdvisorMessageOut:
    if payload.category not in {c.value for c in AdvisorCategory}:
        raise HTTPException(status_code=422, detail="Unknown category")
    if db.get(User, payload.recipient_id) is None:
        raise HTTPException(status_code=422, detail="Recipient not found")
    msg = AdvisorMessage(**payload.model_dump(), author_id=actor.id)
    db.add(msg)
    db.flush()
    audit.record(db, action="advisor.message.create", actor=actor, target_type="advisor_message", target_id=msg.id)
    db.commit()
    db.refresh(msg)
    return AdvisorMessageOut.model_validate(msg)


@router.post("/messages/{message_id}/read", response_model=AdvisorMessageOut)
def mark_read(
    message_id: int,
    actor: User = Depends(require("advisor:view")),
    db: Session = Depends(get_db),
) -> AdvisorMessageOut:
    msg = db.get(AdvisorMessage, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.recipient_id != actor.id and msg.author_id != actor.id:
        # Advisors must not see unrelated company-sensitive information.
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.recipient_id == actor.id:
        msg.status = AdvisorMessageStatus.READ.value
        msg.read_at = datetime.now(timezone.utc)
    audit.record(db, action="advisor.message.read", actor=actor, target_type="advisor_message", target_id=msg.id)
    db.commit()
    db.refresh(msg)
    return AdvisorMessageOut.model_validate(msg)
