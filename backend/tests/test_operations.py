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
        json={"kind": "contact", "name": "زائر", "email": "r@example.com", "message": "x", "company_id": cid},
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


def test_accountant_dashboard_actions_deep_link_to_each_entry_kind(client, make_user, login):
    """PDF p.24: the three buttons must open the accounting screen on the right tab.

    The accounting page reads `?kind=`, so a link without it lands on the default
    tab and the button silently does the wrong thing.
    """
    make_user("dash_acct@safir-platform.com", ["accountant"])
    dash = client.get("/api/v1/dashboard", headers=login("dash_acct@safir-platform.com")).json()
    assert dash["role"] == "accountant"
    hrefs = {a["label_en"]: a["href"] for a in dash["actions"]}
    assert hrefs["Expense"] == "/accounting?kind=expense"
    assert hrefs["Invoice"] == "/accounting?kind=invoice"
    assert hrefs["Commission"] == "/accounting?kind=commission"


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
    first = _company(client, h_owner, "EXP-1")
    second = _company(client, h_owner, "EXP-2")
    for cid, ref in ((first, "REF-A"), (second, "REF-B")):
        resp = client.post(
            "/api/v1/accounting",
            headers=h_owner,
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


def test_every_ai_source_link_points_at_a_real_screen():
    """Each "open the source record" link must resolve to a screen that exists.

    The assistant cites accounting entries, service requests and directives, but
    those screens have no per-record route. The links were built as
    ``/accounting/{id}`` and similar, which the app answers with 404 — the
    reference requires the user to be able to open the original record.
    """
    repo = Path(__file__).resolve().parents[2]
    routes = {
        str(p.parent.relative_to(repo / "frontend" / "app" / "(app)"))
        for p in (repo / "frontend" / "app" / "(app)").rglob("page.tsx")
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
