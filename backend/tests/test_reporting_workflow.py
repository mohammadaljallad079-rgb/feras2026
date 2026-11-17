"""Monthly reporting workflow state-machine tests, end to end through the API."""

from __future__ import annotations

import io
from datetime import date

from app.models.business import FormField
from app.models.identity import User
from app.models.operations import StoredFile


def _company(client, headers, code="RPT-1") -> int:
    resp = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"code": code, "name_ar": "شركة التقارير", "name_en": "Reports Co", "country": "SA", "sector": "tech", "currency": "SAR", "status": "active"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _period(client, headers) -> int:
    resp = client.post(
        "/api/v1/periods",
        headers=headers,
        json={"label_ar": "يناير 2026", "label_en": "Jan 2026", "year": 2026, "month": 1, "opens_on": "2026-01-01", "due_on": "2026-02-05"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _required_field(db, code="revenue"):
    field = FormField(code=code, name_ar="الإيرادات", name_en="Revenue", field_type="amount", is_required=True, version=1)
    db.add(field)
    db.commit()
    return field.id


def _bank_statement(db, user: User) -> int:
    f = StoredFile(storage_name="stmt1", original_name="bank.pdf", content_type="application/pdf", size_bytes=10, checksum="x", owner_id=user.id)
    db.add(f)
    db.commit()
    return f.id


def _attach_bank_statement(db, report_id: int, file_id: int):
    from app.models.business import MonthlyReport

    report = db.get(MonthlyReport, report_id)
    report.bank_statement_file_id = file_id
    db.commit()


def test_full_report_lifecycle(client, make_user, login, db):
    owner = make_user("rpt_owner@safir-platform.com", ["owner"])
    manager = make_user("rpt_manager@safir-platform.com", ["company_manager"])
    accountant = make_user("rpt_acct@safir-platform.com", ["accountant"])

    h_owner = login("rpt_owner@safir-platform.com")
    h_manager = login("rpt_manager@safir-platform.com")
    h_acct = login("rpt_acct@safir-platform.com")

    cid = _company(client, h_owner)
    # Grant manager access to this company.
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)
    fid = _required_field(db)

    created = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid})
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    assert created.json()["status"] == "draft"

    # Save a value.
    saved = client.put(
        f"/api/v1/reports/{rid}/values",
        headers=h_manager,
        json={"commentary": "تعليق", "values": [{"field_id": fid, "value_number": "1500.00"}]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["values"][0]["value_number"] == "1500.00"

    # Cannot submit without a bank statement.
    blocked = client.post(f"/api/v1/reports/{rid}/submit", headers=h_manager)
    assert blocked.status_code == 422
    assert blocked.json()["detail"]["error"] == "bank_statement_required"

    _attach_bank_statement(db, rid, _bank_statement(db, manager))

    submitted = client.post(f"/api/v1/reports/{rid}/submit", headers=h_manager)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    # Submitted reports cannot be edited.
    assert client.put(f"/api/v1/reports/{rid}/values", headers=h_manager, json={"values": []}).status_code == 409

    # Accountant returns with a mandatory reason.
    ret = client.post(f"/api/v1/reports/{rid}/return", headers=h_acct, json={"reason": "المرفق غير واضح"})
    assert ret.status_code == 200
    assert ret.json()["status"] == "returned"
    assert ret.json()["returned_reason"] == "المرفق غير واضح"

    # Manager corrects and resubmits.
    assert client.put(f"/api/v1/reports/{rid}/values", headers=h_manager, json={"values": [{"field_id": fid, "value_number": "1700.00"}]}).status_code == 200
    resub = client.post(f"/api/v1/reports/{rid}/submit", headers=h_manager)
    assert resub.status_code == 200

    # Accountant approves and forwards.
    appr = client.post(f"/api/v1/reports/{rid}/approve", headers=h_acct)
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"
    fwd = client.post(f"/api/v1/reports/{rid}/forward", headers=h_acct)
    assert fwd.status_code == 200
    assert fwd.json()["status"] == "forwarded"

    # Locked after approval.
    assert client.put(f"/api/v1/reports/{rid}/values", headers=h_manager, json={"values": []}).status_code == 409

    # History is fully recorded.
    history = client.get(f"/api/v1/reports/{rid}/history", headers=h_owner).json()
    transitions = [h["to_status"] for h in history]
    assert transitions == ["submitted", "returned", "submitted", "approved", "forwarded"]

    # Owner sees the forwarded report.
    owner_list = client.get("/api/v1/reports", headers=h_owner).json()
    assert any(r["id"] == rid and r["status"] == "forwarded" for r in owner_list)


def test_return_requires_reason(client, make_user, login, db):
    make_user("r2_owner@safir-platform.com", ["owner"])
    manager = make_user("r2_manager@safir-platform.com", ["company_manager"])
    make_user("r2_acct@safir-platform.com", ["accountant"])
    h_owner = login("r2_owner@safir-platform.com")
    cid = _company(client, h_owner, code="RPT-2")
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)
    h_manager = login("r2_manager@safir-platform.com")
    rid = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid}).json()["id"]
    # Validation error: reason too short.
    resp = client.post(f"/api/v1/reports/{rid}/return", headers=login("r2_acct@safir-platform.com"), json={"reason": "x"})
    assert resp.status_code == 422


