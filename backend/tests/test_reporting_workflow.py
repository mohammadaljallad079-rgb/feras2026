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
    # §7.1: the writer is the company manager, not the owner.
    mgr = make_user("r3_mgr@safir-platform.com", ["company_manager"])
    h_manager = login("r3_mgr@safir-platform.com")
    cid = _company(client, h_owner, code="RPT-3")
    client.patch(f"/api/v1/users/{mgr.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)
    # Close the period directly.
    from app.models.business import ReportingPeriod

    db.get(ReportingPeriod, pid).status = "closed"
    db.commit()
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


def test_owner_sees_a_report_only_after_it_is_sent_to_management(client, make_user, login, db):
    """§5.1/§7.1: «بعد الاعتماد يرسل المحاسب للإدارة. عندها فقط يراه المالك».

    The owner reads the reports sent to management — the ``forwarded`` state — and
    neither a merely ``approved`` report (Table 8 marks «معتمد» as the accountant's)
    nor the drafts and submissions before it.
    """
    make_user("fwd_owner@safir-platform.com", ["owner"])
    manager = make_user("fwd_manager@safir-platform.com", ["company_manager"])
    acct = make_user("fwd_acct@safir-platform.com", ["accountant"])
    h_owner = login("fwd_owner@safir-platform.com")
    h_manager = login("fwd_manager@safir-platform.com")
    h_acct = login("fwd_acct@safir-platform.com")

    cid = _company(client, h_owner, code="FWD-1")
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)
    rid = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid}).json()["id"]

    user = db.query(User).filter(User.email == "fwd_manager@safir-platform.com").one()
    _attach_bank_statement(db, rid, _bank_statement(db, user))
    assert client.post(f"/api/v1/reports/{rid}/submit", headers=h_manager).status_code == 200

    # Submitted and approved are not yet sent to management.
    assert rid not in [r["id"] for r in client.get("/api/v1/reports", headers=h_owner).json()]
    assert client.post(f"/api/v1/reports/{rid}/approve", headers=h_acct).status_code == 200
    assert rid not in [r["id"] for r in client.get("/api/v1/reports", headers=h_owner).json()]
    assert client.get(f"/api/v1/reports/{rid}", headers=h_owner).status_code == 404

    # Only after the accountant sends it to management does the owner see it.
    assert client.post(f"/api/v1/reports/{rid}/forward", headers=h_acct).status_code == 200
    assert rid in [r["id"] for r in client.get("/api/v1/reports", headers=h_owner).json()]
    assert client.get(f"/api/v1/reports/{rid}", headers=h_owner).status_code == 200


def test_business_developer_fills_the_holdings_own_report(client, make_user, login, db):
    """§7.1: "The company manager (or the Business Developer for the Holding)
    fills it in and sends it to the Accountant." The Holding keeps its own report,
    so the developer must be able to create, open, fill and submit it — while a
    subsidiary draft stays invisible to the developer until it is sent.
    """
    from app.services.bootstrap import ensure_holding_company

    make_user("hold_owner@safir-platform.com", ["owner"])
    make_user("hold_bd@safir-platform.com", ["business_developer"])
    manager = make_user("hold_mgr@safir-platform.com", ["company_manager"])
    make_user("hold_acct@safir-platform.com", ["accountant"])
    h_owner = login("hold_owner@safir-platform.com")
    h_bd = login("hold_bd@safir-platform.com")
    h_manager = login("hold_mgr@safir-platform.com")
    h_acct = login("hold_acct@safir-platform.com")

    holding = ensure_holding_company(db)
    db.commit()
    cid = _company(client, h_owner, code="SUB-1")
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)

    # The developer authors the Holding's report and can open it while a draft.
    created = client.post("/api/v1/reports", headers=h_bd, json={"company_id": holding.id, "period_id": pid})
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    assert client.get(f"/api/v1/reports/{rid}", headers=h_bd).status_code == 200
    assert rid in [r["id"] for r in client.get("/api/v1/reports", headers=h_bd).json()]

    # The accountant may review the Holding's report too (§5.3).
    assert client.get(f"/api/v1/reports/{rid}", headers=h_acct).status_code == 200

    # A subsidiary draft is still hidden from the developer until sent.
    sub_draft = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid}).json()["id"]
    assert sub_draft not in [r["id"] for r in client.get("/api/v1/reports", headers=h_bd).json()]
    assert client.get(f"/api/v1/reports/{sub_draft}", headers=h_bd).status_code == 404


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


