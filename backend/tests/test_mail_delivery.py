"""Mail transport and scheduling verification (§7.5, §8, §12).

The point of these tests is honesty: the platform must never claim a message was
delivered when the transport refused, and the daily reminder job must be safe to
run from cron (idempotent, timezone-aware, and logging without leaking data).

The SMTP success path is exercised with a fake ``smtplib.SMTP`` so the real
``mail.send`` code — message construction, TLS, login, ``send_message`` — runs
without a network. No production credentials are used anywhere.
"""

from __future__ import annotations

import logging
from datetime import date

from app.models.business import Company, ReportingPeriod
from app.models.enums import PeriodStatus
from app.services import mail, reminders


class _FakeSMTP:
    """Records what the real code would put on the wire."""

    instances: list["_FakeSMTP"] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.started_tls = False
        self.logged_in = False
        self.sent: list = []
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = True

    def send_message(self, message):
        self.sent.append(message)


def test_smtp_success_path_sends_the_message(monkeypatch):
    from app.core.config import settings

    _FakeSMTP.instances.clear()
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com", raising=False)
    monkeypatch.setattr(settings, "smtp_user", "user", raising=False)
    monkeypatch.setattr(settings, "smtp_password", "secret", raising=False)
    monkeypatch.setattr(settings, "smtp_use_tls", True, raising=False)
    monkeypatch.setattr(mail.smtplib, "SMTP", _FakeSMTP)

    content = mail.report_deadline_email("ar", company="شركة", period="2026-10", days_left=3)
    assert mail.send("someone@safir-platform.com", content) is True

    assert len(_FakeSMTP.instances) == 1
    smtp = _FakeSMTP.instances[0]
    assert smtp.started_tls and smtp.logged_in
    assert len(smtp.sent) == 1
    message = smtp.sent[0]
    assert message["To"] == "someone@safir-platform.com"
    assert "2026-10" in message["Subject"]


def test_unconfigured_transport_is_reported_and_not_logged_as_sent(monkeypatch, caplog):
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "", raising=False)
    with caplog.at_level(logging.INFO):
        assert mail.send("someone@safir-platform.com", mail.invitation_email("ar", "t", "manager")) is False
    # No "sent" claim anywhere in the logs.
    assert not any("sent" in r.message.lower() and "not" not in r.message.lower() for r in caplog.records)


def test_transport_failure_is_reported_and_logged_without_secrets(monkeypatch, caplog):
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com", raising=False)
    monkeypatch.setattr(settings, "smtp_user", "user", raising=False)
    monkeypatch.setattr(settings, "smtp_password", "super-secret-password", raising=False)

    def boom(*_a, **_k):
        raise OSError("connection refused")

    monkeypatch.setattr(mail.smtplib, "SMTP", boom)
    with caplog.at_level(logging.WARNING):
        assert mail.send("someone@safir-platform.com", mail.password_reset_email("ar", "tok")) is False

    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "failed" in text.lower()
    # The SMTP password and the reset token must never reach the log.
    assert "super-secret-password" not in text
    assert "tok" not in text


def test_notify_counts_only_real_deliveries(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com", raising=False)
    monkeypatch.setattr(mail.smtplib, "SMTP", _FakeSMTP)
    _FakeSMTP.instances.clear()

    def half_boom(host, port, timeout=None):
        raise OSError("refused")

    content = mail.directive_email("ar", title="t", body="b")
    # A duplicate and an empty address are skipped; a failing one is not counted.
    original = mail.smtplib.SMTP
    monkeypatch.setattr(mail.smtplib, "SMTP", lambda *a, **k: _FakeSMTP(*a, **k))
    assert mail.notify(["a@x.com", "a@x.com", None], content) == 1

    monkeypatch.setattr(mail.smtplib, "SMTP", half_boom)
    assert mail.notify(["b@x.com"], content) == 0
    monkeypatch.setattr(mail.smtplib, "SMTP", original)


def test_reminder_email_states_the_offset_correctly():
    three = mail.report_deadline_email("ar", company="شركة أ", period="2026-10", days_left=3)
    assert "3" in three.body and "يستحق بعد" in three.body
    due = mail.report_deadline_email("en", company="Co A", period="2026-10", days_left=0)
    assert "due today" in due.body
    late = mail.report_deadline_email("en", company="Co A", period="2026-10", days_left=-4)
    assert "4 day(s) late" in late.body
    # A reminder carries no financial figure.
    import re

    assert not re.search(r"\d+\.\d{2}", three.body + due.body + late.body)


def test_daily_job_is_safe_to_run_twice(db, monkeypatch):
    """The cron entry point (``reminders.run`` equivalent) sends at most once per
    day per company, so an overlapping cron run cannot double-send."""
    from app.core.security import hash_password
    from app.models.identity import Role, User, UserRole

    manager = User(
        email="cron_mgr@safir-platform.com",
        full_name_ar="مدير",
        full_name_en="Manager",
        locale="ar",
        password_hash=hash_password("Passw0rd!"),
        is_active=True,
    )
    db.add(manager)
    db.flush()
    db.add(UserRole(user_id=manager.id, role_id=db.query(Role).filter_by(slug="company_manager").one().id))
    company = Company(
        code="CRON-1",
        name_ar="شركة",
        name_en="Co",
        country="BH",
        sector="تقنية",
        manager_user_id=manager.id,
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

    sent: list[int] = []

    def capture(_to, _content):
        sent.append(1)
        return True

    monkeypatch.setattr(mail, "send", capture)
    first = reminders.send_report_reminders(db, date(2026, 11, 2))
    second = reminders.send_report_reminders(db, date(2026, 11, 2))
    assert first == 1 and second == 0
    assert len(sent) == 1


def test_send_report_reminders_script_exit_code(monkeypatch):
    """The script returns 0 on a completed run and 2 when the run raises, so cron
    can distinguish "nothing to do" from "the job failed"."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "send_report_reminders",
        Path(__file__).resolve().parent.parent / "scripts" / "send_report_reminders.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(module.reminders, "run", lambda: 0)
    assert module.main() == 0

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(module.reminders, "run", boom)
    assert module.main() == 2
