"""Executive directives: send, receive, complete, overdue tracking."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, require
from app.core.db import get_db
from app.models.enums import DirectiveStatus
from app.models.identity import User
from app.models.operations import ExecutiveDirective
from app.schemas import DirectiveCreate, DirectiveOut
from app.services import audit, mail

router = APIRouter(prefix="/directives", tags=["directives"])


def _decorate(d: ExecutiveDirective) -> DirectiveOut:
    out = DirectiveOut.model_validate(d)
    return out


@router.get("", response_model=list[DirectiveOut])
def list_directives(
    box: str = "all",
    user: User = Depends(require("directive:view")),
    db: Session = Depends(get_db),
) -> list[DirectiveOut]:
    stmt = select(ExecutiveDirective)
    if box == "inbox":
        stmt = stmt.where(ExecutiveDirective.recipient_id == user.id)
    elif box == "sent":
        stmt = stmt.where(ExecutiveDirective.created_by_id == user.id)
    else:
        stmt = stmt.where(
            or_(ExecutiveDirective.recipient_id == user.id, ExecutiveDirective.created_by_id == user.id)
        )
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(
            (ExecutiveDirective.company_id.is_(None)) | (ExecutiveDirective.company_id.in_(allowed or {-1}))
        )
    rows = db.execute(stmt.order_by(ExecutiveDirective.id.desc())).scalars().all()
    return [_decorate(d) for d in rows]


@router.post("", response_model=DirectiveOut, status_code=status.HTTP_201_CREATED)
def create_directive(
    payload: DirectiveCreate,
    actor: User = Depends(require("directive:create")),
    db: Session = Depends(get_db),
) -> DirectiveOut:
    if db.get(User, payload.recipient_id) is None:
        raise HTTPException(status_code=422, detail="Recipient not found")
    d = ExecutiveDirective(**payload.model_dump(), created_by_id=actor.id)
    db.add(d)
    db.flush()
    audit.record(db, action="directive.create", actor=actor, target_type="directive", target_id=d.id, company_id=d.company_id)
    db.commit()
    db.refresh(d)
    # Table 5: «توجيه جديد … لمستلم واحد فقط دون نسخة لغيره». The single
    # recipient is notified; no copy reaches anyone else.
    recipient = db.get(User, d.recipient_id)
    if recipient is not None:
        mail.notify(
            [recipient.email],
            mail.directive_email(recipient.locale or "ar", title=d.title, body=d.body or ""),
        )
    return _decorate(d)


@router.post("/{directive_id}/send", response_model=DirectiveOut)
def send_directive(
    directive_id: int,
    actor: User = Depends(require("directive:create")),
    db: Session = Depends(get_db),
) -> DirectiveOut:
    d = db.get(ExecutiveDirective, directive_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Directive not found")
    if d.created_by_id != actor.id and "directive:create" not in _perms(actor):
        raise HTTPException(status_code=403, detail="Not permitted")
    d.status = DirectiveStatus.SENT.value
    d.sent_at = datetime.now(timezone.utc)
    audit.record(db, action="directive.send", actor=actor, target_type="directive", target_id=d.id)
    db.commit()
    db.refresh(d)
    return _decorate(d)


@router.post("/{directive_id}/receive", response_model=DirectiveOut)
def receive_directive(
    directive_id: int,
    actor: User = Depends(require("directive:view")),
    db: Session = Depends(get_db),
) -> DirectiveOut:
    d = db.get(ExecutiveDirective, directive_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Directive not found")
    if d.recipient_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the recipient may acknowledge receipt")
    if d.status != DirectiveStatus.SENT.value:
        raise HTTPException(status_code=409, detail="Directive is not awaiting receipt")
    d.status = DirectiveStatus.RECEIVED.value
    d.received_at = datetime.now(timezone.utc)
    audit.record(db, action="directive.receive", actor=actor, target_type="directive", target_id=d.id)
    db.commit()
    db.refresh(d)
    return _decorate(d)


@router.post("/{directive_id}/complete", response_model=DirectiveOut)
def complete_directive(
    directive_id: int,
    actor: User = Depends(require("directive:update")),
    db: Session = Depends(get_db),
) -> DirectiveOut:
    d = db.get(ExecutiveDirective, directive_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Directive not found")
    if d.recipient_id != actor.id and "directive:create" not in _perms(actor):
        raise HTTPException(status_code=403, detail="Not permitted")
    if d.status not in {DirectiveStatus.SENT.value, DirectiveStatus.RECEIVED.value}:
        raise HTTPException(status_code=409, detail="Directive cannot be completed from its current state")
    d.status = DirectiveStatus.COMPLETED.value
    d.completed_at = datetime.now(timezone.utc)
    audit.record(db, action="directive.complete", actor=actor, target_type="directive", target_id=d.id)
    db.commit()
    db.refresh(d)
    return _decorate(d)


@router.get("/overdue", response_model=list[DirectiveOut])
def overdue(
    actor: User = Depends(require("directive:view")),
    db: Session = Depends(get_db),
) -> list[DirectiveOut]:
    today = date.today()
    stmt = select(ExecutiveDirective).where(
        ExecutiveDirective.follow_up_on.is_not(None),
        ExecutiveDirective.follow_up_on < today,
        ExecutiveDirective.status != DirectiveStatus.COMPLETED.value,
    )
    # A directive has a single recipient. An overdue one is the sender's
    # business or its recipient's; it must not surface to an unrelated holder
    # of directive:view (PDF p.13).
    stmt = stmt.where(
        or_(
            ExecutiveDirective.recipient_id == actor.id,
            ExecutiveDirective.created_by_id == actor.id,
        )
    )
    allowed = allowed_company_ids(db, actor)
    if allowed is not None:
        stmt = stmt.where(
            (ExecutiveDirective.company_id.is_(None)) | (ExecutiveDirective.company_id.in_(allowed or {-1}))
        )
    rows = db.execute(stmt.order_by(ExecutiveDirective.id.desc())).scalars().all()
    return [_decorate(d) for d in rows]


def _perms(user: User) -> set[str]:
    out: set[str] = set()
    for ur in user.roles:
        if ur.role:
            out |= ur.role.permission_codes
    return out
