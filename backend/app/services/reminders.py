"""Monthly-report deadline reminders (§7.5, §12).

The brief replaces the simulation's date switch with real scheduling: a reminder
goes out three days before the due date, again on the due date, and then daily
once the period is late. ``send_report_reminders`` is the single entry point a
cron job calls; it is idempotent per day because it only fires on the exact
day offsets the brief names.

A reminder is skipped for a company that has already submitted its report for
the period — there is nothing left to remind about — and for a company with no
manager account to receive it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.business import Company, MonthlyReport, ReportingPeriod
from app.models.enums import CompanyStatus, PeriodStatus, ReportStatus
from app.models.identity import Role, User, UserRole
from app.services import mail

# §7.5: the exact offsets that trigger a reminder.
REMINDER_OFFSETS = {3, 0}
# A report in any of these states counts as "sent" for the period.
_SENT = {
    ReportStatus.SUBMITTED.value,
    ReportStatus.APPROVED.value,
    ReportStatus.FORWARDED.value,
}


@dataclass
class Reminder:
    company_id: int
    company_name_ar: str
    company_name_en: str
    recipient_email: str | None
    recipient_locale: str
    period_label: str
    days_left: int


def _should_remind(days_left: int) -> bool:
    return days_left in REMINDER_OFFSETS or days_left < 0


def _business_developer_email(db: Session) -> tuple[str | None, str]:
    """The Holding's own report is the business developer's to send (§7.1)."""
    bd = db.execute(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.slug == "business_developer", User.is_active.is_(True))
        .order_by(User.id)
    ).scalars().first()
    if bd is None:
        return None, "ar"
    return bd.email, bd.locale or "ar"


def due_reminders(db: Session, today: date | None = None) -> list[Reminder]:
    """Companies with an open period that is due or nearly due and no report yet."""
    today = today or date.today()
    period = db.execute(
        select(ReportingPeriod)
        .where(ReportingPeriod.status == PeriodStatus.OPEN.value)
        .order_by(ReportingPeriod.year.desc(), ReportingPeriod.month.desc())
    ).scalars().first()
    if period is None or period.due_on is None:
        return []
    days_left = (period.due_on - today).days
    if not _should_remind(days_left):
        return []
    label = f"{period.year:04d}-{period.month:02d}"
    bd_email, bd_locale = _business_developer_email(db)

    reported = {
        row[0]
        for row in db.execute(
            select(MonthlyReport.company_id).where(
                MonthlyReport.period_id == period.id,
                MonthlyReport.status.in_(_SENT),
            )
        ).all()
    }
    companies = db.execute(
        select(Company).where(Company.status == CompanyStatus.ACTIVE.value)
    ).scalars().all()

    out: list[Reminder] = []
    for company in companies:
        if company.id in reported:
            continue
        if company.is_holding:
            email, locale = bd_email, bd_locale
        else:
            email, locale = None, "ar"
            if company.manager_user_id is not None:
                manager = db.get(User, company.manager_user_id)
                if manager is not None and manager.is_active:
                    email, locale = manager.email, (manager.locale or "ar")
        out.append(
            Reminder(
                company_id=company.id,
                company_name_ar=company.name_ar,
                company_name_en=company.name_en,
                recipient_email=email,
                recipient_locale=locale,
                period_label=label,
                days_left=days_left,
            )
        )
    return out


def send_report_reminders(db: Session, today: date | None = None) -> int:
    """Send every due reminder and return how many emails actually went out."""
    sent = 0
    for r in due_reminders(db, today):
        if not r.recipient_email:
            continue
        content = mail.report_deadline_email(
            r.recipient_locale,
            company=r.company_name_en if r.recipient_locale == "en" else r.company_name_ar,
            period=r.period_label,
            days_left=r.days_left,
        )
        if mail.send(r.recipient_email, content):
            sent += 1
    return sent


def run(today: date | None = None) -> int:
    """Entry point for the scheduled job: open a session, send, close."""
    db = SessionLocal()
    try:
        return send_report_reminders(db, today)
    finally:
        db.close()
