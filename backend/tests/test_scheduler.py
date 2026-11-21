"""Scheduler tests (§7.5, §12.3).

The scheduler decides *when* the reminder job runs; ``reminders`` owns the
at-most-once claim. These tests cover the four things the brief asks of the
schedule itself, each against the real decision logic rather than a copy of it:

* the run lands on the configured hour in the operating timezone (not a drifting
  24-hour sleep, not the server's zone);
* a failed run is retried after 15 minutes and never counted as a success;
* two schedulers starting at once cannot send a reminder twice (the durable
  claim, not the scheduler, is the arbiter);
* a container restart neither repeats a completed day nor loses a missed one.
"""

from __future__ import annotations

import json
import threading
from datetime import date, datetime, time as clock_time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.models.business import ReportReminderLog
from app.services import mail, reminders, scheduler

BAHRAIN = ZoneInfo("Asia/Bahrain")


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


# --- the daily slot -------------------------------------------------------


def test_the_run_lands_on_the_configured_hour_in_bahrain():
    """07:00 Asia/Bahrain is 04:00 UTC; the slot is resolved locally."""
    decision = scheduler.decide(
        _utc(2026, 11, 17, 1, 0), None, clock_time(7, 0), BAHRAIN
    )
    assert decision.run_now is False
    assert decision.wake_at.astimezone(BAHRAIN).strftime("%Y-%m-%d %H:%M") == "2026-11-17 07:00"
    assert decision.wake_at == _utc(2026, 11, 17, 4, 0)


def test_a_slot_already_passed_today_runs_immediately():
    """A restart after the hour with no success today catches the day up."""
    decision = scheduler.decide(
        _utc(2026, 11, 17, 9, 0), None, clock_time(7, 0), BAHRAIN
    )
    assert decision.run_now is True
    assert "catch" in decision.reason


def test_a_day_that_already_succeeded_waits_for_tomorrow():
    """Re-running a completed day would be redundant; the next slot is tomorrow."""
    decision = scheduler.decide(
        _utc(2026, 11, 17, 9, 0), date(2026, 11, 17), clock_time(7, 0), BAHRAIN
    )
    assert decision.run_now is False
    assert decision.wake_at.astimezone(BAHRAIN).date() == date(2026, 11, 18)


def test_the_next_run_is_the_next_day_when_now_is_exactly_the_slot():
    """``next_run_at`` is strict, so a wake at the slot does not return itself."""
    now = _utc(2026, 11, 17, 4, 0)
    assert scheduler.next_run_at(now, clock_time(7, 0), BAHRAIN) == _utc(2026, 11, 18, 4, 0)


def test_the_schedule_does_not_drift_with_a_long_run(monkeypatch):
    """A fixed local hour, not a 24h sleep: 07:00 stays 07:00 next day."""
    tz = BAHRAIN
    at = clock_time(7, 0)
    first = scheduler.next_run_at(_utc(2026, 11, 17, 3, 0), at, tz)
    # A run that started at 04:00 and took 3 hours ends at 07:00 UTC = 10:00 local.
    after_long_run = _utc(2026, 11, 17, 7, 0)
    second = scheduler.next_run_at(after_long_run, at, tz)
    assert first.astimezone(tz).strftime("%H:%M") == "07:00"
    assert second.astimezone(tz).strftime("%H:%M") == "07:00"
    assert second.astimezone(tz).date() == date(2026, 11, 18)


def test_an_invalid_schedule_time_falls_back_to_seven(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "reminder_schedule_time", "not-a-time")
    assert scheduler.schedule_time() == clock_time(7, 0)


def test_the_timezone_defaults_to_bahrain(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "reminders_timezone", "Asia/Bahrain")
    assert scheduler.zone().key == "Asia/Bahrain"


# --- retry ----------------------------------------------------------------


def test_a_failed_run_is_retried_after_fifteen_minutes(monkeypatch):
    """One failure then a success: two attempts, one 15-minute sleep."""
    calls: list[str] = []
    sleeps: list[float] = []

    def flaky():
        calls.append("run")
        if len(calls) == 1:
            raise RuntimeError("database is down")
        return 2

    monkeypatch.setattr(reminders, "run", flaky)
    monkeypatch.setattr(scheduler.time, "sleep", lambda s: sleeps.append(s))

    assert scheduler.run_day(clock_time(7, 0), BAHRAIN) is True
    assert calls == ["run", "run"]
    assert sleeps == [scheduler.RETRY_DELAY.total_seconds()] == [900.0]


def test_retries_are_bounded_and_a_failure_is_never_a_success(monkeypatch):
    """Every attempt fails: the run reports failure and stops at the cap."""
    attempts: list[int] = []
    sleeps: list[float] = []

    def always_fails():
        attempts.append(1)
        raise RuntimeError("still down")

    monkeypatch.setattr(reminders, "run", always_fails)
    monkeypatch.setattr(scheduler.time, "sleep", lambda s: sleeps.append(s))

    assert scheduler.run_day(clock_time(7, 0), BAHRAIN) is False
    assert len(attempts) == scheduler.MAX_ATTEMPTS == 3
    # Three attempts sleep twice, never after the last one.
    assert sleeps == [900.0, 900.0]


