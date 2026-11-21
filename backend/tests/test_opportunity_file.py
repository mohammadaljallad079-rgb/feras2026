"""The opportunity file: classification, financials, risk, recommendation,
follow-up, outcome and comparison.

The brief (§5.1, Table 5, design page 12) fixes the six table columns and the
four decision buttons. These tests cover the analysis kept beside them, and
assert that adding it left the brief's workflow intact.
"""

from __future__ import annotations

import pytest


def _company(client, headers, code="OPP-A", status="active"):
    resp = client.post(
        "/api/v1/companies",
        headers=headers,
        json={
            "code": code, "name_ar": f"شركة {code}", "name_en": f"Co {code}",
            "country": "البحرين", "sector": "تقنية", "status": status,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.fixture()
def cast(client, make_user, login):
    """An owner, a business developer scoped to one company, and a rival company."""
    owner = make_user("o@safir-platform.com", ["owner"])
    bd = make_user("bd@safir-platform.com", ["business_developer"])
    h_owner = login("o@safir-platform.com")
    h_bd = login("bd@safir-platform.com")
    cid = _company(client, h_owner, "OPP-A")
    other = _company(client, h_owner, "OPP-B")
    client.patch(f"/api/v1/users/{bd.id}", headers=h_owner, json={"company_ids": [cid]})
    return {"owner": owner, "bd": bd, "h_owner": h_owner, "h_bd": h_bd, "cid": cid, "other": other}


def _draft(client, cast, **extra):
    payload = {"title": "فرصة", "company_id": cast["cid"], "country": "البحرين", **extra}
    resp = client.post("/api/v1/opportunities", headers=cast["h_bd"], json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_the_brief_workflow_survives_an_opportunity_with_no_analysis(client, cast):
    """§5.1: topic, country and file are the whole requirement."""
    oid = _draft(client, cast)
    assert client.post(f"/api/v1/opportunities/{oid}/submit", headers=cast["h_bd"]).status_code == 200
    decided = client.post(
        f"/api/v1/opportunities/{oid}/decision",
        headers=cast["h_owner"], json={"decision": "approved"},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"


def test_a_whole_analysis_file_can_be_recorded(client, cast):
    oid = _draft(
        client, cast,
        category="investment",
        requested_from_group="تمويل مشترك بنسبة 40%",
        investment_amount="250000.00",
        expected_return="400000.00",
        expected_return_pct="18.50",
        cashflow_note="تدفق موجب من الشهر التاسع",
        risk_level="medium",
        risk_note="مخاطر تنظيمية في السوق المستهدف",
        recommendation="المضي في الدراسة التفصيلية",
        estimated_value="250000.00",
    )
    row = client.get("/api/v1/opportunities", headers=cast["h_bd"]).json()[0]
    assert row["id"] == oid
    assert row["category"] == "investment"
    assert row["requested_from_group"] == "تمويل مشترك بنسبة 40%"
    assert row["expected_return_pct"] == "18.50"
    assert row["risk_level"] == "medium"
    assert row["recommendation"] == "المضي في الدراسة التفصيلية"


def test_the_draft_can_be_filled_in_after_it_is_created(client, cast):
    oid = _draft(client, cast)
    resp = client.patch(
        f"/api/v1/opportunities/{oid}", headers=cast["h_bd"],
        json={"category": "commercial", "risk_level": "high", "expected_return_pct": "9.00"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["category"] == "commercial"
    assert resp.json()["risk_level"] == "high"


def test_the_analysis_is_frozen_once_the_case_is_submitted(client, cast):
    """The owner decides on what was sent, so a submitted case cannot be rewritten."""
    oid = _draft(client, cast, category="commercial")
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=cast["h_bd"])
    resp = client.patch(
        f"/api/v1/opportunities/{oid}", headers=cast["h_bd"], json={"risk_level": "low"}
    )
    assert resp.status_code == 409, resp.text


def test_the_decision_names_who_follows_up_and_when(client, cast):
    oid = _draft(client, cast)
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=cast["h_bd"])
    resp = client.post(
        f"/api/v1/opportunities/{oid}/decision", headers=cast["h_owner"],
        json={
            "decision": "approved",
            "next_step_owner_id": cast["bd"].id,
            "next_step_on": "2027-01-15",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["next_step_owner_id"] == cast["bd"].id
    assert body["next_step_owner_name"]
    assert body["next_step_on"] == "2027-01-15"


def test_an_unknown_follow_up_owner_is_refused(client, cast):
    oid = _draft(client, cast)
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=cast["h_bd"])
    resp = client.post(
        f"/api/v1/opportunities/{oid}/decision", headers=cast["h_owner"],
        json={"decision": "approved", "next_step_owner_id": 999999},
    )
    assert resp.status_code == 422, resp.text
    # The refusal must not leave the case half-decided.
    rows = client.get("/api/v1/opportunities", headers=cast["h_owner"]).json()
    row = next(r for r in rows if r["id"] == oid)
    assert row["status"] == "submitted"
    assert row["next_step_owner_id"] is None


def test_the_outcome_is_recorded_after_the_decision(client, cast):
    """«عرض نتائج الفرص ومقارنتها بالتوقعات» needs the realised figure."""
    oid = _draft(client, cast, expected_return="400000.00", expected_return_pct="18.50")
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=cast["h_bd"])
    client.post(f"/api/v1/opportunities/{oid}/decision", headers=cast["h_owner"], json={"decision": "approved"})
    resp = client.patch(
        f"/api/v1/opportunities/{oid}", headers=cast["h_bd"],
        json={"actual_return": "360000.00", "actual_note": "أقل من التوقع لارتفاع التكاليف"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["actual_return"] == "360000.00"
    assert body["expected_return"] == "400000.00"
    assert body["actual_note"]


def test_the_outcome_does_not_reopen_the_decided_fields(client, cast):
    oid = _draft(client, cast, category="commercial")
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=cast["h_bd"])
    client.post(f"/api/v1/opportunities/{oid}/decision", headers=cast["h_owner"], json={"decision": "approved"})
    resp = client.patch(
        f"/api/v1/opportunities/{oid}", headers=cast["h_bd"], json={"title": "عنوان آخر"}
    )
    assert resp.status_code == 409, resp.text


def test_chosen_opportunities_come_back_for_comparison(client, cast):
    first = _draft(client, cast, title="أولى", investment_amount="100000.00")
    second = _draft(client, cast, title="ثانية", investment_amount="200000.00")
    rows = client.get(
        "/api/v1/opportunities/compare", headers=cast["h_bd"],
        params={"ids": f"{first},{second}"},
    )
    assert rows.status_code == 200, rows.text
    assert [r["id"] for r in rows.json()] == sorted([first, second])


def test_comparison_does_not_reach_another_company(client, cast):
    """The same isolation the list enforces applies to the comparison."""
    mine = _draft(client, cast)
    foreign = client.post(
        "/api/v1/opportunities", headers=cast["h_owner"],
        json={"title": "خارج النطاق", "company_id": cast["other"], "country": "البحرين"},
    ).json()["id"]
    rows = client.get(
        "/api/v1/opportunities/compare", headers=cast["h_bd"],
        params={"ids": f"{mine},{foreign}"},
    )
    assert [r["id"] for r in rows.json()] == [mine]


def test_comparison_refuses_a_malformed_id_list(client, cast):
    resp = client.get(
        "/api/v1/opportunities/compare", headers=cast["h_bd"], params={"ids": "1,abc"}
    )
    assert resp.status_code == 422, resp.text


def test_a_business_developer_cannot_decide_or_read_another_company(client, cast):
    oid = _draft(client, cast)
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=cast["h_bd"])
    assert client.post(
        f"/api/v1/opportunities/{oid}/decision", headers=cast["h_bd"], json={"decision": "approved"}
    ).status_code == 403
    foreign = client.post(
        "/api/v1/opportunities", headers=cast["h_owner"],
        json={"title": "خارج النطاق", "company_id": cast["other"], "country": "البحرين"},
    ).json()["id"]
    assert client.patch(
        f"/api/v1/opportunities/{foreign}", headers=cast["h_bd"], json={"category": "commercial"}
    ).status_code == 404


def test_every_change_is_written_to_the_audit_log(client, cast):
    oid = _draft(client, cast)
    client.patch(f"/api/v1/opportunities/{oid}", headers=cast["h_bd"], json={"risk_level": "low"})
    client.post(f"/api/v1/opportunities/{oid}/submit", headers=cast["h_bd"])
    client.post(f"/api/v1/opportunities/{oid}/decision", headers=cast["h_owner"], json={"decision": "approved"})
    actions = [r["action"] for r in client.get("/api/v1/audit", headers=cast["h_owner"]).json()]
    assert "opportunity.update" in actions
    assert "opportunity.submit" in actions
    assert "opportunity.decision" in actions
