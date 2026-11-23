"""§11.5: amounts in different currencies are never summed into one number.

The platform holds companies in different currencies (BHD, SAR, USD …). Every
place that shows money — the owner dashboard's group summary, the monthly report
detail and its Excel export, the accounting Excel export, and the AI assistant's
facts and owner summary — must keep each amount in its own company's currency and
must not present a single combined figure. These tests prove that against real
requests, and also assert the absence of any aggregate "total" field.
"""

from __future__ import annotations

import io
from datetime import date

from app.models.business import Company, FormField, MonthlyReport, ReportingPeriod, ReportValue
from app.models.enums import PeriodStatus
from app.models.identity import User


def _period(db) -> ReportingPeriod:
    period = ReportingPeriod(
        label_ar="2026-10",
        label_en="2026-10",
        year=2026,
        month=10,
        opens_on=date(2026, 10, 1),
        due_on=date(2026, 11, 5),
        status=PeriodStatus.OPEN.value,
    )
    db.add(period)
    db.commit()
    return period


def _revenue_field(db) -> FormField:
    field = FormField(code="revenue", name_ar="الإيراد", name_en="Revenue", field_type="amount")
    db.add(field)
    db.commit()
    return field


def _company(db, code: str, currency: str) -> Company:
    company = Company(
        code=code,
        name_ar=f"شركة {code}",
        name_en=f"Co {code}",
        country="BH",
        sector="تقنية",
        currency=currency,
        status="active",
    )
    db.add(company)
    db.commit()
    return company


def _report(db, company: Company, period: ReportingPeriod, field: FormField, amount: str) -> MonthlyReport:
    # ``forwarded`` is the state in which the owner may read a report (§7.1), so
    # the detail and export checks below can run as the owner.
    report = MonthlyReport(company_id=company.id, period_id=period.id, status="forwarded", currency=company.currency)
    db.add(report)
    db.flush()
    db.add(ReportValue(report_id=report.id, field_id=field.id, value_number=amount, field_version=1))
    db.commit()
    return report


def _mixed_currencies(db):
    period = _period(db)
    field = _revenue_field(db)
    bhd = _company(db, "CUR-BHD", "BHD")
    sar = _company(db, "CUR-SAR", "SAR")
    usd = _company(db, "CUR-USD", "USD")
    _report(db, bhd, period, field, "1000")
    _report(db, sar, period, field, "1000")
    _report(db, usd, period, field, "1000")
    return {"period": period, "field": field, "BHD": bhd, "SAR": sar, "USD": usd}


def test_owner_dashboard_group_summary_keeps_each_currency_separate(client, make_user, login, db):
    """The group summary shows one row per company in its own currency and has no
    combined total."""
    make_user("cur_owner@safir-platform.com", ["owner"])
    headers = login("cur_owner@safir-platform.com")
    data = _mixed_currencies(db)

    body = client.get("/api/v1/dashboard", headers=headers).json()
    section = next(s for s in body["sections"] if s["key"] == "group_summary")

    # The title states the rule explicitly.
    assert "دون جمع" in section["title_ar"]
    assert "not summed" in section["title_en"]

    rows_by_name = {row[0]: row for row in section["rows"]}
    for code, currency in (("CUR-BHD", "BHD"), ("CUR-SAR", "SAR"), ("CUR-USD", "USD")):
        company = data[currency]
        row = rows_by_name[company.name_ar]
        # The currency column carries the company's own currency …
        assert row[2] == currency
        # … and the revenue cell shows that company's figure, not a group total.
        assert "1,000" in row[3]

    # There is no aggregate row and no summed money column.
    assert all(row[0] not in {"الإجمالي", "Total", "المجموع"} for row in section["rows"])
    flat = " ".join(str(cell) for row in section["rows"] for cell in row)
    assert "3,000" not in flat, "amounts across currencies must never be summed"


def test_owner_dashboard_has_no_cross_currency_total_card(client, make_user, login, db):
    """No dashboard KPI is a monetary total that could mix currencies."""
    make_user("cur_owner2@safir-platform.com", ["owner"])
    headers = login("cur_owner2@safir-platform.com")
    _mixed_currencies(db)
    body = client.get("/api/v1/dashboard", headers=headers).json()
    for card in body["cards"]:
        # The owner's KPIs are counts, never money totals.
        assert isinstance(card["value"], int)
        assert "إجمالي" not in card["label_ar"] and "total" not in card["label_en"].lower()


