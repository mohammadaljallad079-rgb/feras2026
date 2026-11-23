"""Automatic monthly period rollover (§7.1, §12.3).

§7.1 opens a period per month with the due date on the fifth of the following
month, and §12.3 replaces the simulation's manual date switch with real
scheduling. Before this module the only way a period appeared was
``POST /periods``, so a deployment that never called it kept reminding companies
about a month that had long passed — the state the live database was found in
(period ``2026-01`` open while the calendar said November).

These tests pin the calendar arithmetic, the derived due date, the closing of
superseded periods and the idempotency that lets the daily job call it blindly.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.models.business import ReportingPeriod
from app.models.enums import PeriodStatus
from app.services import periods


def _periods(db) -> list[ReportingPeriod]:
    return list(
        db.execute(
            select(ReportingPeriod).order_by(ReportingPeriod.year, ReportingPeriod.month)
        ).scalars()
    )


def test_current_period_is_the_month_that_just_ended():
    """§5.1: in November the platform reports October's numbers."""
    assert periods.current_period(date(2026, 11, 17)) == (2026, 10)
    assert periods.current_period(date(2026, 3, 1)) == (2026, 2)


def test_january_reports_the_previous_december():
    """Mirrors the prototype's ``curPer()`` year rollover."""
    assert periods.current_period(date(2026, 1, 5)) == (2025, 12)


def test_due_date_is_the_fifth_of_the_next_month():
    """§7.1: «الاستحقاق هو اليوم الخامس من الشهر التالي»."""
    assert periods.due_on(2026, 10) == date(2026, 11, 5)
    assert periods.due_on(2026, 12) == date(2027, 1, 5)


def test_rollover_opens_the_current_period_with_derived_dates(db):
    period = periods.ensure_open_period(db, date(2026, 11, 17))

    assert (period.year, period.month) == (2026, 10)
    assert period.label_ar == "2026-10"
    assert period.opens_on == date(2026, 10, 1)
    assert period.due_on == date(2026, 11, 5)
    assert period.status == PeriodStatus.OPEN.value


def test_rollover_is_idempotent(db):
    first = periods.ensure_open_period(db, date(2026, 11, 17))
    second = periods.ensure_open_period(db, date(2026, 11, 20))

    assert first.id == second.id
    assert len(_periods(db)) == 1


def test_rollover_closes_the_superseded_open_period(db):
    db.add(
        ReportingPeriod(
            label_ar="2026-01",
            label_en="2026-01",
            year=2026,
            month=1,
            opens_on=date(2026, 1, 1),
            due_on=date(2026, 2, 5),
            status=PeriodStatus.OPEN.value,
        )
    )
    db.commit()

    periods.ensure_open_period(db, date(2026, 11, 17))

    by_label = {p.label_ar: p for p in _periods(db)}
    assert by_label["2026-01"].status == PeriodStatus.CLOSED.value
    assert by_label["2026-10"].status == PeriodStatus.OPEN.value


def test_rollover_leaves_a_newer_period_alone(db):
    """A period ahead of today's month must not be closed by a stale clock."""
    db.add(
        ReportingPeriod(
            label_ar="2026-12",
            label_en="2026-12",
            year=2026,
            month=12,
            opens_on=date(2026, 12, 1),
            due_on=date(2027, 1, 5),
            status=PeriodStatus.OPEN.value,
        )
    )
    db.commit()

    periods.ensure_open_period(db, date(2026, 11, 17))

    by_label = {p.label_ar: p for p in _periods(db)}
    assert by_label["2026-12"].status == PeriodStatus.OPEN.value
    assert by_label["2026-10"].status == PeriodStatus.OPEN.value


def test_rollover_audits_the_automatic_opening(db):
    periods.ensure_open_period(db, date(2026, 11, 17))

    from app.models.identity import AuditEvent

    actions = db.execute(select(AuditEvent.action)).scalars().all()
    assert "period.auto_open" in actions


def test_daily_job_opens_the_period_before_reminding(db, monkeypatch):
    """The scheduler's single run must roll the period over, not only send."""
    from app.services import scheduler

    called: list[str] = []
    monkeypatch.setattr(periods, "run_rollover", lambda: called.append("rollover"))
    monkeypatch.setattr(
        scheduler.reminders, "run", lambda: called.append("reminders") or 0
    )

    assert scheduler.run_once() is True
    assert called == ["rollover", "reminders"]
