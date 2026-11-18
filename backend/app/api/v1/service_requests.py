"""Service requests with an activity thread and recipient-scoped visibility."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, assert_company_access, require
from app.core.db import get_db
from app.models.business import Company
from app.models.enums import RequestPriority, RequestStatus, ServiceType
from app.models.identity import Role, User, UserRole
from app.models.operations import ServiceRequest, ServiceRequestReply
from app.schemas import (
    ComplaintCreate,
    ReplyCreate,
    ReplyOut,
    ServiceRequestCreate,
    ServiceRequestOut,
    ServiceRequestUpdate,
)
from app.services import audit, mail

router = APIRouter(prefix="/service-requests", tags=["service-requests"])


@router.get("", response_model=list[ServiceRequestOut])
def list_requests(
    box: str = "all",
    user: User = Depends(require("service:view")),
    db: Session = Depends(get_db),
) -> list[ServiceRequestOut]:
    stmt = select(ServiceRequest)
    allowed = allowed_company_ids(db, user)
    if box == "inbox":
        stmt = stmt.where(ServiceRequest.recipient_id == user.id)
    elif box == "sent":
        stmt = stmt.where(ServiceRequest.created_by_id == user.id)
    else:
        # Being the recipient or the creator is itself the grant, so an assigned
        # specialist sees their inbox even without a company-scope row.
        own = or_(ServiceRequest.recipient_id == user.id, ServiceRequest.created_by_id == user.id)
        if allowed is None:
            stmt = stmt.where(own)
        else:
            stmt = stmt.where(or_(own, ServiceRequest.company_id.in_(allowed or {-1})))
    rows = db.execute(stmt.order_by(ServiceRequest.id.desc())).scalars().all()
    return [ServiceRequestOut.model_validate(r) for r in rows]


def _visible(db: Session, user: User, request_id: int) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    perms = _perms(user)
    # Being the recipient or the creator is itself the grant: recipients see only
    # their assigned requests, and they must be able to act on them regardless of
    # a company-scope grant. Anyone else needs service:assign *and* company access.
    if req.recipient_id == user.id or req.created_by_id == user.id:
        return req
    if "service:assign" not in perms:
        raise HTTPException(status_code=404, detail="Request not found")
    assert_company_access(db, user, req.company_id)
    return req


@router.post("", response_model=ServiceRequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: ServiceRequestCreate,
    actor: User = Depends(require("service:create")),
    db: Session = Depends(get_db),
) -> ServiceRequestOut:
    assert_company_access(db, actor, payload.company_id)
    if payload.service_type not in {t.value for t in ServiceType}:
        raise HTTPException(status_code=422, detail="Unknown service type")
    if payload.priority not in {p.value for p in RequestPriority}:
        raise HTTPException(status_code=422, detail="Unknown priority")
    recipient_id = payload.recipient_id
    if recipient_id is None:
        # §6.4: "the request is routed to the specialist by service type". The
        # specialist role carries the service:reply grant and is chosen in
        # registration order when several exist.
        recipient_id = db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.slug == "service_specialist", User.is_active.is_(True))
            .order_by(User.id)
        ).scalars().first()
        recipient_id = recipient_id.id if recipient_id else None
    if recipient_id is None or db.get(User, recipient_id) is None:
        raise HTTPException(status_code=422, detail="Recipient not found")
    req = ServiceRequest(
        **payload.model_dump(exclude={"recipient_id"}),
        recipient_id=recipient_id,
        created_by_id=actor.id,
    )
    db.add(req)
    db.flush()
    audit.record(db, action="service_request.create", actor=actor, target_type="service_request", target_id=req.id, company_id=req.company_id)
    db.commit()
    db.refresh(req)
    # Table 5: «الطلب يوجَّه للمختص حسب نوع الخدمة، ويصله بريد».
    recipient = db.get(User, recipient_id)
    if recipient is not None:
        company = db.get(Company, req.company_id)
        mail.notify(
            [recipient.email],
            mail.service_request_routed_email(
                recipient.locale or "ar",
                subject=req.subject,
                company=(company.name_ar if company else "—"),
                service_type=req.service_type or "—",
            ),
        )
    return ServiceRequestOut.model_validate(req)


@router.post("/complaint", response_model=ServiceRequestOut, status_code=status.HTTP_201_CREATED)
def send_complaint(
    payload: ComplaintCreate,
    actor: User = Depends(require("service:create")),
    db: Session = Depends(get_db),
) -> ServiceRequestOut:
    """Table 5: the marketer's «إرسال شكوى للمالك» — one owner recipient only.

    The complaint is a service request addressed to the sole owner. The marketer
    holds ``service:create`` but no ``service:view``, so it does not appear in
    their own list; it surfaces on the owner's dashboard and inbox.
    """
    if not payload.body.strip():
        raise HTTPException(status_code=422, detail="Complaint text is required")
    owner = db.execute(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.slug == "owner", User.is_active.is_(True))
        .order_by(User.id)
    ).scalars().first()
    if owner is None:
        raise HTTPException(status_code=409, detail="No owner account exists to receive the complaint")
    # The marketer may be scoped to one company; use it, else the first company.
    allowed = sorted(allowed_company_ids(db, actor) or set())
    company_id = payload.company_id if payload.company_id is not None else (allowed[0] if allowed else None)
    if company_id is None:
        raise HTTPException(status_code=422, detail="A company is required")
    assert_company_access(db, actor, company_id)
    req = ServiceRequest(
        subject=payload.subject or "شكوى للمالك",
        body=payload.body,
        company_id=company_id,
        created_by_id=actor.id,
        recipient_id=owner.id,
        priority=RequestPriority.NORMAL.value,
        status=RequestStatus.NEW.value,
    )
    db.add(req)
    db.flush()
    audit.record(db, action="service_request.complaint", actor=actor, target_type="service_request", target_id=req.id, company_id=req.company_id)
    db.commit()
    db.refresh(req)
    # Table 5: «ترسل للمالك وحده» — one owner recipient, notified by email.
    company = db.get(Company, req.company_id)
    mail.notify([owner.email], mail.complaint_email(
        owner.locale or "ar",
        body=req.body,
        company=(company.name_ar if company else "—"),
    ))
    return ServiceRequestOut.model_validate(req)


@router.get("/{request_id}", response_model=ServiceRequestOut)
def get_request(
    request_id: int,
    user: User = Depends(require("service:view")),
    db: Session = Depends(get_db),
) -> ServiceRequestOut:
    return ServiceRequestOut.model_validate(_visible(db, user, request_id))


@router.get("/{request_id}/thread", response_model=list[ReplyOut])
def thread(
    request_id: int,
    user: User = Depends(require("service:view")),
    db: Session = Depends(get_db),
) -> list[ReplyOut]:
    _visible(db, user, request_id)
    rows = db.execute(
        select(ServiceRequestReply).where(ServiceRequestReply.request_id == request_id).order_by(ServiceRequestReply.id)
    ).scalars().all()
    return [ReplyOut.model_validate(r) for r in rows]


@router.post("/{request_id}/replies", response_model=ReplyOut, status_code=status.HTTP_201_CREATED)
def add_reply(
    request_id: int,
    payload: ReplyCreate,
    actor: User = Depends(require("service:reply")),
    db: Session = Depends(get_db),
) -> ReplyOut:
    req = _visible(db, actor, request_id)
    if payload.new_status is not None and payload.new_status not in {s.value for s in RequestStatus}:
        raise HTTPException(status_code=422, detail="Unknown status")
    reply = ServiceRequestReply(
        request_id=req.id,
        author_id=actor.id,
        body=payload.body,
        is_status_change=payload.new_status is not None,
        new_status=payload.new_status,
    )
    db.add(reply)
    if payload.new_status is not None:
        req.status = payload.new_status
    audit.record(db, action="service_request.reply", actor=actor, target_type="service_request", target_id=req.id, company_id=req.company_id)
    db.commit()
    db.refresh(reply)
    return ReplyOut.model_validate(reply)


@router.patch("/{request_id}", response_model=ServiceRequestOut)
def update_request(
    request_id: int,
    payload: ServiceRequestUpdate,
    actor: User = Depends(require("service:assign")),
    db: Session = Depends(get_db),
) -> ServiceRequestOut:
    req = _visible(db, actor, request_id)
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in {s.value for s in RequestStatus}:
        raise HTTPException(status_code=422, detail="Unknown status")
    for key, value in changes.items():
        setattr(req, key, value)
    audit.record(db, action="service_request.update", actor=actor, target_type="service_request", target_id=req.id, company_id=req.company_id)
    db.commit()
    db.refresh(req)
    return ServiceRequestOut.model_validate(req)


def _perms(user: User) -> set[str]:
    out: set[str] = set()
    for ur in user.roles:
        if ur.role:
            out |= ur.role.permission_codes
    return out
