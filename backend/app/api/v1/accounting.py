"""Holding accounting: expenses, invoices, commissions."""

from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, assert_company_access, require
from app.core.db import get_db
from app.models.enums import AccountingKind, AccountingStatus
from app.models.identity import User
from app.models.operations import AccountingEntry
from app.schemas import AccountingCreate, AccountingOut, AccountingUpdate
from app.services import audit

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.get("", response_model=list[AccountingOut])
def list_entries(
    kind: str | None = None,
    company_id: int | None = None,
    entry_status: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    user: User = Depends(require("accounting:view")),
    db: Session = Depends(get_db),
) -> list[AccountingOut]:
    stmt = select(AccountingEntry)
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(AccountingEntry.company_id.in_(allowed or {-1}))
    if kind:
        stmt = stmt.where(AccountingEntry.kind == kind)
    if company_id:
        stmt = stmt.where(AccountingEntry.company_id == company_id)
    if entry_status:
        stmt = stmt.where(AccountingEntry.status == entry_status)
    if q:
        stmt = stmt.where(AccountingEntry.reference.ilike(f"%{q}%") | AccountingEntry.description.ilike(f"%{q}%"))
    rows = db.execute(stmt.order_by(AccountingEntry.entry_date.desc(), AccountingEntry.id.desc())).scalars().all()
    return [AccountingOut.model_validate(e) for e in rows]


@router.post("", response_model=AccountingOut, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: AccountingCreate,
    actor: User = Depends(require("accounting:manage")),
    db: Session = Depends(get_db),
) -> AccountingOut:
    if payload.kind not in {k.value for k in AccountingKind}:
        raise HTTPException(status_code=422, detail="Unknown entry kind")
    assert_company_access(db, actor, payload.company_id)
    entry = AccountingEntry(**payload.model_dump(), created_by_id=actor.id)
    db.add(entry)
    db.flush()
    audit.record(db, action="accounting.create", actor=actor, target_type="accounting_entry", target_id=entry.id, company_id=entry.company_id)
    db.commit()
    db.refresh(entry)
    return AccountingOut.model_validate(entry)


@router.patch("/{entry_id}", response_model=AccountingOut)
def update_entry(
    entry_id: int,
    payload: AccountingUpdate,
    actor: User = Depends(require("accounting:manage")),
    db: Session = Depends(get_db),
) -> AccountingOut:
    entry = db.get(AccountingEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    assert_company_access(db, actor, entry.company_id)
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in {s.value for s in AccountingStatus}:
        raise HTTPException(status_code=422, detail="Unknown status")
    if "status" in changes and changes["status"] in {AccountingStatus.REVIEWED.value, AccountingStatus.REJECTED.value}:
        entry.reviewed_by_id = actor.id
        entry.reviewed_at = datetime.now(timezone.utc)
    for key, value in changes.items():
        setattr(entry, key, value)
    audit.record(db, action="accounting.update", actor=actor, target_type="accounting_entry", target_id=entry.id, company_id=entry.company_id)
    db.commit()
    db.refresh(entry)
    return AccountingOut.model_validate(entry)


@router.get("/export.xlsx")
def export_entries(
    company_id: int | None = None,
    user: User = Depends(require("accounting:view")),
    db: Session = Depends(get_db),
):
    from openpyxl import Workbook

    stmt = select(AccountingEntry)
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(AccountingEntry.company_id.in_(allowed or {-1}))
    if company_id:
        assert_company_access(db, user, company_id)
        stmt = stmt.where(AccountingEntry.company_id == company_id)
    rows = db.execute(stmt.order_by(AccountingEntry.entry_date)).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Accounting"
    ws.append(["ID", "Kind", "Company", "Reference", "Description", "Amount", "Currency", "Date", "Status"])
    for e in rows:
        ws.append([e.id, e.kind, e.company_id, e.reference, e.description, float(e.amount), e.currency, str(e.entry_date), e.status])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    audit.record(db, action="accounting.export", actor=user)
    db.commit()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=accounting.xlsx"},
    )