def test_manager_cannot_submit_into_closed_period(client, make_user, login, db):
    make_user("r3_owner@safir-platform.com", ["owner"])
    h_owner = login("r3_owner@safir-platform.com")
    cid = _company(client, h_owner, code="RPT-3")
    pid = _period(client, h_owner)
    # Close the period directly.
    from app.models.business import ReportingPeriod

    db.get(ReportingPeriod, pid).status = "closed"
    db.commit()
    h_manager = login("r3_owner@safir-platform.com")
    resp = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid})
    assert resp.status_code == 409


def test_owner_and_developer_see_only_reports_sent_to_management(client, make_user, login, db):
    """Design reference page 8: the owner reads the reports formally sent to
    management, not every draft the manager is still working on."""
    make_user("vis_owner@safir-platform.com", ["owner"])
    make_user("vis_bd@safir-platform.com", ["business_developer"])
    manager = make_user("vis_manager@safir-platform.com", ["company_manager"])
    make_user("vis_acct@safir-platform.com", ["accountant"])
    h_owner = login("vis_owner@safir-platform.com")
    h_bd = login("vis_bd@safir-platform.com")
    h_manager = login("vis_manager@safir-platform.com")
    h_acct = login("vis_acct@safir-platform.com")

    cid = _company(client, h_owner, code="VIS-1")
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)

    draft_id = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid}).json()["id"]

    # A draft is visible to its author and to the accountant, but not yet to the
    # owner or the business developer.
    assert draft_id in [r["id"] for r in client.get("/api/v1/reports", headers=h_manager).json()]
    assert draft_id in [r["id"] for r in client.get("/api/v1/reports", headers=h_acct).json()]
    assert draft_id not in [r["id"] for r in client.get("/api/v1/reports", headers=h_owner).json()]
    assert draft_id not in [r["id"] for r in client.get("/api/v1/reports", headers=h_bd).json()]

    # Submit, approve and forward; the owner and the developer now see it.
    user = db.query(User).filter(User.email == "vis_manager@safir-platform.com").one()
    _attach_bank_statement(db, draft_id, _bank_statement(db, user))
    assert client.post(f"/api/v1/reports/{draft_id}/submit", headers=h_manager).status_code == 200
    assert client.post(f"/api/v1/reports/{draft_id}/approve", headers=h_acct).status_code == 200
    assert client.post(f"/api/v1/reports/{draft_id}/forward", headers=h_acct).status_code == 200

    assert draft_id in [r["id"] for r in client.get("/api/v1/reports", headers=h_owner).json()]
    assert draft_id in [r["id"] for r in client.get("/api/v1/reports", headers=h_bd).json()]


