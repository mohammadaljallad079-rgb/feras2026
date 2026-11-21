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

The claim is a single atomic statement in every branch, so exactly one worker can
ever hold the right to send a given reminder:

* a fresh reminder is claimed with ``INSERT … ON CONFLICT DO NOTHING`` — the
  unique constraint is the arbiter, and the losing worker gets no row back;
* a ``failed`` reminder is retried, and a ``sending`` reminder whose claim is
  older than ``REMINDER_STALE_MINUTES`` is reclaimed, with a **conditional**
  ``UPDATE … WHERE status/age … RETURNING id``. Under PostgreSQL READ COMMITTED
  a second worker blocks on the row lock, then re-evaluates the ``WHERE`` against
  the committed version and matches nothing, so only one worker is handed the
  row. A read-then-write would let both read the same ``failed`` row and both
  send; the conditional ``UPDATE`` closes that window.

Every claim and retry stamps ``updated_at`` (``func.now()``), which is also the
clock the stale test is measured against.

Guarantee and its limit
-----------------------
The design is **at-most-once per day per (company, period, kind)**, enforced by
the unique constraint and the atomic claim. It is deliberately **not** an
exactly-once guarantee end to end, because the transport cannot be made part of
the transaction: if ``mail.send`` reaches the SMTP server and the server accepts
the message, but the process dies before the ``sent`` status is committed, the
row stays ``failed`` (or a stale ``sending``) and a later run retries it. The
recipient can therefore receive the reminder **twice** in that narrow window.
Closing it would need an idempotent transport (a provider-side message key) or a
transactional outbox with at-least-once delivery plus a deduplicating consumer,
neither of which SMTP offers. The trade-off is chosen deliberately: a duplicate
reminder is harmless, a *missing* deadline reminder is the failure that matters,
so a retry is preferred over a silently dropped reminder. Both branches — the
in-transaction duplicate suppression and the post-acceptance retry window — are
covered by tests and stated in the README.

A reminder is skipped for a company that has already submitted its report for the
period — there is nothing left to remind about — and for a company with no
manager account to receive it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func, or_, select, update
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
    was already sent or is being sent by a live worker. Each branch is a single
    statement so two workers cannot both win:

    1. ``INSERT … ON CONFLICT DO NOTHING RETURNING id`` — the unique constraint
       lets exactly one worker insert; the loser gets no row and stops.
    2. ``UPDATE … WHERE status='failed' … RETURNING id`` — a retry. The ``WHERE``
       makes it conditional: a concurrent worker blocks on the row lock, then
       re-reads the committed row, finds it no longer ``failed`` and updates
       nothing, so only one worker is handed the row.
    3. ``UPDATE … WHERE status='sending' AND updated_at < now() - stale …
       RETURNING id`` — reclaim a claim abandoned by a crashed worker, with the
       same lock-and-recheck semantics.

    Every claim/retry stamps ``updated_at`` so the stale clock and the audit
    trail stay truthful. The claim is committed immediately so a concurrent
    worker sees it and backs off.
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
            updated_at=func.now(),
        )
        .on_conflict_do_nothing(
            index_elements=["company_id", "period_id", "reminder_date", "kind"]
        )
        .returning(ReportReminderLog.id)
    ).scalar_one_or_none()
    db.commit()
    if inserted is not None:
        return db.get(ReportReminderLog, inserted)

    # A row already exists. Try to take it over atomically; the conditional
    # UPDATE is the arbiter, so at most one worker is returned a row. The stale
    # boundary is evaluated on the database clock, the same clock that stamps
    # ``updated_at``, so client/server clock skew cannot widen the window.
    stale_before = func.now() - timedelta(minutes=REMINDER_STALE_MINUTES)
    reclaimable = or_(
        ReportReminderLog.status == "failed",
        and_(
            ReportReminderLog.status == "sending",
            ReportReminderLog.updated_at < stale_before,
        ),
    )
    claimed_id = db.execute(
        update(ReportReminderLog)
        .where(
            ReportReminderLog.company_id == company_id,
            ReportReminderLog.period_id == period_id,
            ReportReminderLog.reminder_date == reminder_date,
            ReportReminderLog.kind == kind,
            reclaimable,
        )
        .values(
            status="sending",
            attempts=ReportReminderLog.attempts + 1,
            last_error=None,
            updated_at=func.now(),
        )
        .returning(ReportReminderLog.id)
    ).scalar_one_or_none()
    db.commit()
    if claimed_id is None:
        # Either already sent, or being sent by a live worker this cycle.
        return None
    row = db.get(ReportReminderLog, claimed_id)
    # The claim was made with a Core UPDATE, which does not refresh an instance
    # already in this session's identity map; reload so the caller sees the
    # committed attempts/status it will act on.
    db.refresh(row)
    return row


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
