"""Permission-constrained retrieval that grounds assistant answers in records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import GroundedContext
from app.api.deps import allowed_company_ids, permissions_of
from app.models.business import Company, MonthlyReport, ReportingPeriod, ReportValue
from app.models.enums import ReportStatus
from app.models.identity import User
from app.models.operations import AccountingEntry, ExecutiveDirective, ServiceRequest


def gather_context(db: Session, user: User, *, company_id: int | None, period_id: int | None) -> GroundedContext:
    perms = permissions_of(user)
    allowed = allowed_company_ids(db, user)
    ctx = GroundedContext()

    def company_ok(cid: int) -> bool:
        return allowed is None or cid in allowed

    if "company:view" in perms:
        stmt = select(Company)
        if allowed is not None:
            stmt = stmt.where(Company.id.in_(allowed or {-1}))
        if company_id is not None:
            stmt = stmt.where(Company.id == company_id)
        for c in db.execute(stmt.limit(50)).scalars().all():
            ctx.facts.append(
                f"company#{c.id} code={c.code} name_ar={c.name_ar} sector={c.sector} status={c.status} currency={c.currency}"
            )
            ctx.sources.append({"kind": "company", "ref": str(c.id), "label": f"شركة: {c.name_ar}", "url": f"/companies/{c.id}"})

    if "report:view_own" in perms or "report:view_all" in perms:
        stmt = select(MonthlyReport)
        if "report:view_all" not in perms and allowed is not None:
            stmt = stmt.where(MonthlyReport.company_id.in_(allowed or {-1}))
        if company_id is not None:
            stmt = stmt.where(MonthlyReport.company_id == company_id)
        if period_id is not None:
            stmt = stmt.where(MonthlyReport.period_id == period_id)
        reports = db.execute(stmt.limit(25)).scalars().all()
        for r in reports:
            period = db.get(ReportingPeriod, r.period_id)
            # Currency rule: each amount is reported in the company's own currency
            # and is never summed with amounts in another currency.
            amounts = [
                f"{v.field.name_ar}={v.value_number} {r.currency}"
                for v in r.values
                if v.value_number is not None and v.field is not None
            ]
            ctx.facts.append(
                f"report#{r.id} company={r.company.name_ar} period={period.label_ar if period else r.period_id} "
                f"status={r.status} currency={r.currency} values=[{'; '.join(amounts)}]"
            )
            ctx.sources.append({"kind": "report", "ref": str(r.id), "label": f"تقرير {r.company.name_ar}", "url": f"/reports/{r.id}"})

    if "accounting:view" in perms:
        stmt = select(AccountingEntry)
        if allowed is not None:
            stmt = stmt.where(AccountingEntry.company_id.in_(allowed or {-1}))
        if company_id is not None:
            stmt = stmt.where(AccountingEntry.company_id == company_id)
        for e in db.execute(stmt.limit(25)).scalars().all():
            ctx.facts.append(
                f"accounting#{e.id} kind={e.kind} ref={e.reference} amount={e.amount} {e.currency} status={e.status}"
            )
            ctx.sources.append({"kind": "accounting", "ref": str(e.id), "label": f"قيد محاسبي {e.reference}", "url": f"/accounting/{e.id}"})

    if "service:view" in perms:
        stmt = select(ServiceRequest).where(ServiceRequest.recipient_id == user.id)
        for s in db.execute(stmt.limit(25)).scalars().all():
            ctx.facts.append(f"service_request#{s.id} subject={s.subject} status={s.status} priority={s.priority}")
            ctx.sources.append({"kind": "service_request", "ref": str(s.id), "label": f"طلب خدمة {s.subject}", "url": f"/service-requests/{s.id}"})

    if "directive:view" in perms:
        stmt = select(ExecutiveDirective).where(ExecutiveDirective.recipient_id == user.id)
        for d in db.execute(stmt.limit(25)).scalars().all():
            ctx.facts.append(f"directive#{d.id} title={d.title} status={d.status} follow_up={d.follow_up_on}")
            ctx.sources.append({"kind": "directive", "ref": str(d.id), "label": f"توجيه {d.title}", "url": f"/directives/{d.id}"})

    return ctx