def test_report_list_detail_and_export_agree_for_a_holding_reviewer(client, make_user, login, db):
    """The accountant holds ``report:view_all`` as the holding's reviewer, so the
    reports it can list are the ones it can open, read the history of and export.

    The list was holding-wide while the detail, history and export re-applied
    company scoping, so the accountant saw a full queue but could open only the
    reports of the companies granted to it.
    """
    make_user("agree_owner@safir-platform.com", ["owner"])
    acct = make_user("agree_acct@safir-platform.com", ["accountant"])
    mgr = make_user("agree_mgr@safir-platform.com", ["company_manager"])
    h_owner = login("agree_owner@safir-platform.com")
    h_acct = login("agree_acct@safir-platform.com")
    h_mgr = login("agree_mgr@safir-platform.com")

    cid_a = _company(client, h_owner, code="AGR-A")
    cid_b = _company(client, h_owner, code="AGR-B")
    # The accountant is scoped to one company only; the manager authors B's draft.
    client.patch(f"/api/v1/users/{acct.id}", headers=h_owner, json={"company_ids": [cid_a]})
    client.patch(f"/api/v1/users/{mgr.id}", headers=h_owner, json={"company_ids": [cid_b]})
    pid = _period(client, h_owner)
    rid_b = client.post("/api/v1/reports", headers=h_mgr, json={"company_id": cid_b, "period_id": pid}).json()["id"]

    listed = client.get("/api/v1/reports", headers=h_acct).json()
    assert any(r["id"] == rid_b for r in listed), "the holding reviewer's queue spans every company"

    # Every listed report must be openable, readable and exportable.
    for row in listed:
        assert client.get(f"/api/v1/reports/{row['id']}", headers=h_acct).status_code == 200
        assert client.get(f"/api/v1/reports/{row['id']}/history", headers=h_acct).status_code == 200
        assert client.get(f"/api/v1/reports/{row['id']}/export", headers=h_acct).status_code == 200
    # The company filter agrees with the unfiltered queue.
    assert client.get(f"/api/v1/reports?company_id={cid_b}", headers=h_acct).status_code == 200


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


def test_sector_and_company_scoped_fields_apply_only_within_scope(client, make_user, login, db):
    """§7.4: «يظهر في تقارير الشركات ضمن نطاقه فقط» — a sector field belongs only
    to that sector's reports and a company field only to that company's. The
    required-field check must honour the scope, so a field scoped elsewhere can
    never block a report it does not belong to.
    """
    make_user("sc_owner@safir-platform.com", ["owner"])
    manager = make_user("sc_manager@safir-platform.com", ["company_manager"])
    h_owner = login("sc_owner@safir-platform.com")
    h_manager = login("sc_manager@safir-platform.com")

    cid = _company(client, h_owner, code="SC-1")  # sector "tech"
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})
    pid = _period(client, h_owner)

    # A required field scoped to the industrial sector must not apply here.
    other = FormField(
        code="sc_industrial_only", name_ar="إنتاج صناعي", name_en="Industrial output",
        field_type="amount", is_required=True, sector_scope="صناعي", version=1,
    )
    # A required field scoped to a different company must not apply either.
    other_cid = _company(client, h_owner, code="SC-2")
    other_company = FormField(
        code="sc_other_company", name_ar="حقل شركة أخرى", name_en="Other-company field",
        field_type="amount", is_required=True, company_id=other_cid, version=1,
    )
    # A required field with no scope applies to every company.
    global_field = FormField(
        code="sc_global", name_ar="حقل عام", name_en="Global field",
        field_type="amount", is_required=True, version=1,
    )
    db.add_all([other, other_company, global_field])
    db.commit()

    rid = client.post("/api/v1/reports", headers=h_manager, json={"company_id": cid, "period_id": pid}).json()["id"]
    _attach_bank_statement(db, rid, _bank_statement(db, manager))

    # Only the global required field is missing.
    blocked = client.post(f"/api/v1/reports/{rid}/submit", headers=h_manager)
    assert blocked.status_code == 422, blocked.text
    assert blocked.json()["detail"]["field_ids"] == [global_field.id]

    # Supplying the global field clears the block, proving the out-of-scope
    # fields were never demanded.
    client.put(
        f"/api/v1/reports/{rid}/values",
        headers=h_manager,
        json={"values": [{"field_id": global_field.id, "value_number": "1"}]},
    )
    assert client.post(f"/api/v1/reports/{rid}/submit", headers=h_manager).status_code == 200


def test_invoice_carries_tax_registration_and_service_item(client, make_user, login):
    """Table 5, «إيراد / فاتورة جديدة»: the invoice records the client's tax
    registration number (manual entry) and the service item, and both are
    returned so the accounting table can show them."""
    make_user("inv_owner@safir-platform.com", ["owner"])
    acct = make_user("inv_acct@safir-platform.com", ["accountant"])
    h_owner = login("inv_owner@safir-platform.com")
    h_acct = login("inv_acct@safir-platform.com")
    cid = _company(client, h_owner, code="INV-1")
    client.patch(f"/api/v1/users/{acct.id}", headers=h_owner, json={"company_ids": [cid]})

    created = client.post(
        "/api/v1/accounting",
        headers=h_acct,
        json={
            "kind": "invoice",
            "company_id": cid,
            "reference": "INV-2026-001",
            "description": "استشارات",
            "amount": "1000.00",
            "currency": "BHD",
            "entry_date": "2026-01-15",
            "party": "عميل أ",
            "tax_amount": "100.00",
            "tax_registration_no": "165704-1",
            "service_item": "استشارات أعمال",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["tax_registration_no"] == "165704-1"
    assert body["service_item"] == "استشارات أعمال"

    listed = client.get("/api/v1/accounting?kind=invoice", headers=h_acct).json()
    row = next(r for r in listed if r["id"] == body["id"])
    assert row["tax_registration_no"] == "165704-1"
    assert row["service_item"] == "استشارات أعمال"
