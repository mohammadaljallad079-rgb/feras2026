"""Automatic monthly reporting periods (§7.1, §12.3).

§7.1 opens a new period for every active company and for the Holding, with the
due date on the fifth of the following month. §12.3 replaces the simulation's
date switch («تاريخ المحاكاة») with real scheduling, so the period must roll
over on its own rather than waiting for someone to press a button.

The reporting period is the calendar month that just ended: the platform works
on October's numbers during November, which is why §5.1 shows «الفترة الحالية
2026-10 · الاستحقاق 2026-11-05». `current_period` mirrors the simulation's
`curPer()`, which returns the previous month (and December of the previous year
in January).

`ensure_open_period` is idempotent and safe to call from every scheduled run:
it creates the period when it is missing, leaves an existing one untouched, and
closes the older open periods so exactly one period is open at a time.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.business import ReportingPeriod
from app.models.enums import PeriodStatus
from app.services import audit

logger = logging.getLogger(__name__)


def current_period(today: date) -> tuple[int, int]:
    """The (year, month) the platform is working in: the month before ``today``."""
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def due_on(year: int, month: int) -> date:
    """§7.1: the fifth day of the month that follows the reporting month."""
    return date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 5)


def opens_on(year: int, month: int) -> date:
    return date(year, month, 1)


def _today() -> date:
    """The calendar day in the operating timezone, not the server's (§7.5)."""
    try:
        zone = ZoneInfo(settings.reminders_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = timezone.utc
    return datetime.now(timezone.utc).astimezone(zone).date()


def run_rollover(today: date | None = None) -> ReportingPeriod:
    """Open the current month's period, for the scheduled job and for scripts."""
    db = SessionLocal()
    try:
        return ensure_open_period(db, today or _today())
    finally:
        db.close()


def ensure_open_period(db, today: date) -> ReportingPeriod:
    """Return the period for ``today``'s reporting month, creating it if needed.

    Older open periods are closed first, so the reminders and the dashboards all
    agree on which month is current.
    """
    year, month = current_period(today)
    existing = db.execute(
        select(ReportingPeriod).where(
            ReportingPeriod.year == year, ReportingPeriod.month == month
        )
    ).scalar_one_or_none()

    for stale in db.execute(
        select(ReportingPeriod).where(
            ReportingPeriod.status == PeriodStatus.OPEN.value,
            (ReportingPeriod.year < year)
            | ((ReportingPeriod.year == year) & (ReportingPeriod.month < month)),
        )
    ).scalars():
        stale.status = PeriodStatus.CLOSED.value
        logger.info("Closed reporting period %04d-%02d", stale.year, stale.month)

    if existing is not None:
        if existing.status != PeriodStatus.OPEN.value:
            existing.status = PeriodStatus.OPEN.value
        db.commit()
        return existing

    label = f"{year:04d}-{month:02d}"
    period = ReportingPeriod(
        label_ar=label,
        label_en=label,
        year=year,
        month=month,
        opens_on=opens_on(year, month),
        due_on=due_on(year, month),
        status=PeriodStatus.OPEN.value,
    )
    db.add(period)
    db.flush()
    audit.record(
        db,
        action="period.auto_open",
        target_type="period",
        target_id=period.id,
    )
    db.commit()
    db.refresh(period)
    logger.info(
        "Opened reporting period %s (due %s)", label, period.due_on.isoformat()
    )
    return period
