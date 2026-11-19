"""Public, unauthenticated endpoints for the corporate website.

These are validated, rate-limited and persisted. Only companies flagged
``public_visible`` (and active) are ever returned, and only through the fields
the brief permits: no financial value, manager, address or internal field
appears here.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.site_content import OPPORTUNITY_COUNTRIES
from app.core.config import settings
from app.core.db import get_db
from app.models.business import Company
from app.models.enums import CompanyStatus, SubmissionKind, SubmissionStatus
from app.models.operations import StoredFile, WebsiteSubmission, WebsiteSubmissionEvent
from app.schemas import PublicCompanyOut, PublicSubmission, SiteBootstrap, SubmissionOut
from app.services import audit, site
from app.services.files import path_for, save_upload

router = APIRouter(prefix="/public", tags=["public"])

# Fields each form requires, beyond name/email/consent (Table 12). Only the
# starred fields are mandatory: «نوع الخدمة *» for a service request,
# «دولة المشروع *» and «وصف مختصر *» for an opportunity, and the CV for a job
# application. «موضوع الفرصة» and «مجال الاهتمام أو الخبرة» carry no star.
_KIND_REQUIRED: dict[str, tuple[str, ...]] = {
    SubmissionKind.CONTACT.value: (),
    SubmissionKind.SERVICE_REQUEST.value: ("phone", "service_type"),
    SubmissionKind.OPPORTUNITY.value: ("phone", "country", "message"),
    SubmissionKind.JOB_APPLICATION.value: ("phone",),
}


@router.get("/site", response_model=SiteBootstrap)
def site_bootstrap(db: Session = Depends(get_db)) -> SiteBootstrap:
    """Everything the public site renders with, in one request."""
    return SiteBootstrap(
        settings=site.settings_map(db),
        sections=site.visible_sections(db),
        slides=site.active_slides(db),
        services=site.active_services(db),
        header_nav=site.nav_links(db, "header"),
        footer_nav=site.nav_links(db, "footer"),
        opportunity_countries=site.opportunity_countries(),
    )


@router.get("/companies", response_model=list[PublicCompanyOut])
def public_companies(
    sector: str | None = None,
    db: Session = Depends(get_db),
) -> list[PublicCompanyOut]:
    """Published companies only. `public_visible` is the single gate."""
    stmt = select(Company).where(
        Company.public_visible.is_(True), Company.status == CompanyStatus.ACTIVE.value
    )
    if sector:
        stmt = stmt.where(Company.sector == sector)
    rows = db.execute(stmt.order_by(Company.name_en)).scalars().all()
    return [
        PublicCompanyOut(
            code=c.code,
            name_ar=c.name_ar,
            name_en=c.name_en,
            sector=c.sector,
            country=c.country,
            logo_url=f"/api/v1/public/companies/{c.code}/logo" if c.logo_file_id else None,
            activity_ar=c.public_activity_ar,
            activity_en=c.public_activity_en,
            website_url=c.website_url,
        )
        for c in rows
    ]


@router.get("/companies/{code}/logo")
def public_company_logo(code: str, db: Session = Depends(get_db)) -> FileResponse:
    """The logo of a published company, served inline for the public site.

    Only a company that is both active and flagged ``public_visible`` exposes
    its logo here; the file is served inline as an image so the portfolio card
    and the preview modal can render it. No other file is reachable this way.
    """
    company = db.execute(
        select(Company).where(
            Company.code == code,
            Company.public_visible.is_(True),
            Company.status == CompanyStatus.ACTIVE.value,
        )
    ).scalars().first()
    if company is None or company.logo_file_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No public logo")
    record = db.get(StoredFile, company.logo_file_id)
    if record is None or not record.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No public logo")
    return FileResponse(
        path_for(record),
        media_type=record.content_type,
        content_disposition_type="inline",
    )


def _check_rate_limit(db: Session, ip: str) -> None:
    window_start = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = db.execute(
        select(func.count(WebsiteSubmission.id)).where(
            WebsiteSubmission.source_ip == ip, WebsiteSubmission.created_at >= window_start
        )
    ).scalar_one()
    if recent >= settings.public_rate_limit_per_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"error": "rate_limited"}
        )


def _reference_no(kind: str) -> str:
    prefix = {
        SubmissionKind.SERVICE_REQUEST.value: "SR",
        SubmissionKind.OPPORTUNITY.value: "OP",
        SubmissionKind.JOB_APPLICATION.value: "JB",
    }.get(kind, "CT")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}-{stamp}-{secrets.token_hex(3).upper()}"


@router.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def submit_form(
    payload: PublicSubmission,
    request: Request,
    db: Session = Depends(get_db),
) -> SubmissionOut:
    """JSON submission (contact, service request, opportunity without a file)."""
    return _persist(db, request, payload)


@router.post(
    "/submissions/with-file",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_form_with_file(
    request: Request,
    kind: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str | None = Form(default=None),
    message: str | None = Form(default=None),
    service_type: str | None = Form(default=None),
    country: str | None = Form(default=None),
    subject: str | None = Form(default=None),
    expertise: str | None = Form(default=None),
    consent: bool = Form(default=False),
    attachment: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    """Multipart submission for the opportunity (study file) and job (CV) forms.

    The submission row is written first and the attachment linked in the same
    transaction: if the file is rejected the request is still recorded, never
    lost, and flagged for follow-up.
    """
    payload = PublicSubmission(
        kind=kind,
        name=name,
        email=email,
        phone=phone,
        message=message,
        service_type=service_type,
        country=country,
        subject=subject,
        expertise=expertise,
        consent=consent,
    )
    attachment_id: int | None = None
    if attachment is not None and attachment.filename:
        record = await save_upload(
            db, attachment, owner_id=None, company_id=None, is_confidential=True
        )
        attachment_id = record.id
    return _persist(db, request, payload, attachment_file_id=attachment_id)


def _persist(
    db: Session,
    request: Request,
    data: PublicSubmission,
    attachment_file_id: int | None = None,
) -> SubmissionOut:
    kind = data.kind
    if kind not in {k.value for k in SubmissionKind}:
        raise HTTPException(status_code=422, detail={"error": "unknown_kind"})
    if not data.consent:
        raise HTTPException(status_code=422, detail={"error": "consent_required"})

    missing = [f for f in _KIND_REQUIRED.get(kind, ()) if not getattr(data, f, None)]
    if missing:
        raise HTTPException(status_code=422, detail={"error": "missing_fields", "fields": missing})
    if kind == SubmissionKind.OPPORTUNITY.value and data.country not in OPPORTUNITY_COUNTRIES:
        raise HTTPException(status_code=422, detail={"error": "unsupported_country"})
    if kind == SubmissionKind.JOB_APPLICATION.value and attachment_file_id is None:
        raise HTTPException(status_code=422, detail={"error": "cv_required"})

    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(db, ip)

    if data.company_id is not None and db.get(Company, data.company_id) is None:
        raise HTTPException(status_code=422, detail={"error": "unknown_company"})

    sub = WebsiteSubmission(
        reference_no=_reference_no(kind),
        kind=kind,
        name=data.name,
        email=str(data.email),
        phone=data.phone,
        message=data.message,
        service_type=data.service_type,
        country=data.country,
        subject=data.subject,
        expertise=data.expertise,
        consent=data.consent,
        company_id=data.company_id,
        attachment_file_id=attachment_file_id,
        status=SubmissionStatus.NEW.value,
        source_ip=ip,
    )
    db.add(sub)
    db.flush()
    db.add(
        WebsiteSubmissionEvent(
            submission_id=sub.id, to_status=SubmissionStatus.NEW.value, note="received"
        )
    )
    audit.record(
        db,
        action="website.submission_received",
        target_type="website_submission",
        target_id=sub.id,
        meta={"kind": kind, "reference_no": sub.reference_no},
    )
    db.commit()
    db.refresh(sub)
    return SubmissionOut.model_validate(sub)
