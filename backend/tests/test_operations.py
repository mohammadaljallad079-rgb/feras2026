"""Business operation tests: opportunities, directives, service requests, leads,
website conversion, form builder versioning and the AI configuration status."""

from __future__ import annotations

import re
from pathlib import Path


def _company(client, headers, code, status="active"):
    resp = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"code": code, "name_ar": f"شركة {code}", "name_en": f"Co {code}", "country": "SA", "sector": "tech", "status": status},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_opportunity_decision_flow(client, make_user, login):
    make_user("o_owner@safir-platform.com", ["owner"])
    bd = make_user("o_bd@safir-platform.com", ["business_developer"])
    h_owner = login("o_owner@safir-platform.com")
    h_bd = login("o_bd@safir-platform.com")
    cid = _company(client, h_owner, "OPP-1")
    client.patch(f"/api/v1/users/{bd.id}", headers=h_owner, json={"company_ids": [cid]})

    created = client.post(
        "/api/v1/opportunities",
        headers=h_bd,
        json={"title": "فرصة جديدة", "company_id": cid, "country": "البحرين", "estimated_value": "50000.00", "currency": "SAR"},
    )
    assert created.status_code == 201, created.text
    oid = created.json()["id"]
    assert created.json()["status"] == "draft"

    assert client.post(f"/api/v1/opportunities/{oid}/submit", headers=h_bd).json()["status"] == "submitted"

    # Business developer cannot decide.
    assert client.post(f"/api/v1/opportunities/{oid}/decision", headers=h_bd, json={"decision": "approved"}).status_code == 403

    decided = client.post(f"/api/v1/opportunities/{oid}/decision", headers=h_owner, json={"decision": "approved", "note": "موافق"})
    assert decided.status_code == 200
    body = decided.json()
    assert body["status"] == "approved"
    assert body["decided_at"] is not None
    assert body["decision_note"] == "موافق"


def test_directive_receive_and_complete(client, make_user, login):
    owner = make_user("d_owner@safir-platform.com", ["owner"])
    manager = make_user("d_manager@safir-platform.com", ["company_manager"])
    h_owner = login("d_owner@safir-platform.com")
    h_manager = login("d_manager@safir-platform.com")

    created = client.post(
        "/api/v1/directives",
        headers=h_owner,
        json={"title": "توجيه تنفيذي", "body": "نص التوجيه", "recipient_id": manager.id, "follow_up_on": "2026-01-01"},
    )
    assert created.status_code == 201, created.text
    did = created.json()["id"]
    assert created.json()["status"] == "draft"

    assert client.post(f"/api/v1/directives/{did}/send", headers=h_owner).json()["status"] == "sent"

    # Only the recipient may acknowledge.
    assert client.post(f"/api/v1/directives/{did}/receive", headers=h_owner).status_code == 403
    received = client.post(f"/api/v1/directives/{did}/receive", headers=h_manager)
    assert received.json()["status"] == "received"
    assert received.json()["received_at"] is not None

    completed = client.post(f"/api/v1/directives/{did}/complete", headers=h_manager)
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None

    # Overdue list excludes completed directives.
    overdue = client.get("/api/v1/directives/overdue", headers=h_owner).json()
    assert all(d["id"] != did for d in overdue)


def test_overdue_directives_stay_with_their_sender_and_recipient(client, make_user, login):
    """PDF p.13: a directive has a single recipient.

    The overdue list returned every overdue directive system-wide, so a
    company manager holding `directive:view` could read directives addressed to
    other people — including their titles and bodies.
    """
    owner = make_user("od_owner@safir-platform.com", ["owner"])
    accountant = make_user("od_acct@safir-platform.com", ["accountant"])
    outsider = make_user("od_manager@safir-platform.com", ["company_manager"])
    h_owner = login("od_owner@safir-platform.com")
    h_outsider = login("od_manager@safir-platform.com")

    created = client.post(
        "/api/v1/directives",
        headers=h_owner,
        json={"title": "سري للمحاسب", "body": "نص سري", "recipient_id": accountant.id, "follow_up_on": "2020-01-01"},
    )
    assert created.status_code == 201, created.text
    did = created.json()["id"]
    assert client.post(f"/api/v1/directives/{did}/send", headers=h_owner).json()["status"] == "sent"

    # The sender sees their own overdue directive.
    sender_overdue = client.get("/api/v1/directives/overdue", headers=h_owner).json()
    assert any(d["id"] == did for d in sender_overdue)

    # An unrelated directive:view holder does not.
    outsider_overdue = client.get("/api/v1/directives/overdue", headers=h_outsider).json()
    assert all(d["id"] != did for d in outsider_overdue)


def test_service_request_thread_and_recipient_scoping(client, make_user, login):
    owner = make_user("s_owner@safir-platform.com", ["owner"])
    designer = make_user("s_designer@safir-platform.com", ["designer"])
    other = make_user("s_other@safir-platform.com", ["service_specialist"])
    h_owner = login("s_owner@safir-platform.com")
    h_designer = login("s_designer@safir-platform.com")
    h_other = login("s_other@safir-platform.com")
    cid = _company(client, h_owner, "SR-1")

    created = client.post(
        "/api/v1/service-requests",
        headers=h_owner,
        json={"subject": "تصميم هوية", "body": "تفاصيل", "service_type": "design", "company_id": cid, "recipient_id": designer.id, "priority": "urgent"},
    )
    assert created.status_code == 201, created.text
    rid = created.json()["id"]

    # Unrelated specialist does not see the request.
    assert client.get(f"/api/v1/service-requests/{rid}", headers=h_other).status_code == 404

    # Designer replies and changes status.
    reply = client.post(
        f"/api/v1/service-requests/{rid}/replies",
        headers=h_designer,
        json={"body": "تم البدء", "new_status": "in_progress"},
    )
    assert reply.status_code == 201, reply.text
    thread = client.get(f"/api/v1/service-requests/{rid}/thread", headers=h_designer).json()
    assert len(thread) == 1
    assert client.get(f"/api/v1/service-requests/{rid}", headers=h_designer).json()["status"] == "in_progress"


