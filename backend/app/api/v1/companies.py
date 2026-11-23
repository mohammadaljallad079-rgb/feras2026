"""Companies management and the four-step creation wizard."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, assert_company_access, get_current_user, permissions_of, require
from app.core.db import get_db
from app.models.business import Company
from app.models.enums import CompanyStatus
from app.models.identity import User
from app.models.operations import StoredFile
from app.schemas import CompanyCreate, CompanyOut, CompanyUpdate
from app.services import audit

router = APIRouter(prefix="/companies", tags=["companies"])


def _visible_query(db: Session, user: User):
    stmt = select(Company)
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(Company.id.in_(allowed or {-1}))
    return stmt


def _assert_logo_belongs_to_company(db: Session, file_id: int, company_id: int) -> None:
    """A company logo must be an uploaded file recorded against that company.

    Accepting an arbitrary id would let a manager point the logo at another
    company's private document.
    """
    record = db.get(StoredFile, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Logo file not found")
    if record.company_id != company_id:
        raise HTTPException(status_code=422, detail="Logo file does not belong to this company")
    if not record.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Logo must be an image")


@router.get("", response_model=list[CompanyOut])
def list_companies(
    status_filter: str | None = Query(default=None, alias="status"),
    include_closed: bool = Query(default=False),
    include_holding: bool = Query(default=False),
    q: str | None = None,
    user: User = Depends(require("company:view")),
    db: Session = Depends(get_db),
) -> list[CompanyOut]:
    stmt = _visible_query(db, user)
    # §7.4: the Holding's own record carries the Holding report fields but is not
    # a subsidiary, so it stays out of the companies list unless explicitly asked
    # for (the reports screen asks for it).
    if not include_holding:
        stmt = stmt.where(Company.is_holding.is_(False))
    if status_filter:
        stmt = stmt.where(Company.status == status_filter)
    elif include_closed:
        stmt = stmt.where(Company.status.in_([CompanyStatus.ACTIVE.value, CompanyStatus.CLOSED.value]))
    elif "company:manage" in permissions_of(user):
        # §6.2: «الشركة المحفوظة مسودة لا تظهر في القوائم ولا التقارير حتى تُفعَّل».
        # The owner keeps sight of the draft so «حفظ مسودة» has a way back — the
        # row is what carries the «تفعيل» control (§6.3, design p.6).
        stmt = stmt.where(Company.status.in_([CompanyStatus.ACTIVE.value, CompanyStatus.DRAFT.value]))
    else:
        stmt = stmt.where(Company.status == CompanyStatus.ACTIVE.value)
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
    data = payload.model_dump()
    # §6.2: the wizard does not collect a code. When one is not supplied, derive a
    # stable unique code so the record satisfies the unique index.
    code = (data.pop("code") or "").strip()
    if not code:
        last_id = db.execute(select(func.max(Company.id))).scalar_one() or 0
        code = f"C-{last_id + 1:04d}"
    if db.execute(select(Company).where(Company.code == code)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company code already exists")
    if payload.status not in {s.value for s in CompanyStatus}:
        raise HTTPException(status_code=422, detail="Invalid status")
    company = Company(code=code, **data)
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
    changes = payload.model_dump(exclude_unset=True)
    if "logo_file_id" in changes and changes["logo_file_id"] is not None:
        _assert_logo_belongs_to_company(db, changes["logo_file_id"], company_id)
    for key, value in changes.items():
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


@router.post("/{company_id}/reactivate", response_model=CompanyOut)
def reactivate_company(
    company_id: int,
    actor: User = Depends(require("company:manage")),
    db: Session = Depends(get_db),
) -> CompanyOut:
    """Table 4: a closed (archived) company returns to active with its history
    intact. There is no legal or accounting liquidation here — the record stays."""
    assert_company_access(db, actor, company_id)
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.status != CompanyStatus.CLOSED.value:
        raise HTTPException(status_code=409, detail="Only a closed company can be reactivated")
    company.status = CompanyStatus.ACTIVE.value
    company.closed_at = None
    company.activated_at = datetime.now(timezone.utc)
    audit.record(db, action="company.reactivate", actor=actor, target_type="company", target_id=company.id, company_id=company.id)
    db.commit()
    db.refresh(company)
    return CompanyOut.model_validate(company)
