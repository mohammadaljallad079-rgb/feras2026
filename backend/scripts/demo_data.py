"""Populate the platform with reviewable demonstration data through the API.

The visual and functional acceptance passes need screens that show real records
rather than empty states, and those records must be produced the same way a user
would produce them: over HTTP, subject to every permission and validation rule.

This is *not* seed data for the product. It writes rows a human explicitly asked
for, tagged "DEMO", so a reviewer can tell them apart from genuine business
records. `--purge` removes them again.

    python scripts/demo_data.py            # create
    python scripts/demo_data.py --purge    # remove everything this script made

Needs a running API. Point it with SAFIR_BASE_URL (default http://localhost:8000).
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Any

import httpx

BASE = os.environ.get("SAFIR_BASE_URL", "http://localhost:8000")
PASSWORD = "Safir!2026"
TAG = "DEMO"

ACCOUNTS = {
    "owner": "owner@safir-platform.com",
    "manager": "manager@safir-platform.com",
    "accountant": "accountant@safir-platform.com",
    "bd": "bd@safir-platform.com",
    "marketer": "marketer@safir-platform.com",
    "designer": "designer@safir-platform.com",
    "advisor": "advisor@safir-platform.com",
    "specialist": "specialist@safir-platform.com",
}

COMPANIES = [
    {
        "code": "DEMO-ALFA",
        "name_ar": "شركة ألفا للتقنية",
        "name_en": "Alfa Technology",
        "country": "SA",
        "sector": "technology",
        "currency": "SAR",
        "ownership_percent": "85.00",
        "contact_email": "alfa@example.com",
        "contact_phone": "+966500000001",
    },
    {
        "code": "DEMO-BETA",
        "name_ar": "شركة بيتا للمقاولات",
        "name_en": "Beta Contracting",
        "country": "AE",
        "sector": "construction",
        "currency": "AED",
        "ownership_percent": "60.00",
        "contact_email": "beta@example.com",
        "contact_phone": "+971500000002",
    },
]


def _login(email: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=30)
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    if resp.status_code != 200:
        raise SystemExit(f"login failed for {email}: {resp.status_code} {resp.text}")
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return client


def _step(label: str, resp: httpx.Response, *ok: int) -> Any:
    allowed = ok or (200, 201)
    if resp.status_code not in allowed:
        print(f"  !! {label}: {resp.status_code} {resp.text[:160]}")
        return None
    print(f"  ok {label}")
    return resp.json() if resp.content else None


def _find_or_create_company(owner: httpx.Client, spec: dict) -> int:
    existing = owner.get("/api/v1/companies").json()
    for row in existing:
        if row["code"] == spec["code"]:
            return row["id"]
    created = _step("company " + spec["code"], owner.post("/api/v1/companies", json=spec), 201)
    cid = created["id"]
    _step("activate " + spec["code"], owner.post(f"/api/v1/companies/{cid}/activate"))
    return cid


def _period(owner: httpx.Client, month: int = 2, year: int = 2026) -> int:
    labels = {
        2: ("فبراير 2026", "February 2026", "2026-02-01", "2026-02-28"),
        3: ("مارس 2026", "March 2026", "2026-03-01", "2026-03-31"),
        4: ("أبريل 2026", "April 2026", "2026-04-01", "2026-04-30"),
    }
    for row in owner.get("/api/v1/periods").json():
        if row.get("month") == month and row.get("year") == year:
            return row["id"]
    label_ar, label_en, opens, due = labels[month]
    created = _step(
        f"period {year}-{month:02d}",
        owner.post(
            "/api/v1/periods",
            json={"label_ar": label_ar, "label_en": label_en, "year": year, "month": month, "opens_on": opens, "due_on": due},
        ),
        201,
        409,
    )
    if created is None:
        return owner.get("/api/v1/periods").json()[0]["id"]
    return created["id"]


def _scope_user(owner: httpx.Client, role: str, company_ids: list[int]) -> dict | None:
    """Grant the seeded demo account a role scoped to the demo companies."""
    email = ACCOUNTS[role]
    users = owner.get("/api/v1/users").json()
    row = next((u for u in users if u["email"] == email), None)
    if row is None:
        print(f"  !! {email} is not registered; run scripts/seed.py first")
        return None
    updated = _step(
        f"scope {role} -> {company_ids}",
        owner.patch(
            f"/api/v1/users/{row['id']}",
            json={"role_slugs": row["roles"], "company_ids": company_ids},
        ),
    )
    return updated


def _fields(owner: httpx.Client) -> list[dict]:
    return owner.get("/api/v1/form-fields").json()


def _ensure_field(owner: httpx.Client, code: str, payload: dict) -> int | None:
    """Create the field, or reconcile an existing one to the given payload.

    Reconciling matters because a field that is required and unscoped applies to
    every company, including companies other tests create; the demo fields are
    therefore scoped to a company.
    """
    existing = next((f for f in _fields(owner) if f["code"] == code), None)
    if existing is None:
        created = _step("form field " + code, owner.post("/api/v1/form-fields", json=payload), 201)
        return created["id"] if created else None
    patch = {k: v for k, v in payload.items() if k != "code" and existing.get(k) != v}
    if patch:
        _step(f"form field {code} reconciled", owner.patch(f"/api/v1/form-fields/{existing['id']}", json=patch))
    return existing["id"]


def _ensure_report(clients, company_id: int, period_id: int, statement: bytes) -> int | None:
    manager = clients["manager"]
    rows = manager.get("/api/v1/reports").json()
    for r in rows:
        if r["company_id"] == company_id and r["period_id"] == period_id:
            return r["id"]
    created = _step("report", manager.post("/api/v1/reports", json={"company_id": company_id, "period_id": period_id}), 201)
    return created["id"] if created else None


def build() -> int:
    clients = {k: _login(v) for k, v in ACCOUNTS.items()}
    owner = clients["owner"]

    print("companies")
    alfa = _find_or_create_company(owner, COMPANIES[0])
    beta = _find_or_create_company(owner, COMPANIES[1])

    print("role scoping")
    for role in ("manager", "accountant", "bd", "marketer", "designer", "specialist"):
        _scope_user(owner, role, [alfa])

    print("reporting period")
    period = _period(owner)

    print("dynamic report fields")
    parent = _ensure_field(
        owner,
        "DEMO_REVENUE",
        {
            "code": "DEMO_REVENUE",
            "name_ar": "إجمالي الإيرادات",
            "name_en": "Total revenue",
            "field_type": "amount",
            "is_required": True,
            "company_id": alfa,
        },
    )
    if parent:
        _ensure_field(
            owner,
            "DEMO_REVENUE_ONLINE",
            {
                "code": "DEMO_REVENUE_ONLINE",
                "name_ar": "منها إيرادات رقمية",
                "name_en": "Of which digital",
                "field_type": "amount",
                "parent_id": parent,
                "company_id": alfa,
            },
        )

    print("monthly reports")
    report_alfa = _ensure_report(clients, alfa, period, b"%PDF-1.4 demo statement")
    if report_alfa:
        # Re-runs must not fight the workflow: only edit and submit a report
        # that is still a draft or was returned, then walk it to forwarded so
        # the owner's screen (PDF p.8) has a report sent to management to show.
        def _status() -> str | None:
            resp = clients["accountant"].get(f"/api/v1/reports/{report_alfa}")
            return resp.json().get("status") if resp.status_code == 200 else None

        if _status() in ("draft", "returned"):
            upload = clients["manager"].post(
                "/api/v1/files",
                files={"file": ("demo-statement.pdf", b"%PDF-1.4 demo bank statement", "application/pdf")},
                data={"company_id": str(alfa)},
            )
            statement_id = upload.json()["id"] if upload.status_code == 201 else None
            values = []
            for f in _fields(owner):
                if f["code"] == "DEMO_REVENUE":
                    values.append({"field_id": f["id"], "value_number": "1850000.00"})
                elif f["code"] == "DEMO_REVENUE_ONLINE":
                    values.append({"field_id": f["id"], "value_number": "420000.00"})
            _step(
                "report values",
                clients["manager"].put(
                    f"/api/v1/reports/{report_alfa}/values",
                    json={
                        "commentary": "نمو الإيرادات مدفوع بالعقود الجديدة.",
                        "values": values,
                        "bank_statement_file_id": statement_id,
                    },
                ),
            )
            _step("submit", clients["manager"].post(f"/api/v1/reports/{report_alfa}/submit"))

        if _status() == "submitted":
            _step("accountant approve", clients["accountant"].post(f"/api/v1/reports/{report_alfa}/approve"))
        if _status() == "approved":
            _step("accountant forward", clients["accountant"].post(f"/api/v1/reports/{report_alfa}/forward"))

    # A second period with a report left in draft, so the submission screen
    # (PDF p.23) can be captured in the state its author sees it in.
    print("draft report for the submission screen")
    period_march = _period(owner, month=3)
    draft = _ensure_report(clients, alfa, period_march, b"%PDF-1.4 draft")
    if draft:
        draft_state = clients["manager"].get(f"/api/v1/reports/{draft}")
        if draft_state.status_code == 200 and draft_state.json().get("status") == "draft":
            upload = clients["manager"].post(
                "/api/v1/files",
                files={"file": ("demo-statement-march.pdf", b"%PDF-1.4 demo bank statement", "application/pdf")},
                data={"company_id": str(alfa)},
            )
            statement_id = upload.json()["id"] if upload.status_code == 201 else None
            _step(
                "draft values",
                clients["manager"].put(
                    f"/api/v1/reports/{draft}/values",
                    json={
                        "commentary": "مسودة قيد الإعداد للشهر الجاري.",
                        "values": [
                            {"field_id": f["id"], "value_number": "900000.00"}
                            for f in _fields(owner)
                            if f["code"] == "DEMO_REVENUE"
                        ],
                        "bank_statement_file_id": statement_id,
                    },
                ),
            )

    # A third period with a report submitted but not yet reviewed, so the
    # accountant's review screen (PDF p.25) can be captured in the state that
    # role actually works in. Alfa, because the accountant is scoped to it.
    print("submitted report for the review screen")
    period_april = _period(owner, month=4)
    submitted = _ensure_report(clients, alfa, period_april, b"%PDF-1.4 submitted")
    if submitted:
        resp = clients["accountant"].get(f"/api/v1/reports/{submitted}")
        if resp.status_code == 200 and resp.json().get("status") == "draft":
            upload = clients["manager"].post(
                "/api/v1/files",
                files={"file": ("demo-statement-april.pdf", b"%PDF-1.4 demo bank statement", "application/pdf")},
                data={"company_id": str(alfa)},
            )
            statement_id = upload.json()["id"] if upload.status_code == 201 else None
            _step(
                "submitted values",
                clients["manager"].put(
                    f"/api/v1/reports/{submitted}/values",
                    json={
                        "commentary": "التقرير مُرسل للمحاسبة للمراجعة.",
                        "values": [
                            {"field_id": f["id"], "value_number": "1200000.00"}
                            for f in _fields(owner)
                            if f["code"] == "DEMO_REVENUE"
                        ],
                        "bank_statement_file_id": statement_id,
                    },
                ),
            )
            _step("submit for review", clients["manager"].post(f"/api/v1/reports/{submitted}/submit"))

    print("accounting")
    existing = clients["accountant"].get("/api/v1/accounting").json()
    have = {(e["kind"], e["reference"]) for e in existing}
    for kind, ref, desc, amount, cur in [
        ("expense", "DEMO-EXP-1", "إيجار المقر الرئيسي", "45000.00", "SAR"),
        ("invoice", "DEMO-INV-1", "استشارات تقنية", "125000.75", "SAR"),
        ("invoice", "DEMO-INV-2", "توريد معدات", "88000.00", "SAR"),
        ("commission", "DEMO-COM-1", "عمولة وساطة", "15000.00", "SAR"),
        ("expense", "DEMO-EXP-2", "مصاريف تشغيل", "22000.00", "SAR"),
    ]:
        if (kind, ref) in have:
            continue
        _step(
            f"accounting {ref}",
            clients["accountant"].post(
                "/api/v1/accounting",
                json={
                    "kind": kind,
                    "company_id": alfa,
                    "reference": ref,
                    "description": desc,
                    "amount": amount,
                    "currency": cur,
                    "entry_date": "2026-02-10",
                },
            ),
            201,
        )

    print("leads")
    if not any(l["name"].startswith(TAG) for l in clients["marketer"].get("/api/v1/leads").json()):
        for name, src, svc in [
            (f"{TAG} عميل تجزئة", "website", "تسويق رقمي"),
            (f"{TAG} جهة حكومية", "referral", "استشارات"),
        ]:
            _step("lead", clients["marketer"].post("/api/v1/leads", json={"name": name, "company_id": alfa, "requested_service": svc, "source": src}), 201)

    print("opportunities")
    if not any(o["title"].startswith(TAG) for o in clients["bd"].get("/api/v1/opportunities").json()):
        created = _step(
            "opportunity",
            clients["bd"].post(
                "/api/v1/opportunities",
                json={"title": f"{TAG} توسّع إقليمي", "company_id": alfa, "description": "دراسة سوق", "estimated_value": "750000.00", "currency": "SAR"},
            ),
            201,
        )
        if created:
            _step("submit opportunity", clients["bd"].post(f"/api/v1/opportunities/{created['id']}/submit"))

    print("directives")
    if not any(d["title"].startswith(TAG) for d in owner.get("/api/v1/directives").json()):
        manager_id = clients["manager"].get("/api/v1/auth/me").json()["id"]
        created = _step(
            "directive",
            owner.post(
                "/api/v1/directives",
                json={"title": f"{TAG} توجيه تنفيذي", "body": "إعداد خطة الربع الثاني.", "recipient_id": manager_id, "follow_up_on": "2026-03-15"},
            ),
            201,
        )
        if created:
            _step("send directive", owner.post(f"/api/v1/directives/{created['id']}/send"))
            _step("receive directive", clients["manager"].post(f"/api/v1/directives/{created['id']}/receive"))

    print("service requests")
    if not any(r["subject"].startswith(TAG) for r in owner.get("/api/v1/service-requests").json()):
        specialist_id = clients["specialist"].get("/api/v1/auth/me").json()["id"]
        created = _step(
            "service request",
            owner.post(
                "/api/v1/service-requests",
                json={"subject": f"{TAG} طلب صيانة", "body": "صيانة دورية للمقر.", "company_id": alfa, "recipient_id": specialist_id, "priority": "high", "deadline": "2026-03-01"},
            ),
            201,
        )
        if created:
            _step("reply", clients["specialist"].post(f"/api/v1/service-requests/{created['id']}/replies", json={"body": "تم استلام الطلب.", "new_status": "in_progress"}), 201)

    print("employees")
    if not any(e["name_en"].startswith(TAG) for e in owner.get("/api/v1/employees").json()):
        created = _step(
            "employee",
            owner.post(
                "/api/v1/employees",
                json={
                    "name_ar": "سارة الحربي",
                    "name_en": f"{TAG} Sarah Alharbi",
                    "job_title": "مديرة العمليات",
                    "company_id": alfa,
                    "contact_email": "sarah@example.com",
                    "salary": "28000.00",
                    "currency": "SAR",
                    "contract_type": "full_time",
                    "hired_on": "2024-05-01",
                },
            ),
            201,
        )
        if created:
            _step("employee event", owner.post(f"/api/v1/employees/{created['id']}/events", json={"kind": "leave", "detail": "إجازة سنوية", "effective_on": "2026-03-01"}), 201)

    print("advisor messages")
    if not any(m["subject"].startswith(TAG) for m in clients["advisor"].get("/api/v1/advisor/messages").json()):
        owner_id = owner.get("/api/v1/auth/me").json()["id"]
        _step(
            "advisor message",
            clients["advisor"].post(
                "/api/v1/advisor/messages",
                json={"recipient_id": owner_id, "category": "recommendation", "subject": f"{TAG} توصية استثمارية", "body": "يُقترح تنويع المحفظة نحو القطاع الرقمي."},
            ),
            201,
        )

    print("website submissions")
    public = httpx.Client(base_url=BASE, timeout=30)
    inbox = clients["bd"].get("/api/v1/website/submissions")
    existing_submissions = inbox.json() if inbox.status_code == 200 else []
    if not any(str(s.get("name", "")).startswith(TAG) for s in existing_submissions):
        _step(
            "public submission",
            public.post(
                "/api/v1/public/submissions",
                json={"kind": "contact", "name": f"{TAG} زائر", "email": f"visitor-{uuid.uuid4().hex[:6]}@example.com", "message": "أرغب بالتواصل.", "company_id": alfa},
            ),
            201,
        )

    print("\nDemo data is in place. Records are tagged DEMO.")
    return 0


def purge() -> int:
    """Remove only the rows this script created, by their DEMO markers."""
    from sqlalchemy import delete, or_, select  # local import: script must run standalone

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from app.core.db import SessionLocal
    from app.models.business import Company, Employee, Lead, Opportunity
    from app.models.operations import ServiceRequest

    db = SessionLocal()
    try:
        removed = 0
        for model, column, pattern in [
            (Lead, Lead.name, f"{TAG}%"),
            (Opportunity, Opportunity.title, f"{TAG}%"),
            (ServiceRequest, ServiceRequest.subject, f"{TAG}%"),
            (Employee, Employee.name_en, f"{TAG}%"),
            (Company, Company.code, f"{TAG}-%"),
        ]:
            rows = db.execute(select(model).where(column.like(pattern))).scalars().all()
            for row in rows:
                db.delete(row)
                removed += 1
        db.commit()
        print(f"Removed {removed} demo rows.")
    finally:
        db.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purge", action="store_true", help="delete the DEMO-tagged rows instead of creating them")
    args = parser.parse_args()
    return purge() if args.purge else build()


if __name__ == "__main__":
    sys.exit(main())
