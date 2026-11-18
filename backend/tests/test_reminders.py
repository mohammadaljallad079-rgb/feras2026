"""Deadline-reminder tests (§7.5, §12).

These exercise the durable idempotency guarantee directly: repeated runs, two
concurrent workers, a failed delivery that must not be recorded as sent, the
retry that follows, and the timezone boundary. They also re-assert the schedule
the brief names (three days before, on the due date, daily when late, stop once
the report is sent).
"""

from __future__ import annotations

import threading
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from app.models.business import (
    Company,
    MonthlyReport,
    ReportReminderLog,
    ReportingPeriod,
)
from app.models.enums import PeriodStatus
from app.services import mail, reminders


def _setup(db, manager_email: str = "rem_manager@safir-platform.com"):
    manager = _make_manager(db, manager_email)
    company = Company(
        code="REM-1",
        name_ar="شركة تذكير",
        name_en="Reminder Co",
        country="SA",
        sector="تقنية",
        manager_user_id=manager.id,
        status="active",
    )
    db.add(company)
    db.flush()
    period = ReportingPeriod(
        label_ar="2026-10",
        label_en="2026-10",
        year=2026,
        month=10,
        opens_on=date(2026, 10, 1),
        due_on=date(2026, 11, 5),
        status=PeriodStatus.OPEN.value,
    )
    db.add(period)
    db.commit()
    return company, period, manager


