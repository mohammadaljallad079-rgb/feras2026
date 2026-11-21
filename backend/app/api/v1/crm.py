"""Leads and opportunities, including the owner decision workflow."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, assert_company_access, require
from app.core.db import get_db
from app.models.business import Company
from app.models.enums import LeadStatus, OpportunityStatus
from app.models.identity import User
from app.models.operations import Lead, Opportunity
from app.schemas import (
    LeadCreate,
    LeadOut,
    LeadUpdate,
    OpportunityCreate,
    OpportunityDecision,
    OpportunityOut,
    OpportunityUpdate,
)
from app.services import audit

router = APIRouter(tags=["crm"])


# --- Leads ------------------------------------------------------------------
@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    lead_status: str | None = Query(default=None, alias="status"),
    company_id: int | None = None,
    assigned_to_me: bool = False,
    user: User = Depends(require("lead:view")),
    db: Session = Depends(get_db),
) -> list[LeadOut]:
    stmt = select(Lead)
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(Lead.company_id.in_(allowed or {-1}))
    if lead_status:
        stmt = stmt.where(Lead.status == lead_status)
    if company_id:
        assert_company_access(db, user, company_id)
        stmt = stmt.where(Lead.company_id == company_id)
    if assigned_to_me:
        stmt = stmt.where(Lead.assigned_to_id == user.id)
    rows = db.execute(stmt.order_by(Lead.id.desc())).scalars().all()
    return [LeadOut.model_validate(l) for l in rows]


@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    actor: User = Depends(require("lead:manage")),
    db: Session = Depends(get_db),
) -> LeadOut:
    # Companies must be selected from registered companies.
    company = db.get(Company, payload.company_id)
    if company is None:
        raise HTTPException(status_code=422, detail="Company must be a registered company")
    assert_company_access(db, actor, payload.company_id)
    data = payload.model_dump()
    # Table 6, «حفظ وتحويل»: the lead is converted to the receiving company's
    # manager, so it lands in that manager's «عملاء محولون» without a second
    # manual step. An explicit assignee still wins.
    if data.get("assigned_to_id") is None:
        data["assigned_to_id"] = company.manager_user_id
    lead = Lead(**data)
    db.add(lead)
    db.flush()
    audit.record(db, action="lead.create", actor=actor, target_type="lead", target_id=lead.id, company_id=lead.company_id)
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    actor: User = Depends(require("lead:manage")),
    db: Session = Depends(get_db),
) -> LeadOut:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    assert_company_access(db, actor, lead.company_id)
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in {s.value for s in LeadStatus}:
        raise HTTPException(status_code=422, detail="Unknown status")
    for key, value in changes.items():
        setattr(lead, key, value)
    audit.record(db, action="lead.update", actor=actor, target_type="lead", target_id=lead.id, company_id=lead.company_id)
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


# --- Opportunities ----------------------------------------------------------
@router.get("/opportunities", response_model=list[OpportunityOut])
def list_opportunities(
    opp_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(require("opportunity:view")),
    db: Session = Depends(get_db),
) -> list[OpportunityOut]:
    stmt = select(Opportunity)
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(Opportunity.company_id.in_(allowed or {-1}))
    if opp_status:
        stmt = stmt.where(Opportunity.status == opp_status)
    rows = db.execute(stmt.order_by(Opportunity.id.desc())).scalars().all()
    return [OpportunityOut.model_validate(o) for o in rows]


@router.post("/opportunities", response_model=OpportunityOut, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    payload: OpportunityCreate,
    actor: User = Depends(require("opportunity:create")),
    db: Session = Depends(get_db),
) -> OpportunityOut:
    if db.get(Company, payload.company_id) is None:
        raise HTTPException(status_code=422, detail="Company must be a registered company")
    assert_company_access(db, actor, payload.company_id)
    opp = Opportunity(**payload.model_dump(), created_by_id=actor.id, status=OpportunityStatus.DRAFT.value)
    db.add(opp)
    db.flush()
    audit.record(db, action="opportunity.create", actor=actor, target_type="opportunity", target_id=opp.id, company_id=opp.company_id)
    db.commit()
    db.refresh(opp)
    return OpportunityOut.model_validate(opp)


@router.get("/opportunities/compare", response_model=list[OpportunityOut])
def compare_opportunities(
    ids: str = Query(description="Comma-separated opportunity ids"),
    user: User = Depends(require("opportunity:view")),
    db: Session = Depends(get_db),
) -> list[OpportunityOut]:
    """The chosen opportunities side by side.

    Reading the same records the list already returns, so it grants nothing
    extra: the company scope applies here too.
    """
    try:
        wanted = {int(part) for part in ids.split(",") if part.strip()}
    except ValueError:
        raise HTTPException(status_code=422, detail={"error": "invalid_ids"}) from None
    if not wanted:
        return []
    stmt = select(Opportunity).where(Opportunity.id.in_(wanted))
    allowed = allowed_company_ids(db, user)
    if allowed is not None:
        stmt = stmt.where(Opportunity.company_id.in_(allowed or {-1}))
    rows = db.execute(stmt.order_by(Opportunity.id)).scalars().all()
    return [OpportunityOut.model_validate(o) for o in rows]


@router.patch("/opportunities/{opp_id}", response_model=OpportunityOut)
def update_opportunity(
    opp_id: int,
    payload: OpportunityUpdate,
    actor: User = Depends(require("opportunity:create")),
    db: Session = Depends(get_db),
) -> OpportunityOut:
    """Fill in the analysis file, or record the realised outcome after approval."""
    opp = db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    assert_company_access(db, actor, opp.company_id)
    data = payload.model_dump(exclude_unset=True)
    outcome = {k: data.pop(k) for k in ("actual_return", "actual_note") if k in data}
    if data and opp.status != OpportunityStatus.DRAFT.value:
        # Past the draft the record is the owner's to decide on; only the
        # outcome fields stay open, so a submitted case cannot be rewritten
        # under the decision.
        raise HTTPException(status_code=409, detail={"error": "not_a_draft"})
    for field, value in data.items():
        setattr(opp, field, value)
    for field, value in outcome.items():
        setattr(opp, field, value)
    audit.record(
        db, action="opportunity.update", actor=actor,
        target_type="opportunity", target_id=opp.id, company_id=opp.company_id,
        meta={"fields": sorted(data) + sorted(outcome)},
    )
    db.commit()
    db.refresh(opp)
    return OpportunityOut.model_validate(opp)


@router.post("/opportunities/{opp_id}/submit", response_model=OpportunityOut)
def submit_opportunity(
    opp_id: int,
    actor: User = Depends(require("opportunity:create")),
    db: Session = Depends(get_db),
) -> OpportunityOut:
    opp = db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.status != OpportunityStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="Only drafts can be submitted")
    opp.status = OpportunityStatus.SUBMITTED.value
    opp.submitted_at = datetime.now(timezone.utc)
    audit.record(db, action="opportunity.submit", actor=actor, target_type="opportunity", target_id=opp.id, company_id=opp.company_id)
    db.commit()
    db.refresh(opp)
    return OpportunityOut.model_validate(opp)


@router.post("/opportunities/{opp_id}/decision", response_model=OpportunityOut)
def decide_opportunity(
    opp_id: int,
    payload: OpportunityDecision,
    actor: User = Depends(require("opportunity:decide")),
    db: Session = Depends(get_db),
) -> OpportunityOut:
    opp = db.get(Opportunity, opp_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.status not in {OpportunityStatus.SUBMITTED.value, OpportunityStatus.UNDER_REVIEW.value}:
        raise HTTPException(status_code=409, detail="Only submitted opportunities can be decided")
    allowed_decisions = {
        OpportunityStatus.APPROVED.value,
        OpportunityStatus.REJECTED.value,
        OpportunityStatus.DEFERRED.value,
        OpportunityStatus.UNDER_REVIEW.value,
    }
    if payload.decision not in allowed_decisions:
        raise HTTPException(status_code=422, detail="Invalid decision")
    # Table 5: rejection and deferral require a reason; approval and review do not.
    if payload.decision in {OpportunityStatus.REJECTED.value, OpportunityStatus.DEFERRED.value}:
        if not (payload.note or "").strip():
            raise HTTPException(status_code=422, detail={"error": "reason_required"})
    # «المسؤول عن المتابعة والموعد القادم» — the owner names both with the
    # decision. They do not gate the decision itself: the brief's four buttons
    # work without them.
    if payload.next_step_owner_id is not None and db.get(User, payload.next_step_owner_id) is None:
        raise HTTPException(status_code=422, detail={"error": "unknown_next_step_owner"})
    opp.status = payload.decision
    opp.decided_by_id = actor.id
    opp.decided_at = datetime.now(timezone.utc)
    opp.decision_note = payload.note
    if payload.next_step_owner_id is not None:
        opp.next_step_owner_id = payload.next_step_owner_id
    if payload.next_step_on is not None:
        opp.next_step_on = payload.next_step_on
    audit.record(db, action="opportunity.decision", actor=actor, target_type="opportunity", target_id=opp.id, company_id=opp.company_id, meta={"decision": payload.decision})
    db.commit()
    db.refresh(opp)
    return OpportunityOut.model_validate(opp)
