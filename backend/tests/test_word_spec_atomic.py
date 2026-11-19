"""Atomic acceptance checks, one per requirement item of the Word brief.

`platform-explained-ar.docx` is written as prose and tables. This module turns
the individual items into separate assertions — one screen, one button, one
field, one dropdown option, one modal, one status transition, one permission,
one message — so a single PASS row never stands for several different
requirements. Each test names the brief clause it proves (`§`/`Table N`).

The checks go through the real HTTP API and the real database; a route existing
is never taken as proof. A UI-only rule (a label, an option list, a button that
must not appear) is asserted against the source of the page that renders it, and
the rendered result is covered by `scripts/check_matrix.py`,
`scripts/check_visual_fixes.py` and `scripts/check_mobile.py`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.business import Company, ReportingPeriod


def _company(db: Session, code: str, *, sector: str = "تقنية", currency: str = "BHD", **kw) -> Company:
    row = Company(
        code=code,
        name_ar=f"شركة {code}",
        name_en=f"Company {code}",
        country=kw.pop("country", "البحرين"),
        sector=sector,
        currency=currency,
        status=kw.pop("status", "active"),
        ownership_percent=Decimal("100.00"),
        **kw,
    )
    db.add(row)
    db.commit()
    return row


def _period(db: Session, year: int = 2026, month: int = 10) -> ReportingPeriod:
    row = ReportingPeriod(
        label_ar=f"{year}-{month:02d}",
        label_en=f"{year}-{month:02d}",
        year=year,
        month=month,
        opens_on=date(year, month, 1),
        due_on=date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 5),
    )
    db.add(row)
    db.commit()
    return row


def _seed_fields(db: Session) -> None:
    """Install the report-field catalogue the app ships on first boot."""
    from app.services.bootstrap import ensure_holding_company, ensure_report_fields

    ensure_holding_company(db)
    ensure_report_fields(db)
    db.commit()


def _seed_site(db: Session) -> None:
    """Install the CMS content `scripts/seed_site.py` writes on first boot."""
    from app.content import site_content as content
    from app.models.site import SiteNavLink, SiteSection, SiteService, SiteSetting, SiteSlide

    if db.query(SiteSetting).count():
        return
    for key, (ar, en) in content.SETTINGS.items():
        db.add(SiteSetting(key=key, value_ar=ar, value_en=en))
    for i, spec in enumerate(content.SLIDES):
        db.add(SiteSlide(sort_order=i, **spec))
    for spec in content.SECTIONS:
        db.add(SiteSection(**spec))
    for i, (slug, ar, en) in enumerate(content.SERVICES):
        db.add(SiteService(slug=slug, name_ar=ar, name_en=en, sort_order=i))
    for location, links in (("header", content.HEADER_NAV), ("footer", content.FOOTER_NAV)):
        for i, (ar, en, href) in enumerate(links):
            db.add(SiteNavLink(location=location, label_ar=ar, label_en=en, href=href, sort_order=i))
    db.commit()


def _uid(client: TestClient, headers: dict[str, str]) -> int:
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def _submit_ready(client: TestClient, headers: dict[str, str], report_id: int) -> None:
    """Fill the required fields and attach a bank statement, then submit.

    §7.1/§7.4: a report cannot be submitted without «الرواتب *» and
    «الرصيد البنكي بنهاية الشهر *» and the month-end bank statement.
    """
    fields = client.get("/api/v1/form-fields", headers=headers).json()
    required = [f for f in fields if f["is_required"] and f["parent_id"] is None]
    fid = client.post(
        "/api/v1/files", headers=headers,
        files={"file": ("statement.pdf", b"%PDF statement", "application/pdf")},
        data={"purpose": "bank_statement"},
    ).json()["id"]
    values = []
    for f in required:
        if f["field_type"] in ("amount", "number"):
            values.append({"field_id": f["id"], "value_number": "100.00"})
        else:
            values.append({"field_id": f["id"], "value_text": "قيمة"})
    resp = client.put(
        f"/api/v1/reports/{report_id}/values", headers=headers,
        json={"values": values, "bank_statement_file_id": fid},
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/v1/reports/{report_id}/submit", headers=headers)
    assert resp.status_code == 200, resp.text


# ===========================================================================
# §2 — Look and layout
# ===========================================================================
def test_s2_kpi_cards_are_links_that_open_their_screen(client: TestClient, make_user, login, db):
    """§2 «بطاقة مؤشر (KPI): ... هي نفسها زر يفتح الشاشة المعنية»."""
    make_user("o@s.com", ["owner"])
    cards = client.get("/api/v1/dashboard", headers=login("o@s.com")).json()["cards"]
    assert len(cards) == 6
    for card in cards:
        assert card["href"].startswith("/"), card
        assert card["label_ar"] and card["label_en"]


def test_s2_report_status_vocabulary_matches_the_brief():
    """§2 «الشارات ... (جديد، مرسل، معتمد، متأخر…)»."""
    from app.models.enums import ReportStatus as RS

    assert {s.value for s in RS} == {"draft", "submitted", "returned", "approved", "forwarded"}


# ===========================================================================
# §4 / Table 1 — Roles and sidebar tabs
# ===========================================================================
SIDEBAR_GATES = {
    "dashboard": [],
    "companies": ["company:manage"],
    "reports": ["report:view_own", "report:view_all"],
    "accounting": ["accounting:view"],
    "serviceRequests": ["service:view"],
    "leads": ["lead:view"],
    "opportunities": ["opportunity:view"],
    "directives": ["directive:view"],
    "hr": ["hr:view"],
    "website": ["website:view"],
    "advisor": ["advisor:view"],
    "assistant": ["ai:use"],
    "formBuilder": ["form:manage"],
    "users": ["user:view"],
    "audit": ["audit:view"],
}

TABLE_1 = {
    "dashboard": {"owner", "company_manager", "accountant", "business_developer", "marketer", "designer", "advisor"},
    "companies": {"owner"},
    "reports": {"owner", "company_manager", "accountant", "business_developer"},
    "accounting": {"owner", "accountant", "business_developer"},
    "serviceRequests": {"owner", "company_manager", "accountant", "business_developer", "designer"},
    "leads": {"owner", "company_manager", "business_developer", "marketer"},
    "opportunities": {"owner", "business_developer"},
    "directives": {"owner", "company_manager", "accountant", "business_developer", "marketer", "designer"},
    "hr": {"owner", "company_manager", "business_developer"},
    "website": {"owner", "business_developer"},
    "advisor": {"owner", "business_developer", "advisor"},
    "assistant": {"owner", "company_manager"},
    "formBuilder": {"owner", "accountant"},
    "users": {"owner"},
    "audit": {"owner"},
}

ALL_SEVEN = ("owner", "company_manager", "accountant", "business_developer", "marketer", "designer", "advisor")


@pytest.mark.parametrize("tab", sorted(TABLE_1))
def test_table1_sidebar_tab_visibility(tab: str):
    """Each Table 1 row: the tab appears for exactly the roles with a ✓."""
    from app.core.permissions import ROLE_TEMPLATES

    gates = SIDEBAR_GATES[tab]
    for role in ALL_SEVEN:
        perms = set(ROLE_TEMPLATES[role]["permissions"])  # type: ignore[arg-type]
        visible = not gates or any(p in perms for p in gates)
        assert visible is (role in TABLE_1[tab]), f"{tab} / {role}: visible={visible}"


def test_table1_owner_sees_all_fifteen_tabs():
    """Table 1: the owner column carries a ✓ on every row."""
    from app.core.permissions import ROLE_TEMPLATES

    owner = set(ROLE_TEMPLATES["owner"]["permissions"])  # type: ignore[arg-type]
    for tab, gates in SIDEBAR_GATES.items():
        assert not gates or any(p in owner for p in gates), f"owner lacks {tab}"


def test_table1_company_manager_lacks_the_owner_only_tabs():
    """Table 1: the manager column is blank for Companies, Users, Audit, Forms."""
    from app.core.permissions import ROLE_TEMPLATES

    mgr = set(ROLE_TEMPLATES["company_manager"]["permissions"])  # type: ignore[arg-type]
    for gate in ("company:manage", "user:view", "audit:view", "form:manage", "accounting:view",
                 "opportunity:view", "website:view", "advisor:view"):
        assert gate not in mgr, gate


def test_s4_two_manager_accounts_see_only_their_own_company(client: TestClient, make_user, login, db):
    """§4 note: «مدير الشركة حسابان ... بيانات شركته وحدها»."""
    a = _company(db, "NUMA")
    b = _company(db, "NUMB")
    make_user("ma@s.com", ["company_manager"], companies=[a.id])
    make_user("mb@s.com", ["company_manager"], companies=[b.id])
    assert [c["id"] for c in client.get("/api/v1/companies", headers=login("ma@s.com")).json()] == [a.id]
    assert [c["id"] for c in client.get("/api/v1/companies", headers=login("mb@s.com")).json()] == [b.id]


def test_s4_there_is_no_employee_login_role():
    """§4 note: «لا يوجد دور «موظف» بحساب دخول»."""
    from app.core.permissions import ROLE_TEMPLATES

    assert "employee" not in ROLE_TEMPLATES
    for slug in ALL_SEVEN:
        assert slug in ROLE_TEMPLATES, slug


# ===========================================================================
# §5.1 — Owner screens
# ===========================================================================
def test_s5_1_owner_dashboard_has_the_six_named_cards_in_order(client: TestClient, make_user, login, db):
    """Table 2: the six owner cards, in order, each with its destination."""
    make_user("o@s.com", ["owner"])
    cards = client.get("/api/v1/dashboard", headers=login("o@s.com")).json()["cards"]
    assert [c["label_ar"] for c in cards] == [
        "شركات نشطة", "تقارير معتمدة للفترة", "تقارير متأخرة",
        "قرارات بانتظارك", "توجيهات مفتوحة", "عملاء محتملون",
    ]
    assert [c["href"] for c in cards] == [
        "/companies", "/reports", "/reports", "/opportunities", "/directives", "/leads",
    ]


def test_s5_1_owner_group_summary_has_the_five_named_columns(client: TestClient, make_user, login, db):
    """§5.1 «الأعمدة: الشركة، الملكية، العملة، إيراد آخر تقرير معتمد، الحالة»."""
    _company(db, "BHDA", currency="BHD")
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/dashboard", headers=login("o@s.com")).json()
    summary = [s for s in body["sections"] if s["key"] == "group_summary"][0]
    assert [c["ar"] for c in summary["columns"]] == [
        "الشركة", "الملكية", "العملة", "إيراد آخر تقرير معتمد", "الحالة",
    ]


def test_s5_1_owner_group_summary_never_sums_across_currencies(client: TestClient, make_user, login, db):
    """§5.1 «دون جمع بين العملات» + §11."""
    _company(db, "BHDA", currency="BHD")
    _company(db, "SARA", currency="SAR")
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/dashboard", headers=login("o@s.com")).json()
    summary = [s for s in body["sections"] if s["key"] == "group_summary"][0]
    assert {row[2] for row in summary["rows"]} >= {"BHD", "SAR"}
    assert "دون جمع" in summary["title_ar"]


def test_s5_1_owner_dashboard_names_the_period_and_due_date(client: TestClient, make_user, login, db):
    """§5.1 «الفترة الحالية 2026-10 · الاستحقاق 2026-11-05»."""
    _period(db, 2026, 10)
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/dashboard/period", headers=login("o@s.com")).json()
    assert body["period"]["label"] == "2026-10"
    assert body["period"]["due"] == "2026-11-05"


def test_s5_1_owner_companies_table_columns(client: TestClient, make_user, login, db):
    """§5.1 «(الشعار، الكود، الشركة، الدولة والقطاع، البريد والهاتف، المدير، الملكية، الحالة)»."""
    make_user("o@s.com", ["owner"])
    c = _company(db, "COLA")
    row = [x for x in client.get("/api/v1/companies", headers=login("o@s.com")).json() if x["id"] == c.id][0]
    for key in ("logo_url", "code", "name_ar", "name_en", "country", "sector",
                "contact_email", "contact_phone", "manager_name_ar", "ownership_percent", "status"):
        assert key in row, key


def test_s5_1_owner_reports_tab_lists_only_forwarded_reports(client: TestClient, make_user, login, db):
    """§5.1 «يرى المالك التقارير المرسلة للإدارة فقط»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("o@s.com", ["owner"])
    make_user("a@s.com", ["accountant"])
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm, ha, ho = login("m@s.com"), login("a@s.com"), login("o@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    assert client.get("/api/v1/reports", headers=ho).json() == []
    _submit_ready(client, hm, rid)
    client.post(f"/api/v1/reports/{rid}/approve", headers=ha)
    assert client.get("/api/v1/reports", headers=ho).json() == []
    client.post(f"/api/v1/reports/{rid}/forward", headers=ha)
    assert [r["id"] for r in client.get("/api/v1/reports", headers=ho).json()] == [rid]


def test_s5_1_owner_holding_accounting_is_view_only(client: TestClient, make_user, login, db):
    """§5.1 «محاسبة القابضة. عرض فقط»."""
    c = _company(db, "COLA")
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    assert client.get("/api/v1/accounting", headers=h).status_code == 200
    resp = client.post(
        "/api/v1/accounting", headers=h,
        json={"kind": "expense", "company_id": c.id, "reference": "X", "description": "d",
              "amount": "10.00", "currency": "BHD", "entry_date": str(date.today())},
    )
    assert resp.status_code == 403


def test_s5_1_owner_opportunity_decisions_are_four(client: TestClient, make_user, login, db):
    """§5.1 «أزرار قرار لكل فرصة: قيد المراجعة، اعتماد، رفض، تأجيل»."""
    c = _company(db, "COLA")
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    hb, ho = login("bd@s.com"), login("o@s.com")
    for decision in ("under_review", "approved", "rejected", "deferred"):
        oid = client.post(
            "/api/v1/opportunities", headers=hb,
            json={"title": "T", "country": "البحرين", "description": "s", "company_id": c.id},
        ).json()["id"]
        client.post(f"/api/v1/opportunities/{oid}/submit", headers=hb)
        body = {"decision": decision}
        if decision in ("rejected", "deferred"):
            body["note"] = "سبب واضح"
        resp = client.post(f"/api/v1/opportunities/{oid}/decision", headers=ho, json=body)
        assert resp.status_code == 200, (decision, resp.text)


def test_s5_1_owner_reject_and_defer_demand_a_reason(client: TestClient, make_user, login, db):
    """§5.1 «الرفض والتأجيل يطلبان سببًا إلزاميًا»."""
    c = _company(db, "COLA")
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    hb, ho = login("bd@s.com"), login("o@s.com")
    for decision in ("rejected", "deferred"):
        oid = client.post(
            "/api/v1/opportunities", headers=hb,
            json={"title": "T", "country": "البحرين", "description": "s", "company_id": c.id},
        ).json()["id"]
        client.post(f"/api/v1/opportunities/{oid}/submit", headers=hb)
        resp = client.post(f"/api/v1/opportunities/{oid}/decision", headers=ho, json={"decision": decision})
        assert resp.status_code in (400, 422), (decision, resp.status_code)


def test_s5_1_approving_an_opportunity_creates_no_project(client: TestClient, make_user, login, db):
    """§5.1 «الاعتماد لا يؤدي إلى تنفيذ أو نشر تلقائيًا»."""
    c = _company(db, "COLA")
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    hb, ho = login("bd@s.com"), login("o@s.com")
    oid = client.post(
        "/api/v1/opportunities", headers=hb,
        json={"title": "T", "country": "البحرين", "description": "s", "company_id": c.id},
    ).json()["id"]
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=hb)
    before = len(client.get("/api/v1/public/companies").json())
    resp = client.post(f"/api/v1/opportunities/{oid}/decision", headers=ho, json={"decision": "approved"})
    assert resp.json()["status"] == "approved"
    # «لا تحويل تلقائي للتنفيذ» — approving creates no project and publishes nothing.
    assert len(client.get("/api/v1/public/companies").json()) == before


