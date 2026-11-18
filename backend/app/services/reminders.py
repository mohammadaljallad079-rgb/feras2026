"""Monthly-report deadline reminders (§7.5, §12).

The brief replaces the simulation's date switch with real scheduling: a reminder
goes out three days before the due date, again on the due date, and then daily
once the period is late. ``send_report_reminders`` is the single entry point a
cron job calls.

Sending is made idempotent by a durable log (``report_reminder_logs``), not by
the date arithmetic alone. Before a message is sent the worker claims a row keyed
by ``(company, period, calendar day, reminder kind)``; a unique constraint means
a second run on the same day, or a second worker running at the same time, cannot
claim the same row twice. A reminder is therefore sent at most once per company
per day however often the job is started.

Failure handling is explicit: a claim is written as ``sending`` first, then moved
to ``sent`` only after the transport reports success, or to ``failed`` when it
does not. A ``failed`` row is retried on the next run the same day; a row left in
``sending`` by a process that died mid-send is only re-claimed once it is older
than ``REMINDER_STALE_MINUTES`` (see the note on the guarantee below).

Guarantee and its limit
-----------------------
The design is **at-most-once per day**. If a worker crashes after the claim is
committed but before the send completes, the row stays ``sending``; while it is
fresh (within ``REMINDER_STALE_MINUTES``) a later run that day skips it, so that
day's reminder can be lost rather than duplicated. Once the row is stale it is
re-claimed, which prefers delivery over strict single delivery at that point.
Both branches are covered by tests.

A reminder is skipped for a company that has already submitted its report for the
period — there is nothing left to remind about — and for a company with no
manager account to receive it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.business import Company, MonthlyReport, ReportReminderLog, ReportingPeriod
from app.models.enums import CompanyStatus, PeriodStatus, ReportStatus
from app.models.identity import Role, User, UserRole
from app.services import mail

logger = logging.getLogger(__name__)

# §7.5: the exact day offsets that trigger a reminder.
REMINDER_OFFSETS = {3, 0}
# A report in any of these states counts as "sent" for the period.
_SENT = {
    ReportStatus.SUBMITTED.value,
    ReportStatus.APPROVED.value,
    ReportStatus.FORWARDED.value,
}
# A claim older than this, still marked ``sending``, is treated as abandoned by a
# crashed worker and may be re-claimed. Kept well under a day so the same-day
# guarantee holds across a single cron cycle.
REMINDER_STALE_MINUTES = 60

KIND_THREE_DAYS = "three_days_before"
KIND_DUE_DATE = "due_date"
KIND_LATE = "late"


@dataclass
class Reminder:
    company_id: int
    period_id: int
    company_name_ar: str
    company_name_en: str
    recipient_email: str | None
    recipient_locale: str
    period_label: str
    days_left: int
    kind: str


def _should_remind(days_left: int) -> bool:
    return days_left in REMINDER_OFFSETS or days_left < 0


def _kind(days_left: int) -> str:
    if days_left == 3:
        return KIND_THREE_DAYS
    if days_left == 0:
        return KIND_DUE_DATE
    return KIND_LATE


def today_in_timezone(now: datetime | None = None) -> date:
    """The calendar day in the configured reminders timezone.

    The due dates are Bahrain business dates, so "today" must be resolved in the
    operating timezone rather than the server's, otherwise a cron run near
    midnight can fire on the wrong day.
    """
    moment = now or datetime.now(timezone.utc)
    try:
        zone = ZoneInfo(settings.reminders_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = timezone.utc
    return moment.astimezone(zone).date()


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
    today = today or today_in_timezone()
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
    kind = _kind(days_left)

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
                period_id=period.id,
                company_name_ar=company.name_ar,
                company_name_en=company.name_en,
                recipient_email=email,
                recipient_locale=locale,
                period_label=label,
                days_left=days_left,
                kind=kind,
            )
        )
    return out


def _claim(
    db: Session,
    *,
    company_id: int,
    period_id: int,
    reminder_date: date,
    kind: str,
    recipient_email: str,
) -> ReportReminderLog | None:
    """Atomically claim the right to send one reminder.

    Returns the log row when this caller may send, or ``None`` when the reminder
    was already sent (or is being sent by a live worker). The claim is committed
    immediately so a concurrent worker sees it and backs off.
    """
    inserted = db.execute(
        pg_insert(ReportReminderLog)
        .values(
            company_id=company_id,
            period_id=period_id,
            reminder_date=reminder_date,
            kind=kind,
            status="sending",
            recipient_email=recipient_email,
            attempts=1,
        )
        .on_conflict_do_nothing(
            index_elements=["company_id", "period_id", "reminder_date", "kind"]
        )
        .returning(ReportReminderLog.id)
    ).scalar_one_or_none()
    db.commit()
    if inserted is not None:
        return db.get(ReportReminderLog, inserted)

    # A row already exists. Decide whether it is safe to (re)send.
    existing = db.execute(
        select(ReportReminderLog).where(
            ReportReminderLog.company_id == company_id,
            ReportReminderLog.period_id == period_id,
            ReportReminderLog.reminder_date == reminder_date,
            ReportReminderLog.kind == kind,
        )
    ).scalars().first()
    if existing is None:
        # Raced with a delete/rollback; treat as not ours this cycle.
        return None
    if existing.status == "sent":
        return None
    if existing.status == "failed":
        # A prior attempt never delivered: retry it now.
        existing.status = "sending"
        existing.attempts += 1
        existing.last_error = None
        db.commit()
        return existing
    # status == "sending": only re-claim if the claim is stale (crashed worker).
    reference = existing.updated_at or existing.created_at
    if reference is not None and reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    if reference is not None and datetime.now(timezone.utc) - reference > timedelta(
        minutes=REMINDER_STALE_MINUTES
    ):
        existing.attempts += 1
        db.commit()
        return existing
    return None


def send_report_reminders(db: Session, today: date | None = None) -> int:
    """Send every due reminder and return how many emails actually went out.

    A reminder whose delivery fails is recorded ``failed`` (never ``sent``) so it
    is retried, and is not counted as sent.
    """
    sent = 0
    for r in due_reminders(db, today):
        if not r.recipient_email:
            continue
        reminder_date = today or today_in_timezone()
        log = _claim(
            db,
            company_id=r.company_id,
            period_id=r.period_id,
            reminder_date=reminder_date,
            kind=r.kind,
            recipient_email=r.recipient_email,
        )
        if log is None:
            continue
        content = mail.report_deadline_email(
            r.recipient_locale,
            company=r.company_name_en if r.recipient_locale == "en" else r.company_name_ar,
            period=r.period_label,
            days_left=r.days_left,
        )
        try:
            delivered = mail.send(r.recipient_email, content)
            error: str | None = None
        except Exception as exc:  # a transport must never abort the whole run
            delivered = False
            error = str(exc)
        if delivered:
            log.status = "sent"
            log.sent_at = datetime.now(timezone.utc)
            log.last_error = None
            sent += 1
        else:
            log.status = "failed"
            log.last_error = error or "mail transport reported failure"
            logger.warning(
                "Report reminder to %s for company %s was not delivered",
                r.recipient_email,
                r.company_id,
            )
        db.commit()
    return sent


def run(today: date | None = None) -> int:
    """Entry point for the scheduled job: open a session, send, close."""
    db = SessionLocal()
    try:
        return send_report_reminders(db, today)
    finally:
        db.close()
