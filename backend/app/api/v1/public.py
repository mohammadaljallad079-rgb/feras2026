"""Public, unauthenticated endpoints for the marketing website.

These are validated, rate-limited and persisted. The public website's *visual*
design is not specified by the platform PDF, so it is delivered separately.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.business import Company
from app.models.enums import CompanyStatus, SubmissionKind
from app.models.operations import WebsiteSubmission
from app.schemas import PublicSubmission

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/companies")
def public_companies(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Company).where(
            Company.public_visible.is_(True), Company.status == CompanyStatus.ACTIVE.value
        )
    ).scalars().all()
    return [
        {"code": c.code, "name_ar": c.name_ar, "name_en": c.name_en, "sector": c.sector, "country": c.country}
        for c in rows
    ]


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
def submit_form(
    payload: PublicSubmission,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    if payload.kind not in {k.value for k in SubmissionKind}:
        raise HTTPException(status_code=422, detail="Unknown submission kind")

    ip = request.client.host if request.client else "unknown"
    window_start = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = db.execute(
        select(func.count(WebsiteSubmission.id)).where(
            WebsiteSubmission.source_ip == ip, WebsiteSubmission.created_at >= window_start
        )
    ).scalar_one()
    if recent >= settings.public_rate_limit_per_hour:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    if payload.company_id is not None and db.get(Company, payload.company_id) is None:
        raise HTTPException(status_code=422, detail="Unknown company")

    sub = WebsiteSubmission(**payload.model_dump(), source_ip=ip)
    db.add(sub)
    db.commit()
    return {"id": sub.id, "status": sub.status}
