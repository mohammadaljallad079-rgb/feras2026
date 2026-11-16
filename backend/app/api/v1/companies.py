"""Companies management and the four-step creation wizard."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, assert_company_access, get_current_user, require
from app.core.db import get_db
from app.models.business import Company
from app.models.enums import CompanyStatus
from app.models.identity import User
from app.schemas import CompanyCreate, CompanyOut, CompanyUpdate
from app.services import audit

router = APIRouter(prefix="/companies", tags=["companies"])


def _visible_query(db: Session, user: User):
    stmt = select(Company)
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(Company.id.in_(allowed or {-1}))
    return stmt


@router.get("", response_model=list[CompanyOut])
def list_companies(
    status_filter: str | None = Query(default=None, alias="status"),
    include_closed: bool = Query(default=False),
    q: str | None = None,
    user: User = Depends(require("company:view")),
    db: Session = Depends(get_db),
) -> list[CompanyOut]:
    stmt = _visible_query(db, user)
    if status_filter:
        stmt = stmt.where(Company.status == status_filter)
    elif not include_closed:
        stmt = stmt.where(Company.status != CompanyStatus.CLOSED.value)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Company.name_ar.ilike(like) | Company.name_en.ilike(like) | Company.code.ilike(like))
    rows = db.execute(stmt.order_by(Company.id.desc())).scalars().all()
    return [CompanyOut.model_validate(c) for c in rows]


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    actor: User = Depends(require("company:manage")),
    db: Session = Depends(get_db),
) -> CompanyOut:
    if db.execute(select(Company).where(Company.code == payload.code)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company code already exists")
    if payload.status not in {s.value for s in CompanyStatus}:
        raise HTTPException(status_code=422, detail="Invalid status")
    company = Company(**payload.model_dump())
    if payload.status == CompanyStatus.ACTIVE.value:
        company.activated_at = datetime.now(timezone.utc)
    db.add(company)
    db.flush()
    audit.record(db, action="company.create", actor=actor, target_type="company", target_id=company.id, company_id=company.id)
    db.commit()
    db.refresh(company)
    return CompanyOut.model_validate(company)


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int,
    user: User = Depends(require("company:view")),
    db: Session = Depends(get_db),
) -> CompanyOut:
    assert_company_access(db, user, company_id)
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyOut.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    actor: User = Depends(require("company:manage")),
    db: Session = Depends(get_db),
) -> CompanyOut:
    assert_company_access(db, actor, company_id)
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.status == CompanyStatus.CLOSED.value:
        raise HTTPException(status_code=409, detail="Closed companies are read-only")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    audit.record(db, action="company.update", actor=actor, target_type="company", target_id=company.id, company_id=company.id)
    db.commit()
    db.refresh(company)
    return CompanyOut.model_validate(company)


@router.post("/{company_id}/activate", response_model=CompanyOut)
def activate_company(
    company_id: int,
    actor: User = Depends(require("company:manage")),
    db: Session = Depends(get_db),
) -> CompanyOut:
    assert_company_access(db, actor, company_id)
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.status == CompanyStatus.CLOSED.value:
        raise HTTPException(status_code=409, detail="A closed company cannot be activated")
    company.status = CompanyStatus.ACTIVE.value
    company.activated_at = datetime.now(timezone.utc)
    audit.record(db, action="company.activate", actor=actor, target_type="company", target_id=company.id, company_id=company.id)
    db.commit()
    db.refresh(company)
    return CompanyOut.model_validate(company)


@router.post("/{company_id}/close", response_model=CompanyOut)
def close_company(
    company_id: int,
    actor: User = Depends(require("company:manage")),
    db: Session = Depends(get_db),
) -> CompanyOut:
    assert_company_access(db, actor, company_id)
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    company.status = CompanyStatus.CLOSED.value
    company.closed_at = datetime.now(timezone.utc)
    company.public_visible = False
    audit.record(db, action="company.close", actor=actor, target_type="company", target_id=company.id, company_id=company.id)
    db.commit()
    db.refresh(company)
    return CompanyOut.model_validate(company)
