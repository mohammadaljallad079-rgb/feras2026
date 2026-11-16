"""Role-specific dashboards. Each persona gets a distinct composition."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, get_current_user, permissions_of, role_slugs
from app.core.db import get_db
from app.models.business import Company, MonthlyReport, ReportValue, ReportingPeriod
from app.models.enums import CompanyStatus, DirectiveStatus, OpportunityStatus, ReportStatus
from app.models.identity import User
from app.models.operations import (
    AccountingEntry,
    AdvisorMessage,
    AiQuery,
    Employee,
    ExecutiveDirective,
    Lead,
    Opportunity,
    ServiceRequest,
    WebsiteSubmission,
)
from app.schemas import DashboardAction, DashboardCard, DashboardOut

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


def _card(key, ar, en, value, hint_ar=None, hint_en=None, href=None) -> DashboardCard:
    return DashboardCard(
        key=key, label_ar=ar, label_en=en, value=value, hint_ar=hint_ar, hint_en=hint_en, href=href
    )


@router.get("/period")
def current_period(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """The reporting period the platform is currently working in.

    Every PDF screen shows «الفترة الحالية: 2026-10 — الاستحقاق 2026-11-05» in the
    sidebar, so the shell needs this independent of any role's dashboard cards.
    """
    row = db.execute(
        select(ReportingPeriod).order_by(ReportingPeriod.year.desc(), ReportingPeriod.month.desc())
    ).scalars().first()
    if row is None:
        return {"period": None}
    label = f"{row.year:04d}-{row.month:02d}"
    return {"period": {"label": label, "due": row.due_on.isoformat() if row.due_on else None}}


@router.get("", response_model=DashboardOut)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardOut:
    role = _primary_role(user)
    perms = permissions_of(user)
    allowed = allowed_company_ids(db, user)
    cards: list[DashboardCard] = []
    sections: list[dict] = []
    banner_ar: str | None = None
    banner_en: str | None = None
    actions: list[DashboardAction] = []

    def company_scope(stmt, col):
        if allowed is not None:
            return stmt.where(col.in_(allowed or {-1}))
        return stmt

    if role == "owner":
        # PDF page 5: six clickable KPIs in this exact order.
        active = db.execute(
            company_scope(select(func.count(Company.id)).where(Company.status == CompanyStatus.ACTIVE.value), Company.id)
        ).scalar_one()
        approved_period = db.execute(
            select(func.count(MonthlyReport.id)).where(
                MonthlyReport.status.in_([ReportStatus.APPROVED.value, ReportStatus.FORWARDED.value])
            )
        ).scalar_one()
        late = db.execute(
            select(func.count(MonthlyReport.id)).where(MonthlyReport.status == ReportStatus.RETURNED.value)
        ).scalar_one()
        decisions = db.execute(
            select(func.count(Opportunity.id)).where(
                Opportunity.status.in_([OpportunityStatus.SUBMITTED.value, OpportunityStatus.UNDER_REVIEW.value])
            )
        ).scalar_one()
        open_directives = db.execute(
            select(func.count(ExecutiveDirective.id)).where(
                ExecutiveDirective.status != DirectiveStatus.COMPLETED.value
            )
        ).scalar_one()
        leads = db.execute(select(func.count(Lead.id))).scalar_one()
        cards = [
            _card("companies", "شركات نشطة", "Active companies", active, href="/companies"),
            _card("approved_period", "تقارير معتمدة للفترة", "Approved reports (period)", approved_period, href="/reports"),
            _card("late_reports", "تقارير متأخرة", "Late reports", late, href="/reports"),
            _card("decisions", "قرارات بانتظارك", "Pending decisions", decisions, href="/opportunities"),
            _card("open_directives", "توجيهات مفتوحة", "Open directives", open_directives, href="/directives"),
            _card("leads", "عملاء محتملون", "Leads", leads, href="/leads"),
        ]
        # Group summary: each company in its own currency, never summed (PDF p.5).
        rows = []
        companies = db.execute(company_scope(select(Company), Company.id)).scalars().all()
        for company in companies:
            last = db.execute(
                select(MonthlyReport)
                .where(
                    MonthlyReport.company_id == company.id,
                    MonthlyReport.status.in_([ReportStatus.APPROVED.value, ReportStatus.FORWARDED.value]),
                )
                .order_by(MonthlyReport.reviewed_at.desc().nullslast())
            ).scalars().first()
            revenue = None
            if last is not None:
                revenue = db.execute(
                    select(ReportValue.value_number)
                    .where(ReportValue.report_id == last.id, ReportValue.value_number.is_not(None))
                    .limit(1)
                ).scalar_one_or_none()
            ownership = "إدارة فقط (0%)" if not company.ownership_percent or float(company.ownership_percent) == 0 else f"{company.ownership_percent}%"
            rows.append(
                [
                    company.name_ar,
                    ownership,
                    company.currency,
                    (
                        f"{revenue:,.0f} {f'({last.period.year:04d}-{last.period.month:02d})' if last and last.period else ''}".strip()
                        if revenue is not None
                        else "—"
                    ),
                    "منتظم" if last is not None else "لا تقرير",
                ]
            )
        sections.append(
            {
                "key": "group_summary",
                "title_ar": "ملخص المجموعة (كل شركة بعملتها دون جمع)",
                "title_en": "Group summary (each company in its own currency, not summed)",
                "columns": [
                    {"ar": "الشركة", "en": "Company"},
                    {"ar": "الملكية", "en": "Ownership"},
                    {"ar": "العملة", "en": "Currency"},
                    {"ar": "إيراد آخر تقرير معتمد", "en": "Revenue, last approved"},
                    {"ar": "الحالة", "en": "Status"},
                ],
                "rows": rows,
            }
        )
        # Advisor messages addressed to the owner (PDF p.5).
        advisor_rows = [
            [m.subject, m.category]
            for m in db.execute(
                select(AdvisorMessage).where(AdvisorMessage.recipient_id == user.id)
            ).scalars().all()
        ]
        sections.append(
            {
                "key": "advisor_messages",
                "title_ar": "رسائل المستشار الموجهة إليك",
                "title_en": "Advisor messages addressed to you",
                "columns": [{"ar": "العنوان", "en": "Title"}, {"ar": "النوع", "en": "Type"}],
                "rows": advisor_rows,
            }
        )
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
        # PDF p.22: exactly four cards, in this order.
        cards = [
            _card("companies", "شركتك", "Your company", len(my_companies), href="/companies"),
            _card("requests", "طلبات مفتوحة", "Open requests", requests, href="/service-requests"),
            _card("leads", "عملاء محولون", "Transferred leads", leads, href="/leads"),
            _card("directives", "توجيهاتي", "My directives", directives, href="/directives"),
        ]
        # PDF p.22: the banner names the period, the company and the days left.
        banner_ar, banner_en = _period_banner(db, my_companies)
        # PDF p.22: the five actions that start the monthly work.
        actions = [
            DashboardAction(label_ar="تقرير جديد", label_en="New report", href="/reports"),
            DashboardAction(label_ar="طلب خدمة", label_en="Service request", href="/service-requests"),
            DashboardAction(label_ar="إضافة موظف", label_en="Add employee", href="/hr"),
            DashboardAction(label_ar="العملاء المحولون", label_en="Transferred leads", href="/leads"),
            DashboardAction(label_ar="توجيهاتي", label_en="My directives", href="/directives"),
        ]
    elif role == "accountant":
        awaiting = db.execute(
            select(func.count(MonthlyReport.id)).where(MonthlyReport.status == ReportStatus.SUBMITTED.value)
        ).scalar_one()
        approved = db.execute(
            select(func.count(MonthlyReport.id)).where(MonthlyReport.status == ReportStatus.APPROVED.value)
        ).scalar_one()
        entries = db.execute(select(func.count(AccountingEntry.id))).scalar_one()
        # PDF p.24: three cards.
        cards = [
            _card("awaiting_review", "تقارير بانتظار المراجعة", "Reports awaiting review", awaiting, href="/reports"),
            _card("awaiting_forward", "معتمدة وغير مرسلة للإدارة", "Approved, not yet sent", approved, href="/reports"),
            _card("entries", "سجلات القابضة", "Holding records", entries, href="/accounting"),
        ]
        # PDF p.24: the three accounting entry buttons.
        actions = [
            DashboardAction(label_ar="مصروف", label_en="Expense", href="/accounting?kind=expense"),
            DashboardAction(label_ar="فاتورة", label_en="Invoice", href="/accounting?kind=invoice"),
            DashboardAction(label_ar="عمولة", label_en="Commission", href="/accounting?kind=commission"),
        ]
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
        assistant_tasks = db.execute(
            select(func.count(AiQuery.id)).where(AiQuery.user_id == user.id)
        ).scalar_one()
        # PDF p.26: six cards.
        cards = [
            _card("group_reports", "تقارير المجموعة المعتمدة", "Approved group reports", group_reports, href="/reports"),
            _card("leads", "عملاء محتملون", "Leads", my_leads, href="/leads"),
            _card("opportunities", "فرص", "Opportunities", my_opps, href="/opportunities"),
            _card("submissions", "طلبات من الموقع", "Website submissions", submissions, href="/website"),
            _card("advisor", "رسائل المستشار", "Advisor messages", advisor, href="/advisor"),
            _card("assistant", "مهام من المساعد", "Assistant tasks", assistant_tasks, href="/assistant"),
        ]
    elif role == "marketer":
        assigned = db.execute(select(func.count(Lead.id)).where(Lead.assigned_to_id == user.id)).scalar_one()
        complaints = db.execute(
            select(func.count(ServiceRequest.id)).where(
                or_(ServiceRequest.recipient_id == user.id, ServiceRequest.created_by_id == user.id)
            )
        ).scalar_one()
        # PDF p.27: leads plus owner complaints.
        cards = [
            _card("leads", "عملائي", "My leads", assigned, href="/leads"),
            _card("complaints", "شكاوى المالك", "Owner complaints", complaints, href="/service-requests"),
        ]
    elif role == "designer":
        design_requests = db.execute(
            select(func.count(ServiceRequest.id)).where(ServiceRequest.recipient_id == user.id)
        ).scalar_one()
        # PDF p.28: only the design requests assigned to this designer.
        cards = [
            _card("design_requests", "طلبات الخدمات", "Service requests", design_requests, href="/service-requests")
        ]
    elif role == "advisor":
        messages = db.execute(
            select(func.count(AdvisorMessage.id)).where(AdvisorMessage.recipient_id == user.id)
        ).scalar_one()
        # PDF p.29: the advisor sees only their own messages.
        cards = [_card("messages", "رسائلي", "My messages", messages, href="/advisor")]
    else:
        assigned = db.execute(
            select(func.count(ServiceRequest.id)).where(ServiceRequest.recipient_id == user.id)
        ).scalar_one()
        cards = [_card("requests", "طلبات الخدمة المُسندة", "Assigned service requests", assigned)]

    title_ar, title_en = DASH_TITLES.get(role, ("لوحة التحكم", "Dashboard"))
    return DashboardOut(
        role=role,
        title_ar=title_ar,
        title_en=title_en,
        cards=cards,
        sections=sections,
        banner_ar=banner_ar,
        banner_en=banner_en,
        actions=actions,
    )


def _period_banner(db: Session, company_ids: list[int]) -> tuple[str | None, str | None]:
    """«تقرير 2026-10 — شركة نمو التقنية: يستحق بعد 3 أيام» (PDF page 22)."""
    period = db.execute(
        select(ReportingPeriod).order_by(ReportingPeriod.year.desc(), ReportingPeriod.month.desc())
    ).scalars().first()
    if period is None:
        return None, None
    label = f"{period.year:04d}-{period.month:02d}"
    company = None
    if company_ids:
        company = db.get(Company, company_ids[0])
    days = (period.due_on - date.today()).days if period.due_on else None
    if days is None:
        return f"تقرير {label}", f"Report {label}"
    if days > 0:
        tail_ar, tail_en = f"يستحق بعد {days} أيام", f"due in {days} day(s)"
    elif days == 0:
        tail_ar, tail_en = "يستحق اليوم", "due today"
    else:
        tail_ar, tail_en = f"متأخر {abs(days)} أيام", f"{abs(days)} day(s) late"
    # An unassigned manager has no company scope yet; the banner still shows the
    # period and the deadline without an empty name slot.
    if company is None:
        return f"تقرير {label}: {tail_ar}", f"Report {label}: {tail_en}"
    return (
        f"تقرير {label} — {company.name_ar}: {tail_ar}",
        f"Report {label} — {company.name_en}: {tail_en}",
    )
