"""Website administration: CMS content, public form inbox, conversion."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require, require_any
from app.core.db import get_db
from app.models.business import Company
from app.models.enums import RequestPriority, RequestStatus, ServiceType, SubmissionKind, SubmissionStatus
from app.models.identity import Role, User, UserRole
from app.models.operations import Lead, Opportunity, ServiceRequest, WebsiteSubmission, WebsiteSubmissionEvent
from app.models.site import SiteNavLink, SiteSection, SiteService, SiteSetting, SiteSlide
from app.schemas import (
    CompanyProfileUpdate,
    SiteNavLinkCreate,
    SiteNavLinkOut,
    SiteNavLinkUpdate,
    SiteSectionOut,
    SiteSectionUpdate,
    SiteServiceCreate,
    SiteServiceOut,
    SiteServiceUpdate,
    SiteSettingOut,
    SiteSettingUpdate,
    SiteSlideCreate,
    SiteSlideOut,
    SiteSlideUpdate,
    SubmissionConvert,
    SubmissionEventOut,
    SubmissionOut,
    SubmissionUpdate,
    VisibilityUpdate,
)
from app.services import audit, mail

router = APIRouter(prefix="/website", tags=["website"])

# The status workflow the inbox moves through (brief §7). Proposed, not assumed
# approved: the owner confirms it in the CMS.
SUBMISSION_STATUSES = [s.value for s in SubmissionStatus]

# §6.5: which internal record each kind of submission produces when the inbox
# operator takes action.
_DEFAULT_TARGET = {
    SubmissionKind.SERVICE_REQUEST.value: "service_request",
    SubmissionKind.OPPORTUNITY.value: "opportunity",
    SubmissionKind.JOB_APPLICATION.value: "job_application",
    SubmissionKind.CONTACT.value: "lead",
}

# §6.5: the public «اطلب خدمة» service labels map onto the internal four
# service types used for routing.
_SERVICE_TYPE_BY_PUBLIC = {
    "تأسيس الأعمال والخدمات المرتبطة بها": ServiceType.ACCOUNTING.value,
    "الدراسات ودراسات الجدوى": ServiceType.STUDY.value,
    "الاستشارات": ServiceType.STUDY.value,
    "التسويق والإعلان": ServiceType.MARKETING.value,
    "التوريد والتوزيع": ServiceType.ACCOUNTING.value,
    "خدمة أخرى": ServiceType.STUDY.value,
    # English labels, in case the public form is filled in English.
    "business setup": ServiceType.ACCOUNTING.value,
    "studies and feasibility": ServiceType.STUDY.value,
    "consulting": ServiceType.STUDY.value,
    "marketing and advertising": ServiceType.MARKETING.value,
    "supply and distribution": ServiceType.ACCOUNTING.value,
    "other service": ServiceType.STUDY.value,
}


@router.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(
    kind: str | None = None,
    submission_status: str | None = Query(default=None, alias="status"),
    assigned_user_id: int | None = None,
    _: User = Depends(require_any("site:submissions", "website:view")),
    db: Session = Depends(get_db),
) -> list[SubmissionOut]:
    stmt = select(WebsiteSubmission)
    if kind:
        stmt = stmt.where(WebsiteSubmission.kind == kind)
    if submission_status:
        stmt = stmt.where(WebsiteSubmission.status == submission_status)
    if assigned_user_id is not None:
        stmt = stmt.where(WebsiteSubmission.assigned_user_id == assigned_user_id)
    rows = db.execute(stmt.order_by(WebsiteSubmission.id.desc())).scalars().all()
    return [SubmissionOut.model_validate(s) for s in rows]


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    _: User = Depends(require_any("site:submissions", "website:view")),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    sub = db.get(WebsiteSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return SubmissionOut.model_validate(sub)


@router.get("/submissions/{submission_id}/history", response_model=list[SubmissionEventOut])
def submission_history(
    submission_id: int,
    _: User = Depends(require_any("site:submissions", "website:view")),
    db: Session = Depends(get_db),
) -> list[SubmissionEventOut]:
    if db.get(WebsiteSubmission, submission_id) is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    rows = (
        db.execute(
            select(WebsiteSubmissionEvent)
            .where(WebsiteSubmissionEvent.submission_id == submission_id)
            .order_by(WebsiteSubmissionEvent.id)
        )
        .scalars()
        .all()
    )
    return [SubmissionEventOut.model_validate(r) for r in rows]


@router.patch("/submissions/{submission_id}", response_model=SubmissionOut)
def update_submission(
    submission_id: int,
    payload: SubmissionUpdate,
    actor: User = Depends(require_any("site:submissions", "website:manage")),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    sub = db.get(WebsiteSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    if payload.status is not None:
        if payload.status not in SUBMISSION_STATUSES:
            raise HTTPException(status_code=422, detail={"error": "unknown_status"})
        if payload.status != sub.status:
            db.add(
                WebsiteSubmissionEvent(
                    submission_id=sub.id,
                    actor_user_id=actor.id,
                    from_status=sub.status,
                    to_status=payload.status,
                )
            )
            sub.status = payload.status
            if payload.status in (
                SubmissionStatus.COMPLETED.value,
                SubmissionStatus.CLOSED.value,
                SubmissionStatus.REJECTED.value,
            ):
                sub.reviewed_at = datetime.now(timezone.utc)

    if payload.assigned_user_id is not None:
        assignee = db.get(User, payload.assigned_user_id)
        if assignee is None:
            raise HTTPException(status_code=422, detail={"error": "unknown_assignee"})
        sub.assigned_user_id = payload.assigned_user_id
        db.add(
            WebsiteSubmissionEvent(
                submission_id=sub.id,
                actor_user_id=actor.id,
                note=f"assigned to {assignee.email}",
            )
        )

    if payload.internal_notes is not None:
        sub.internal_notes = payload.internal_notes

    audit.record(
        db,
        action="website.submission_update",
        actor=actor,
        target_type="website_submission",
        target_id=sub.id,
    )
    db.commit()
    db.refresh(sub)
    return SubmissionOut.model_validate(sub)


@router.post("/submissions/{submission_id}/convert", response_model=SubmissionOut)
def convert_submission(
    submission_id: int,
    payload: SubmissionConvert,
    actor: User = Depends(require("website:manage")),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    """§6.5 «اتخاذ إجراء»: the effect depends on the submission kind.

    A service request opens the routing modal and becomes a service request
    addressed to the specialist (with the chosen receiving company and service
    type). An opportunity becomes a draft for internal review, and a job
    application is recorded for human review only — no user is created.
    """
    sub = db.get(WebsiteSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.status == SubmissionStatus.CONVERTED.value:
        raise HTTPException(status_code=409, detail="Submission already converted")

    # The kind decides the outcome; the target is only a fallback for callers
    # that still pass it explicitly.
    target = payload.target or _DEFAULT_TARGET.get(sub.kind, "")
    if target == "lead":
        if sub.company_id is None or db.get(Company, sub.company_id) is None:
            raise HTTPException(status_code=422, detail="A registered company is required to convert to a lead")
        record = Lead(
            name=sub.name,
            contact_email=sub.email,
            contact_phone=sub.phone,
            requested_service=sub.service_type or sub.kind,
            source="website",
            company_id=sub.company_id,
            notes=sub.message,
            status="new",
        )
    elif target == "opportunity":
        if sub.company_id is None or db.get(Company, sub.company_id) is None:
            raise HTTPException(status_code=422, detail="A registered company is required to convert to an opportunity")
        record = Opportunity(
            title=sub.subject or f"{sub.name} — {sub.kind}",
            company_id=sub.company_id,
            description=sub.message,
            country=sub.country,
            attachment_file_id=sub.attachment_file_id,
            source="website",
            created_by_id=actor.id,
            status=OpportunityStatus.DRAFT.value,
        )
    elif target == "service_request":
        company_id = payload.company_id or sub.company_id
        if company_id is None or db.get(Company, company_id) is None:
            raise HTTPException(status_code=422, detail="A receiving company is required to route the service request")
        service_type = payload.service_type or _SERVICE_TYPE_BY_PUBLIC.get(sub.service_type or "", None)
        if service_type is None or service_type not in {t.value for t in ServiceType}:
            raise HTTPException(status_code=422, detail={"error": "service_type_required"})
        # §6.5: the request goes to the specialist, routed by service type.
        specialist = db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.slug == "service_specialist", User.is_active.is_(True))
            .order_by(User.id)
        ).scalars().first()
        if specialist is None:
            raise HTTPException(status_code=409, detail="No service specialist account exists")
        record = ServiceRequest(
            subject=sub.subject or f"{sub.kind}: {sub.name}",
            body=sub.message,
            service_type=service_type,
            company_id=company_id,
            created_by_id=actor.id,
            recipient_id=specialist.id,
            priority=RequestPriority.NORMAL.value,
            status=RequestStatus.NEW.value,
        )
    elif target == "job_application":
        # §6.5: «رسالة سُجل الطلب للمراجعة البشرية» — no user is created.
        record = None
    else:
        raise HTTPException(status_code=422, detail="Unknown conversion target")

    created_id: int | None = None
    if record is not None:
        db.add(record)
        db.flush()
        created_id = record.id
    db.add(
        WebsiteSubmissionEvent(
            submission_id=sub.id,
            actor_user_id=actor.id,
            from_status=sub.status,
            to_status=SubmissionStatus.CONVERTED.value,
            note=f"converted to {target} #{created_id}" if created_id else f"recorded for {target}",
        )
    )
    sub.status = SubmissionStatus.CONVERTED.value
    sub.converted_type = target
    sub.converted_id = created_id
    audit.record(db, action="website.convert", actor=actor, target_type="website_submission", target_id=sub.id, meta={"target": target, "created_id": created_id})
    db.commit()
    db.refresh(sub)
    # Table 6: «نسخة بريد لمدير الشركة والمختص» — the receiving company's manager
    # and, for a routed service request, the specialist get a copy. The message
    # names the item and the target only; it carries no financial detail.
    _notify_conversion(db, sub, target, record)
    return SubmissionOut.model_validate(sub)


_TARGET_LABEL = {
    "lead": ("عميل محتمل", "lead"),
    "opportunity": ("فرصة", "opportunity"),
    "service_request": ("طلب خدمة", "service request"),
    "job_application": ("طلب توظيف", "job application"),
}


def _notify_conversion(db: Session, sub: WebsiteSubmission, target: str, record: object | None) -> None:
    """Table 6: mail a copy to the receiving company's manager and, when the
    submission became a service request, to the specialist it was routed to."""
    company_id = getattr(record, "company_id", None) if record is not None else sub.company_id
    manager_email: str | None = None
    manager_locale = "ar"
    if company_id is not None:
        company = db.get(Company, company_id)
        if company is not None and company.manager_user_id is not None:
            manager = db.get(User, company.manager_user_id)
            if manager is not None:
                manager_email = manager.email
                manager_locale = manager.locale or "ar"
    specialist_email: str | None = None
    specialist_locale = "ar"
    if isinstance(record, ServiceRequest):
        specialist = db.get(User, record.recipient_id)
        if specialist is not None:
            specialist_email = specialist.email
            specialist_locale = specialist.locale or "ar"
    label_ar, label_en = _TARGET_LABEL.get(target, (target, target))
    item = sub.subject or sub.name
    for email, locale in ((manager_email, manager_locale), (specialist_email, specialist_locale)):
        if not email:
            continue
        mail.notify([email], mail.conversion_copy_email(locale, item=item, target_ar=label_ar, target_en=label_en))


@router.post("/submissions/{submission_id}/reject", response_model=SubmissionOut)
def reject_submission(
    submission_id: int,
    actor: User = Depends(require("website:manage")),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    sub = db.get(WebsiteSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    db.add(
        WebsiteSubmissionEvent(
            submission_id=sub.id,
            actor_user_id=actor.id,
            from_status=sub.status,
            to_status=SubmissionStatus.REJECTED.value,
        )
    )
    sub.status = SubmissionStatus.REJECTED.value
    sub.reviewed_at = datetime.now(timezone.utc)
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


@router.patch("/companies/{company_id}/profile", response_model=dict)
def set_public_profile(
    company_id: int,
    payload: CompanyProfileUpdate,
    actor: User = Depends(require("website:manage")),
    db: Session = Depends(get_db),
) -> dict:
    """Table 7: «تعديل النشاط» — the company's public activity text and an
    optional live-site link. Only public fields are touched."""
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(company, key, value)
    audit.record(db, action="website.profile", actor=actor, target_type="company", target_id=company.id, company_id=company.id)
    db.commit()
    db.refresh(company)
    return {
        "company_id": company_id,
        "public_activity_ar": company.public_activity_ar,
        "public_activity_en": company.public_activity_en,
        "website_url": company.website_url,
    }


# --- CMS: settings ----------------------------------------------------------
@router.get("/settings", response_model=list[SiteSettingOut])
def list_settings(
    _: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> list[SiteSettingOut]:
    rows = db.execute(select(SiteSetting).order_by(SiteSetting.key)).scalars().all()
    return [SiteSettingOut.model_validate(r) for r in rows]


@router.patch("/settings/{key}", response_model=SiteSettingOut)
def update_setting(
    key: str,
    payload: SiteSettingUpdate,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> SiteSettingOut:
    row = db.execute(select(SiteSetting).where(SiteSetting.key == key)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    if payload.value_ar is not None:
        row.value_ar = payload.value_ar
    if payload.value_en is not None:
        row.value_en = payload.value_en
    audit.record(db, action="site.setting_update", actor=actor, target_type="site_setting", target_id=row.id, meta={"key": key})
    db.commit()
    db.refresh(row)
    return SiteSettingOut.model_validate(row)


# --- CMS: sections ----------------------------------------------------------
@router.get("/sections", response_model=list[SiteSectionOut])
def list_sections(
    _: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> list[SiteSectionOut]:
    rows = db.execute(select(SiteSection).order_by(SiteSection.sort_order, SiteSection.id)).scalars().all()
    return [SiteSectionOut.model_validate(r) for r in rows]


@router.patch("/sections/{section_id}", response_model=SiteSectionOut)
def update_section(
    section_id: int,
    payload: SiteSectionUpdate,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> SiteSectionOut:
    row = db.get(SiteSection, section_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Section not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    audit.record(db, action="site.section_update", actor=actor, target_type="site_section", target_id=row.id, meta={"key": row.key})
    db.commit()
    db.refresh(row)
    return SiteSectionOut.model_validate(row)


# --- CMS: slides ------------------------------------------------------------
@router.get("/slides", response_model=list[SiteSlideOut])
def list_slides(
    _: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> list[SiteSlideOut]:
    rows = db.execute(select(SiteSlide).order_by(SiteSlide.sort_order, SiteSlide.id)).scalars().all()
    return [SiteSlideOut.model_validate(r) for r in rows]


@router.post("/slides", response_model=SiteSlideOut, status_code=status.HTTP_201_CREATED)
def create_slide(
    payload: SiteSlideCreate,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> SiteSlideOut:
    row = SiteSlide(**payload.model_dump())
    db.add(row)
    db.flush()
    audit.record(db, action="site.slide_create", actor=actor, target_type="site_slide", target_id=row.id)
    db.commit()
    db.refresh(row)
    return SiteSlideOut.model_validate(row)


@router.patch("/slides/{slide_id}", response_model=SiteSlideOut)
def update_slide(
    slide_id: int,
    payload: SiteSlideUpdate,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> SiteSlideOut:
    row = db.get(SiteSlide, slide_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Slide not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    audit.record(db, action="site.slide_update", actor=actor, target_type="site_slide", target_id=row.id)
    db.commit()
    db.refresh(row)
    return SiteSlideOut.model_validate(row)


@router.delete("/slides/{slide_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_slide(
    slide_id: int,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> None:
    row = db.get(SiteSlide, slide_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Slide not found")
    db.delete(row)
    audit.record(db, action="site.slide_delete", actor=actor, target_type="site_slide", target_id=slide_id)
    db.commit()


# --- CMS: services ----------------------------------------------------------
@router.get("/services", response_model=list[SiteServiceOut])
def list_services(
    _: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> list[SiteServiceOut]:
    rows = db.execute(select(SiteService).order_by(SiteService.sort_order, SiteService.id)).scalars().all()
    return [SiteServiceOut.model_validate(r) for r in rows]


@router.post("/services", response_model=SiteServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: SiteServiceCreate,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> SiteServiceOut:
    if db.execute(select(SiteService).where(SiteService.slug == payload.slug)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Service slug already exists")
    row = SiteService(**payload.model_dump())
    db.add(row)
    db.flush()
    audit.record(db, action="site.service_create", actor=actor, target_type="site_service", target_id=row.id)
    db.commit()
    db.refresh(row)
    return SiteServiceOut.model_validate(row)


@router.patch("/services/{service_id}", response_model=SiteServiceOut)
def update_service(
    service_id: int,
    payload: SiteServiceUpdate,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> SiteServiceOut:
    row = db.get(SiteService, service_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Service not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    audit.record(db, action="site.service_update", actor=actor, target_type="site_service", target_id=row.id)
    db.commit()
    db.refresh(row)
    return SiteServiceOut.model_validate(row)


# --- CMS: navigation --------------------------------------------------------
@router.get("/nav", response_model=list[SiteNavLinkOut])
def list_nav(
    location: str | None = None,
    _: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> list[SiteNavLinkOut]:
    stmt = select(SiteNavLink)
    if location:
        stmt = stmt.where(SiteNavLink.location == location)
    rows = db.execute(stmt.order_by(SiteNavLink.location, SiteNavLink.sort_order, SiteNavLink.id)).scalars().all()
    return [SiteNavLinkOut.model_validate(r) for r in rows]


@router.post("/nav", response_model=SiteNavLinkOut, status_code=status.HTTP_201_CREATED)
def create_nav(
    payload: SiteNavLinkCreate,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> SiteNavLinkOut:
    row = SiteNavLink(**payload.model_dump())
    db.add(row)
    db.flush()
    audit.record(db, action="site.nav_create", actor=actor, target_type="site_nav", target_id=row.id)
    db.commit()
    db.refresh(row)
    return SiteNavLinkOut.model_validate(row)


@router.patch("/nav/{nav_id}", response_model=SiteNavLinkOut)
def update_nav(
    nav_id: int,
    payload: SiteNavLinkUpdate,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> SiteNavLinkOut:
    row = db.get(SiteNavLink, nav_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Nav link not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    audit.record(db, action="site.nav_update", actor=actor, target_type="site_nav", target_id=row.id)
    db.commit()
    db.refresh(row)
    return SiteNavLinkOut.model_validate(row)


@router.delete("/nav/{nav_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_nav(
    nav_id: int,
    actor: User = Depends(require("site:manage")),
    db: Session = Depends(get_db),
) -> None:
    row = db.get(SiteNavLink, nav_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Nav link not found")
    db.delete(row)
    audit.record(db, action="site.nav_delete", actor=actor, target_type="site_nav", target_id=nav_id)
    db.commit()