def test_lead_requires_registered_company(client, make_user, login):
    make_user("l_owner@safir-platform.com", ["owner"])
    bd = make_user("l_bd@safir-platform.com", ["business_developer"])
    h_owner = login("l_owner@safir-platform.com")
    h_bd = login("l_bd@safir-platform.com")
    cid = _company(client, h_owner, "LEAD-1")
    # The business developer is granted access to this company.
    client.patch(f"/api/v1/users/{bd.id}", headers=h_owner, json={"company_ids": [cid]})
    bad = client.post("/api/v1/leads", headers=h_bd, json={"name": "x", "company_id": 999999, "requested_service": "تصميم"})
    assert bad.status_code == 422
    ok = client.post("/api/v1/leads", headers=h_bd, json={"name": "عميل", "company_id": cid, "source": "referral", "requested_service": "تسويق"})
    assert ok.status_code == 201, ok.text


def test_lead_requires_the_requested_service(client, make_user, login):
    """Table 6 R3 stars «الخدمة المطلوبة *»: the API must refuse a lead without it."""
    make_user("ls_owner@safir-platform.com", ["owner"])
    h_owner = login("ls_owner@safir-platform.com")
    cid = _company(client, h_owner, "LEADS-1")

    missing = client.post("/api/v1/leads", headers=h_owner, json={"name": "عميل", "company_id": cid})
    assert missing.status_code == 422, missing.text

    blank = client.post(
        "/api/v1/leads", headers=h_owner, json={"name": "عميل", "company_id": cid, "requested_service": ""}
    )
    assert blank.status_code == 422, blank.text


