"""End-to-end functional acceptance: real PostgreSQL, real HTTP, real RBAC.

Covers the journeys the delivery brief requires, including the negative
cross-company isolation checks. Run with the API base URL of a live server:

    SAFIR_BASE_URL=http://localhost:8000 python -m pytest tests/test_e2e_journeys.py -v
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

BASE = os.environ.get("SAFIR_BASE_URL", "http://localhost:8000")
PASSWORD = "Safir!2026"

ACCOUNTS = {
    "owner": "owner@safir-platform.com",
    "manager": "manager@safir-platform.com",
    "accountant": "accountant@safir-platform.com",
    "bd": "bd@safir-platform.com",
    "marketer": "marketer@safir-platform.com",
    "advisor": "advisor@safir-platform.com",
    "specialist": "specialist@safir-platform.com",
}


def _login(email: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=30)
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(scope="module")
def clients() -> dict[str, httpx.Client]:
    return {key: _login(email) for key, email in ACCOUNTS.items()}


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def company_id(clients) -> int:
    resp = clients["owner"].post(
        "/api/v1/companies",
        json={
            "code": _unique("E2E").upper(),
            "name_ar": "شركة اختبار",
            "name_en": "Acceptance Co",
            "country": "SA",
            "sector": "technology",
            "currency": "SAR",
            "ownership_percent": "80.00",
        },
    )
    assert resp.status_code == 201, resp.text
    cid = resp.json()["id"]
    activated = clients["owner"].post(f"/api/v1/companies/{cid}/activate")
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    return cid


@pytest.fixture(scope="module")
def period_id(clients) -> int:
    resp = clients["owner"].post(
        "/api/v1/periods",
        json={
            "label_ar": "فترة القبول",
            "label_en": "Acceptance period",
            "year": 2026,
            "month": 1,
            "opens_on": "2026-01-01",
            "due_on": "2026-01-31",
        },
    )
    assert resp.status_code in (201, 409), resp.text
    if resp.status_code == 409:
        return clients["owner"].get("/api/v1/periods").json()[0]["id"]
    return resp.json()["id"]


def _invite_and_login(owner: httpx.Client, role_slug: str, company_id: int) -> httpx.Client:
    """Owner invites a user scoped to one company, sets a password through the
    single-use reset link, and signs in. This is the invitation journey."""
    email = f"{role_slug}-{uuid.uuid4().hex[:8]}@example.com"
    invited = owner.post(
        "/api/v1/users",
        json={
            "email": email,
            "full_name_ar": f"مستخدم {role_slug}",
            "full_name_en": f"User {role_slug}",
            "locale": "ar",
            "role_slugs": [role_slug],
            "company_ids": [company_id],
        },
    )
    assert invited.status_code == 201, invited.text
    setup_token = invited.json()["setup_token"]

    anon = httpx.Client(base_url=BASE, timeout=30)
    confirmed = anon.post("/api/v1/auth/password-reset/confirm", json={"token": setup_token, "new_password": PASSWORD})
    assert confirmed.status_code == 204, confirmed.text
    return _login(email)


@pytest.fixture(scope="module")
def scoped(clients, company_id) -> dict[str, httpx.Client]:
    """Users granted a single company through the invitation flow."""
    return {
        "manager": _invite_and_login(clients["owner"], "company_manager", company_id),
        "accountant": _invite_and_login(clients["owner"], "accountant", company_id),
        "bd": _invite_and_login(clients["owner"], "business_developer", company_id),
        "marketer": _invite_and_login(clients["owner"], "marketer", company_id),
    }


def test_owner_creates_and_activates_company(company_id):
    assert isinstance(company_id, int)


def test_cross_company_access_is_denied(clients, company_id):
    """A manager scoped to no company must not read an unrelated company."""
    manager = clients["manager"]
    resp = manager.get(f"/api/v1/companies/{company_id}")
    assert resp.status_code in (403, 404), resp.text
    assert "name_ar" not in resp.text


def test_reporting_lifecycle_with_return_and_forward(clients, scoped, company_id, period_id):
    manager, accountant, owner = scoped["manager"], scoped["accountant"], clients["owner"]

    created = manager.post("/api/v1/reports", json={"company_id": company_id, "period_id": period_id})
    if created.status_code == 409:
        existing = manager.get("/api/v1/reports").json()
        report_id = existing[0]["id"]
    else:
        assert created.status_code == 201, created.text
        report_id = created.json()["id"]

    # The manager attaches the required bank statement before submitting.
    upload = manager.post(
        "/api/v1/files",
        files={"file": ("statement.pdf", b"%PDF-1.4 statement", "application/pdf")},
        data={"company_id": str(company_id)},
    )
    assert upload.status_code == 201, upload.text
    statement_id = upload.json()["id"]
    saved = manager.put(
        f"/api/v1/reports/{report_id}/values",
        json={"commentary": "تقرير الشهر", "values": [], "bank_statement_file_id": statement_id},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["bank_statement_file_id"] == statement_id

    submitted = manager.post(f"/api/v1/reports/{report_id}/submit")
    assert submitted.status_code == 200, submitted.text

    returned = accountant.post(f"/api/v1/reports/{report_id}/return", json={"reason": "أرقام غير مطابقة"})
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == "returned"

    resubmitted = manager.post(f"/api/v1/reports/{report_id}/submit")
    assert resubmitted.status_code == 200, resubmitted.text

    approved = accountant.post(f"/api/v1/reports/{report_id}/approve")
    assert approved.status_code == 200, approved.text

    locked = manager.put(f"/api/v1/reports/{report_id}/values", json={"commentary": "late", "values": []})
    assert locked.status_code == 409, locked.text

    forwarded = accountant.post(f"/api/v1/reports/{report_id}/forward")
    assert forwarded.status_code == 200, forwarded.text

    visible = owner.get("/api/v1/reports")
    assert visible.status_code == 200
    assert report_id in [r["id"] for r in visible.json()]


def test_accountant_records_accounting_entries(scoped, company_id):
    resp = scoped["accountant"].post(
        "/api/v1/accounting",
        json={
            "kind": "invoice",
            "company_id": company_id,
            "reference": _unique("INV"),
            "description": "استشارات",
            "amount": "12500.75",
            "currency": "SAR",
            "entry_date": "2026-01-15",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["amount"] == "12500.75"


def test_business_developer_opportunity_and_owner_decision(clients, scoped, company_id):
    bd, owner = scoped["bd"], clients["owner"]
    created = bd.post(
        "/api/v1/opportunities",
        json={"title": _unique("Opp"), "company_id": company_id, "estimated_value": "50000.00", "currency": "SAR"},
    )
    assert created.status_code == 201, created.text
    opp_id = created.json()["id"]

    assert bd.post(f"/api/v1/opportunities/{opp_id}/submit").status_code == 200

    decided = owner.post(f"/api/v1/opportunities/{opp_id}/decision", json={"decision": "approved", "note": "مقبول"})
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"
    assert decided.json()["decided_at"] is not None

    forbidden = clients["marketer"].post(f"/api/v1/opportunities/{opp_id}/decision", json={"decision": "rejected"})
    assert forbidden.status_code == 403, forbidden.text


def test_directive_receipt_and_completion(clients):
    owner, manager = clients["owner"], clients["manager"]
    me = manager.get("/api/v1/auth/me").json()

    created = owner.post(
        "/api/v1/directives",
        json={"title": _unique("Directive"), "body": "نص التوجيه", "recipient_id": me["id"], "follow_up_on": "2026-02-01"},
    )
    assert created.status_code == 201, created.text
    directive_id = created.json()["id"]

    assert owner.post(f"/api/v1/directives/{directive_id}/send").status_code == 200
    received = manager.post(f"/api/v1/directives/{directive_id}/receive")
    assert received.status_code == 200, received.text
    assert received.json()["received_at"] is not None

    completed = manager.post(f"/api/v1/directives/{directive_id}/complete")
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_specialist_service_request_thread(clients, company_id):
    owner, specialist = clients["owner"], clients["specialist"]
    me = specialist.get("/api/v1/auth/me").json()

    created = owner.post(
        "/api/v1/service-requests",
        json={"subject": _unique("Request"), "body": "تفاصيل", "company_id": company_id, "recipient_id": me["id"], "priority": "high"},
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    mine = specialist.get("/api/v1/service-requests")
    assert request_id in [r["id"] for r in mine.json()]

    reply = specialist.post(f"/api/v1/service-requests/{request_id}/replies", json={"body": "تم البدء", "new_status": "in_progress"})
    assert reply.status_code == 201, reply.text

    thread = owner.get(f"/api/v1/service-requests/{request_id}/thread")
    assert thread.status_code == 200
    assert any(r["body"] == "تم البدء" for r in thread.json())


def test_marketer_lead_and_advisor_recommendation(clients, scoped, company_id):
    marketer, advisor, owner = scoped["marketer"], clients["advisor"], clients["owner"]

    lead = marketer.post(
        "/api/v1/leads",
        json={"name": _unique("Lead"), "company_id": company_id, "requested_service": "تسويق", "source": "website"},
    )
    assert lead.status_code == 201, lead.text

    me = owner.get("/api/v1/auth/me").json()
    message = advisor.post(
        "/api/v1/advisor/messages",
        json={"recipient_id": me["id"], "category": "recommendation", "subject": _unique("Rec"), "body": "توصية"},
    )
    assert message.status_code == 201, message.text
    assert message.json()["status"] != "read"
    read = owner.post(f"/api/v1/advisor/messages/{message.json()['id']}/read")
    assert read.status_code == 200
    assert read.json()["status"] == "read"


def test_owner_creates_dynamic_form_field(clients):
    owner = clients["owner"]
    resp = owner.post(
        "/api/v1/form-fields",
        json={"code": _unique("FLD").upper(), "name_ar": "حقل تجريبي", "name_en": "Test field", "field_type": "amount", "is_required": True},
    )
    assert resp.status_code == 201, resp.text
    field = resp.json()
    assert field["version"] == 1

    updated = owner.patch(f"/api/v1/form-fields/{field['id']}", json={"is_required": False})
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2, "a definition change must bump the version so historical reports stay valid"


def test_public_submission_converted_to_internal_record(scoped, company_id):
    public = httpx.Client(base_url=BASE, timeout=30)
    created = public.post(
        "/api/v1/public/submissions",
        json={"kind": "contact", "name": "زائر", "email": f"{_unique('visitor')}@example.com", "message": "مرحباً", "company_id": company_id},
    )
    assert created.status_code == 201, created.text
    submission_id = created.json()["id"]

    converted = scoped["bd"].post(f"/api/v1/website/submissions/{submission_id}/convert", json={"target": "lead"})
    assert converted.status_code == 200, converted.text
    body = converted.json()
    assert body["status"] == "converted"
    assert body["converted_type"] == "lead"
    assert body["converted_id"]


def test_ai_reports_configuration_status_without_fabricating(clients):
    status = clients["owner"].get("/api/v1/ai/status")
    assert status.status_code == 200
    payload = status.json()
    assert "configured" in payload

    answer = clients["owner"].post("/api/v1/ai/ask", json={"prompt": "ما إجمالي الإيرادات؟"})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    if not body["configured"]:
        # A missing provider key yields a clear configuration status and a
        # deterministic refusal; it never fabricates financial values.
        assert body["confidence"] == "unconfigured"
        assert body["answer"]
    else:
        assert body["confidence"] in {"grounded", "low", "no_data"}
        assert all("amount" not in str(s).lower() or s.get("ref") for s in body["sources"])


def test_audit_log_is_read_only_and_scoped(clients):
    owner = clients["owner"]
    listing = owner.get("/api/v1/audit")
    assert listing.status_code == 200
    assert isinstance(listing.json(), list)
    # There is no write surface on the audit log.
    assert owner.post("/api/v1/audit", json={"action": "x"}).status_code in (404, 405)