def test_a_transport_failure_is_not_a_scheduler_failure(db, monkeypatch):
    """A rejected delivery is recorded ``failed`` and is not retried by the
    scheduler; only an exception is. The job itself still returns normally."""
    from tests.test_reminders import _Recorder, _setup

    _company, _period, _manager = _setup(db)
    box = _Recorder(deliver=False)
    monkeypatch.setattr(mail, "send", box)

    assert scheduler.run_once() is True
    # The job completed, but nothing was recorded as sent.
    assert db.query(ReportReminderLog).filter_by(status="sent").count() == 0
    assert db.query(ReportReminderLog).filter_by(status="failed").count() == 1


def test_a_raised_job_error_is_reported_as_failure(monkeypatch):
    def boom():
        raise RuntimeError("database is down")

    monkeypatch.setattr(reminders, "run", boom)
    assert scheduler.run_once() is False


def test_a_successful_run_reports_how_many_went_out(monkeypatch, caplog):
    monkeypatch.setattr(reminders, "run", lambda: 4)
    with caplog.at_level("INFO", logger="scheduler"):
        assert scheduler.run_once() is True
    assert "4 reminder(s) sent" in caplog.text


# --- restart safety -------------------------------------------------------


def test_the_success_marker_survives_a_restart(tmp_path):
    """The marker is on disk, so a new process reads the completed day."""
    path = tmp_path / "scheduler_state.json"
    assert scheduler.load_last_success(path) is None

    scheduler.save_last_success(date(2026, 11, 17), path)
    assert json.loads(path.read_text())["last_success_date"] == "2026-11-17"
    assert scheduler.load_last_success(path) == date(2026, 11, 17)


def test_a_corrupt_marker_re_runs_the_day_rather_than_skipping_it(tmp_path):
    """An unreadable marker must fail safe: attempt the day again."""
    path = tmp_path / "scheduler_state.json"
    path.write_text("{not json", encoding="utf-8")
    assert scheduler.load_last_success(path) is None


def test_a_restart_after_success_does_not_repeat_the_day(tmp_path):
    path = tmp_path / "scheduler_state.json"
    scheduler.save_last_success(date(2026, 11, 17), path)
    decision = scheduler.decide(
        _utc(2026, 11, 17, 12, 0),
        scheduler.load_last_success(path),
        clock_time(7, 0),
        BAHRAIN,
    )
    assert decision.run_now is False


def test_a_restart_after_a_missed_day_runs_immediately(tmp_path):
    path = tmp_path / "scheduler_state.json"
    scheduler.save_last_success(date(2026, 11, 16), path)
    decision = scheduler.decide(
        _utc(2026, 11, 17, 12, 0),
        scheduler.load_last_success(path),
        clock_time(7, 0),
        BAHRAIN,
    )
    assert decision.run_now is True


# --- concurrency ----------------------------------------------------------


def test_two_schedulers_starting_together_send_once(engine, db, monkeypatch):
    """The durable claim, not the scheduler, prevents a duplicate.

    Two processes both decide to run (a fresh volume, or two replicas), and both
    drive the real job against the same database. Exactly one reminder leaves.
    """
    from sqlalchemy.orm import sessionmaker

    from tests.test_reminders import _Recorder, _setup

    _setup(db)
    db.commit()

    box = _Recorder(delay=0.2)
    monkeypatch.setattr(mail, "send", box)

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    barrier = threading.Barrier(2)
    results: list[int] = []
    lock = threading.Lock()

    def worker():
        session = factory()
        try:
            barrier.wait(timeout=10)
            sent = reminders.send_report_reminders(session, date(2026, 11, 5))
            with lock:
                results.append(sent)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(results) == [0, 1]
    assert len(box.messages) == 1
    assert db.query(ReportReminderLog).filter_by(status="sent").count() == 1


# --- deployment wiring ----------------------------------------------------


def test_the_deployed_service_runs_the_scheduler_module():
    """The compose service must run this policy, not a bare shell loop."""
    import pathlib

    import yaml

    compose = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"
    services = yaml.safe_load(compose.read_text(encoding="utf-8"))["services"]
    service = services["scheduler"]

    assert service["command"] == ["python", "-m", "app.services.scheduler"]
    env = service["environment"]
    assert env["REMINDERS_TIMEZONE"] == "${REMINDERS_TIMEZONE:-Asia/Bahrain}"
    assert env["REMINDER_SCHEDULE_TIME"] == "${REMINDER_SCHEDULE_TIME:-07:00}"
    # The marker must survive a container replacement.
    assert any("storage:" in v for v in service["volumes"])
    # SMTP must reach the job or it cannot deliver.
    for key in ("SMTP_HOST", "SMTP_FROM", "SMTP_PORT", "SMTP_USE_TLS"):
        assert key in env
    # The database must be up (migrations applied) before the job starts.
    assert service["depends_on"]["backend"]["condition"] == "service_healthy"
