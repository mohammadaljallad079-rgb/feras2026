"""Role-specific dashboards. Each persona gets a distinct composition."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, get_current_user, permissions_of, role_slugs
from app.core.db import get_db
from app.models.business import Company, MonthlyReport, ReportingPeriod
from app.models.enums import CompanyStatus, DirectiveStatus, ReportStatus
from app.models.identity import User
from app.models.operations import (
    AdvisorMessage,
    Employee,
    ExecutiveDirective,
    Lead,
    Opportunity,
    ServiceRequest,
    WebsiteSubmission,
)
from app.schemas import DashboardCard, DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DASH_TITLES = {
    "owner": ("لوحة المالك", "Owner dashboard"),
    "company_manager": ("لوحة مدير الشركة", "Company manager dashboard"),
    "accountant": ("لوحة المحاسب", "Accountant dashboard"),
    "business_developer": ("لوحة مطوّر الأعمال", "Business developer dashboard"),
    "marketer": ("لوحة المسوّق", "Marketer dashboard"),
    "designer": ("لوحة المصمّم", "Designer dashboard"),
    "advisor": ("لوحة المستشار", "Advisor dashboard"),
    "service_specialist": ("لوحة أخصائي الخدمات", "Service specialist dashboard"),
}


def _primary_role(user: User) -> str:
    slugs = role_slugs(user)
    for candidate in DASH_TITLES:
        if candidate in slugs:
            return candidate
    return "owner" if "owner" in slugs else (slugs[0] if slugs else "owner")


def _card(key, ar, en, value, hint_ar=None, hint_en=None) -> DashboardCard:
    return DashboardCard(key=key, label_ar=ar, label_en=en, value=value, hint_ar=hint_ar, hint_en=hint_en)


@router.get("", response_model=DashboardOut)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardOut:
    role = _primary_role(user)
    perms = permissions_of(user)
    allowed = allowed_company_ids(db, user)
    cards: list[DashboardCard] = []
    sections: list[dict] = []

    def company_scope(stmt, col):
        if allowed is not None:
            return stmt.where(col.in_(allowed or {-1}))
        return stmt

    if role == "owner":
        total = db.execute(company_scope(select(func.count(Company.id)), Company.id)).scalar_one()
        active = db.execute(
            company_scope(select(func.count(Company.id)).where(Company.status == CompanyStatus.ACTIVE.value), Company.id)
        ).scalar_one()
        pending = db.execute(
            select(func.count(MonthlyReport.id)).where(
                MonthlyReport.status.in_([ReportStatus.SUBMITTED.value, ReportStatus.APPROVED.value])
            )
        ).scalar_one()
        forwarded = db.execute(
            select(func.count(MonthlyReport.id)).where(MonthlyReport.status == ReportStatus.FORWARDED.value)
        ).scalar_one()
        overdue = db.execute(
            select(func.count(ExecutiveDirective.id)).where(
                ExecutiveDirective.follow_up_on.is_not(None),
                ExecutiveDirective.follow_up_on < date.today(),
                ExecutiveDirective.status != DirectiveStatus.COMPLETED.value,
            )
        ).scalar_one()
        cards = [
            _card("companies", "إجمالي الشركات", "Total companies", total),
            _card("active", "شركات مفعّلة", "Active companies", active),
            _card("awaiting", "تقارير بانتظار الإجراء", "Reports awaiting action", pending),
            _card("forwarded", "تقارير مُرسلة للإدارة", "Reports sent to management", forwarded),
            _card("overdue_directives", "توجيهات متأخرة", "Overdue directives", overdue),
        ]
    elif role == "company_manager":
        my_companies = sorted(allowed or set())
        open_reports = db.execute(
            select(func.count(MonthlyReport.id)).where(MonthlyReport.status.in_([ReportStatus.DRAFT.value, ReportStatus.RETURNED.value]))
        ).scalar_one()
        requests = db.execute(
            select(func.count(ServiceRequest.id)).where(ServiceRequest.recipient_id == user.id)
        ).scalar_one()
        employees = db.execute(
            company_scope(select(func.count(Employee.id)), Employee.company_id)
        ).scalar_one()
        directives = db.execute(
            select(func.count(ExecutiveDirective.id)).where(ExecutiveDirective.recipient_id == user.id)
        ).scalar_one()
        leads = db.execute(
            select(func.count(Lead.id)).where(Lead.assigned_to_id == user.id)
        ).scalar_one()
        cards = [
            _card("companies", "شركاتي", "My companies", len(my_companies)),
            _card("open_reports", "تقارير مفتوحة", "Open reports", open_reports),
            _card("requests", "طلبات خدمة مُسندة", "Assigned service requests", requests),
            _card("employees", "الموظفون", "Employees", employees),
            _card("directives", "توجيهات مستلمة", "Received directives", directives),
            _card("leads", "فرص محوّلة", "Transferred leads", leads),
        ]
    elif role == "accountant":
        awaiting = db.execute(
            select(func.count(MonthlyReport.id)).where(MonthlyReport.status == ReportStatus.SUBMITTED.value)
        ).scalar_one()
        approved = db.execute(
            select(func.count(MonthlyReport.id)).where(MonthlyReport.status == ReportStatus.APPROVED.value)
        ).scalar_one()
        cards = [
            _card("awaiting_review", "تقارير بانتظار المراجعة", "Reports awaiting review", awaiting),
            _card("awaiting_forward", "تقارير معتمدة بانتظار الإرسال", "Approved awaiting forwarding", approved),
        ]
        sections.append({"key": "accounting", "route": "/accounting", "title_ar": "القيود المالية", "title_en": "Financial records"})
    elif role == "business_developer":
        group_reports = db.execute(
            select(func.count(MonthlyReport.id)).where(MonthlyReport.status == ReportStatus.FORWARDED.value)
        ).scalar_one()
        my_leads = db.execute(select(func.count(Lead.id)).where(Lead.assigned_to_id == user.id)).scalar_one()
        my_opps = db.execute(select(func.count(Opportunity.id)).where(Opportunity.created_by_id == user.id)).scalar_one()
        submissions = db.execute(select(func.count(WebsiteSubmission.id))).scalar_one()
        advisor = db.execute(
            select(func.count(AdvisorMessage.id)).where(AdvisorMessage.recipient_id == user.id)
        ).scalar_one()
        cards = [
            _card("group_reports", "تقارير المجموعة المعتمدة", "Approved group reports", group_reports),
            _card("leads", "عملائي المحتملون", "My leads", my_leads),
            _card("opportunities", "الفرص", "Opportunities", my_opps),
            _card("submissions", "طلبات الموقع", "Public submissions", submissions),
            _card("advisor", "رسائل المستشار", "Advisor messages", advisor),
        ]
    elif role == "marketer":
        assigned = db.execute(select(func.count(Lead.id)).where(Lead.assigned_to_id == user.id)).scalar_one()
        complaints = db.execute(
            select(func.count(ServiceRequest.id)).where(
                or_(ServiceRequest.recipient_id == user.id, ServiceRequest.created_by_id == user.id)
            )
        ).scalar_one()
        cards = [
            _card("leads", "عملاء محتملون مُسندون", "Assigned leads", assigned),
            _card("complaints", "شكاوى المالك", "Owner complaints", complaints),
        ]
    elif role == "designer":
        design_requests = db.execute(
            select(func.count(ServiceRequest.id)).where(ServiceRequest.recipient_id == user.id)
        ).scalar_one()
        cards = [_card("design_requests", "طلبات التصميم المُسندة", "Assigned design requests", design_requests)]
    elif role == "advisor":
        messages = db.execute(
            select(func.count(AdvisorMessage.id)).where(AdvisorMessage.recipient_id == user.id)
        ).scalar_one()
        cards = [_card("messages", "الرسائل ذات الصلة", "Relevant messages", messages)]
    else:
        assigned = db.execute(
            select(func.count(ServiceRequest.id)).where(ServiceRequest.recipient_id == user.id)
        ).scalar_one()
        cards = [_card("requests", "طلبات الخدمة المُسندة", "Assigned service requests", assigned)]

    title_ar, title_en = DASH_TITLES.get(role, ("لوحة التحكم", "Dashboard"))
    return DashboardOut(role=role, title_ar=title_ar, title_en=title_en, cards=cards, sections=sections)