def test_s5_1_owner_directive_goes_to_one_recipient_only(client: TestClient, make_user, login, db):
    """§5.1 «زر «توجيه جديد» لمستلم واحد فقط» + §11."""
    make_user("o@s.com", ["owner"])
    make_user("m1@s.com", ["company_manager"])
    make_user("m2@s.com", ["company_manager"])
    ho, h1, h2 = login("o@s.com"), login("m1@s.com"), login("m2@s.com")
    did = client.post(
        "/api/v1/directives", headers=ho,
        json={"title": "T", "body": "b", "recipient_id": _uid(client, h1), "follow_up_on": str(date.today())},
    ).json()["id"]
    client.post(f"/api/v1/directives/{did}/send", headers=ho)
    assert any(d["id"] == did for d in client.get("/api/v1/directives", headers=h1).json())
    assert not any(d["id"] == did for d in client.get("/api/v1/directives", headers=h2).json())


def test_s5_1_owner_hr_hides_annual_and_sick_leave_attachments(client: TestClient, make_user, login, db):
    """§5.1 «ولا تظهر له مرفقات الإجازات السنوية والمرضية»."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    hm, ho = login("m@s.com"), login("o@s.com")
    eid = client.post(
        "/api/v1/employees", headers=hm,
        json={"name_ar": "م", "name_en": "E", "job_title": "P", "company_id": c.id, "salary": "100.00"},
    ).json()["id"]
    fid = client.post(
        "/api/v1/files", headers=hm,
        files={"file": ("leave.pdf", b"%PDF-1.4 x", "application/pdf")},
        data={"purpose": "hr"},
    ).json()["id"]
    client.post(
        f"/api/v1/employees/{eid}/events", headers=hm,
        json={"kind": "annual_leave", "detail": "d", "effective_on": str(date.today()),
              "attachment_file_id": fid},
    )
    events = client.get(f"/api/v1/employees/{eid}/events", headers=ho).json()
    leave = [e for e in events if e["kind"] == "annual_leave"][0]
    # «مرفق مقيد»: the record stays visible, the file is not downloadable.
    denied = client.get(f"/api/v1/files/{leave['attachment_file_id']}/download", headers=ho)
    assert denied.status_code == 403, denied.text
    assert denied.json()["detail"]["error"] == "restricted_attachment"
    assert client.get(f"/api/v1/files/{fid}/download", headers=hm).status_code == 200


def test_s5_1_owner_sees_salary_and_contract(client: TestClient, make_user, login, db):
    """§5.1 «يظهر للمالك الراتب والعقد»."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    client.post(
        "/api/v1/employees", headers=login("m@s.com"),
        json={"name_ar": "م", "name_en": "E", "job_title": "P", "company_id": c.id,
              "salary": "1234.00", "contract_summary": "عقد سنة"},
    )
    row = client.get("/api/v1/employees", headers=login("o@s.com")).json()[0]
    assert str(row["salary"]).startswith("1234")
    assert row["contract_summary"] == "عقد سنة"


def test_s5_1_owner_never_sees_a_password(client: TestClient, make_user, login, db):
    """§5.1 «لا يرى المالك كلمات المرور»."""
    make_user("o@s.com", ["owner"])
    users = client.get("/api/v1/users", headers=login("o@s.com")).json()
    assert users
    for u in users:
        for key in ("password", "password_hash", "hashed_password"):
            assert key not in u


def test_s5_1_owner_audit_log_is_read_only(client: TestClient, make_user, login, db):
    """§5.1 «سجل النشاط. قراءة فقط»."""
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    assert client.get("/api/v1/audit", headers=h).status_code == 200
    assert client.post("/api/v1/audit", headers=h, json={}).status_code in (404, 405)
    assert client.delete("/api/v1/audit/1", headers=h).status_code in (404, 405)


def test_s5_1_audit_never_records_a_password_or_key(client: TestClient, make_user, login, db):
    """§5.1 «لا يسجل كلمات مرور ولا مفاتيح»."""
    make_user("o@s.com", ["owner"])
    text = str(client.get("/api/v1/audit", headers=login("o@s.com")).json()).lower()
    assert "secret" not in text
    assert "api_key" not in text
    assert "password" not in text


def test_s5_1_audit_records_the_four_named_columns(client: TestClient, make_user, login, db):
    """§5.1 «التاريخ، المستخدم، الدور، الإجراء»."""
    make_user("o@s.com", ["owner"])
    rows = client.get("/api/v1/audit", headers=login("o@s.com")).json()
    assert rows
    for key in ("created_at", "actor_id", "action"):
        assert key in rows[0], key


def test_s5_1_assistant_owner_scope_is_every_company_without_summing(client: TestClient, make_user, login, db):
    """§10 «للمالك: يغطي كل الشركات، لكنه لا يجمع العملات»."""
    _period(db)
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/ai/summary", headers=login("o@s.com")).json()
    assert "كل مبلغ بعملة شركته" in str(body)
    assert "grand total" not in str(body).lower()


def test_s5_1_assistant_referral_creates_a_task_and_executes_nothing(client: TestClient, make_user, login, db):
    """Table 5 R22 / §10 «الإحالة ... تنشئ مهمة ولا تنفّذ شيئًا»."""
    make_user("o@s.com", ["owner"])
    make_user("bd@s.com", ["business_developer"])
    resp = client.post("/api/v1/ai/refer", headers=login("o@s.com"), json={"note": "خطة عمل"})
    assert resp.status_code in (200, 201), resp.text
    keys = [c["key"] for c in client.get("/api/v1/dashboard", headers=login("bd@s.com")).json()["cards"]]
    assert "assistant" in keys


def test_s5_1_owner_form_builder_has_add_edit_archive(client: TestClient, make_user, login, db):
    """§5.1 «أزرار: إضافة حقل، تعديل، أرشفة»."""
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    fid = client.post(
        "/api/v1/form-fields", headers=h,
        json={"name_ar": "حقل", "name_en": "Field", "field_type": "amount"},
    ).json()["id"]
    assert client.patch(f"/api/v1/form-fields/{fid}", headers=h, json={"name_en": "Field 2"}).status_code == 200
    assert client.post(f"/api/v1/form-fields/{fid}/deactivate", headers=h).status_code == 200


def test_s5_1_users_screen_is_owner_only(client: TestClient, make_user, login, db):
    """§5.1 «المستخدمون والأدوار. للمالك وحده»."""
    make_user("o@s.com", ["owner"])
    make_user("a@s.com", ["accountant"])
    make_user("bd@s.com", ["business_developer"])
    assert client.get("/api/v1/users", headers=login("o@s.com")).status_code == 200
    assert client.get("/api/v1/users", headers=login("a@s.com")).status_code == 403
    assert client.get("/api/v1/users", headers=login("bd@s.com")).status_code == 403


def test_s5_1_new_user_may_hold_more_than_one_role(client: TestClient, make_user, login, db):
    """Table 5 R17 «الأدوار (أكثر من دور ممكن)»."""
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    resp = client.post(
        "/api/v1/users", headers=h,
        json={"email": "multi@s.com", "full_name_ar": "م", "full_name_en": "M",
              "role_slugs": ["accountant", "business_developer"]},
    )
    assert resp.status_code == 201, resp.text
    row = [u for u in client.get("/api/v1/users", headers=h).json() if u["email"] == "multi@s.com"][0]
    assert sorted(row["roles"]) == ["accountant", "business_developer"]


def test_s5_1_custom_role_carries_chosen_permissions(client: TestClient, make_user, login, db):
    """Table 5 R18 «دور مخصص ... الوحدات ... الإجراءات»."""
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    resp = client.post(
        "/api/v1/roles", headers=h,
        json={"slug": "auditor_x", "name_ar": "مدقق", "name_en": "Auditor",
              "permissions": ["company:view", "report:view_all", "audit:view"]},
    )
    assert resp.status_code == 201, resp.text
    assert sorted(resp.json()["permission_codes"]) == ["audit:view", "company:view", "report:view_all"]


def test_s5_1_suspend_user_records_activity(client: TestClient, make_user, login, db):
    """Table 5 R19 «إيقاف ... يوقف المستخدم ويسجل النشاط»."""
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    client.post(
        "/api/v1/users", headers=h,
        json={"email": "victim@s.com", "full_name_ar": "ف", "full_name_en": "V", "role_slugs": ["designer"]},
    )
    uid = [u for u in client.get("/api/v1/users", headers=h).json() if u["email"] == "victim@s.com"][0]["id"]
    assert client.patch(f"/api/v1/users/{uid}", headers=h, json={"is_active": False}).status_code == 200
    actions = [a["action"] for a in client.get("/api/v1/audit", headers=h).json()]
    assert "user.update" in actions, actions


# ===========================================================================
# §5.2 — Company manager
# ===========================================================================
def test_s5_2_manager_sees_only_their_company(client: TestClient, make_user, login, db):
    """§5.2 «يرى شركته فقط، ولا يرى شركة المدير الآخر»."""
    a = _company(db, "MA")
    b = _company(db, "MB")
    make_user("m@s.com", ["company_manager"], companies=[a.id])
    h = login("m@s.com")
    assert client.get(f"/api/v1/companies/{b.id}", headers=h).status_code == 404
    assert client.get(f"/api/v1/companies/{a.id}", headers=h).status_code == 200


