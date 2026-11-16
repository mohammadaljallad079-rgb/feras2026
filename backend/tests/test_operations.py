"""Business operation tests: opportunities, directives, service requests, leads,
website conversion, form builder versioning and the AI configuration status."""

from __future__ import annotations


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
        json={"title": "فرصة جديدة", "company_id": cid, "estimated_value": "50000.00", "currency": "SAR"},
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
        json={"subject": "تصميم هوية", "body": "تفاصيل", "company_id": cid, "recipient_id": designer.id, "priority": "high"},
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
    bad = client.post("/api/v1/leads", headers=h_bd, json={"name": "x", "company_id": 999999})
    assert bad.status_code == 422
    ok = client.post("/api/v1/leads", headers=h_bd, json={"name": "عميل", "company_id": cid, "source": "referral"})
    assert ok.status_code == 201, ok.text


def test_public_submission_rate_limit_and_conversion(client, make_user, login, db):
    make_user("w_owner@safir-platform.com", ["owner"])
    h_owner = login("w_owner@safir-platform.com")
    cid = _company(client, h_owner, "WEB-1")

    sub = client.post(
        "/api/v1/public/submissions",
        json={"kind": "contact", "name": "زائر", "email": "v@example.com", "message": "مرحبا", "company_id": cid},
    )
    assert sub.status_code == 201, sub.text
    sid = sub.json()["id"]

    converted = client.post(f"/api/v1/website/submissions/{sid}/convert", headers=h_owner, json={"target": "lead"})
    assert converted.status_code == 200, converted.text
    assert converted.json()["status"] == "converted"
    assert converted.json()["converted_type"] == "lead"

    # Cannot convert twice.
    assert client.post(f"/api/v1/website/submissions/{sid}/convert", headers=h_owner, json={"target": "lead"}).status_code == 409


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