def test_report_detail_and_export_keep_each_value_in_its_own_currency(client, make_user, login, db):
    make_user("cur_owner3@safir-platform.com", ["owner"])
    headers = login("cur_owner3@safir-platform.com")
    data = _mixed_currencies(db)

    for currency in ("BHD", "SAR", "USD"):
        company = data[currency]
        report = db.query(MonthlyReport).filter(MonthlyReport.company_id == company.id).one()

        detail = client.get(f"/api/v1/reports/{report.id}", headers=headers).json()
        assert detail["currency"] == currency

        export = client.get(f"/api/v1/reports/{report.id}/export", headers=headers)
        assert export.status_code == 200, export.text
        wb = __import__("openpyxl").load_workbook(io.BytesIO(export.content))
        ws = wb.active
        cells = [[c.value for c in row] for row in ws.iter_rows()]
        flat = [str(v) for row in cells for v in row if v is not None]
        assert currency in flat, f"export must label the {currency} amount with its currency"
        # The export carries the company's currency, never a merged total.
        assert any(row and row[0] == "Currency" and row[1] == currency for row in cells)
        assert "3000" not in " ".join(flat)
        assert "3,000" not in " ".join(flat)


def test_accounting_export_labels_each_amount_with_its_currency(client, make_user, login, db):
    make_user("cur_owner4@safir-platform.com", ["owner"])
    headers = login("cur_owner4@safir-platform.com")
    data = _mixed_currencies(db)
    acct = make_user("cur_acct@safir-platform.com", ["accountant"])
    client.patch(f"/api/v1/users/{acct.id}", headers=headers, json={"company_ids": [data["BHD"].id, data["SAR"].id]})
    h_acct = login("cur_acct@safir-platform.com")

    for currency in ("BHD", "SAR"):
        company = data[currency]
        created = client.post(
            "/api/v1/accounting",
            headers=h_acct,
            json={
                "kind": "invoice",
                "company_id": company.id,
                "reference": f"INV-{currency}",
                "description": "خدمة",
                "amount": "500.00",
                "currency": currency,
                "entry_date": "2026-10-15",
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["currency"] == currency

    export = client.get("/api/v1/accounting/export.xlsx", headers=h_acct)
    assert export.status_code == 200, export.text
    wb = __import__("openpyxl").load_workbook(io.BytesIO(export.content))
    ws = wb.active
    rows = [[c.value for c in row] for row in ws.iter_rows()]
    header = rows[0]
    assert "Currency" in header
    assert "Amount" in header
    cur_idx = header.index("Currency")
    amt_idx = header.index("Amount")

    currencies = {r[cur_idx] for r in rows[1:] if r[cur_idx]}
    assert currencies == {"BHD", "SAR"}
    # Each amount row carries its own currency; there is no total row that would
    # combine the two currencies.
    amounts = [(r[amt_idx], r[cur_idx]) for r in rows[1:] if r[amt_idx] is not None]
    assert (500.0, "BHD") in amounts and (500.0, "SAR") in amounts
    assert not any(str(r[0]).upper() == "TOTAL" for r in rows[1:])


def test_ai_facts_carry_each_amount_with_its_own_currency(client, make_user, login, db, monkeypatch):
    """The AI context is built per company currency; a combined figure is never
    produced, so the model cannot sum across currencies."""
    from app.ai.provider import GroundedContext
    from app.ai.retrieval import gather_context

    make_user("cur_ai_owner@safir-platform.com", ["owner"])
    owner = db.query(User).filter_by(email="cur_ai_owner@safir-platform.com").one()
    _mixed_currencies(db)

    ctx: GroundedContext = gather_context(db, owner, company_id=None, period_id=None)
    report_facts = [f for f in ctx.facts if f.startswith("report#")]
    assert report_facts, "the owner should see the reports"
    # Every report fact names the company's currency next to its amount …
    for fact in report_facts:
        assert "currency=" in fact
    # … and no fact is a cross-currency sum.
    joined = " ".join(ctx.facts)
    assert "3000" not in joined and "3,000" not in joined
    for currency in ("BHD", "SAR", "USD"):
        assert f"currency={currency}" in joined


def test_ai_summary_scope_states_the_no_summation_rule(client, make_user, login, db):
    make_user("cur_ai_owner2@safir-platform.com", ["owner"])
    headers = login("cur_ai_owner2@safir-platform.com")
    _mixed_currencies(db)
    body = client.get("/api/v1/ai/summary", headers=headers).json()
    assert "كل مبلغ بعملة شركته" in body["scope_ar"]
    assert "own company currency" in body["scope_en"]
    # Each cited source carries its own currency.
    for src in body["sources"]:
        assert src["currency"] in {"BHD", "SAR", "USD"}