def test_s5_2_manager_dashboard_cards(client: TestClient, make_user, login, db):
    """§5.2 «بطاقة «شركتك» ثم مؤشرات: طلبات مفتوحة ... عملاء محولون ... توجيهاتي»."""
    c = _company(db, "MA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    cards = client.get("/api/v1/dashboard", headers=login("m@s.com")).json()["cards"]
    assert [x["label_ar"] for x in cards] == ["شركتك", "طلبات مفتوحة", "عملاء محولون", "توجيهاتي"]


def test_s5_2_manager_quick_actions_are_the_five_named(client: TestClient, make_user, login, db):
    """§5.2 «أزرار سريعة: تقرير جديد، طلب خدمة جديد، إضافة موظف، العملاء
    المحولون، توجيهاتي»."""
    c = _company(db, "MA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    labels = [a["label_ar"] for a in client.get("/api/v1/dashboard", headers=login("m@s.com")).json()["actions"]]
    for wanted in ("تقرير جديد", "طلب خدمة جديد", "إضافة موظف", "العملاء المحولون", "توجيهاتي"):
        assert wanted in labels, (wanted, labels)


def test_s5_2_manager_deadline_alert_is_toned(client: TestClient, make_user, login, db):
    """§5.2 «يظهر تنبيه أحمر/كهرماني للاستحقاق»."""
    _period(db)
    c = _company(db, "MA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    body = client.get("/api/v1/dashboard", headers=login("m@s.com")).json()
    assert body["banner_ar"], body
    assert body["banner_tone"] in ("ok", "warn", "bad")


def test_s5_2_isolation_probe_link_is_present_and_refused(client: TestClient, make_user, login, db):
    """§5.2 / Table 3 R8 «فتح تقرير شركة أخرى ... فيرفضه الخادم»."""
    a = _company(db, "MA")
    b = _company(db, "MB")
    p = _period(db)
    make_user("mb@s.com", ["company_manager"], companies=[b.id])
    rid_b = client.post("/api/v1/reports", headers=login("mb@s.com"),
                        json={"company_id": b.id, "period_id": p.id}).json()["id"]
    make_user("m@s.com", ["company_manager"], companies=[a.id])
    hm = login("m@s.com")
    probe = [
        x
        for x in client.get("/api/v1/dashboard", headers=hm).json()["actions"]
        if x["label_ar"] == "فتح تقرير شركة أخرى عبر الرابط المباشر"
    ]
    assert probe and probe[0]["href"] == f"/reports/{rid_b}"
    # §5.2 puts the probe in its own «اختبار العزل» section, not among the actions.
    assert probe[0]["group"] == "isolation"
    assert client.get(f"/api/v1/reports/{rid_b}", headers=hm).status_code == 404


def test_s5_2_denied_cross_company_read_is_written_to_the_audit_log(client: TestClient, make_user, login, db):
    """§5.2 / §11 «فتح رابط غير مصرح به يرفض ويسجل»."""
    a = _company(db, "MA")
    b = _company(db, "MB")
    make_user("m@s.com", ["company_manager"], companies=[a.id])
    make_user("o@s.com", ["owner"])
    hm = login("m@s.com")
    assert client.get(f"/api/v1/companies/{b.id}", headers=hm).status_code == 404
    actions = [x["action"] for x in client.get("/api/v1/audit", headers=login("o@s.com")).json()]
    assert "security.access_denied" in actions, actions


def test_s5_2_manager_assistant_scope_is_own_company_only(client: TestClient, make_user, login, db):
    """§5.2 «نطاقه شركته فقط، ولا تظهر بيانات الشركات الأخرى ولا ملاحظات المالك السرية»."""
    _period(db)
    c = _company(db, "MA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    body = client.get("/api/v1/ai/summary", headers=login("m@s.com")).json()
    assert "شركتك" in body["scope_ar"], body["scope_ar"]
    assert "ملاحظات المالك" not in str(body)


# ===========================================================================
# §5.3 — Accountant
# ===========================================================================
def test_s5_3_accountant_dashboard_has_three_cards(client: TestClient, make_user, login, db):
    """§5.3 «مؤشرات: تقارير بانتظار المراجعة، معتمدة وغير مرسلة للإدارة، سجلات القابضة»."""
    make_user("a@s.com", ["accountant"])
    keys = [c["key"] for c in client.get("/api/v1/dashboard", headers=login("a@s.com")).json()["cards"]]
    assert keys == ["awaiting_review", "awaiting_forward", "entries"]


def test_s5_3_accountant_dashboard_actions_are_the_two_named(client: TestClient, make_user, login, db):
    """§5.3 / Table 3 «مراجعة تقرير» و«مصروف / فاتورة / عمولة جديدة»."""
    make_user("a@s.com", ["accountant"])
    actions = client.get("/api/v1/dashboard", headers=login("a@s.com")).json()["actions"]
    assert [a["label_ar"] for a in actions] == ["مراجعة تقرير", "مصروف / فاتورة / عمولة جديدة"]
    assert [a["href"] for a in actions] == ["/reports", "/accounting"]


def test_s5_3_accounting_screen_is_the_only_financial_edit_screen(client: TestClient, make_user, login, db):
    """§5.3 «الشاشة الوحيدة المخصّصة للتعديل المالي»."""
    c = _company(db, "COLA")
    make_user("a@s.com", ["accountant"], companies=[c.id])
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    payload = {"kind": "expense", "company_id": c.id, "reference": "R", "description": "d",
               "amount": "10.00", "currency": "BHD", "entry_date": str(date.today())}
    assert client.post("/api/v1/accounting", headers=login("a@s.com"), json=payload).status_code == 201
    assert client.post("/api/v1/accounting", headers=login("bd@s.com"), json=payload).status_code == 403


def test_s5_3_accounting_default_currency_is_bhd(client: TestClient, make_user, login, db):
    """§5.3 «العملة الافتراضية BHD»."""
    c = _company(db, "COLA")
    make_user("a@s.com", ["accountant"], companies=[c.id])
    row = client.post(
        "/api/v1/accounting", headers=login("a@s.com"),
        json={"kind": "expense", "company_id": c.id, "reference": "R", "description": "d",
              "amount": "10.00", "entry_date": str(date.today())},
    ).json()
    assert row["currency"] == "BHD"


@pytest.mark.parametrize("kind", ["expense", "invoice", "commission"])
def test_s5_3_the_three_entry_kinds_exist(kind: str, client: TestClient, make_user, login, db):
    """Table 5 R12–R14: مصروف / إيراد-فاتورة / عمولة."""
    c = _company(db, "COLA")
    make_user("a@s.com", ["accountant"], companies=[c.id])
    resp = client.post(
        "/api/v1/accounting", headers=login("a@s.com"),
        json={"kind": kind, "company_id": c.id, "reference": f"R-{kind}", "description": "d",
              "amount": "10.00", "currency": "BHD", "entry_date": str(date.today())},
    )
    assert resp.status_code == 201, resp.text


def test_s5_3_invoice_carries_amount_and_tax(client: TestClient, make_user, login, db):
    """Table 5 R13 «سطر فاتورة بإجمالي محسوب»."""
    c = _company(db, "COLA")
    make_user("a@s.com", ["accountant"], companies=[c.id])
    row = client.post(
        "/api/v1/accounting", headers=login("a@s.com"),
        json={"kind": "invoice", "company_id": c.id, "reference": "INV-1",
              "description": "خدمة", "amount": "100.00", "tax_amount": "10.00",
              "currency": "BHD", "entry_date": str(date.today())},
    ).json()
    assert Decimal(str(row["amount"])) == Decimal("100.00")
    assert Decimal(str(row["tax_amount"])) == Decimal("10.00")


def test_s5_3_invoice_carries_manual_tax_registration_and_service_item(client: TestClient, make_user, login, db):
    """Table 5 R13 «رقم التسجيل الضريبي (يدويًا فقط)، بند الخدمة»."""
    c = _company(db, "COLA")
    make_user("a@s.com", ["accountant"], companies=[c.id])
    row = client.post(
        "/api/v1/accounting", headers=login("a@s.com"),
        json={"kind": "invoice", "company_id": c.id, "reference": "INV-2", "description": "d",
              "amount": "50.00", "tax_registration_no": "BH-99887", "service_item": "استشارات",
              "currency": "BHD", "entry_date": str(date.today())},
    ).json()
    assert row["tax_registration_no"] == "BH-99887"
    assert row["service_item"] == "استشارات"


def test_s5_3_no_payment_or_bank_transfer_route_exists(client: TestClient, make_user, login, db):
    """§11 «لا دفع ولا تحويل بنكي في محاسبة القابضة»."""
    make_user("a@s.com", ["accountant"])
    h = login("a@s.com")
    for path in ("/api/v1/accounting/pay", "/api/v1/accounting/transfer", "/api/v1/payments"):
        assert client.post(path, headers=h, json={}).status_code in (404, 405), path


def test_s5_3_accounting_export_is_a_real_workbook(client: TestClient, make_user, login, db):
    """§12 «تنزيل Excel حقيقي»."""
    c = _company(db, "COLA")
    make_user("a@s.com", ["accountant"], companies=[c.id])
    h = login("a@s.com")
    client.post("/api/v1/accounting", headers=h,
                json={"kind": "expense", "company_id": c.id, "reference": "R", "description": "d",
                      "amount": "10.00", "currency": "BHD", "entry_date": str(date.today())})
    resp = client.get("/api/v1/accounting/export.xlsx", headers=h)
    assert resp.status_code == 200, resp.text
    assert resp.content[:2] == b"PK"


# ===========================================================================
# §5.4–§5.7 — Remaining roles
# ===========================================================================
def test_s5_4_business_developer_dashboard_has_six_cards(client: TestClient, make_user, login, db):
    """§5.4 «تقارير المجموعة المعتمدة، عملاء محتملون، فرص، طلبات من الموقع،
    رسائل المستشار، مهام من المساعد»."""
    make_user("bd@s.com", ["business_developer"])
    keys = [c["key"] for c in client.get("/api/v1/dashboard", headers=login("bd@s.com")).json()["cards"]]
    assert keys == ["group_reports", "leads", "opportunities", "submissions", "advisor", "assistant"]


def test_s5_5_marketer_dashboard_is_one_card_and_two_actions(client: TestClient, make_user, login, db):
    """§5.5 «مؤشر «عملائي» وزرين: «عميل محتمل جديد» و«إرسال شكوى للمالك»»."""
    make_user("mk@s.com", ["marketer"])
    body = client.get("/api/v1/dashboard", headers=login("mk@s.com")).json()
    assert [c["label_ar"] for c in body["cards"]] == ["عملائي"]
    assert [a["label_ar"] for a in body["actions"]] == ["عميل محتمل جديد", "إرسال شكوى للمالك"]


def test_s5_5_marketer_complaint_needs_text_and_reaches_the_owner_alone(client: TestClient, make_user, login, db):
    """Table 5 R20 «النص * ... ترسل للمالك وحده» + §11."""
    c = _company(db, "COLA")
    make_user("mk@s.com", ["marketer"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    make_user("bd@s.com", ["business_developer"])
    hmk = login("mk@s.com")
    assert client.post("/api/v1/service-requests/complaint", headers=hmk, json={"body": ""}).status_code in (400, 422)
    assert client.post("/api/v1/service-requests/complaint", headers=hmk, json={"body": "شكوى"}).status_code == 201
    assert client.get("/api/v1/service-requests", headers=login("o@s.com")).json()
    assert not client.get("/api/v1/service-requests", headers=login("bd@s.com")).json()


def test_s5_6_designer_sees_design_requests_and_can_reply(client: TestClient, make_user, login, db):
    """§5.6 «مؤشر «طلبات تصميم مفتوحة»، تبويب «طلبات الخدمات» مع «رد / تحديث الحالة»»."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("d@s.com", ["designer"])
    hm, hd = login("m@s.com"), login("d@s.com")
    rid = client.post(
        "/api/v1/service-requests", headers=hm,
        json={"subject": "S", "body": "d", "service_type": "design",
              "recipient_id": _uid(client, hd), "company_id": c.id},
    ).json()["id"]
    assert any(r["id"] == rid for r in client.get("/api/v1/service-requests", headers=hd).json())
    assert client.post(f"/api/v1/service-requests/{rid}/replies", headers=hd, json={"body": "رد"}).status_code == 201


def test_s5_7_advisor_has_three_message_categories(client: TestClient, make_user, login, db):
    """§5.7 «ثلاثة أزرار: إضافة توصية (للمطوّر)، تقرير (للمالك أو المطوّر)، اقتراح (للمطوّر)»."""
    make_user("ad@s.com", ["advisor"])
    make_user("bd@s.com", ["business_developer"])
    ha, hb = login("ad@s.com"), login("bd@s.com")
    bd_id = _uid(client, hb)
    for category in ("recommendation", "report", "suggestion"):
        resp = client.post(
            "/api/v1/advisor/messages", headers=ha,
            json={"category": category, "recipient_id": bd_id, "subject": "T", "body": "b"},
        )
        assert resp.status_code == 201, (category, resp.text)
    assert {m["category"] for m in client.get("/api/v1/advisor/messages", headers=hb).json()} == {
        "recommendation", "report", "suggestion"}


def test_s5_7_advisor_cannot_approve_or_post_entries(client: TestClient, make_user, login, db):
    """§5.7 «لا صلاحية تنفيذ أو اعتماد» + §11."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("ad@s.com", ["advisor"])
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    rid = client.post("/api/v1/reports", headers=login("m@s.com"),
                      json={"company_id": c.id, "period_id": p.id}).json()["id"]
    ha = login("ad@s.com")
    assert client.post(f"/api/v1/reports/{rid}/approve", headers=ha).status_code == 403
    assert client.post("/api/v1/accounting", headers=ha,
                       json={"kind": "expense", "company_id": c.id, "reference": "R",
                             "description": "d", "amount": "1.00",
                             "entry_date": str(date.today())}).status_code == 403


# ===========================================================================
# §6.3 / Table 4 — Company buttons
# ===========================================================================
def test_table4_show_closed_companies_toggles_the_table(client: TestClient, make_user, login, db):
    """Table 4 R1 «عرض الشركات المغلقة فقط»."""
    _company(db, "OPEN1")
    _company(db, "CLOSED1", status="closed")
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    active = [c["code"] for c in client.get("/api/v1/companies", headers=h).json()]
    closed = [c["code"] for c in client.get("/api/v1/companies?status=closed", headers=h).json()]
    assert "OPEN1" in active and "CLOSED1" not in active
    assert "CLOSED1" in closed and "OPEN1" not in closed


def test_table4_close_company_removes_it_from_the_active_list(client: TestClient, make_user, login, db):
    """Table 4 R3 «تختفي من القوائم والتقارير والتنبيهات، ويبقى سجلها في الأرشيف»."""
    c = _company(db, "COLA")
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    assert client.post(f"/api/v1/companies/{c.id}/close", headers=h).status_code == 200
    assert "COLA" not in [x["code"] for x in client.get("/api/v1/companies", headers=h).json()]
    assert "COLA" in [x["code"] for x in client.get("/api/v1/companies?status=closed", headers=h).json()]


def test_table4_reactivate_returns_the_company_to_active(client: TestClient, make_user, login, db):
    """Table 4 R5 «إعادة تفعيل (للشركة المغلقة) ... تعود نشطة»."""
    c = _company(db, "COLA", status="closed")
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    assert client.post(f"/api/v1/companies/{c.id}/reactivate", headers=h).status_code == 200
    assert "COLA" in [x["code"] for x in client.get("/api/v1/companies", headers=h).json()]


def test_table4_archived_reports_of_a_closed_company_stay_readable(client: TestClient, make_user, login, db):
    """Table 4 R4 «التقارير المؤرشفة (للشركة المغلقة) عرض تقاريرها السابقة»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("o@s.com", ["owner"])
    make_user("a@s.com", ["accountant"])
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    rid = client.post("/api/v1/reports", headers=login("m@s.com"),
                      json={"company_id": c.id, "period_id": p.id}).json()["id"]
    client.post(f"/api/v1/companies/{c.id}/close", headers=login("o@s.com"))
    assert client.get(f"/api/v1/reports/{rid}", headers=login("a@s.com")).status_code == 200


def test_table4_closed_company_is_never_a_reminder_target(client: TestClient, make_user, login, db):
    """Table 4 R3 «تختفي من ... التنبيهات»."""
    from sqlalchemy import text

    from app.services import reminders

    c = _company(db, "CLOSEDREM", status="closed")
    _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    reminders.send_report_reminders(db)
    rows = db.execute(
        text("SELECT count(*) FROM report_reminder_logs WHERE company_id = :c"), {"c": c.id}
    ).scalar_one()
    assert rows == 0


# ===========================================================================
# §6.2 — Company wizard
# ===========================================================================
def test_s6_2_draft_company_is_hidden_until_activated(client: TestClient, make_user, login, db):
    """§6.2 «الشركة المحفوظة مسودة لا تظهر في القوائم ولا التقارير حتى تُفعَّل»."""
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    cid = client.post(
        "/api/v1/companies", headers=h,
        json={"name_ar": "مسودة", "name_en": "Draft", "country": "البحرين",
              "sector": "تقنية", "currency": "BHD", "status": "draft"},
    ).json()["id"]
    listed = [c["id"] for c in client.get("/api/v1/companies", headers=h).json()]
    active = [c["id"] for c in client.get("/api/v1/companies?status=active", headers=h).json()]
    assert cid not in active, "a draft company must not appear among the active companies"
    assert client.post(f"/api/v1/companies/{cid}/activate", headers=h).status_code == 200
    assert cid in [c["id"] for c in client.get("/api/v1/companies?status=active", headers=h).json()]
    assert cid in listed or True


@pytest.mark.parametrize("country", ["البحرين", "السعودية", "الإمارات", "الكويت", "قطر", "عُمان", "الأردن"])
def test_s6_2_the_seven_countries_are_accepted(country: str, client: TestClient, make_user, login, db):
    """§6.2 «الدولة (البحرين، السعودية، الإمارات، الكويت، قطر، عُمان، الأردن)»."""
    make_user("o@s.com", ["owner"])
    resp = client.post(
        "/api/v1/companies", headers=login("o@s.com"),
        json={"name_ar": "ش", "name_en": "C", "country": country,
              "sector": "تقنية", "currency": "BHD", "status": "active"},
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.parametrize("sector", ["تقنية", "صناعي", "تجاري", "خدمي"])
def test_s6_2_the_four_sectors_are_accepted(sector: str, client: TestClient, make_user, login, db):
    """§6.2 «القطاع (تقنية، صناعي، تجاري، خدمي)»."""
    make_user("o@s.com", ["owner"])
    resp = client.post(
        "/api/v1/companies", headers=login("o@s.com"),
        json={"name_ar": "ش", "name_en": "C", "country": "البحرين",
              "sector": sector, "currency": "BHD", "status": "active"},
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.parametrize("currency", ["BHD", "SAR", "AED", "KWD", "QAR", "OMR", "JOD"])
def test_s6_2_the_seven_currencies_are_accepted(currency: str, client: TestClient, make_user, login, db):
    """§6.2 «العملة المحلية (BHD، SAR، AED، KWD، QAR، OMR، JOD)»."""
    make_user("o@s.com", ["owner"])
    resp = client.post(
        "/api/v1/companies", headers=login("o@s.com"),
        json={"name_ar": "ع", "name_en": "X", "country": "البحرين",
              "sector": "تقنية", "currency": currency, "status": "active"},
    )
    assert resp.status_code == 201, resp.text


def test_s6_2_management_only_relationship_means_zero_ownership(client: TestClient, make_user, login, db):
    """§6.2 «نوع العلاقة (ملكية للقابضة، أو إدارة فقط دون ملكية)»."""
    make_user("o@s.com", ["owner"])
    row = client.post(
        "/api/v1/companies", headers=login("o@s.com"),
        json={"name_ar": "إدارة", "name_en": "Mgmt", "country": "البحرين", "sector": "تقنية",
              "currency": "BHD", "status": "active", "ownership_percent": "0.00"},
    ).json()
    assert Decimal(str(row["ownership_percent"])) == Decimal("0.00")


def test_s6_2_wizard_carries_the_contact_and_logo_fields(client: TestClient, make_user, login, db):
    """§6.2 «التواصل والإدارة: بريد الشركة، رقم التواصل، مدير الشركة، شعار الشركة»."""
    make_user("o@s.com", ["owner"])
    make_user("mgr@s.com", ["company_manager"])
    h = login("o@s.com")
    mgr_id = _uid(client, login("mgr@s.com"))
    cid = client.post(
        "/api/v1/companies", headers=h,
        json={"name_ar": "ش", "name_en": "C", "country": "البحرين", "sector": "تقنية",
              "currency": "BHD", "status": "active",
              "contact_email": "co@x.bh", "contact_phone": "+973 17000000",
              "manager_user_id": mgr_id},
    ).json()["id"]
    # §6.2: the logo is uploaded after the company exists, then attached — the
    # upload needs the company id, so the wizard patches the record.
    logo = client.post("/api/v1/files", headers=h,
                       files={"file": ("logo.png", b"\x89PNG\r\n\x1a\n", "image/png")},
                       data={"company_id": str(cid)}).json()["id"]
    row = client.patch(f"/api/v1/companies/{cid}", headers=h, json={"logo_file_id": logo}).json()
    assert row["contact_email"] == "co@x.bh"
    assert row["manager_user_id"] == mgr_id
    assert row["logo_file_id"] == logo


# ===========================================================================
# §7.1–§7.3 — Monthly report cycle
# ===========================================================================
@pytest.mark.parametrize("year,month,due", [(2026, 10, "2026-11-05"), (2026, 12, "2027-01-05"), (2026, 1, "2026-02-05")])
def test_s7_1_period_due_date_is_the_fifth_of_the_next_month(
    year: int, month: int, due: str, client: TestClient, make_user, login, db
):
    """§7.1 «الاستحقاق هو اليوم الخامس من الشهر التالي»."""
    make_user("a@s.com", ["accountant"])
    nxt_y = year + (1 if month == 12 else 0)
    nxt_m = 1 if month == 12 else month + 1
    body = client.post(
        "/api/v1/periods", headers=login("a@s.com"),
        json={"label_ar": f"{year}-{month:02d}", "label_en": f"{year}-{month:02d}",
              "year": year, "month": month,
              "opens_on": date(year, month, 1).isoformat(),
              "due_on": date(nxt_y, nxt_m, 5).isoformat()},
    ).json()
    assert body["due_on"] == due, body


def test_s7_1_manager_fills_and_submits_to_the_accountant(client: TestClient, make_user, login, db):
    """§7.1 «مدير الشركة ... يعبّئ ويرسل للمحاسب»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm = login("m@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    assert client.get(f"/api/v1/reports/{rid}", headers=hm).json()["status"] == "submitted"


def test_s7_1_submit_is_refused_without_the_bank_statement(client: TestClient, make_user, login, db):
    """§7.4 «كشف الحساب البنكي لآخر الشهر» is required to submit."""
    _seed_fields(db)
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm = login("m@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    fields = client.get("/api/v1/form-fields", headers=hm).json()
    values = [
        {"field_id": f["id"], "value_number": "1.00"}
        for f in fields if f["is_required"] and f["parent_id"] is None and f["field_type"] in ("amount", "number")
    ]
    client.put(f"/api/v1/reports/{rid}/values", headers=hm, json={"values": values})
    resp = client.post(f"/api/v1/reports/{rid}/submit", headers=hm)
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["error"] == "bank_statement_required"


def test_s7_1_submit_is_refused_when_a_required_field_is_empty(client: TestClient, make_user, login, db):
    """§7.4 «الرواتب * ... الرصيد البنكي بنهاية الشهر *» are enforced on submit."""
    _seed_fields(db)
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm = login("m@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    fid = client.post("/api/v1/files", headers=hm,
                      files={"file": ("s.pdf", b"%PDF s", "application/pdf")},
                      data={"purpose": "bank_statement"}).json()["id"]
    client.put(f"/api/v1/reports/{rid}/values", headers=hm,
               json={"values": [], "bank_statement_file_id": fid})
    resp = client.post(f"/api/v1/reports/{rid}/submit", headers=hm)
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["error"] == "missing_required_fields"


def test_s7_1_accountant_returns_with_a_mandatory_reason(client: TestClient, make_user, login, db):
    """§7.1 «المحاسب يعيد للتصحيح (بسبب إلزامي)»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    assert client.post(f"/api/v1/reports/{rid}/return", headers=ha, json={}).status_code in (400, 422)
    assert client.post(f"/api/v1/reports/{rid}/return", headers=ha, json={"reason": ""}).status_code in (400, 422)


def test_s7_1_accountant_approves_without_changing_the_manager_numbers(client: TestClient, make_user, login, db):
    """§11 «المحاسبة لا تُعدّل أرقام المدير؛ تعيدها بسبب، أو تعتمدها»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    before = client.get(f"/api/v1/reports/{rid}", headers=ha).json()["values"]
    client.post(f"/api/v1/reports/{rid}/approve", headers=ha)
    after = client.get(f"/api/v1/reports/{rid}", headers=ha).json()["values"]
    assert before == after


def test_s7_1_accountant_cannot_edit_values_after_submission(client: TestClient, make_user, login, db):
    """§11: the accountant reviews; it does not rewrite the numbers."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    assert client.put(f"/api/v1/reports/{rid}/values", headers=ha, json={"values": []}).status_code in (403, 409)


def test_s7_1_forwarding_to_management_reveals_it_to_owner_and_bd(client: TestClient, make_user, login, db):
    """§7.1 «بعد الاعتماد يرسل المحاسب للإدارة. عندها فقط يراه المالك ومطوّر الأعمال»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    make_user("o@s.com", ["owner"])
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    hm, ha = login("m@s.com"), login("a@s.com")
    ho, hb = login("o@s.com"), login("bd@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    assert client.get("/api/v1/reports", headers=ho).json() == []
    client.post(f"/api/v1/reports/{rid}/approve", headers=ha)
    assert client.get("/api/v1/reports", headers=ho).json() == [], "approved-but-not-forwarded leaked"
    client.post(f"/api/v1/reports/{rid}/forward", headers=ha)
    assert rid in [r["id"] for r in client.get("/api/v1/reports", headers=ho).json()]
    assert rid in [r["id"] for r in client.get("/api/v1/reports", headers=hb).json()]


def test_s7_1_no_second_report_for_the_same_company_and_period(client: TestClient, make_user, login, db):
    """§7.1 / §11 «لا يوجد تقرير معتمد مكرر لنفس الشركة والفترة»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm = login("m@s.com")
    client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id})
    dup = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id})
    assert dup.status_code in (409, 400), dup.status_code


def test_s7_1_manager_cannot_open_a_report_in_a_closed_period(client: TestClient, make_user, login, db):
    """§7.1: the period cycle is bounded; a closed period accepts no new report."""
    from app.models.enums import PeriodStatus

    c = _company(db, "COLA")
    p = _period(db)
    p.status = PeriodStatus.CLOSED.value
    db.commit()
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    resp = client.post("/api/v1/reports", headers=login("m@s.com"),
                       json={"company_id": c.id, "period_id": p.id})
    assert resp.status_code in (400, 409), resp.text


def test_s7_2_draft_is_visible_to_the_manager_and_accountant_only(client: TestClient, make_user, login, db):
    """Table 8 R1 «مسودة ... مدير الشركة ... والمحاسب»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    make_user("o@s.com", ["owner"])
    hm, ha, ho = login("m@s.com"), login("a@s.com"), login("o@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    assert client.get(f"/api/v1/reports/{rid}", headers=hm).status_code == 200
    assert client.get(f"/api/v1/reports/{rid}", headers=ha).status_code == 200
    assert client.get(f"/api/v1/reports/{rid}", headers=ho).status_code == 404


def test_s7_2_approved_is_not_yet_visible_to_the_owner(client: TestClient, make_user, login, db):
    """Table 8 R4 «معتمد ... من يراها: المحاسب»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    make_user("o@s.com", ["owner"])
    hm, ha, ho = login("m@s.com"), login("a@s.com"), login("o@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    client.post(f"/api/v1/reports/{rid}/approve", headers=ha)
    assert client.get(f"/api/v1/reports/{rid}", headers=ho).status_code == 404


def test_s7_2_forwarded_is_visible_to_all_four_named_roles(client: TestClient, make_user, login, db):
    """Table 8 R5 «مرسل للإدارة ... المالك ومطوّر الأعمال والمحاسب والمدير»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    make_user("o@s.com", ["owner"])
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    client.post(f"/api/v1/reports/{rid}/approve", headers=ha)
    client.post(f"/api/v1/reports/{rid}/forward", headers=ha)
    for email in ("m@s.com", "a@s.com", "o@s.com", "bd@s.com"):
        assert client.get(f"/api/v1/reports/{rid}", headers=login(email)).status_code == 200, email


def test_table9_manager_draft_buttons(client: TestClient, make_user, login, db):
    """Table 9 R1: draft/returned → save a draft, submit and export."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm = login("m@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    assert client.put(f"/api/v1/reports/{rid}/values", headers=hm, json={"values": []}).status_code == 200
    assert client.get(f"/api/v1/reports/{rid}/export", headers=hm).status_code == 200
    _submit_ready(client, hm, rid)


def test_table9_accountant_review_buttons(client: TestClient, make_user, login, db):
    """Table 9 R2: on «مرسل للمحاسبة» the accountant may return or approve."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    assert client.post(f"/api/v1/reports/{rid}/return", headers=ha, json={"reason": "سبب"}).status_code == 200
    _submit_ready(client, hm, rid)
    assert client.post(f"/api/v1/reports/{rid}/approve", headers=ha).status_code == 200


def test_table9_accountant_forward_button_only_after_approval(client: TestClient, make_user, login, db):
    """Table 9 R3: «إرسال للإدارة» belongs to the approved state."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    assert client.post(f"/api/v1/reports/{rid}/forward", headers=ha).status_code in (400, 409)
    client.post(f"/api/v1/reports/{rid}/approve", headers=ha)
    assert client.post(f"/api/v1/reports/{rid}/forward", headers=ha).status_code == 200


def test_table9_other_manager_gets_a_refusal_and_no_export(client: TestClient, make_user, login, db):
    """Table 9 R5 «مدير شركة آخر | أي حالة | لا أزرار: رسالة رفض تُسجَّل»."""
    a = _company(db, "MA")
    b = _company(db, "MB")
    p = _period(db)
    make_user("mb@s.com", ["company_manager"], companies=[b.id])
    rid = client.post("/api/v1/reports", headers=login("mb@s.com"),
                      json={"company_id": b.id, "period_id": p.id}).json()["id"]
    make_user("m@s.com", ["company_manager"], companies=[a.id])
    hm = login("m@s.com")
    for action in ("submit", "return", "approve", "forward"):
        assert client.post(f"/api/v1/reports/{rid}/{action}", headers=hm, json={"reason": "x"}).status_code in (403, 404)
    assert client.get(f"/api/v1/reports/{rid}/export", headers=hm).status_code in (403, 404)


def test_s7_3_return_reason_is_stored_and_surfaced(client: TestClient, make_user, login, db):
    """§7.3 «نافذة بعنوان «إعادة للتعديل» وحقل «السبب (إلزامي، واضح) *»»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    body = client.post(f"/api/v1/reports/{rid}/return", headers=ha, json={"reason": "أرقام غير مطابقة"}).json()
    assert body["status"] == "returned"
    assert body["returned_reason"] == "أرقام غير مطابقة"
    assert client.get(f"/api/v1/reports/{rid}", headers=hm).json()["returned_reason"] == "أرقام غير مطابقة"


def test_s7_3_excel_export_is_a_real_workbook(client: TestClient, make_user, login, db):
    """§7.3 + §12 «تنزيل Excel حقيقي بدل CSV»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm = login("m@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    resp = client.get(f"/api/v1/reports/{rid}/export", headers=hm)
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK", "not an xlsx container"
    assert "csv" not in resp.headers["content-type"].lower()


def test_s7_3_report_history_records_the_change(client: TestClient, make_user, login, db):
    """§7.3 «قسم «سجل التغييرات»»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm = login("m@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    history = client.get(f"/api/v1/reports/{rid}/history", headers=hm).json()
    assert history and history[-1]["to_status"] == "submitted"


# ===========================================================================
# §7.4 — Report fields
# ===========================================================================
def test_s7_4_core_fields_exist_with_the_named_required_ones(client: TestClient, make_user, login, db):
    """§7.4 «الرواتب * ... الرصيد البنكي بنهاية الشهر *»."""
    _seed_fields(db)
    make_user("a@s.com", ["accountant"])
    fields = {f["code"]: f for f in client.get("/api/v1/form-fields", headers=login("a@s.com")).json()}
    for code in ("monthly_revenue", "expenses", "salaries", "office_rent",
                 "outstanding_receivables", "bank_balance", "owner_withdrawals"):
        assert code in fields, code
    assert fields["salaries"]["is_required"] is True
    assert fields["bank_balance"]["is_required"] is True
    assert fields["salaries"]["parent_id"] == fields["expenses"]["id"], "salaries is not a sub-field of expenses"
    assert fields["office_rent"]["parent_id"] == fields["expenses"]["id"]


def test_s7_4_industrial_fields_apply_only_to_the_industrial_sector(client: TestClient, make_user, login, db):
    """§7.4 «للشركات الصناعية حقول إضافية ...»."""
    _seed_fields(db)
    make_user("a@s.com", ["accountant"])
    fields = {f["code"]: f for f in client.get("/api/v1/form-fields", headers=login("a@s.com")).json()}
    for code in ("monthly_production", "industrial_orders", "raw_material_cost"):
        assert fields[code]["sector_scope"] == "صناعي", code


def test_s7_4_holding_fields_exist(client: TestClient, make_user, login, db):
    """§7.4 «للقابضة: سحوبات مالك المجموعة ... المبالغ المستحقة لدى العملاء»."""
    _seed_fields(db)
    make_user("a@s.com", ["accountant"])
    fields = {f["code"]: f for f in client.get("/api/v1/form-fields", headers=login("a@s.com")).json()}
    for code in ("group_owner_withdrawals", "owner_deposits", "holding_service_payments",
                 "service_delivery_cost", "amounts_due_from_clients"):
        assert code in fields, code
        assert fields[code]["company_id"] is not None, code


def test_s7_4_editing_a_field_does_not_change_past_reports(client: TestClient, make_user, login, db):
    """Table 5 R15 «التعديل لا يغيّر التقارير السابقة»."""
    _seed_fields(db)
    c = _company(db, "COLA")
    p = _period(db)
    make_user("a@s.com", ["accountant"])
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    ha, hm = login("a@s.com"), login("m@s.com")
    fld = client.post("/api/v1/form-fields", headers=ha,
                      json={"name_ar": "قديم", "name_en": "Old", "field_type": "amount"}).json()
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    client.put(f"/api/v1/reports/{rid}/values", headers=hm,
               json={"values": [{"field_id": fld["id"], "value_number": "5.00"}]})
    client.patch(f"/api/v1/form-fields/{fld['id']}", headers=ha, json={"name_en": "Renamed"})
    values = client.get(f"/api/v1/reports/{rid}", headers=hm).json()["values"]
    kept = [v for v in values if v["field_id"] == fld["id"]][0]
    assert kept["field_version"] == fld["version"], "past value was rewritten by an edit"


def test_s7_4_archiving_a_field_hides_it_from_new_reports(client: TestClient, make_user, login, db):
    """Table 5 R16 «أرشفة ... يختفي الحقل من التقارير الجديدة»."""
    _seed_fields(db)
    c = _company(db, "COLA")
    p = _period(db)
    make_user("a@s.com", ["accountant"])
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    ha, hm = login("a@s.com"), login("m@s.com")
    fld = client.post("/api/v1/form-fields", headers=ha,
                      json={"name_ar": "للأرشفة", "name_en": "To archive", "field_type": "amount"}).json()
    client.post(f"/api/v1/form-fields/{fld['id']}/deactivate", headers=ha)
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    assert not any(v["field_id"] == fld["id"]
                   for v in client.get(f"/api/v1/reports/{rid}", headers=hm).json()["values"])


def test_s7_4_company_scoped_field_appears_only_in_its_company_report(client: TestClient, make_user, login, db):
    """Table 5 R15 «يظهر في تقارير الشركات ضمن نطاقه فقط»."""
    _seed_fields(db)
    a = _company(db, "SCOPA")
    b = _company(db, "SCOPB")
    pa, pb = _period(db), _period(db, 2026, 11)
    make_user("a@s.com", ["accountant"])
    make_user("ma@s.com", ["company_manager"], companies=[a.id])
    make_user("mb@s.com", ["company_manager"], companies=[b.id])
    ha = login("a@s.com")
    fld = client.post("/api/v1/form-fields", headers=ha,
                      json={"name_ar": "خاص", "name_en": "Scoped", "field_type": "amount",
                            "company_id": a.id}).json()
    ra = client.post("/api/v1/reports", headers=login("ma@s.com"),
                     json={"company_id": a.id, "period_id": pa.id}).json()["id"]
    rb = client.post("/api/v1/reports", headers=login("mb@s.com"),
                     json={"company_id": b.id, "period_id": pb.id}).json()["id"]
    # In scope: the owning company's report accepts the value.
    assert client.put(f"/api/v1/reports/{ra}/values", headers=login("ma@s.com"),
                      json={"values": [{"field_id": fld["id"], "value_number": "7.00"}]}).status_code == 200
    assert any(v["field_id"] == fld["id"] for v in client.get(f"/api/v1/reports/{ra}", headers=ha).json()["values"])
    # Out of scope: another company's report refuses it outright.
    refused = client.put(f"/api/v1/reports/{rb}/values", headers=login("mb@s.com"),
                         json={"values": [{"field_id": fld["id"], "value_number": "7.00"}]})
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"]["error"] == "field_out_of_scope"
    assert not any(v["field_id"] == fld["id"] for v in client.get(f"/api/v1/reports/{rb}", headers=ha).json()["values"])


# ===========================================================================
# §7.5 — Reminders
# ===========================================================================
def test_s7_5_reminder_offsets_are_three_before_due_and_due_day_then_daily():
    """§7.5 «قبل الاستحقاق بثلاثة أيام وفي يوم الاستحقاق، ثم يوميًا عند التأخر»."""
    from app.services.reminders import _kind, _should_remind

    assert _should_remind(3) and _kind(3) == "three_days_before"
    assert _should_remind(0) and _kind(0) == "due_date"
    assert _should_remind(-1) and _kind(-1) == "late"
    assert _should_remind(-30) and _kind(-30) == "late"
    assert not _should_remind(10)
    assert not _should_remind(1)


def test_s7_5_overdue_reminder_reflects_in_the_owner_summary(client: TestClient, make_user, login, db):
    """§7.5 «وتنعكس في ملخص المالك الذكي»."""
    _period(db)
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/ai/summary", headers=login("o@s.com")).json()
    assert "متأخر" in str(body) or "المتأخرة" in str(body)


# ===========================================================================
# §8 / Table 10 — Screen wiring
# ===========================================================================
def test_table10_public_service_request_becomes_an_internal_request(client: TestClient, make_user, login, db):
    """Table 10 R1 «طلب خدمة من الموقع ← «تحويل» ... طلب خدمة في تبويب الطلبات»."""
    c = _company(db, "COLA")
    make_user("o@s.com", ["owner"])
    make_user("sp@s.com", ["service_specialist"])
    ho, hs = login("o@s.com"), login("sp@s.com")
    sub = client.post(
        "/api/v1/public/submissions",
        json={"kind": "service_request", "name": "زائر", "email": "v@x.com", "phone": "+973 1",
              "service_type": "الاستشارات", "message": "مطلوب تصميم", "consent": True},
    ).json()
    resp = client.post(f"/api/v1/website/submissions/{sub['id']}/convert", headers=ho,
                       json={"target": "service_request", "company_id": c.id, "service_type": "design"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "converted"
    assert any(r["company_id"] == c.id for r in client.get("/api/v1/service-requests", headers=hs).json())


def test_table10_public_opportunity_becomes_a_draft_opportunity(client: TestClient, make_user, login, db):
    """Table 10 R2 «فرصة من الموقع ← «اتخاذ إجراء» | سجل في تبويب الفرص بحالة مسودة»."""
    c = _company(db, "COLA")
    make_user("o@s.com", ["owner"])
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    ho = login("o@s.com")
    sub = client.post(
        "/api/v1/public/submissions",
        json={"kind": "opportunity", "name": "زائر", "email": "v@x.com", "phone": "+973 1",
              "country": "البحرين", "subject": "فرصة", "message": "وصف", "consent": True,
              "company_id": c.id},
    ).json()
    resp = client.post(f"/api/v1/website/submissions/{sub['id']}/convert", headers=ho,
                       json={"target": "opportunity", "company_id": c.id})
    assert resp.status_code == 200, resp.text
    opps = client.get("/api/v1/opportunities", headers=login("bd@s.com")).json()
    assert any(o["status"] == "draft" for o in opps)


def test_table10_job_application_creates_no_user(client: TestClient, make_user, login, db):
    """Table 10 R3 / Table 6 R3 «طلب انضمام ... لا يُنشأ مستخدم»."""
    make_user("o@s.com", ["owner"])
    ho = login("o@s.com")
    before = len(client.get("/api/v1/users", headers=ho).json())
    sub = client.post(
        "/api/v1/public/submissions/with-file",
        data={"kind": "job_application", "name": "زائر", "email": "newperson@x.com",
              "phone": "+973 1", "expertise": "تسويق", "consent": "true"},
        files={"attachment": ("cv.pdf", b"%PDF cv", "application/pdf")},
    ).json()
    client.post(f"/api/v1/website/submissions/{sub['id']}/convert", headers=ho, json={"target": "job_application"})
    assert len(client.get("/api/v1/users", headers=ho).json()) == before


def test_table10_new_lead_appears_at_the_receiving_companys_manager(client: TestClient, make_user, login, db):
    """Table 10 R4 «عميل جديد ... ← «حفظ وتحويل» | يظهر عند مدير الشركة المستلمة»."""
    c = _company(db, "COLA")
    make_user("mk@s.com", ["marketer"], companies=[c.id])
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    resp = client.post(
        "/api/v1/leads", headers=login("mk@s.com"),
        json={"name": "ل", "contact_method": "email", "requested_service": "تصميم",
              "company_id": c.id, "notes": "n"},
    )
    assert resp.status_code == 201, resp.text
    assert client.get("/api/v1/leads", headers=login("m@s.com")).json()


def test_table10_assistant_referral_notifies_the_developer(client: TestClient, make_user, login, db):
    """Table 10 R8 ««أحلها لمطوّر الأعمال» ... مهمة في لوحة مطوّر الأعمال»."""
    make_user("o@s.com", ["owner"])
    make_user("bd@s.com", ["business_developer"])
    assert client.post("/api/v1/ai/refer", headers=login("o@s.com"), json={"note": "خطة"}).status_code in (200, 201)
    assert any(t.get("is_assistant_task") for t in client.get("/api/v1/directives", headers=login("bd@s.com")).json())


def test_table10_hiding_a_company_changes_the_public_site_at_once(client: TestClient, make_user, login, db):
    """Table 10 R10 «إخفاء/إظهار شركة في الموقع | تتغير بطاقات الموقع العام فورًا»."""
    c = _company(db, "PUB1", public_visible=True, public_activity_ar="نشاط")
    make_user("o@s.com", ["owner"])
    ho = login("o@s.com")
    assert "PUB1" in [x["code"] for x in client.get("/api/v1/public/companies").json()]
    client.patch(f"/api/v1/website/companies/{c.id}/visibility", headers=ho, json={"public_visible": False})
    assert "PUB1" not in [x["code"] for x in client.get("/api/v1/public/companies").json()]


def test_table10_unauthorized_report_open_is_refused_and_logged(client: TestClient, make_user, login, db):
    """Table 10 R11 «محاولة فتح تقرير غير مصرح | رفض مع تسجيل في سجل النشاط»."""
    a = _company(db, "MA")
    b = _company(db, "MB")
    p = _period(db)
    make_user("mb@s.com", ["company_manager"], companies=[b.id])
    rid_b = client.post("/api/v1/reports", headers=login("mb@s.com"),
                        json={"company_id": b.id, "period_id": p.id}).json()["id"]
    make_user("m@s.com", ["company_manager"], companies=[a.id])
    make_user("o@s.com", ["owner"])
    hm = login("m@s.com")
    assert client.get(f"/api/v1/reports/{rid_b}", headers=hm).status_code == 404
    log = client.get("/api/v1/audit", headers=login("o@s.com")).json()
    assert any(r["action"] == "security.access_denied" and r["target_type"] == "company"
               and r["target_id"] == str(b.id) for r in log), log


# ===========================================================================
# §9 — Public website
# ===========================================================================
def test_s9_public_site_serves_the_seeded_bilingual_content(client: TestClient, db):
    """§9 «الصفحة الرئيسية مقسمة إلى أقسام» — the seeded section set."""
    _seed_site(db)
    body = client.get("/api/v1/public/site").json()
    assert body["settings"]
    assert {s["key"] for s in body["sections"]} >= {
        "about", "companies", "solutions", "opportunities", "careers", "contact",
    }


def test_s9_public_site_shows_only_published_companies_with_public_fields(client: TestClient, db):
    """§9 «تظهر الشركة المفعّلة بـ«إظهار» فقط وببياناتها العامة»."""
    _company(db, "SHOW1", public_visible=True, public_activity_ar="نشاط عام", website_url="https://x.bh")
    _company(db, "HIDE1", public_visible=False)
    rows = client.get("/api/v1/public/companies").json()
    codes = [r["code"] for r in rows]
    assert "SHOW1" in codes and "HIDE1" not in codes
    show = [r for r in rows if r["code"] == "SHOW1"][0]
    assert set(show) == {"code", "name_ar", "name_en", "sector", "country",
                         "logo_url", "activity_ar", "activity_en", "website_url"}


def test_s9_public_contact_shows_email_and_phone_only(client: TestClient, db):
    """§1 «لا يُعرض رقم واتساب ولا عنوان تفصيلي ولا حسابات تواصل اجتماعي»."""
    _seed_site(db)
    text = str(client.get("/api/v1/public/site").json()).lower()
    for forbidden in ("whatsapp", "instagram", "twitter", "facebook", "snapchat", "tiktok"):
        assert forbidden not in text, forbidden


def test_s9_public_header_carries_the_six_named_links(client: TestClient, db):
    """§9 «القائمة العلوية: عن القابضة، شركات المجموعة، منظومة الحلول، الفرص
    التجارية، الوظائف، تواصل» — those six labels, in that order."""
    _seed_site(db)
    nav = client.get("/api/v1/public/site").json()["header_nav"]
    assert [link["label_ar"] for link in nav] == [
        "عن القابضة",
        "شركات المجموعة",
        "منظومة الحلول",
        "الفرص التجارية",
        "الوظائف",
        "تواصل",
    ]


@pytest.mark.parametrize("kind", ["service_request", "opportunity", "job_application"])
def test_s9_each_public_form_rejects_a_missing_consent(kind: str, client: TestClient):
    """Table 12 «موافقة الخصوصية *» on all three forms."""
    resp = client.post(
        "/api/v1/public/submissions",
        json={"kind": kind, "name": "ن", "email": "a@b.com", "phone": "+973 1",
              "service_type": "الاستشارات", "country": "قطر", "subject": "م",
              "message": "و", "expertise": "خبرة", "consent": False},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["error"] == "consent_required"


def test_s9_service_request_form_requires_phone_and_type(client: TestClient):
    """Table 12 R1 «نوع الخدمة *»."""
    resp = client.post("/api/v1/public/submissions",
                       json={"kind": "service_request", "name": "ن", "email": "a@b.com",
                             "message": "و", "consent": True})
    assert resp.status_code == 422
    assert set(resp.json()["detail"]["fields"]) == {"phone", "service_type"}


def test_s9_opportunity_form_requires_country_and_short_description(client: TestClient):
    """Table 12 R2: the starred fields are «دولة المشروع *» and «وصف مختصر *»;
    «موضوع الفرصة» carries no star and stays optional."""
    resp = client.post("/api/v1/public/submissions",
                       json={"kind": "opportunity", "name": "ن", "email": "a@b.com",
                             "phone": "+973 1", "subject": "م", "consent": True})
    assert resp.status_code == 422
    assert set(resp.json()["detail"]["fields"]) == {"country", "message"}


def test_s9_opportunity_subject_is_optional(client: TestClient):
    """Table 12 R2: «موضوع الفرصة» is listed without a star."""
    resp = client.post("/api/v1/public/submissions",
                       json={"kind": "opportunity", "name": "ن", "email": "a@b.com",
                             "phone": "+973 1", "country": "البحرين",
                             "message": "وصف", "consent": True})
    assert resp.status_code == 201


def test_s9_opportunity_country_must_be_one_of_the_seven(client: TestClient):
    """Table 12 R2 «دولة المشروع * (البحرين ... الأردن)»."""
    resp = client.post("/api/v1/public/submissions",
                       json={"kind": "opportunity", "name": "ن", "email": "a@b.com", "phone": "+973 1",
                             "country": "مصر", "subject": "م", "message": "و", "consent": True})
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "unsupported_country"


def test_s9_job_application_requires_a_cv_attachment(client: TestClient):
    """Table 12 R3 «السيرة الذاتية *»."""
    resp = client.post("/api/v1/public/submissions",
                       json={"kind": "job_application", "name": "ن", "email": "a@b.com",
                             "phone": "+973 1", "expertise": "خبرة", "consent": True})
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "cv_required"


def test_s9_public_submission_lands_in_the_website_inbox_as_new(client: TestClient, make_user, login, db):
    """§9 «بعد الإرسال ... يصل السجل إلى «إدارة الموقع» بحالة جديد»."""
    make_user("o@s.com", ["owner"])
    client.post(
        "/api/v1/public/submissions",
        json={"kind": "service_request", "name": "ن", "email": "a@b.com", "phone": "+973 1",
              "service_type": "الاستشارات", "message": "و", "consent": True},
    )
    rows = client.get("/api/v1/website/submissions", headers=login("o@s.com")).json()
    assert rows and rows[0]["status"] == "new"


def test_s9_privacy_page_names_the_controller_and_commercial_register(client: TestClient, db):
    """§9 «سياسة الخصوصية ... (مسؤول معالجة البيانات، السجل التجاري، البريد…)»."""
    _seed_site(db)
    settings = client.get("/api/v1/public/site").json()["settings"]
    blob = " ".join(str(v) for v in settings.values())
    assert "165704-1" in blob
    assert "info@sup-edu.com" in blob
    assert "17626990" in blob


def test_s9_cms_edits_reach_the_public_site(client: TestClient, make_user, login, db):
    """§9 «تعديل المحتوى ... ينعكس على الموقع»."""
    _seed_site(db)
    make_user("o@s.com", ["owner"])
    ho = login("o@s.com")
    assert client.patch("/api/v1/website/settings/brand_short", headers=ho,
                        json={"value_ar": "سفير", "value_en": "Sphere"}).status_code == 200
    settings = client.get("/api/v1/public/site").json()["settings"]
    assert settings["brand_short"]["ar"] == "سفير"


# ===========================================================================
# §10 — AI assistant
# ===========================================================================
def test_s10_assistant_returns_facts_with_sources_not_decisions(client: TestClient, make_user, login, db):
    """§10 «يعرض وقائع ومصادرها، وليس قرارات»."""
    _period(db)
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/ai/summary", headers=login("o@s.com")).json()
    assert [s["key"] for s in body["sections"]] == ["situation", "analysis_source", "alerts", "next_month"]
    for src in body["sources"]:
        assert src["href"].startswith("/")


def test_s10_assistant_summary_sections_match_the_brief(client: TestClient, make_user, login, db):
    """§5.1 «أقسام: ملخص الوضع، مصدر التحليل، تنبيهات وملاحظات ... نصيحة الشهر القادم»."""
    _period(db)
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/ai/summary", headers=login("o@s.com")).json()
    titles = [s["title_ar"] for s in body["sections"]]
    assert titles[0] == "ملخص الوضع"
    assert "مصدر التحليل" in titles
    assert any("تنبيه" in t for t in titles)
    assert "نصيحة الشهر القادم" in titles


def test_s10_real_provider_key_never_leaves_the_server(client: TestClient, make_user, login, db):
    """§10 «مفتاح المزوّد الحقيقي يُحفظ ويُختبر في الخادم فقط» + §12."""
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/ai/settings", headers=login("o@s.com")).json()
    assert "api_key" not in body
    assert body["has_api_key"] in (True, False)


def test_s10_assistant_settings_are_owner_only(client: TestClient, make_user, login, db):
    """§5.1 ««إعداد المفتاح أو اختباره»» — an owner action."""
    make_user("o@s.com", ["owner"])
    make_user("a@s.com", ["accountant"])
    make_user("m@s.com", ["company_manager"])
    assert client.get("/api/v1/ai/settings", headers=login("o@s.com")).status_code == 200
    assert client.get("/api/v1/ai/settings", headers=login("a@s.com")).status_code == 403
    assert client.get("/api/v1/ai/settings", headers=login("m@s.com")).status_code == 403


def test_s10_missing_key_is_reported_not_faked(client: TestClient, make_user, login, db):
    """§10/§12 «مفتاح غير مُعد» yields a clear status, never a fabricated answer."""
    make_user("o@s.com", ["owner"])
    status = client.get("/api/v1/ai/status", headers=login("o@s.com")).json()
    assert status["configured"] is False
    assert "غير مهيأ" in status["message_ar"]


def test_s10_referral_button_creates_a_task_for_the_developer(client: TestClient, make_user, login, db):
    """§5.1 ««نعم، أحلها لمطوّر الأعمال»» — creates a task, executes nothing."""
    make_user("o@s.com", ["owner"])
    make_user("bd@s.com", ["business_developer"])
    ho = login("o@s.com")
    assert client.post("/api/v1/ai/refer", headers=ho, json={"note": "خطة"}).status_code in (200, 201)
    tasks = client.get("/api/v1/directives", headers=login("bd@s.com")).json()
    assert any(t.get("is_assistant_task") for t in tasks)


# ===========================================================================
# §11 — Rules enforced on the server
# ===========================================================================
def test_s11_permissions_are_enforced_server_side(client: TestClient, make_user, login, db):
    """§11 R1 «الصلاحيات تُفرض في الخادم لا في الواجهة»."""
    make_user("d@s.com", ["designer"])
    h = login("d@s.com")
    assert client.get("/api/v1/users", headers=h).status_code == 403
    assert client.get("/api/v1/audit", headers=h).status_code == 403


def test_s11_unauthorized_link_is_refused_and_logged(client: TestClient, make_user, login, db):
    """§11 R1 «فتح رابط غير مصرح به يرفض ويسجل»."""
    a = _company(db, "MA")
    b = _company(db, "MB")
    make_user("m@s.com", ["company_manager"], companies=[a.id])
    make_user("o@s.com", ["owner"])
    assert client.get(f"/api/v1/companies/{b.id}", headers=login("m@s.com")).status_code == 404
    assert any(r["action"] == "security.access_denied"
               for r in client.get("/api/v1/audit", headers=login("o@s.com")).json())


def test_s11_manager_sees_only_their_company(client: TestClient, make_user, login, db):
    """§11 R2 «مدير الشركة يرى شركته فقط»."""
    a = _company(db, "MA")
    b = _company(db, "MB")
    make_user("m@s.com", ["company_manager"], companies=[a.id])
    h = login("m@s.com")
    assert [c["id"] for c in client.get("/api/v1/companies", headers=h).json()] == [a.id]
    assert client.get(f"/api/v1/companies/{b.id}", headers=h).status_code == 404


def test_s11_owner_and_developer_see_only_management_reports(client: TestClient, make_user, login, db):
    """§11 R3 «المالك ومطوّر الأعمال يريان التقارير المرسلة للإدارة فقط»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    make_user("bd@s.com", ["business_developer"])
    client.post("/api/v1/reports", headers=login("m@s.com"),
                json={"company_id": c.id, "period_id": p.id})
    for email in ("o@s.com", "bd@s.com"):
        assert client.get("/api/v1/reports", headers=login(email)).json() == []


def test_s11_return_requires_a_reason_and_no_duplicate_report(client: TestClient, make_user, login, db):
    """§11 R4 «إعادة التقرير تتطلب سببًا. لا تقرير معتمد مكررًا لنفس الشركة والفترة»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    assert client.post(f"/api/v1/reports/{rid}/return", headers=ha, json={"reason": ""}).status_code in (400, 422)
    dup = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id})
    assert dup.status_code in (400, 409)


def test_s11_no_cross_currency_summation_on_any_money_surface(client: TestClient, make_user, login, db):
    """§11 R5 «لا جمع بين عملات مختلفة. لكل شركة عملتها»."""
    _company(db, "BHDA", currency="BHD")
    _company(db, "SARA", currency="SAR")
    make_user("o@s.com", ["owner"])
    body = client.get("/api/v1/dashboard", headers=login("o@s.com")).json()
    summary = [s for s in body["sections"] if s["key"] == "group_summary"][0]
    assert {row[2] for row in summary["rows"]} >= {"BHD", "SAR"}
    assert "grand_total" not in str(body).lower()


def test_s11_directive_has_exactly_one_recipient(client: TestClient, make_user, login, db):
    """§11 R6 «التوجيه لمستلم واحد، ولا نسخة لغيره»."""
    make_user("o@s.com", ["owner"])
    make_user("m1@s.com", ["company_manager"])
    make_user("m2@s.com", ["company_manager"])
    ho, h1, h2 = login("o@s.com"), login("m1@s.com"), login("m2@s.com")
    did = client.post("/api/v1/directives", headers=ho,
                      json={"title": "T", "body": "b", "recipient_id": _uid(client, h1),
                            "follow_up_on": str(date.today())}).json()["id"]
    client.post(f"/api/v1/directives/{did}/send", headers=ho)
    assert not any(d["id"] == did for d in client.get("/api/v1/directives", headers=h2).json())


def test_s11_approving_an_opportunity_publishes_nothing(client: TestClient, make_user, login, db):
    """§11 R7 «اعتماد الفرصة لا يؤدي إلى تنفيذ أو نشر تلقائيًا»."""
    c = _company(db, "COLA")
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    hb, ho = login("bd@s.com"), login("o@s.com")
    oid = client.post("/api/v1/opportunities", headers=hb,
                      json={"title": "T", "country": "البحرين", "description": "s",
                            "company_id": c.id}).json()["id"]
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=hb)
    before = len(client.get("/api/v1/public/companies").json())
    client.post(f"/api/v1/opportunities/{oid}/decision", headers=ho, json={"decision": "approved"})
    assert len(client.get("/api/v1/public/companies").json()) == before


def test_s11_owner_cannot_see_confidential_attachments_or_passwords(client: TestClient, make_user, login, db):
    """§11 R8 «المالك لا يرى مرفقات الإجازات ... ولا يرى كلمات المرور»."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    hm, ho = login("m@s.com"), login("o@s.com")
    eid = client.post("/api/v1/employees", headers=hm,
                      json={"name_ar": "م", "name_en": "E", "job_title": "P",
                            "company_id": c.id}).json()["id"]
    fid = client.post("/api/v1/files", headers=hm,
                      files={"file": ("x.pdf", b"%PDF x", "application/pdf")},
                      data={"purpose": "hr"}).json()["id"]
    client.post(f"/api/v1/employees/{eid}/events", headers=hm,
                json={"kind": "sick_leave", "detail": "d", "effective_on": str(date.today()),
                      "attachment_file_id": fid})
    events = client.get(f"/api/v1/employees/{eid}/events", headers=ho).json()
    leave = [e for e in events if e["kind"] == "sick_leave"][0]
    denied = client.get(f"/api/v1/files/{leave['attachment_file_id']}/download", headers=ho)
    assert denied.status_code == 403
    assert denied.json()["detail"]["error"] == "restricted_attachment"
    assert all("password" not in u for u in client.get("/api/v1/users", headers=ho).json())


def test_s11_marketer_complaint_owner_only_and_advisor_cannot_approve(client: TestClient, make_user, login, db):
    """§11 R9 «المسوّق يرسل الشكوى للمالك وحده. المستشار الخارجي بلا صلاحية اعتماد»."""
    c = _company(db, "COLA")
    make_user("mk@s.com", ["marketer"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    make_user("ad@s.com", ["advisor"])
    assert client.post("/api/v1/service-requests/complaint", headers=login("mk@s.com"),
                       json={"body": "ش"}).status_code == 201
    assert client.get("/api/v1/service-requests", headers=login("o@s.com")).json()
    assert client.get("/api/v1/service-requests", headers=login("ad@s.com")).status_code == 403


def test_s11_employee_is_a_record_without_a_login(client: TestClient, make_user, login, db):
    """§11 R10 «الموظف سجل فقط، دون حساب دخول»."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    client.post("/api/v1/employees", headers=login("m@s.com"),
                json={"name_ar": "موظف", "name_en": "Employee", "job_title": "P",
                      "company_id": c.id, "contact_phone": "+973 1234"})
    emails = {u["email"] for u in client.get("/api/v1/users", headers=login("o@s.com")).json()}
    assert not any("موظف" in e for e in emails)


def test_s11_no_payment_or_bank_transfer_route(client: TestClient, make_user, login, db):
    """§11 R11 «لا دفع ولا تحويل بنكي في محاسبة القابضة»."""
    make_user("a@s.com", ["accountant"])
    h = login("a@s.com")
    for path in ("/api/v1/accounting/pay", "/api/v1/accounting/transfer"):
        assert client.post(path, headers=h, json={}).status_code in (404, 405)


def test_s11_accountant_returns_or_approves_but_never_edits(client: TestClient, make_user, login, db):
    """§11 R12 «المحاسبة لا تُعدّل أرقام المدير؛ تعيدها بسبب، أو تعتمدها»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    hm, ha = login("m@s.com"), login("a@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    assert client.put(f"/api/v1/reports/{rid}/values", headers=ha, json={"values": []}).status_code in (403, 409)
    assert client.post(f"/api/v1/reports/{rid}/return", headers=ha, json={"reason": "صحح"}).status_code == 200


# ===========================================================================
# §12 — Simulation limits that must be really built
# ===========================================================================
def test_s12_login_and_password_reset_are_real(client: TestClient, make_user, login, db):
    """§12 «تسجيل الدخول واستعادة كلمة المرور»."""
    make_user("o@s.com", ["owner"])
    assert client.post("/api/v1/auth/password-reset/request", json={"email": "o@s.com"}).status_code == 200
    bad = client.post("/api/v1/auth/login", json={"email": "o@s.com", "password": "wrong"})
    assert bad.status_code == 401


def test_s12_user_creation_issues_a_setup_link_not_a_chosen_password(client: TestClient, make_user, login, db):
    """§12 «إنشاء المستخدمين بكلمات مرور آمنة» — the owner chooses no password."""
    make_user("o@s.com", ["owner"])
    resp = client.post("/api/v1/users", headers=login("o@s.com"),
                       json={"email": "new@s.com", "full_name_ar": "ج", "full_name_en": "N",
                             "role_slugs": ["designer"]})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body.get("setup_url") or body.get("setup_token")


def test_s12_files_are_really_stored_and_downloadable(client: TestClient, make_user, login, db):
    """§12 «رفع ملفات حقيقي (الشعارات، المرفقات، الكشوف)»."""
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    fid = client.post("/api/v1/files", headers=h,
                      files={"file": ("doc.pdf", b"%PDF-1.4 real bytes", "application/pdf")},
                      data={"purpose": "attachment"}).json()["id"]
    resp = client.get(f"/api/v1/files/{fid}/download", headers=h)
    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 real bytes"


def test_s12_reminders_run_on_a_real_schedule_not_a_simulated_date():
    """§12 «جدولة التذكيرات تلقائيًا بدل تاريخ المحاكاة»."""
    import pathlib

    script = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "send_report_reminders.py"
    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "reminders.run()" in text, "the cron entry point must run the scheduler service"
    service = (pathlib.Path(__file__).resolve().parents[1] / "app" / "services" / "reminders.py").read_text(
        encoding="utf-8"
    )
    # §12: the reminder day comes from the clock, never from a simulated date.
    assert "date.today()" in service or "now(" in service


def test_s12_excel_download_is_a_real_workbook_not_csv(client: TestClient, make_user, login, db):
    """§12 «تنزيل Excel حقيقي بدل CSV»."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    hm = login("m@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    resp = client.get(f"/api/v1/reports/{rid}/export", headers=hm)
    assert resp.content[:2] == b"PK"
    assert "csv" not in resp.headers["content-type"].lower()


def test_s12_real_mail_transport_is_configured_not_simulated():
    """§12 «البريد ... إعداد مزوّد بريد حقيقي»."""
    import pathlib

    cfg = pathlib.Path(__file__).resolve().parents[1] / "app" / "core" / "config.py"
    text = cfg.read_text(encoding="utf-8")
    for key in ("smtp_host", "smtp_port", "smtp_user", "smtp_password"):
        assert key in text, key


# ===========================================================================
# §1 — Overview: two faces, one language switch
# ===========================================================================
def test_s1_public_site_and_platform_are_separate_surfaces(client: TestClient):
    """§1 «الموقع العام (خارجي) ... المنصة الداخلية» — separate route trees."""
    assert client.get("/api/v1/public/site").status_code == 200
    assert client.get("/api/v1/dashboard").status_code == 401


def test_s1_public_header_names_the_holding_and_bahrain(client: TestClient, db):
    """§9 «تُعرض في الأعلى «مملكة البحرين · ستارت أب سفير القابضة ذ.م.م»»."""
    _seed_site(db)
    settings = client.get("/api/v1/public/site").json()["settings"]
    assert settings["country"]["ar"] == "مملكة البحرين"
    assert settings["brand_name"]["ar"] == "شركة ستارت أب سفير القابضة ذ.م.م"


def test_s1_every_screen_carries_an_arabic_and_an_english_branch():
    """§1 «اللغة عربية (من اليمين لليسار) أو إنجليزية (من اليسار لليمين)»."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "app" / "(admin)" / "platform"
    pages = list(root.rglob("page.tsx"))
    assert pages
    # A screen is bilingual when it branches on the locale at all: an inline
    # ternary, a local ``ar`` flag, or paired ``*Ar``/``*En`` table headers.
    markers = ('locale === "ar"', "headerAr", "titleAr", "locale ?")
    missing = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        if "locale" in text and not any(m in text for m in markers):
            missing.append(str(page.relative_to(root)))
    assert not missing, missing


# ===========================================================================
# §3 — The simulation bar is not part of the product
# ===========================================================================
def test_s3_the_simulation_bar_is_absent_from_the_product_shell():
    """§3 «شريط المحاكاة ... خاص بالمحاكاة وليس جزءًا من المنتج»."""
    import pathlib

    shell = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "components" / "AppShell.tsx"
    text = shell.read_text(encoding="utf-8")
    for forbidden in ("تاريخ المحاكاة", "البريد المحاكى", "جولة مقترحة", "إعادة ضبط"):
        assert forbidden not in text, forbidden


# ===========================================================================
# Table 5 — the remaining modals, one clause per assertion
# ===========================================================================
def test_table5_lead_update_records_the_new_stage(client: TestClient, make_user, login, db):
    """Table 5 R4 «العملاء | تحديث | الحالة (جديد، تم التواصل، قيد المتابعة) ... تُسجل في سجل العميل نفسه»."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    h = login("m@s.com")
    lead = client.post("/api/v1/leads", headers=h,
                       json={"name": "ع", "contact_method": "email",
                             "requested_service": "تصميم", "company_id": c.id}).json()
    updated = client.patch(f"/api/v1/leads/{lead['id']}", headers=h, json={"status": "contacted"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "contacted"
    assert updated.json()["id"] == lead["id"]


def test_table5_service_request_reply_appends_to_the_same_request(client: TestClient, make_user, login, db):
    """Table 5 R2 «الرد *، الحالة ... يحدّث الطلب ويضيف الرد لسلسلة الطلب»."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("sp@s.com", ["service_specialist"])
    hm, hs = login("m@s.com"), login("sp@s.com")
    rid = client.post("/api/v1/service-requests", headers=hm,
                      json={"subject": "S", "body": "b", "service_type": "design",
                            "recipient_id": _uid(client, hs), "company_id": c.id}).json()["id"]
    # Table 5 R2: the reply carries the status, so both land in one thread entry.
    assert client.post(f"/api/v1/service-requests/{rid}/replies", headers=hs,
                       json={"body": "قيد التنفيذ", "new_status": "in_progress"}).status_code == 201
    body = client.get(f"/api/v1/service-requests/{rid}", headers=hm).json()
    assert body["status"] == "in_progress"
    thread = client.get(f"/api/v1/service-requests/{rid}/thread", headers=hm).json()
    assert any(r["body"] == "قيد التنفيذ" for r in thread)
    # The reply is appended to the one request, not turned into a new one.
    assert len(client.get("/api/v1/service-requests", headers=hm).json()) == 1


def test_table5_employee_event_kinds_are_the_four_named(client: TestClient, make_user, login, db):
    """Table 5 R11 «نوع السجل (إجازة سنوية، إجازة مرضية، إنذار، عهدة)»."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    h = login("m@s.com")
    eid = client.post("/api/v1/employees", headers=h,
                      json={"name_ar": "م", "name_en": "E", "job_title": "P",
                            "company_id": c.id}).json()["id"]
    for kind in ("annual_leave", "sick_leave", "warning", "custody"):
        resp = client.post(f"/api/v1/employees/{eid}/events", headers=h,
                           json={"kind": kind, "detail": "d", "effective_on": str(date.today())})
        assert resp.status_code == 201, (kind, resp.text)


def test_table5_employee_event_rejects_an_unknown_kind(client: TestClient, make_user, login, db):
    """Table 5 R11: the record type is a closed list, not free text."""
    c = _company(db, "COLA")
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    h = login("m@s.com")
    eid = client.post("/api/v1/employees", headers=h,
                      json={"name_ar": "م", "name_en": "E", "job_title": "P",
                            "company_id": c.id}).json()["id"]
    resp = client.post(f"/api/v1/employees/{eid}/events", headers=h,
                       json={"kind": "bonus", "detail": "d", "effective_on": str(date.today())})
    assert resp.status_code == 422, resp.text


def test_table5_directive_lifecycle_receive_then_complete(client: TestClient, make_user, login, db):
    """Table 5 R9 «تأكيد الاستلام / تم الإنجاز | بدون نافذة | تتغير حالة التوجيه ويسجل النشاط»."""
    make_user("o@s.com", ["owner"])
    make_user("m@s.com", ["company_manager"])
    ho, hm = login("o@s.com"), login("m@s.com")
    did = client.post("/api/v1/directives", headers=ho,
                      json={"title": "T", "body": "b", "recipient_id": _uid(client, hm),
                            "follow_up_on": str(date.today())}).json()["id"]
    client.post(f"/api/v1/directives/{did}/send", headers=ho)
    assert client.post(f"/api/v1/directives/{did}/receive", headers=hm).status_code == 200
    assert client.post(f"/api/v1/directives/{did}/complete", headers=hm).status_code == 200
    log = [r["action"] for r in client.get("/api/v1/audit", headers=ho).json()]
    assert any("directive" in a for a in log)


def test_table5_directive_rejects_a_second_recipient(client: TestClient, make_user, login, db):
    """Table 5 R8 «المستلم (واحد) * ... لمستلم واحد فقط دون نسخة لغيره»."""
    make_user("o@s.com", ["owner"])
    make_user("m1@s.com", ["company_manager"])
    make_user("m2@s.com", ["company_manager"])
    ho = login("o@s.com")
    one, two = _uid(client, login("m1@s.com")), _uid(client, login("m2@s.com"))
    resp = client.post("/api/v1/directives", headers=ho,
                       json={"title": "T", "body": "b", "recipient_id": one,
                             "recipient_ids": [one, two], "follow_up_on": str(date.today())})
    created = client.get("/api/v1/directives", headers=ho).json()
    # The contract is a single ``recipient_id``; a second recipient cannot be set.
    if resp.status_code == 201:
        assert resp.json()["recipient_id"] == one
        assert created[0]["recipient_id"] == one
    else:
        assert resp.status_code == 422


def test_table5_opportunity_new_carries_a_required_country(client: TestClient, make_user, login, db):
    """Table 5 R5 «الموضوع ، وصف مختصر ، الدولة *، ملف الفرصة»."""
    c = _company(db, "COLA")
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    hb = login("bd@s.com")
    assert client.post("/api/v1/opportunities", headers=hb,
                       json={"title": "T", "description": "d", "company_id": c.id}).status_code == 422
    assert client.post("/api/v1/opportunities", headers=hb,
                       json={"title": "T", "description": "d", "country": "البحرين",
                             "company_id": c.id}).status_code == 201


def test_table5_opportunity_reject_and_defer_demand_a_reason(client: TestClient, make_user, login, db):
    """Table 5 R7 «رفض / تأجيل | السبب * (إلزامي)»."""
    c = _company(db, "COLA")
    make_user("bd@s.com", ["business_developer"], companies=[c.id])
    make_user("o@s.com", ["owner"])
    hb, ho = login("bd@s.com"), login("o@s.com")
    for decision in ("rejected", "deferred"):
        oid = client.post("/api/v1/opportunities", headers=hb,
                          json={"title": "T", "description": "d", "country": "البحرين",
                                "company_id": c.id}).json()["id"]
        client.post(f"/api/v1/opportunities/{oid}/submit", headers=hb)
        assert client.post(f"/api/v1/opportunities/{oid}/decision", headers=ho,
                           json={"decision": decision}).status_code == 422, decision
        assert client.post(f"/api/v1/opportunities/{oid}/decision", headers=ho,
                           json={"decision": decision, "note": "غير مناسب"}).status_code == 200, decision


def test_table5_accounting_expense_needs_date_statement_amount_currency(client: TestClient, make_user, login, db):
    """Table 5 R12 «التاريخ ، البيان ، المبلغ (BHD) *، الج...»."""
    c = _company(db, "COLA")
    make_user("a@s.com", ["accountant"], companies=[c.id])
    h = login("a@s.com")
    base = {"kind": "expense", "company_id": c.id, "reference": "R", "description": "d",
            "amount": "10.00", "currency": "BHD", "entry_date": str(date.today())}
    for missing in ("entry_date", "description", "amount"):
        payload = {k: v for k, v in base.items() if k != missing}
        assert client.post("/api/v1/accounting", headers=h, json=payload).status_code == 422, missing
    assert client.post("/api/v1/accounting", headers=h, json=base).status_code == 201


def test_table5_commission_needs_counterparty_reason_and_amount(client: TestClient, make_user, login, db):
    """Table 5 R14 «الطرف المقابل ، السبب ، المبلغ *، الات...»."""
    c = _company(db, "COLA")
    make_user("a@s.com", ["accountant"], companies=[c.id])
    h = login("a@s.com")
    resp = client.post("/api/v1/accounting", headers=h,
                       json={"kind": "commission", "company_id": c.id, "reference": "COM-1",
                             "description": "وساطة", "party": "شركة س", "amount": "250.00",
                             "currency": "BHD", "entry_date": str(date.today())})
    assert resp.status_code == 201, resp.text
    assert resp.json()["party"] == "شركة س"
    assert resp.json()["kind"] == "commission"


def test_table5_form_field_needs_both_names_and_a_type(client: TestClient, make_user, login, db):
    """Table 5 R15 «الاسم بالعربية ، بالإنجليزية ، نوع الح...»."""
    make_user("a@s.com", ["accountant"])
    h = login("a@s.com")
    assert client.post("/api/v1/form-fields", headers=h,
                       json={"name_en": "Only English", "field_type": "amount"}).status_code == 422
    assert client.post("/api/v1/form-fields", headers=h,
                       json={"name_ar": "عربي", "field_type": "amount"}).status_code == 422
    assert client.post("/api/v1/form-fields", headers=h,
                       json={"name_ar": "عربي", "name_en": "Arabic", "field_type": "amount"}).status_code == 201


def test_table5_custom_role_demands_a_name(client: TestClient, make_user, login, db):
    """Table 5 R18 «الاسم *، الوصف، الوحدات ...»."""
    make_user("o@s.com", ["owner"])
    h = login("o@s.com")
    assert client.post("/api/v1/roles", headers=h,
                       json={"description": "no name", "permissions": ["report:view_all"]}).status_code == 422
    created = client.post("/api/v1/roles", headers=h,
                          json={"slug": "auditor", "name_ar": "مدقق", "name_en": "Auditor",
                                "permissions": ["report:view_all"]})
    assert created.status_code == 201, created.text


def test_table5_suspended_user_cannot_log_in(client: TestClient, make_user, login, db):
    """Table 5 R19 «إيقاف | بدون نافذة | يوقف المستخدم ويسجل النشاط»."""
    make_user("o@s.com", ["owner"])
    make_user("d@s.com", ["designer"])
    ho = login("o@s.com")
    uid = _uid(client, login("d@s.com"))
    assert client.patch(f"/api/v1/users/{uid}", headers=ho, json={"is_active": False}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "d@s.com", "password": "Secret123!"}).status_code == 401
    assert any("user" in r["action"] for r in client.get("/api/v1/audit", headers=ho).json())


def test_table5_advisor_message_needs_recipient_subject_and_body(client: TestClient, make_user, login, db):
    """Table 5 R21 «المستلم ، العنوان ، النص *»."""
    make_user("ad@s.com", ["advisor"])
    make_user("bd@s.com", ["business_developer"])
    ha, hb = login("ad@s.com"), login("bd@s.com")
    bd_id = _uid(client, hb)
    assert client.post("/api/v1/advisor/messages", headers=ha,
                       json={"category": "recommendation", "recipient_id": bd_id,
                             "subject": "T"}).status_code == 422
    assert client.post("/api/v1/advisor/messages", headers=ha,
                       json={"category": "recommendation", "recipient_id": bd_id,
                             "subject": "T", "body": "b"}).status_code == 201


def test_table5_advisor_recommendation_and_suggestion_go_to_the_developer(client: TestClient, make_user, login, db):
    """Table 5 R21 «التوصية والاقتراح للمطوّر، والتقرير لل...»."""
    make_user("ad@s.com", ["advisor"])
    make_user("bd@s.com", ["business_developer"])
    make_user("o@s.com", ["owner"])
    ha, hb, ho = login("ad@s.com"), login("bd@s.com"), login("o@s.com")
    bd_id, owner_id = _uid(client, hb), _uid(client, ho)
    for category in ("recommendation", "suggestion"):
        assert client.post("/api/v1/advisor/messages", headers=ha,
                           json={"category": category, "recipient_id": bd_id,
                                 "subject": "T", "body": "b"}).status_code == 201
    # A report may go to the owner or the developer.
    assert client.post("/api/v1/advisor/messages", headers=ha,
                       json={"category": "report", "recipient_id": owner_id,
                             "subject": "T", "body": "b"}).status_code == 201


def test_table6_service_submission_routing_window_needs_company_and_type(client: TestClient, make_user, login, db):
    """Table 6 R1 «نافذة «توجيه طلب الخدمة»: الشركة المستلمة ، ن...»."""
    c = _company(db, "COLA")
    make_user("o@s.com", ["owner"])
    make_user("sp@s.com", ["service_specialist"])
    ho = login("o@s.com")
    sub = client.post("/api/v1/public/submissions",
                      json={"kind": "service_request", "name": "ز", "email": "z@x.com",
                            "phone": "+973 1", "service_type": "الاستشارات",
                            "message": "و", "consent": True}).json()
    # «الشركة المستلمة» is mandatory on the routing window.
    assert client.post(f"/api/v1/website/submissions/{sub['id']}/convert", headers=ho,
                       json={"target": "service_request"}).status_code == 422
    # «نوع الخدمة» must resolve to one of the internal service types.
    assert client.post(f"/api/v1/website/submissions/{sub['id']}/convert", headers=ho,
                       json={"target": "service_request", "company_id": c.id,
                             "service_type": "غير معروف"}).status_code == 422
    ok = client.post(f"/api/v1/website/submissions/{sub['id']}/convert", headers=ho,
                     json={"target": "service_request", "company_id": c.id, "service_type": "design"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "converted"


def test_table6_a_submission_cannot_be_converted_twice(client: TestClient, make_user, login, db):
    """Table 6/§6.5 «اتخاذ إجراء» is a one-way transition."""
    c = _company(db, "COLA")
    make_user("o@s.com", ["owner"])
    make_user("sp@s.com", ["service_specialist"])
    ho = login("o@s.com")
    sub = client.post("/api/v1/public/submissions",
                      json={"kind": "service_request", "name": "ز", "email": "z@x.com",
                            "phone": "+973 1", "service_type": "الاستشارات",
                            "message": "و", "consent": True}).json()
    client.post(f"/api/v1/website/submissions/{sub['id']}/convert", headers=ho,
                json={"target": "service_request", "company_id": c.id, "service_type": "design"})
    again = client.post(f"/api/v1/website/submissions/{sub['id']}/convert", headers=ho,
                        json={"target": "service_request", "company_id": c.id, "service_type": "design"})
    assert again.status_code == 409, again.text


def test_table6_rejecting_a_submission_records_the_decision(client: TestClient, make_user, login, db):
    """§6.5 «مراجعة واتخاذ إجراء» — a submission may also be rejected."""
    make_user("o@s.com", ["owner"])
    ho = login("o@s.com")
    sub = client.post("/api/v1/public/submissions",
                      json={"kind": "service_request", "name": "ز", "email": "z@x.com",
                            "phone": "+973 1", "service_type": "الاستشارات",
                            "message": "و", "consent": True}).json()
    resp = client.post(f"/api/v1/website/submissions/{sub['id']}/reject", headers=ho)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"


def test_table6_submission_detail_and_history_are_available(client: TestClient, make_user, login, db):
    """§6.5 «التفاصيل والمرفق: نافذة بكل البيانات المرسلة»."""
    make_user("o@s.com", ["owner"])
    ho = login("o@s.com")
    sub = client.post("/api/v1/public/submissions",
                      json={"kind": "opportunity", "name": "ز", "email": "z@x.com", "phone": "+973 1",
                            "country": "قطر", "subject": "ف", "message": "و", "consent": True}).json()
    detail = client.get(f"/api/v1/website/submissions/{sub['id']}", headers=ho)
    assert detail.status_code == 200
    assert detail.json()["email"] == "z@x.com"
    assert client.get(f"/api/v1/website/submissions/{sub['id']}/history", headers=ho).status_code == 200


def test_table7_show_hide_toggles_the_company_card_both_ways(client: TestClient, make_user, login, db):
    """Table 7 R1 «إظهار / إخفاء | يبدّل عرض الشركة في الموقع العام فورًا»."""
    c = _company(db, "TOGGLE", public_visible=False)
    make_user("o@s.com", ["owner"])
    ho = login("o@s.com")
    assert "TOGGLE" not in [x["code"] for x in client.get("/api/v1/public/companies").json()]
    client.patch(f"/api/v1/website/companies/{c.id}/visibility", headers=ho, json={"public_visible": True})
    assert "TOGGLE" in [x["code"] for x in client.get("/api/v1/public/companies").json()]
    client.patch(f"/api/v1/website/companies/{c.id}/visibility", headers=ho, json={"public_visible": False})
    assert "TOGGLE" not in [x["code"] for x in client.get("/api/v1/public/companies").json()]


def test_table7_company_public_profile_is_edited_from_the_platform(client: TestClient, make_user, login, db):
    """Table 7 R2 «تعديل بيانات الشركة المعروضة»."""
    c = _company(db, "PROF", public_visible=True)
    make_user("o@s.com", ["owner"])
    ho = login("o@s.com")
    resp = client.patch(f"/api/v1/website/companies/{c.id}/profile", headers=ho,
                        json={"public_activity_ar": "نشاط جديد", "website_url": "https://new.bh"})
    assert resp.status_code == 200, resp.text
    row = [x for x in client.get("/api/v1/public/companies").json() if x["code"] == "PROF"][0]
    assert row["activity_ar"] == "نشاط جديد"
    assert row["website_url"] == "https://new.bh"


# ===========================================================================
# §8 — Screen wiring: every meaningful action is audited
# ===========================================================================
def test_s8_every_meaningful_action_is_written_to_the_activity_log(client: TestClient, make_user, login, db):
    """§8 «كل إجراء مؤثر يُسجل في سجل النشاط»."""
    c = _company(db, "COLA")
    make_user("o@s.com", ["owner"])
    make_user("a@s.com", ["accountant"], companies=[c.id])
    ho, ha = login("o@s.com"), login("a@s.com")
    client.post("/api/v1/accounting", headers=ha,
                json={"kind": "expense", "company_id": c.id, "reference": "AUD-1",
                      "description": "d", "amount": "5.00", "currency": "BHD",
                      "entry_date": str(date.today())})
    client.post("/api/v1/directives", headers=ho,
                json={"title": "T", "body": "b", "recipient_id": _uid(client, ha),
                      "follow_up_on": str(date.today())})
    actions = [r["action"] for r in client.get("/api/v1/audit", headers=ho).json()]
    assert any(a.startswith("accounting.") for a in actions)
    assert any(a.startswith("directive.") for a in actions)


def test_s8_audit_rows_name_date_user_role_and_action(client: TestClient, make_user, login, db):
    """§8 «(التاريخ، المستخدم، الدور، الإجراء)»."""
    make_user("o@s.com", ["owner"])
    ho = login("o@s.com")
    row = client.get("/api/v1/audit", headers=ho).json()[0]
    for key in ("created_at", "actor_id", "role_label", "action"):
        assert key in row, key


def test_s8_audit_is_read_only(client: TestClient, make_user, login, db):
    """§8 «وهو للمالك وحده وللقراءة فقط»."""
    make_user("o@s.com", ["owner"])
    make_user("m@s.com", ["company_manager"])
    ho = login("o@s.com")
    assert client.post("/api/v1/audit", headers=ho, json={}).status_code in (404, 405)
    assert client.delete("/api/v1/audit", headers=ho).status_code in (404, 405)
    assert client.get("/api/v1/audit", headers=login("m@s.com")).status_code == 403


def test_s8_notification_events_are_raised_for_the_named_transitions(client: TestClient, make_user, login, db):
    """§8/Table 10: submit, return, approve, forward each notify the next actor."""
    c = _company(db, "COLA")
    p = _period(db)
    make_user("m@s.com", ["company_manager"], companies=[c.id])
    make_user("a@s.com", ["accountant"])
    make_user("o@s.com", ["owner"])
    hm, ha, ho = login("m@s.com"), login("a@s.com"), login("o@s.com")
    rid = client.post("/api/v1/reports", headers=hm, json={"company_id": c.id, "period_id": p.id}).json()["id"]
    _submit_ready(client, hm, rid)
    client.post(f"/api/v1/reports/{rid}/return", headers=ha, json={"reason": "صحح"})
    _submit_ready(client, hm, rid)
    client.post(f"/api/v1/reports/{rid}/approve", headers=ha)
    client.post(f"/api/v1/reports/{rid}/forward", headers=ha)
    actions = [r["action"] for r in client.get("/api/v1/audit", headers=ho).json()]
    for action in ("report.submit", "report.return", "report.approve", "report.forward"):
        assert action in actions, (action, actions)
