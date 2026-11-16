"""Website administration: public form inbox, conversion to internal records."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.db import get_db
from app.models.business import Company
from app.models.enums import SubmissionKind, SubmissionStatus
from app.models.identity import User
from app.models.operations import Lead, Opportunity, ServiceRequest, WebsiteSubmission
from app.schemas import SubmissionConvert, SubmissionOut, VisibilityUpdate
from app.services import audit

router = APIRouter(prefix="/website", tags=["website"])


@router.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(
    kind: str | None = None,
    submission_status: str | None = Query(default=None, alias="status"),
    _: User = Depends(require("website:view")),
    db: Session = Depends(get_db),
) -> list[SubmissionOut]:
    stmt = select(WebsiteSubmission)
    if kind:
        stmt = stmt.where(WebsiteSubmission.kind == kind)
    if submission_status:
        stmt = stmt.where(WebsiteSubmission.status == submission_status)
    rows = db.execute(stmt.order_by(WebsiteSubmission.id.desc())).scalars().all()
    return [SubmissionOut.model_validate(s) for s in rows]


@router.post("/submissions/{submission_id}/convert", response_model=SubmissionOut)
def convert_submission(
    submission_id: int,
    payload: SubmissionConvert,
    actor: User = Depends(require("website:manage")),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    sub = db.get(WebsiteSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.status == SubmissionStatus.CONVERTED.value:
        raise HTTPException(status_code=409, detail="Submission already converted")

    if payload.target == "lead":
        if sub.company_id is None or db.get(Company, sub.company_id) is None:
            raise HTTPException(status_code=422, detail="A registered company is required to convert to a lead")
        record = Lead(
            name=sub.name,
            contact_email=sub.email,
            contact_phone=sub.phone,
            requested_service=sub.kind,
            source="website",
            company_id=sub.company_id,
            notes=sub.message,
            status="new",
        )
    elif payload.target == "opportunity":
        if sub.company_id is None or db.get(Company, sub.company_id) is None:
            raise HTTPException(status_code=422, detail="A registered company is required to convert to an opportunity")
        record = Opportunity(
            title=f"{sub.name} — {sub.kind}",
            company_id=sub.company_id,
            description=sub.message,
            created_by_id=actor.id,
            status="draft",
        )
    elif payload.target == "service_request":
        if sub.company_id is None or db.get(Company, sub.company_id) is None:
            raise HTTPException(status_code=422, detail="A registered company is required to convert to a service request")
        record = ServiceRequest(
            subject=f"{sub.kind}: {sub.name}",
            body=sub.message,
            company_id=sub.company_id,
            created_by_id=actor.id,
            recipient_id=actor.id,
            priority="normal",
            status="new",
        )
    else:
        raise HTTPException(status_code=422, detail="Unknown conversion target")

    db.add(record)
    db.flush()
    sub.status = SubmissionStatus.CONVERTED.value
    sub.converted_type = payload.target
    sub.converted_id = record.id
    audit.record(db, action="website.convert", actor=actor, target_type="website_submission", target_id=sub.id, meta={"target": payload.target, "created_id": record.id})
    db.commit()
    db.refresh(sub)
    return SubmissionOut.model_validate(sub)


@router.post("/submissions/{submission_id}/reject", response_model=SubmissionOut)
def reject_submission(
    submission_id: int,
    actor: User = Depends(require("website:manage")),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    sub = db.get(WebsiteSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    sub.status = SubmissionStatus.REJECTED.value
    audit.record(db, action="website.reject", actor=actor, target_type="website_submission", target_id=sub.id)
    db.commit()
    db.refresh(sub)
    return SubmissionOut.model_validate(sub)


@router.patch("/companies/{company_id}/visibility")
def set_visibility(
    company_id: int,
    payload: VisibilityUpdate,
    actor: User = Depends(require("website:manage")),
    db: Session = Depends(get_db),
) -> dict:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    company.public_visible = payload.public_visible
    audit.record(db, action="website.visibility", actor=actor, target_type="company", target_id=company.id, company_id=company.id)
    db.commit()
    return {"company_id": company_id, "public_visible": payload.public_visible}