def _make_manager(db, email: str):
    from app.core.security import hash_password
    from app.models.identity import Role, User, UserRole

    user = User(
        email=email,
        full_name_ar=email,
        full_name_en=email,
        locale="ar",
        password_hash=hash_password("Passw0rd!"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    role = db.query(Role).filter(Role.slug == "company_manager").one()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


class _Recorder:
    def __init__(self, deliver: bool = True, delay: float = 0.0) -> None:
        self.messages: list[tuple[str, str]] = []
        self.deliver = deliver
        self.delay = delay
        self._lock = threading.Lock()

    def __call__(self, to_email: str, content) -> bool:
        if self.delay:
            import time

            time.sleep(self.delay)
        with self._lock:
            self.messages.append((to_email, content.subject))
        return self.deliver


def test_reminders_fire_on_the_three_offsets_and_stop_once_sent(db, monkeypatch):
    """§7.5/§12: three days before, on the due date, then daily when late; the
    reminder stops for a company that has already sent its report."""
    _company, period, _manager = _setup(db)

    box = _Recorder()
    monkeypatch.setattr(mail, "send", box)

    # 2026-11-02 is three days before the due date → one reminder.
    assert reminders.send_report_reminders(db, date(2026, 11, 2)) == 1
    # 2026-11-03 is two days before → no reminder.
    assert reminders.send_report_reminders(db, date(2026, 11, 3)) == 0
    # The due date itself → a reminder.
    assert reminders.send_report_reminders(db, date(2026, 11, 5)) == 1
    # Late → daily reminders continue.
    assert reminders.send_report_reminders(db, date(2026, 11, 6)) == 1

    # Once the company sends its report the reminder stops.
    db.add(MonthlyReport(company_id=_company.id, period_id=period.id, status="submitted", currency="SAR"))
    db.commit()
    assert reminders.send_report_reminders(db, date(2026, 11, 7)) == 0

    assert all(to == "rem_manager@safir-platform.com" for to, _ in box.messages)


def test_running_the_job_twice_on_the_same_day_sends_once(db, monkeypatch):
    """A second run on the same calendar day must not send a second reminder."""
    company, period, _manager = _setup(db)
    box = _Recorder()
    monkeypatch.setattr(mail, "send", box)

    assert reminders.send_report_reminders(db, date(2026, 11, 2)) == 1
    assert reminders.send_report_reminders(db, date(2026, 11, 2)) == 0
    assert reminders.send_report_reminders(db, date(2026, 11, 2)) == 0
    assert len(box.messages) == 1

    logs = db.query(ReportReminderLog).filter(ReportReminderLog.company_id == company.id).all()
    assert len(logs) == 1
    assert logs[0].status == "sent"
    assert logs[0].reminder_date == date(2026, 11, 2)
    assert logs[0].kind == reminders.KIND_THREE_DAYS
    assert logs[0].period_id == period.id


def test_two_concurrent_workers_send_once(engine, db, monkeypatch):
    """Two workers started at the same time must send a given reminder once.

    The unique constraint on the claim is the guarantee; this drives it with real
    parallel sessions and a slow transport so both workers overlap.
    """
    _setup(db)
    box = _Recorder(delay=0.3)
    monkeypatch.setattr(mail, "send", box)

    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    barrier = threading.Barrier(2)
    results: list[int] = []
    errors: list[Exception] = []

    def worker() -> None:
        session = factory()
        try:
            barrier.wait()
            results.append(reminders.send_report_reminders(session, date(2026, 11, 5)))
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert sum(results) == 1, results
    assert len(box.messages) == 1

    logs = db.query(ReportReminderLog).all()
    assert len(logs) == 1
    assert logs[0].status == "sent"


def test_failed_delivery_is_not_recorded_as_sent_and_is_retried(db, monkeypatch):
    """A transport failure must record ``failed`` (never ``sent``), not count as a
    delivery, and be retried on the next run the same day."""
    company, _period, _manager = _setup(db)

    failing = _Recorder(deliver=False)
    monkeypatch.setattr(mail, "send", failing)
    assert reminders.send_report_reminders(db, date(2026, 11, 5)) == 0

    log = db.query(ReportReminderLog).filter(ReportReminderLog.company_id == company.id).one()
    assert log.status == "failed"
    assert log.sent_at is None
    assert log.last_error
    assert len(failing.messages) == 1  # an attempt was made …

    # … but it was not a delivery, so the same-day retry succeeds and is counted.
    succeeding = _Recorder(deliver=True)
    monkeypatch.setattr(mail, "send", succeeding)
    assert reminders.send_report_reminders(db, date(2026, 11, 5)) == 1
    db.refresh(log)
    assert log.status == "sent"
    assert log.attempts == 2
    assert log.sent_at is not None


def test_raised_transport_error_is_caught_and_recorded_failed(db, monkeypatch):
    """An exception from the transport must not abort the run; the reminder is
    recorded failed and counted as not sent."""
    company, _period, _manager = _setup(db)

    def boom(*_a, **_k):
        raise OSError("connection refused")

    monkeypatch.setattr(mail, "send", boom)
    assert reminders.send_report_reminders(db, date(2026, 11, 5)) == 0
    log = db.query(ReportReminderLog).filter(ReportReminderLog.company_id == company.id).one()
    assert log.status == "failed"
    assert "connection refused" in (log.last_error or "")


def test_a_fresh_in_progress_claim_is_skipped(db, monkeypatch):
    """A row left ``sending`` by a live worker is respected: no duplicate send."""
    _setup(db)
    box = _Recorder()
    monkeypatch.setattr(mail, "send", box)

    # Simulate another worker that has claimed the row and is still sending.
    db.execute(
        text(
            "INSERT INTO report_reminder_logs "
            "(company_id, period_id, reminder_date, kind, status, attempts, created_at, updated_at) "
            "SELECT c.id, p.id, :d, 'due_date', 'sending', 1, now(), now() "
            "FROM companies c, reporting_periods p WHERE c.code='REM-1'"
        ),
        {"d": date(2026, 11, 5)},
    )
    db.commit()

    assert reminders.send_report_reminders(db, date(2026, 11, 5)) == 0
    assert box.messages == []


def test_a_stale_sending_claim_is_reclaimed(db, monkeypatch):
    """A claim abandoned by a crashed worker (older than the stale window) is
    re-claimed so the reminder is not lost forever."""
    _setup(db)
    box = _Recorder()
    monkeypatch.setattr(mail, "send", box)

    db.execute(
        text(
            "INSERT INTO report_reminder_logs "
            "(company_id, period_id, reminder_date, kind, status, attempts, created_at, updated_at) "
            "SELECT c.id, p.id, :d, 'due_date', 'sending', 1, now() - interval '2 hours', "
            "now() - interval '2 hours' FROM companies c, reporting_periods p WHERE c.code='REM-1'"
        ),
        {"d": date(2026, 11, 5)},
    )
    db.commit()

    assert reminders.send_report_reminders(db, date(2026, 11, 5)) == 1
    assert len(box.messages) == 1
    log = db.query(ReportReminderLog).one()
    assert log.status == "sent"
    assert log.attempts == 2


def test_today_is_resolved_in_the_operating_timezone():
    """A cron run near midnight resolves the Bahrain calendar day, not UTC."""
    # 21:30 UTC on the 18th is 00:30 on the 19th in Asia/Bahrain (UTC+3).
    moment = datetime(2026, 11, 18, 21, 30, tzinfo=timezone.utc)
    assert reminders.today_in_timezone(moment) == date(2026, 11, 19)
    # 20:30 UTC on the 18th is still the 18th (23:30) in Bahrain.
    assert reminders.today_in_timezone(datetime(2026, 11, 18, 20, 30, tzinfo=timezone.utc)) == date(2026, 11, 18)


def test_company_without_a_manager_is_skipped(db, monkeypatch):
    """No manager to receive the reminder ⇒ no send and no claim row."""
    company = Company(
        code="REM-NOMGR",
        name_ar="بلا مدير",
        name_en="No manager",
        country="SA",
        sector="تقنية",
        manager_user_id=None,
        status="active",
    )
    db.add(company)
    db.add(
        ReportingPeriod(
            label_ar="2026-10",
            label_en="2026-10",
            year=2026,
            month=10,
            opens_on=date(2026, 10, 1),
            due_on=date(2026, 11, 5),
            status=PeriodStatus.OPEN.value,
        )
    )
    db.commit()

    box = _Recorder()
    monkeypatch.setattr(mail, "send", box)
    assert reminders.send_report_reminders(db, date(2026, 11, 5)) == 0
    assert box.messages == []
    assert db.query(ReportReminderLog).count() == 0
