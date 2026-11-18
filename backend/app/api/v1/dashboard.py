"""Role-specific dashboards. Each persona gets a distinct composition."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import allowed_company_ids, get_current_user, permissions_of, role_slugs
from app.core.db import get_db
from app.models.business import Company, FormField, MonthlyReport, ReportValue, ReportingPeriod
from app.models.enums import CompanyStatus, DirectiveStatus, OpportunityStatus, ReportStatus
from app.models.identity import User
from app.models.operations import (
    AccountingEntry,
    AdvisorMessage,
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
    banner_tone: str | None = None
    actions: list[DashboardAction] = []

    def company_scope(stmt, col):
        if allowed is not None:
            return stmt.where(col.in_(allowed or {-1}))
        return stmt

    if role == "owner":
        # PDF page 5: six clickable KPIs in this exact order. The Holding's own
        # record (§7.4) is not a subsidiary, so it is excluded from the company
        # counts and the group-summary table.
        active = db.execute(
            company_scope(
                select(func.count(Company.id)).where(
                    Company.status == CompanyStatus.ACTIVE.value,
                    Company.is_holding.is_(False),
                ),
                Company.id,
            )
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
        companies = db.execute(
            company_scope(select(Company).where(Company.is_holding.is_(False)), Company.id)
        ).scalars().all()
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
                # Label the column "revenue" only when the value really is the
                # revenue field. Taking any numeric value (the previous
                # ``limit(1)``) mislabelled whichever field happened to be
                # entered first, which is a wrong financial figure rather than
                # a missing one.
                revenue = db.execute(
                    select(ReportValue.value_number)
                    .join(FormField, FormField.id == ReportValue.field_id)
                    .where(
                        ReportValue.report_id == last.id,
                        ReportValue.value_number.is_not(None),
                        or_(
                            FormField.code.ilike("%revenue%"),
                            FormField.name_ar.like("%إيراد%"),
                            FormField.name_en.ilike("%revenue%"),
                        ),
                    )
                    .order_by(ReportValue.id)
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
        # Advisor messages addressed to the owner (PDF p.5). The type is shown
        # with its Arabic label, matching the group-summary table's style.
        advisor_type_ar = {
            "recommendation": "توصية",
            "report": "تقرير",
            "suggestion": "اقتراح",
        }
        advisor_rows = [
            [m.subject, advisor_type_ar.get(m.category, m.category)]
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
        # §5.2/§11: the manager sees only their own company, so the open-report
        # count is scoped to it rather than counting every draft platform-wide.
        open_reports = db.execute(
            select(func.count(MonthlyReport.id)).where(
                MonthlyReport.company_id.in_(my_companies or {-1}),
                MonthlyReport.status.in_([ReportStatus.DRAFT.value, ReportStatus.RETURNED.value]),
            )
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
        banner_ar, banner_en, banner_tone = _period_banner(db, my_companies)
        # PDF p.22: the five actions that start the monthly work.
        actions = [
            DashboardAction(label_ar="تقرير جديد", label_en="New report", href="/reports"),
            DashboardAction(label_ar="طلب خدمة", label_en="Service request", href="/service-requests"),
            DashboardAction(label_ar="إضافة موظف", label_en="Add employee", href="/hr"),
            DashboardAction(label_ar="العملاء المحولون", label_en="Transferred leads", href="/leads"),
            DashboardAction(label_ar="توجيهاتي", label_en="My directives", href="/directives"),
        ]
        # Table 3: the isolation test — a direct link to another company's
        # report. The server refuses it and records the attempt, which is the
        # proof the check is enforced server-side, not in the UI.
        probe = db.execute(
            select(MonthlyReport.id)
            .where(MonthlyReport.company_id.notin_(my_companies or {-1}))
            .order_by(MonthlyReport.id)
            .limit(1)
        ).scalar_one_or_none()
        if probe is not None:
            actions.append(
                DashboardAction(
                    label_ar="اختبار العزل: فتح تقرير شركة أخرى",
                    label_en="Isolation test: open another company's report",
                    href=f"/reports/{probe}",
                )
            )
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
        # PDF p.24 / §5.3: «مراجعة تقرير» (to the reports) plus the three
        # accounting entry buttons.
        actions = [
            DashboardAction(label_ar="مراجعة تقرير", label_en="Review a report", href="/reports"),
            DashboardAction(label_ar="مصروف جديد", label_en="New expense", href="/accounting?kind=expense"),
            DashboardAction(label_ar="إيراد / فاتورة جديدة", label_en="New income / invoice", href="/accounting?kind=invoice"),
            DashboardAction(label_ar="عمولة جديدة", label_en="New commission", href="/accounting?kind=commission"),
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
        # Table 6: «نعم، أحلها لمطوّر الأعمال» creates a directive flagged as an
        # assistant task for the business developer, so the «مهام من المساعد»
        # card counts those tasks — not every assistant query the user ran.
        assistant_tasks = db.execute(
            select(func.count(ExecutiveDirective.id)).where(
                ExecutiveDirective.recipient_id == user.id,
                ExecutiveDirective.is_assistant_task.is_(True),
                ExecutiveDirective.status != DirectiveStatus.COMPLETED.value,
            )
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
        # Word §5.5: a single «عملائي» card plus two actions — a new lead and a
        # complaint to the owner (free text, sent to the owner alone).
        cards = [_card("leads", "عملائي", "My leads", assigned, href="/leads")]
        actions = [
            DashboardAction(label_ar="عميل محتمل جديد", label_en="New lead", href="/leads"),
            DashboardAction(label_ar="إرسال شكوى للمالك", label_en="Send a complaint to the owner", href="/leads?complaint=1"),
        ]
    elif role == "designer":
        design_requests = db.execute(
            select(func.count(ServiceRequest.id)).where(ServiceRequest.recipient_id == user.id)
        ).scalar_one()
        # PDF p.28 / §5.6: the card is «طلبات تصميم مفتوحة» and opens the
        # service requests assigned to this designer.
        cards = [
            _card("design_requests", "طلبات تصميم مفتوحة", "Open design requests", design_requests, href="/service-requests")
        ]
    elif role == "advisor":
        messages = db.execute(
            select(func.count(AdvisorMessage.id)).where(AdvisorMessage.recipient_id == user.id)
        ).scalar_one()
        # PDF p.29: the advisor sees only their own messages.
        cards = [_card("messages", "رسائلي", "My messages", messages, href="/advisor")]
        # §5.7 / Table 5: the advisor has three actions — «إضافة توصية» (to the
        # Business Developer), «تقرير» (to the Owner or Business Developer) and
        # «اقتراح» (to the Business Developer). The advisor has no approval or
        # execution permission.
        actions = [
            DashboardAction(label_ar="إضافة توصية", label_en="Add a recommendation", href="/advisor?category=recommendation"),
            DashboardAction(label_ar="تقرير", label_en="Report", href="/advisor?category=report"),
            DashboardAction(label_ar="اقتراح", label_en="Suggestion", href="/advisor?category=suggestion"),
        ]
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
        banner_tone=banner_tone,
        actions=actions,
    )


def _period_banner(db: Session, company_ids: list[int]) -> tuple[str | None, str | None, str | None]:
    """«تقرير 2026-10 — شركة نمو التقنية: يستحق بعد 3 أيام» (PDF page 22).

    The tone follows §2 / §7.5: amber while the deadline is approaching and red
    once it is late, so the reminder reads as an alert rather than plain text.
    """
    period = db.execute(
        select(ReportingPeriod).order_by(ReportingPeriod.year.desc(), ReportingPeriod.month.desc())
    ).scalars().first()
    if period is None:
        return None, None, None
    label = f"{period.year:04d}-{period.month:02d}"
    company = None
    if company_ids:
        company = db.get(Company, company_ids[0])
    days = (period.due_on - date.today()).days if period.due_on else None
    if days is None:
        return f"تقرير {label}", f"Report {label}", None
    if days > 3:
        tone = "info"
        tail_ar, tail_en = f"يستحق بعد {days} أيام", f"due in {days} day(s)"
    elif days > 0:
        tone = "warn"
        tail_ar, tail_en = f"يستحق بعد {days} أيام", f"due in {days} day(s)"
    elif days == 0:
        tone = "warn"
        tail_ar, tail_en = "يستحق اليوم", "due today"
    else:
        tone = "bad"
        tail_ar, tail_en = f"متأخر {abs(days)} أيام", f"{abs(days)} day(s) late"
    # An unassigned manager has no company scope yet; the banner still shows the
    # period and the deadline without an empty name slot.
    if company is None:
        return f"تقرير {label}: {tail_ar}", f"Report {label}: {tail_en}", tone
    return (
        f"تقرير {label} — {company.name_ar}: {tail_ar}",
        f"Report {label} — {company.name_en}: {tail_en}",
        tone,
    )