def test_accountant_can_list_reports_for_review(client, make_user, login):
    """Design reference pages 24-25: the accountant's queue is the report list."""
    make_user("rev_owner@safir-platform.com", ["owner"])
    make_user("rev_acct@safir-platform.com", ["accountant"])
    make_user("rev_marketer@safir-platform.com", ["marketer"])
    h_owner = login("rev_owner@safir-platform.com")
    h_acct = login("rev_acct@safir-platform.com")
    h_marketer = login("rev_marketer@safir-platform.com")

    assert client.get("/api/v1/reports", headers=h_acct).status_code == 200
    assert client.get("/api/v1/periods", headers=h_acct).status_code == 200
    # A role with no reporting duty is refused outright.
    assert client.get("/api/v1/reports", headers=h_marketer).status_code == 403


def test_owner_does_not_hold_the_accountants_review_duties(client, make_user, login):
    """The owner has broad oversight but approving and forwarding reports is the
    accountant's duty (design reference pages 8 and 24-25)."""
    make_user("duty_owner@safir-platform.com", ["owner"])
    manager = make_user("duty_manager@safir-platform.com", ["company_manager"])
    h_owner = login("duty_owner@safir-platform.com")
    h_manager = login("duty_manager@safir-platform.com")

    cid = _company(client, h_owner, code="DUTY-1")
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)
    rid = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid}).json()["id"]

    # The owner cannot review, approve or forward, even though it can read.
    assert client.post(f"/api/v1/reports/{rid}/return", headers=h_owner, json={"reason": "no"}).status_code == 403
    assert client.post(f"/api/v1/reports/{rid}/approve", headers=h_owner).status_code == 403
    assert client.post(f"/api/v1/reports/{rid}/forward", headers=h_owner).status_code == 403
    # Opening and closing a period remains an owner/accountant task.
    assert client.post(
        "/api/v1/periods",
        headers=h_owner,
        json={"label_ar": "فبراير 2026", "label_en": "Feb 2026", "year": 2026, "month": 2, "opens_on": "2026-02-01", "due_on": "2026-03-05"},
    ).status_code == 201


def test_accountant_can_open_a_submitted_report_for_review(client, make_user, login, db):
    """Design reference page 25: the accountant opens a submitted report to
    review it, so the detail and history routes must accept ``report:view_all``.

    The accountant holds ``report:view_all`` and not ``report:view_own``; when
    the detail route required the latter, the whole review screen failed with a
    403 even though the report list rendered.
    """
    make_user("det_owner@safir-platform.com", ["owner"])
    manager = make_user("det_manager@safir-platform.com", ["company_manager"])
    acct = make_user("det_acct@safir-platform.com", ["accountant"])
    h_owner = login("det_owner@safir-platform.com")
    h_manager = login("det_manager@safir-platform.com")
    h_acct = login("det_acct@safir-platform.com")

    cid = _company(client, h_owner, code="DET-1")
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    # The holding accountant is scoped to the companies it handles.
    client.patch(f"/api/v1/users/{acct.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)
    rid = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid}).json()["id"]
    user = db.query(User).filter(User.email == "det_manager@safir-platform.com").one()
    _attach_bank_statement(db, rid, _bank_statement(db, user))
    assert client.post(f"/api/v1/reports/{rid}/submit", headers=h_manager).status_code == 200

    detail = client.get(f"/api/v1/reports/{rid}", headers=h_acct)
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "submitted"
    assert client.get(f"/api/v1/reports/{rid}/history", headers=h_acct).status_code == 200

    # The owner must not reach a report by id that the list hides from them.
    assert client.get(f"/api/v1/reports/{rid}", headers=h_owner).status_code == 404


def test_accountant_exports_a_report_to_excel(client, make_user, login, db):
    """Design reference page 25: the accountant exports validated reports."""
    make_user("xls_owner@safir-platform.com", ["owner"])
    manager = make_user("xls_manager@safir-platform.com", ["company_manager"])
    acct = make_user("xls_acct@safir-platform.com", ["accountant"])
    h_owner = login("xls_owner@safir-platform.com")
    h_manager = login("xls_manager@safir-platform.com")
    h_acct = login("xls_acct@safir-platform.com")

    cid = _company(client, h_owner, code="XLS-1")
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    client.patch(f"/api/v1/users/{acct.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)
    rid = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid}).json()["id"]

    resp = client.get(f"/api/v1/reports/{rid}/export", headers=h_acct)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert resp.content[:2] == b"PK"  # an xlsx is a zip container