def test_lead_is_transferred_to_the_receiving_companys_manager(client, make_user, login):
    """Table 6, «حفظ وتحويل»: the lead «يُحوَّل لمدير الشركة المستلمة».

    The conversion must land the lead on the receiving company's manager, which
    is what the manager dashboard's «عملاء محولون» card counts. The lead was
    created without an assignee, so the card always read zero.
    """
    make_user("lt_owner@safir-platform.com", ["owner"])
    manager = make_user("lt_manager@safir-platform.com", ["company_manager"])
    h_owner = login("lt_owner@safir-platform.com")
    cid = _company(client, h_owner, "LEADT-1")
    client.patch(f"/api/v1/companies/{cid}", headers=h_owner, json={"manager_user_id": manager.id})

    created = client.post(
        "/api/v1/leads",
        headers=h_owner,
        json={"name": "عميل", "company_id": cid, "requested_service": "تسويق"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["assigned_to_id"] == manager.id

    # The receiving manager's dashboard counts it under «عملاء محولون».
    h_manager = login("lt_manager@safir-platform.com")
    cards = {c["key"]: c["value"] for c in client.get("/api/v1/dashboard", headers=h_manager).json()["cards"]}
    assert cards["leads"] == 1

    # An explicit assignee still wins over the company default.
    other = make_user("lt_other@safir-platform.com", ["business_developer"])
    explicit = client.post(
        "/api/v1/leads",
        headers=h_owner,
        json={"name": "عميل 2", "company_id": cid, "assigned_to_id": other.id, "source": "manual", "requested_service": "تسويق"},
    )
    assert explicit.status_code == 201, explicit.text
    assert explicit.json()["assigned_to_id"] == other.id


def test_assistant_referral_becomes_a_task_on_the_developers_dashboard(client, make_user, login):
    """Table 6: «أُحيل الطلب إلى مطوّر الأعمال … وتظهر مهمة له في لوحته».

    The referral creates a directive for the business developer, so the
    «مهام من المساعد» card must count those tasks. It counted the developer's own
    assistant queries instead, which the referral never creates — the card read
    zero after a referral.
    """
    make_user("ref_owner@safir-platform.com", ["owner"])
    make_user("ref_bd@safir-platform.com", ["business_developer"])
    h_owner = login("ref_owner@safir-platform.com")
    h_bd = login("ref_bd@safir-platform.com")

    before = {c["key"]: c["value"] for c in client.get("/api/v1/dashboard", headers=h_bd).json()["cards"]}
    assert before["assistant"] == 0

    referred = client.post("/api/v1/ai/refer", headers=h_owner, json={})
    assert referred.status_code == 200, referred.text

    after = {c["key"]: c for c in client.get("/api/v1/dashboard", headers=h_bd).json()["cards"]}
    assert after["assistant"]["value"] == 1
    # Table 1 gives the developer no «المساعد الذكي» tab, so the card must open
    # the directives screen that lists the task, not the assistant screen.
    assert after["assistant"]["href"] == "/directives"

    # The task is also a directive the developer received, so it is actionable.
    directives = client.get("/api/v1/directives", headers=h_bd).json()
    assert any(d["id"] == referred.json()["directive_id"] for d in directives)


def test_lead_keeps_its_contact_method(client, make_user, login):
    """Table 6, «عميل محتمل جديد»: «وسيلة التواصل» is stored apart from the value."""
    make_user("cm_owner@safir-platform.com", ["owner"])
    bd = make_user("cm_bd@safir-platform.com", ["business_developer"])
    h_owner = login("cm_owner@safir-platform.com")
    h_bd = login("cm_bd@safir-platform.com")
    cid = _company(client, h_owner, "CM-1")
    client.patch(f"/api/v1/users/{bd.id}", headers=h_owner, json={"company_ids": [cid]})

    created = client.post(
        "/api/v1/leads",
        headers=h_bd,
        json={"name": "عميل", "company_id": cid, "contact_method": "whatsapp", "contact_phone": "39000000", "requested_service": "تسويق"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["contact_method"] == "whatsapp"

    listed = client.get("/api/v1/leads", headers=h_bd).json()
    assert listed[0]["contact_method"] == "whatsapp"

    # «تحديث»: status and note are written into the lead's own record.
    updated = client.patch(
        f"/api/v1/leads/{created.json()['id']}",
        headers=h_bd,
        json={"status": "contacted", "notes": "تم التواصل هاتفياً"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "contacted"
    assert updated.json()["notes"] == "تم التواصل هاتفياً"


def test_public_submission_rate_limit_and_conversion(client, make_user, login, db):
    make_user("w_owner@safir-platform.com", ["owner"])
    h_owner = login("w_owner@safir-platform.com")
    cid = _company(client, h_owner, "WEB-1")

    sub = client.post(
        "/api/v1/public/submissions",
        json={"kind": "opportunity", "name": "زائر", "email": "v@example.com", "phone": "123", "country": "البحرين", "message": "مرحبا", "company_id": cid, "consent": True},
    )
    assert sub.status_code == 201, sub.text
    sid = sub.json()["id"]

    converted = client.post(f"/api/v1/website/submissions/{sid}/convert", headers=h_owner, json={"target": "opportunity"})
    assert converted.status_code == 200, converted.text
    assert converted.json()["status"] == "converted"
    assert converted.json()["converted_type"] == "opportunity"

    # Cannot convert twice.
    assert client.post(f"/api/v1/website/submissions/{sid}/convert", headers=h_owner, json={"target": "opportunity"}).status_code == 409


def test_website_conversion_defaults_to_the_holding_when_no_company_named(client, make_user, login, db):
    """§6.5 / Table 7: «قدّم فرصة» carries no receiving company, so the
    conversion has nothing to route to. The opportunity form has no routing
    window (unlike the service request), so the Holding receives it rather than
    the action failing with a 422.
    """
    from app.models.enums import OpportunityStatus
    from app.models.operations import Opportunity
    from app.services.bootstrap import ensure_holding_company

    holding = ensure_holding_company(db)
    db.commit()

    make_user("hold_owner@safir-platform.com", ["owner"])
    h_owner = login("hold_owner@safir-platform.com")

    # The public form sends no company_id.
    opp_sub = client.post(
        "/api/v1/public/submissions",
        json={"kind": "opportunity", "name": "مستثمر", "email": "o@example.com", "phone": "123", "country": "البحرين", "subject": "فرصة", "message": "وصف الفرصة", "consent": True},
    )
    assert opp_sub.status_code == 201, opp_sub.text
    converted = client.post(f"/api/v1/website/submissions/{opp_sub.json()['id']}/convert", headers=h_owner, json={"target": "opportunity"})
    assert converted.status_code == 200, converted.text
    assert converted.json()["converted_type"] == "opportunity"

    opp = db.get(Opportunity, converted.json()["converted_id"])
    assert opp is not None
    assert opp.company_id == holding.id, "the opportunity is received by the Holding"
    assert opp.status == OpportunityStatus.DRAFT.value, "it arrives as a draft for internal review"


def test_conversion_target_is_optional(client, make_user, login, db):
    """The submission kind already decides the outcome, so the routing window's
    payload (company + service type) must convert without repeating the target.
    """
    from app.services.bootstrap import ensure_holding_company

    holding = ensure_holding_company(db)
    db.commit()

    make_user("opt_owner@safir-platform.com", ["owner"])
    h_owner = login("opt_owner@safir-platform.com")

    sub = client.post(
        "/api/v1/public/submissions",
        json={"kind": "opportunity", "name": "مستثمر", "email": "opt@example.com", "phone": "123", "country": "البحرين", "subject": "فرصة", "message": "وصف", "consent": True},
    )
    assert sub.status_code == 201, sub.text

    converted = client.post(f"/api/v1/website/submissions/{sub.json()['id']}/convert", headers=h_owner, json={})
    assert converted.status_code == 200, converted.text
    assert converted.json()["converted_type"] == "opportunity"

    from app.models.operations import Opportunity

    opp = db.get(Opportunity, converted.json()["converted_id"])
    assert opp is not None and opp.company_id == holding.id

    # A job application is only recorded for human review — no record, no user.
    # It needs a CV, so it arrives through the multipart route.
    job_sub = client.post(
        "/api/v1/public/submissions/with-file",
        data={"kind": "job_application", "name": "متقدم", "email": "j@example.com", "phone": "1", "expertise": "تسويق", "consent": "true"},
        files={"attachment": ("cv.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert job_sub.status_code == 201, job_sub.text
    job_conv = client.post(f"/api/v1/website/submissions/{job_sub.json()['id']}/convert", headers=h_owner, json={"target": "job_application"})
    assert job_conv.status_code == 200, job_conv.text
    assert job_conv.json()["converted_id"] is None


def test_website_visibility_accepts_a_json_body_and_rejects(client, make_user, login):
    """PDF p.15: the admin toggles a company's public visibility and can reject a
    submission. The screen sent a JSON body but the endpoint declared a query
    parameter, so every Show/Hide click answered 422 and the toggle did nothing.
    """
    make_user("vis_owner@safir-platform.com", ["owner"])
    h_owner = login("vis_owner@safir-platform.com")
    cid = _company(client, h_owner, "VIS-1")

    shown = client.patch(f"/api/v1/website/companies/{cid}/visibility", headers=h_owner, json={"public_visible": True})
    assert shown.status_code == 200, shown.text
    assert shown.json()["public_visible"] is True
    assert client.get(f"/api/v1/companies/{cid}", headers=h_owner).json()["public_visible"] is True

    hidden = client.patch(f"/api/v1/website/companies/{cid}/visibility", headers=h_owner, json={"public_visible": False})
    assert hidden.status_code == 200, hidden.text
    assert hidden.json()["public_visible"] is False

    sub = client.post(
        "/api/v1/public/submissions",
        json={"kind": "opportunity", "name": "زائر", "email": "r@example.com", "phone": "123", "country": "البحرين", "message": "x", "company_id": cid, "consent": True},
    )
    assert sub.status_code == 201, sub.text
    rejected = client.post(f"/api/v1/website/submissions/{sub.json()['id']}/reject", headers=h_owner)
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"

    actions = {e["action"] for e in client.get("/api/v1/audit", headers=h_owner).json()}
    assert "website.visibility" in actions
    assert "website.reject" in actions


def test_form_field_versioning_preserves_history(client, make_user, login):
    make_user("f_owner@safir-platform.com", ["owner"])
    h = login("f_owner@safir-platform.com")
    created = client.post(
        "/api/v1/form-fields",
        headers=h,
        json={"code": "net_profit", "name_ar": "صافي الربح", "name_en": "Net profit", "field_type": "amount"},
    )
    assert created.status_code == 201, created.text
    fid = created.json()["id"]
    assert created.json()["version"] == 1
    updated = client.patch(f"/api/v1/form-fields/{fid}", headers=h, json={"is_required": True})
    assert updated.json()["version"] == 2
    # Deactivation bumps the version again and keeps the record.
    deact = client.post(f"/api/v1/form-fields/{fid}/deactivate", headers=h)
    assert deact.json()["is_active"] is False
    assert deact.json()["version"] == 3


def test_ai_reports_configuration_status_without_key(client, make_user, login):
    make_user("ai_owner@safir-platform.com", ["owner"])
    h = login("ai_owner@safir-platform.com")
    status = client.get("/api/v1/ai/status", headers=h)
    assert status.status_code == 200
    assert status.json()["configured"] is False
    asked = client.post("/api/v1/ai/ask", headers=h, json={"prompt": "ما هي إيرادات الشركة؟"})
    assert asked.status_code == 200, asked.text
    body = asked.json()
    # No fabricated answer: an explicit configuration/uncertainty status.
    assert body["configured"] is False
    assert body["confidence"] in {"unconfigured", "no_data"}
    assert body["note"] in {"ai_provider_not_configured", "no_permitted_sources"}


def test_audit_log_records_sensitive_actions(client, make_user, login):
    make_user("a_owner@safir-platform.com", ["owner"])
    h = login("a_owner@safir-platform.com")
    _company(client, h, "AUD-1")
    events = client.get("/api/v1/audit", headers=h).json()
    actions = {e["action"] for e in events}
    assert "company.create" in actions
    assert "auth.login" in actions


def test_dashboards_differ_per_role(client, make_user, login):
    make_user("dash_owner@safir-platform.com", ["owner"])
    make_user("dash_designer@safir-platform.com", ["designer"])
    owner_dash = client.get("/api/v1/dashboard", headers=login("dash_owner@safir-platform.com")).json()
    designer_dash = client.get("/api/v1/dashboard", headers=login("dash_designer@safir-platform.com")).json()
    assert owner_dash["role"] == "owner"
    assert designer_dash["role"] == "designer"
    owner_keys = {c["key"] for c in owner_dash["cards"]}
    designer_keys = {c["key"] for c in designer_dash["cards"]}
    assert owner_keys != designer_keys


def test_accountant_dashboard_actions_open_the_named_screens(client, make_user, login):
    """PDF p.24 / §5.3 and Table 3: two buttons, each opening its own screen.

    «مراجعة تقرير» opens the reports list; «مصروف / فاتورة / عمولة جديدة» opens
    holding accounting, where the three entry forms live (Table 5).
    """
    make_user("dash_acct@safir-platform.com", ["accountant"])
    dash = client.get("/api/v1/dashboard", headers=login("dash_acct@safir-platform.com")).json()
    assert dash["role"] == "accountant"
    hrefs = {a["label_en"]: a["href"] for a in dash["actions"]}
    assert hrefs == {
        "Review a report": "/reports",
        "New expense / invoice / commission": "/accounting",
    }


def test_advisor_dashboard_actions_are_the_three_message_categories(client, make_user, login):
    """§5.7 / Table 5: the advisor has three actions, each to its own category.

    A recommendation and a suggestion go to the Business Developer; a report
    goes to the Owner or the Business Developer. The advisor has no approval or
    execution permission, so the three buttons only open the compose form with
    the chosen category pre-selected.
    """
    make_user("dash_adv@safir-platform.com", ["advisor"])
    dash = client.get("/api/v1/dashboard", headers=login("dash_adv@safir-platform.com")).json()
    assert dash["role"] == "advisor"
    hrefs = {a["label_en"]: a["href"] for a in dash["actions"]}
    assert hrefs["Add a recommendation"] == "/advisor?category=recommendation"
    assert hrefs["Report"] == "/advisor?category=report"
    assert hrefs["Suggestion"] == "/advisor?category=suggestion"


def test_accounting_export_covers_exactly_the_visible_entries(client, make_user, login):
    """PDF p.9 asks for export where applicable; the file must match the scope.

    The endpoint existed but no screen called it, so the export was unreachable.
    It must also respect company isolation: an accountant scoped to one company
    must not receive another company's entries in the workbook.
    """
    import io

    from openpyxl import load_workbook

    make_user("exp_owner@safir-platform.com", ["owner"])
    h_owner = login("exp_owner@safir-platform.com")
    # §5.1/§5.3: the owner's Holding accounting is view only, so the entries are
    # recorded by the accountant, whose screen is the only financial editor.
    creator = make_user("exp_creator@safir-platform.com", ["accountant"])
    h_creator = login("exp_creator@safir-platform.com")
    first = _company(client, h_owner, "EXP-1")
    second = _company(client, h_owner, "EXP-2")
    client.patch(f"/api/v1/users/{creator.id}", headers=h_owner, json={"company_ids": [first, second]})
    for cid, ref in ((first, "REF-A"), (second, "REF-B")):
        resp = client.post(
            "/api/v1/accounting",
            headers=h_creator,
            json={"kind": "expense", "company_id": cid, "reference": ref, "description": "x", "amount": "10.00", "currency": "SAR", "entry_date": "2026-01-01"},
        )
        assert resp.status_code == 201, resp.text

    # The owner sees both companies.
    both = client.get("/api/v1/accounting/export.xlsx", headers=h_owner)
    assert both.status_code == 200
    rows = list(load_workbook(io.BytesIO(both.content)).active.iter_rows(values_only=True))
    refs = {r[3] for r in rows[1:]}
    assert {"REF-A", "REF-B"} <= refs

    # A user scoped to the first company only gets that company's entry.
    scoped = make_user("exp_acct@safir-platform.com", ["accountant"])
    client.patch(f"/api/v1/users/{scoped.id}", headers=h_owner, json={"company_ids": [first]})
    limited = client.get("/api/v1/accounting/export.xlsx", headers=login("exp_acct@safir-platform.com"))
    assert limited.status_code == 200
    limited_rows = list(load_workbook(io.BytesIO(limited.content)).active.iter_rows(values_only=True))
    limited_refs = {r[3] for r in limited_rows[1:]}
    assert "REF-A" in limited_refs
    assert "REF-B" not in limited_refs

    # A role with no accounting permission must be refused.
    make_user("exp_designer@safir-platform.com", ["designer"])
    denied = client.get("/api/v1/accounting/export.xlsx", headers=login("exp_designer@safir-platform.com"))
    assert denied.status_code == 403

    actions = {e["action"] for e in client.get("/api/v1/audit", headers=h_owner).json()}
    assert "accounting.export" in actions


def test_company_logo_must_be_an_uploaded_image_of_that_company(client, make_user, login):
    """PDF p.6 lists the official logo as a company field.

    The model and the read model carried ``logo_file_id`` but nothing could set
    it, so the field was decorative. Setting it must also be safe: a manager must
    not be able to point a company's logo at another company's private file.
    """
    make_user("logo_owner@safir-platform.com", ["owner"])
    h_owner = login("logo_owner@safir-platform.com")
    first = _company(client, h_owner, "LOGO-1")
    second = _company(client, h_owner, "LOGO-2")

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    uploaded = client.post(
        "/api/v1/files",
        headers=h_owner,
        files={"file": ("logo.png", png, "image/png")},
        data={"company_id": str(first)},
    )
    assert uploaded.status_code == 201, uploaded.text
    file_id = uploaded.json()["id"]

    patched = client.patch(f"/api/v1/companies/{first}", headers=h_owner, json={"logo_file_id": file_id})
    assert patched.status_code == 200, patched.text
    assert patched.json()["logo_file_id"] == file_id
    assert patched.json()["logo_url"] == f"/api/v1/files/{file_id}/download"

    # A logo id belonging to another company is refused.
    other = client.patch(f"/api/v1/companies/{second}", headers=h_owner, json={"logo_file_id": file_id})
    assert other.status_code == 422

    # A missing file id is a 404 rather than a silently accepted dangling pointer.
    missing = client.patch(f"/api/v1/companies/{first}", headers=h_owner, json={"logo_file_id": 999999})
    assert missing.status_code == 404


def test_manager_deadline_reminder_alert_is_toned_by_urgency(client, make_user, login, db):
    """§2 and §7.5: the deadline reminder is an alert, not plain text.

    The banner names the period, the company and the days left; the §2 colour
    rules make it amber while the deadline approaches and red once it is late,
    so the reminder reads as the alert the brief describes.
    """
    from datetime import date, timedelta

    from app.models.business import ReportingPeriod

    make_user("rem_owner@safir-platform.com", ["owner"])
    manager = make_user("rem_manager@safir-platform.com", ["company_manager"])
    h_owner = login("rem_owner@safir-platform.com")
    h_manager = login("rem_manager@safir-platform.com")
    cid = _company(client, h_owner, "REM-1")
    client.patch(f"/api/v1/companies/{cid}", headers=h_owner, json={"status": "active", "manager_user_id": manager.id})
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})

    period = ReportingPeriod(
        label_ar="2026-10", label_en="2026-10", year=2026, month=10,
        opens_on=date.today() - timedelta(days=10), due_on=date.today() + timedelta(days=2),
    )
    db.add(period)
    db.commit()

    approaching = client.get("/api/v1/dashboard", headers=h_manager).json()
    assert approaching["banner_tone"] == "warn"
    assert "يستحق بعد" in approaching["banner_ar"]

    period.due_on = date.today() - timedelta(days=1)
    db.commit()
    late = client.get("/api/v1/dashboard", headers=h_manager).json()
    assert late["banner_tone"] == "bad"
    assert "متأخر" in late["banner_ar"]


def test_company_manager_and_activation_information_are_settable(client, make_user, login):
    """PDF p.6 lists the company manager and the activation information.

    Both were carried by the model but neither could be written and the
    activation note was not even read back, so the two fields were decorative.
    """
    make_user("mgr_owner@safir-platform.com", ["owner"])
    make_user("mgr_person@safir-platform.com", ["company_manager"])
    h_owner = login("mgr_owner@safir-platform.com")
    cid = _company(client, h_owner, "MGR-1")

    people = client.get("/api/v1/users/directory", headers=h_owner).json()
    manager_id = next(p["id"] for p in people if p["full_name_en"] == "mgr_person@safir-platform.com")

    patched = client.patch(
        f"/api/v1/companies/{cid}",
        headers=h_owner,
        json={"manager_user_id": manager_id, "activation_notes": "فُعّلت بعد استيفاء السجل التجاري."},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["manager_user_id"] == manager_id
    assert body["activation_notes"] == "فُعّلت بعد استيفاء السجل التجاري."

    # The values survive a re-read rather than living only in the response.
    reread = client.get(f"/api/v1/companies/{cid}", headers=h_owner).json()
    assert reread["manager_user_id"] == manager_id
    assert reread["activation_notes"] == "فُعّلت بعد استيفاء السجل التجاري."


def test_owner_dashboard_revenue_column_names_the_revenue_field(client, make_user, login, db):
    """PDF p.5: the group-summary column is labelled "revenue".

    It used to take any numeric value from the last approved report, so it
    showed whichever field happened to be entered first. A number under the
    wrong heading is a wrong financial figure, not a missing one.
    """
    from app.models.business import FormField

    make_user("dash_rev_owner@safir-platform.com", ["owner"])
    h = login("dash_rev_owner@safir-platform.com")
    make_user("dash_rev_acct@safir-platform.com", ["accountant"])
    h_acct = login("dash_rev_acct@safir-platform.com")
    # §7.1: the company manager authors the subsidiary report; the owner reads.
    mgr = make_user("dash_rev_mgr@safir-platform.com", ["company_manager"])
    h_mgr = login("dash_rev_mgr@safir-platform.com")
    cid = _company(client, h, "REV-1")
    client.patch(f"/api/v1/users/{mgr.id}", headers=h, json={"company_ids": [cid]})

    period = client.post(
        "/api/v1/periods",
        headers=h,
        json={"label_ar": "فبراير 2026", "label_en": "Feb 2026", "year": 2026, "month": 2, "opens_on": "2026-02-01", "due_on": "2026-03-05"},
    ).json()
    report = client.post("/api/v1/reports", headers=h_mgr, json={"company_id": cid, "period_id": period["id"]}).json()

    # A non-revenue field is created first, so an unordered "first numeric
    # value" would pick it and print it under the revenue heading.
    other = FormField(code="HEADCOUNT", name_ar="عدد الموظفين", name_en="Headcount", field_type="amount", version=1)
    revenue = FormField(code="TOTAL_REVENUE", name_ar="إجمالي الإيرادات", name_en="Total revenue", field_type="amount", version=1)
    db.add_all([other, revenue])
    db.commit()

    from app.models.business import MonthlyReport
    from app.models.operations import StoredFile

    statement = StoredFile(storage_name="s", original_name="b.pdf", content_type="application/pdf", size_bytes=1, checksum="c", owner_id=1)
    db.add(statement)
    db.commit()
    db.get(MonthlyReport, report["id"]).bank_statement_file_id = statement.id
    db.commit()

    saved = client.put(
        f"/api/v1/reports/{report['id']}/values",
        headers=h_mgr,
        json={"values": [
            {"field_id": other.id, "value_number": "42.00"},
            {"field_id": revenue.id, "value_number": "5000.00"},
        ]},
    )
    assert saved.status_code == 200, saved.text

    assert client.post(f"/api/v1/reports/{report['id']}/submit", headers=h_mgr).status_code == 200
    assert client.post(f"/api/v1/reports/{report['id']}/approve", headers=h_acct).status_code == 200

    dash = client.get("/api/v1/dashboard", headers=h).json()
    section = next(s for s in dash["sections"] if s["key"] == "group_summary")
    row = next(r for r in section["rows"] if r[0] == "شركة REV-1")
    assert "5,000" in row[3], row
    assert "42" not in row[3], row


def test_confidential_hr_attachment_is_restricted_to_the_manager(client, make_user, login):
    """Page 14: a leave attachment reads «مرفق مقيد» to the owner.

    The owner holds broad oversight, but the reference names confidential HR
    attachments as information withheld even from the owner. The manager who
    records the leave may still download it; the owner must be refused and see
    the marker instead of a link.
    """
    make_user("owner-hr@example.com", ["owner"])
    manager = make_user("manager-hr@example.com", ["company_manager"])
    h_owner = login("owner-hr@example.com")
    h_manager = login("manager-hr@example.com")

    cid = _company(client, h_owner, "HRC-1")
    # The manager must be scoped to the company before it can record its staff.
    client.patch(f"/api/v1/users/{manager.id}", headers=h_owner, json={"company_ids": [cid]})

    emp = client.post(
        "/api/v1/employees",
        headers=h_manager,
        json={"name_ar": "سارة", "name_en": "Sara", "job_title": "مديرة", "company_id": cid},
    )
    assert emp.status_code == 201, emp.text

    upload = client.post(
        "/api/v1/files",
        headers=h_manager,
        files={"file": ("leave.pdf", b"%PDF-1.4 leave", "application/pdf")},
        data={"is_confidential": "true"},
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    event = client.post(
        f"/api/v1/employees/{emp.json()['id']}/events",
        headers=h_manager,
        json={"kind": "annual_leave", "detail": "إجازة سنوية", "attachment_file_id": file_id},
    )
    assert event.status_code == 201, event.text
    assert event.json()["attachment_file_id"] == file_id

    # The manager who filed it may download the attachment.
    assert client.get(f"/api/v1/files/{file_id}/download", headers=h_manager).status_code == 200
    # The owner must be refused, so the UI shows «مرفق مقيد» rather than a link.
    denied = client.get(f"/api/v1/files/{file_id}/download", headers=h_owner)
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["error"] == "restricted_attachment"


def test_every_ai_source_link_points_at_a_real_screen():
    """Each "open the source record" link must resolve to a screen that exists.

    The assistant cites accounting entries, service requests and directives, but
    those screens have no per-record route. The links were built as
    ``/accounting/{id}`` and similar, which the app answers with 404 — the
    reference requires the user to be able to open the original record.
    """
    repo = Path(__file__).resolve().parents[2]
    # Admin screens live under app/(admin)/platform after the public site took
    # the locale root. Scan that tree so a route rename cannot silently pass.
    admin_root = repo / "frontend" / "app" / "(admin)" / "platform"
    routes = {
        str(p.parent.relative_to(admin_root)).replace("(app)", "").strip("/")
        for p in admin_root.rglob("page.tsx")
    }
    assert routes, "no frontend routes found; the scan is broken"

    source_urls = re.findall(r'"url": f"([^"]+)"', (repo / "backend" / "app" / "ai" / "retrieval.py").read_text())
    assert source_urls, "no AI source URLs found; the scan is broken"

    for template in source_urls:
        segments = template.split("?")[0].strip("/").split("/")
        # A trailing record placeholder needs a matching dynamic route
        # (e.g. ``/reports/{id}`` needs ``reports/[id]``). Without it the link
        # 404s, which is what happened for service requests and directives.
        if re.fullmatch(r"\{[^}]+\}", segments[-1]):
            target = "/".join(segments[:-1] + ["[id]"])
        else:
            target = "/".join(segments)
        assert target in routes, f"{template!r} has no screen: no route {target!r} in {sorted(routes)}"


# --- Business notifications (Word Tables 5, 6, 10; §8, §12) -----------------
class _Mailbox:
    """Captures the messages a workflow event would send, without a transport."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str]] = []

    def __call__(self, to_email: str, content) -> bool:
        self.messages.append((to_email, content.subject, content.body))
        return True

    def recipients(self) -> list[str]:
        return [m[0] for m in self.messages]


def _capture(monkeypatch) -> _Mailbox:
    from app.services import mail

    box = _Mailbox()
    monkeypatch.setattr(mail, "send", box)
    return box


def test_service_request_routing_emails_the_specialist(client, make_user, login, monkeypatch):
    """Table 5: «الطلب يوجَّه للمختص حسب نوع الخدمة، ويصله بريد»."""
    box = _capture(monkeypatch)
    make_user("sr_owner@safir-platform.com", ["owner"])
    specialist = make_user("sr_specialist@safir-platform.com", ["service_specialist"])
    h_owner = login("sr_owner@safir-platform.com")
    cid = _company(client, h_owner, "SR-NOTIFY")

    resp = client.post(
        "/api/v1/service-requests",
        headers=h_owner,
        json={"subject": "طلب تصميم", "body": "احتياج", "service_type": "design", "company_id": cid, "priority": "normal", "recipient_id": specialist.id},
    )
    assert resp.status_code == 201, resp.text
    assert "sr_specialist@safir-platform.com" in box.recipients()
    # The notification names the request and carries no financial figure.
    body = next(m[2] for m in box.messages if m[0] == "sr_specialist@safir-platform.com")
    assert "طلب تصميم" in body
    assert not re.search(r"[$€£]|\bSAR\b|\bBHD\b|\d+\.\d{2}\b", body)


def test_owner_must_name_the_receiving_specialist(client, make_user, login, monkeypatch):
    """Table 6 R1: «للمالك: المختص المستلم *» — the owner cannot leave it blank."""
    _capture(monkeypatch)
    make_user("sr_owner2@safir-platform.com", ["owner"])
    make_user("sr_specialist2@safir-platform.com", ["service_specialist"])
    h_owner = login("sr_owner2@safir-platform.com")
    cid = _company(client, h_owner, "SR-REQ")
    resp = client.post(
        "/api/v1/service-requests",
        headers=h_owner,
        json={"subject": "طلب", "body": "احتياج", "service_type": "design", "company_id": cid},
    )
    assert resp.status_code == 422, resp.text


def test_a_manager_request_is_routed_by_service_type(client, make_user, login, monkeypatch):
    """§6.4: a manager's request is routed to the specialist by service type."""
    box = _capture(monkeypatch)
    make_user("sr_owner3@safir-platform.com", ["owner"])
    make_user("sr_specialist3@safir-platform.com", ["service_specialist"])
    h_owner = login("sr_owner3@safir-platform.com")
    cid = _company(client, h_owner, "SR-MGR")
    make_user("sr_mgr@safir-platform.com", ["company_manager"], companies=[cid])
    resp = client.post(
        "/api/v1/service-requests",
        headers=login("sr_mgr@safir-platform.com"),
        json={"subject": "طلب", "body": "احتياج", "service_type": "design", "company_id": cid},
    )
    assert resp.status_code == 201, resp.text
    assert "sr_specialist3@safir-platform.com" in box.recipients()


def test_complaint_reaches_only_the_owner_by_email(client, make_user, login, monkeypatch):
    """Table 5: «ترسل للمالك وحده» — exactly one recipient, no copy."""
    box = _capture(monkeypatch)
    make_user("cmp_owner@safir-platform.com", ["owner"])
    marketer = make_user("cmp_marketer@safir-platform.com", ["marketer"])
    h_owner = login("cmp_owner@safir-platform.com")
    h_marketer = login("cmp_marketer@safir-platform.com")
    cid = _company(client, h_owner, "CMP-1")
    client.patch(f"/api/v1/users/{marketer.id}", headers=h_owner, json={"company_ids": [cid]})

    resp = client.post("/api/v1/service-requests/complaint", headers=h_marketer, json={"body": "شكوى", "company_id": cid})
    assert resp.status_code == 201, resp.text
    assert box.recipients() == ["cmp_owner@safir-platform.com"]


def test_directive_notifies_its_single_recipient(client, make_user, login, monkeypatch):
    """Table 5/§11: «لمستلم واحد فقط دون نسخة لغيره»."""
    box = _capture(monkeypatch)
    make_user("dir_owner@safir-platform.com", ["owner"])
    recipient = make_user("dir_manager@safir-platform.com", ["company_manager"])
    h_owner = login("dir_owner@safir-platform.com")

    resp = client.post(
        "/api/v1/directives",
        headers=h_owner,
        json={"title": "توجيه", "body": "النص", "recipient_id": recipient.id, "follow_up_on": "2026-01-01"},
    )
    assert resp.status_code == 201, resp.text
    assert box.recipients() == ["dir_manager@safir-platform.com"]


def test_assistant_referral_emails_the_business_developer(client, make_user, login, monkeypatch):
    """Table 5/10: «أُحيل الطلب إلى مطوّر الأعمال … يصله بريد وتظهر مهمة له»."""
    box = _capture(monkeypatch)
    make_user("ai_owner@safir-platform.com", ["owner"])
    make_user("ai_bd@safir-platform.com", ["business_developer"])
    h_owner = login("ai_owner@safir-platform.com")

    resp = client.post(
        "/api/v1/ai/refer",
        headers=h_owner,
        json={"title": "خطة", "body": "تفاصيل"},
    )
    assert resp.status_code == 200, resp.text
    assert box.recipients() == ["ai_bd@safir-platform.com"]


def test_conversion_emails_the_company_manager_and_specialist(client, make_user, login, monkeypatch, db):
    """Table 6/10: «يُنشأ طلب خدمة … مع نسخة بريد لمدير الشركة والمختص»."""
    box = _capture(monkeypatch)
    make_user("cv_owner@safir-platform.com", ["owner"])
    manager = make_user("cv_manager@safir-platform.com", ["company_manager"])
    make_user("cv_specialist@safir-platform.com", ["service_specialist"])
    h_owner = login("cv_owner@safir-platform.com")
    cid = _company(client, h_owner, "CV-1")
    client.patch(f"/api/v1/companies/{cid}", headers=h_owner, json={"manager_user_id": manager.id})

    from app.models.enums import SubmissionKind
    from app.models.operations import WebsiteSubmission

    sub = WebsiteSubmission(
        kind=SubmissionKind.SERVICE_REQUEST.value,
        name="زائر",
        email="visitor@example.com",
        phone="123",
        service_type="الاستشارات",
        message="طلب",
        company_id=cid,
        status="new",
    )
    db.add(sub)
    db.commit()

    resp = client.post(
        f"/api/v1/website/submissions/{sub.id}/convert",
        headers=h_owner,
        json={"target": "service_request", "company_id": cid, "service_type": "accounting"},
    )
    assert resp.status_code == 200, resp.text
    recipients = set(box.recipients())
    assert "cv_manager@safir-platform.com" in recipients
    assert "cv_specialist@safir-platform.com" in recipients

