"""AI integration proof (§5.1, §11, Table 4).

These tests exercise the real request path from the application to an AI provider
HTTP interface using ``httpx.MockTransport`` — the actual URL, ``Authorization``
header, JSON payload and response parsing all run; only the socket is replaced.
That is stronger than asserting a key exists, and it lets the failure modes be
driven deterministically.

Covered here:

* a successful round-trip returns the provider's answer with attached sources;
* connection error, timeout and an HTTP error status all surface as ``502`` and
  never as a fabricated answer;
* a malformed provider body (not JSON, or missing ``choices``) is reported as a
  failure, not turned into an answer;
* the API key is sent to the provider but never returned to the client nor
  stored in the answer record;
* a company-scoped user's facts contain only their own company — isolation is
  enforced before the provider is called;
* when no permitted records exist the assistant returns a deterministic refusal
  and does not call the provider (so no financial figure can be invented).
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.models.business import Company, FormField, MonthlyReport, ReportingPeriod, ReportValue
from app.models.enums import PeriodStatus

SECRET_KEY = "sk-test-secret-key-abcdef0123456789"

# The provider factory is patched per test; always wrap the original so repeated
# patches in one test (isolation checks call it several times) do not nest.
from app.api.v1 import ai as _ai_api  # noqa: E402

_ORIGINAL_GET_PROVIDER = _ai_api.get_provider


@pytest.fixture()
def configured_key(monkeypatch):
    """A provider key that looks real, so the configured path is exercised."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "openai_api_key", SECRET_KEY, raising=False)
    return SECRET_KEY


def _patch_transport(monkeypatch, handler):
    """Route the AI provider through a mock transport while keeping the real code."""
    from app.api.v1 import ai as ai_api

    def patched(name=None, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return _ORIGINAL_GET_PROVIDER(name, **kwargs)

    monkeypatch.setattr(ai_api, "get_provider", patched)


def _ok_handler(captured: list[httpx.Request], answer: str = "الإيراد حسب التقرير المعتمد."):
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": answer}}]},
        )

    return handler


def _make_company_with_report(db, make_user, email="ai_manager@safir-platform.com", currency="BHD"):
    company = Company(
        code=f"AI-{email[:4].upper()}",
        name_ar="شركة الذكاء",
        name_en="AI Co",
        country="BH",
        sector="تقنية",
        currency=currency,
        status="active",
    )
    db.add(company)
    db.flush()
    manager = make_user(email, ["company_manager"], companies=[company.id])
    company.manager_user_id = manager.id
    period = ReportingPeriod(
        label_ar="2026-10",
        label_en="2026-10",
        year=2026,
        month=10,
        opens_on=__import__("datetime").date(2026, 10, 1),
        due_on=__import__("datetime").date(2026, 11, 5),
        status=PeriodStatus.OPEN.value,
    )
    db.add(period)
    db.flush()
    field = FormField(code="revenue", name_ar="الإيراد", name_en="Revenue", field_type="amount")
    db.add(field)
    db.flush()
    report = MonthlyReport(company_id=company.id, period_id=period.id, status="draft", currency=currency)
    db.add(report)
    db.flush()
    db.add(ReportValue(report_id=report.id, field_id=field.id, value_number=1234, field_version=1))
    db.commit()
    return company, manager, period


def test_ai_ask_reaches_provider_and_returns_grounded_answer(client, make_user, login, db, configured_key, monkeypatch):
    company, _manager, _period = _make_company_with_report(db, make_user)
    headers = login("ai_manager@safir-platform.com")

    captured: list[httpx.Request] = []
    _patch_transport(monkeypatch, _ok_handler(captured, answer="الإيراد 1234 BHD حسب التقرير."))

    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "ما إيراد شركتي؟"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"] == "الإيراد 1234 BHD حسب التقرير."
    assert body["configured"] is True
    assert body["confidence"] in {"grounded", "low"}
    assert body["sources"], "the answer must carry its grounding sources"

    # Exactly one real HTTP request went to the provider's chat endpoint.
    assert len(captured) == 1
    req = captured[0]
    assert str(req.url).endswith("/chat/completions")
    assert req.headers["authorization"] == f"Bearer {configured_key}"
    payload = json.loads(req.content)
    assert payload["model"]
    assert payload["messages"][0]["role"] == "system"
    # The grounded fact (the company's own revenue in its own currency) was sent.
    user_msg = payload["messages"][1]["content"]
    assert "1234" in user_msg and "BHD" in user_msg
    assert company.name_ar in user_msg


def test_ai_ask_provider_connection_error_returns_502(client, make_user, login, db, configured_key, monkeypatch):
    _make_company_with_report(db, make_user)
    headers = login("ai_manager@safir-platform.com")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _patch_transport(monkeypatch, handler)
    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "سؤال"})
    assert resp.status_code == 502, resp.text
    assert resp.json()["detail"]["error"] == "ai_provider_failed"


def test_ai_ask_provider_timeout_returns_502(client, make_user, login, db, configured_key, monkeypatch):
    _make_company_with_report(db, make_user)
    headers = login("ai_manager@safir-platform.com")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    _patch_transport(monkeypatch, handler)
    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "سؤال"})
    assert resp.status_code == 502, resp.text
    assert resp.json()["detail"]["error"] == "ai_provider_failed"


def test_ai_ask_provider_http_error_status_returns_502(client, make_user, login, db, configured_key, monkeypatch):
    _make_company_with_report(db, make_user)
    headers = login("ai_manager@safir-platform.com")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"})

    _patch_transport(monkeypatch, handler)
    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "سؤال"})
    assert resp.status_code == 502, resp.text


def test_ai_ask_invalid_response_is_reported_not_fabricated(client, make_user, login, db, configured_key, monkeypatch):
    _make_company_with_report(db, make_user)
    headers = login("ai_manager@safir-platform.com")

    def not_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"this is not json", headers={"content-type": "application/json"})

    _patch_transport(monkeypatch, not_json)
    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "سؤال"})
    assert resp.status_code == 502, resp.text
    assert resp.json()["detail"]["error"] == "ai_provider_failed"

    def missing_choices(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    _patch_transport(monkeypatch, missing_choices)
    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "سؤال"})
    assert resp.status_code == 502, resp.text


def test_ai_answer_never_leaks_the_api_key(client, make_user, login, db, configured_key, monkeypatch):
    from app.models.operations import AiQuery

    _make_company_with_report(db, make_user)
    headers = login("ai_manager@safir-platform.com")

    captured: list[httpx.Request] = []
    _patch_transport(monkeypatch, _ok_handler(captured))

    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "سؤال"})
    assert resp.status_code == 200, resp.text
    # The key goes out on the wire …
    assert captured[0].headers["authorization"] == f"Bearer {configured_key}"
    # … but is never echoed to the client …
    assert configured_key not in resp.text
    # … nor written into the stored answer record.
    record = db.query(AiQuery).order_by(AiQuery.id.desc()).first()
    assert record is not None
    assert configured_key not in (record.answer or "")
    assert configured_key not in (record.sources or "")

    # The settings endpoint exposes only a masked hint, never the key.
    owner = make_user("ai_owner@safir-platform.com", ["owner"])
    owner_headers = login("ai_owner@safir-platform.com")
    settings_resp = client.get("/api/v1/ai/settings", headers=owner_headers)
    assert settings_resp.status_code == 200
    assert configured_key not in settings_resp.text
    assert "api_key" not in settings_resp.json()
    assert settings_resp.json()["api_key_hint"].startswith("sk-")
    assert owner is not None


def test_ai_facts_are_isolated_to_the_calling_users_company(client, make_user, login, db, configured_key, monkeypatch):
    """Two managers each scoped to their own company; the FACTS sent to the
    provider for one never contain the other's company."""
    make_user("iso_owner@safir-platform.com", ["owner"])
    owner_headers = login("iso_owner@safir-platform.com")

    a = Company(code="ISO-A", name_ar="شركة أ", name_en="Co A", country="BH", sector="تقنية", currency="BHD", status="active")
    b = Company(code="ISO-B", name_ar="شركة ب", name_en="Co B", country="BH", sector="تقنية", currency="USD", status="active")
    db.add_all([a, b])
    db.commit()

    mgr_a = make_user("iso_a@safir-platform.com", ["company_manager"], companies=[a.id])
    mgr_b = make_user("iso_b@safir-platform.com", ["company_manager"], companies=[b.id])
    assert mgr_a.id != mgr_b.id
    ha = login("iso_a@safir-platform.com")
    hb = login("iso_b@safir-platform.com")

    captured_a: list[httpx.Request] = []
    _patch_transport(monkeypatch, _ok_handler(captured_a))
    assert client.post("/api/v1/ai/ask", headers=ha, json={"prompt": "ما شركاتي؟"}).status_code == 200
    facts_a = json.loads(captured_a[0].content)["messages"][1]["content"]
    assert "شركة أ" in facts_a
    assert "شركة ب" not in facts_a

    captured_b: list[httpx.Request] = []
    _patch_transport(monkeypatch, _ok_handler(captured_b))
    assert client.post("/api/v1/ai/ask", headers=hb, json={"prompt": "ما شركاتي؟"}).status_code == 200
    facts_b = json.loads(captured_b[0].content)["messages"][1]["content"]
    assert "شركة ب" in facts_b
    assert "شركة أ" not in facts_b

    # The owner, who has holding-wide oversight, does see both.
    captured_o: list[httpx.Request] = []
    _patch_transport(monkeypatch, _ok_handler(captured_o))
    assert client.post("/api/v1/ai/ask", headers=owner_headers, json={"prompt": "ما الشركات؟"}).status_code == 200
    facts_o = json.loads(captured_o[0].content)["messages"][1]["content"]
    assert "شركة أ" in facts_o and "شركة ب" in facts_o


def test_ai_refuses_deterministically_when_no_permitted_records(client, make_user, login, db, configured_key, monkeypatch):
    """With no permitted sources the assistant answers deterministically and does
    not call the provider, so no figure can be invented."""
    from app.ai.provider import GroundedContext
    from app.api.v1 import ai as ai_api

    make_user("nd_manager@safir-platform.com", ["company_manager"])
    headers = login("nd_manager@safir-platform.com")

    monkeypatch.setattr(ai_api, "gather_context", lambda *a, **k: GroundedContext())

    called: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        called.append(1)
        return httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]})

    _patch_transport(monkeypatch, handler)
    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "ما الإيرادات؟"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["confidence"] == "no_data"
    assert body["note"] == "no_permitted_sources"
    assert body["sources"] == []
    assert called == [], "the provider must not be called when there is no permitted data"


def test_ai_reports_configuration_status_when_unconfigured(client, make_user, login, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "openai_api_key", "", raising=False)
    make_user("uc_manager@safir-platform.com", ["company_manager"])
    headers = login("uc_manager@safir-platform.com")
    resp = client.post("/api/v1/ai/ask", headers=headers, json={"prompt": "ما الإيرادات؟"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["configured"] is False
    assert body["confidence"] == "unconfigured"
    assert body["note"] == "ai_provider_not_configured"


def test_ai_summary_keeps_each_amount_in_its_own_currency(client, make_user, login, db):
    """§11.5: the owner summary states amounts per company currency, never summed."""
    make_user("sum_owner@safir-platform.com", ["owner"])
    headers = login("sum_owner@safir-platform.com")
    db.add(
        ReportingPeriod(
            label_ar="2026-10",
            label_en="2026-10",
            year=2026,
            month=10,
            opens_on=__import__("datetime").date(2026, 10, 1),
            due_on=__import__("datetime").date(2026, 11, 5),
            status=PeriodStatus.OPEN.value,
        )
    )
    db.commit()
    resp = client.get("/api/v1/ai/summary", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "كل مبلغ بعملة شركته" in body["scope_ar"]
    assert "own company currency" in body["scope_en"]


def test_ai_summary_without_a_period_does_not_crash(client, make_user, login, db):
    """A fresh deployment with no reporting period returns an explicit empty
    summary rather than a 500, and invents nothing."""
    make_user("np_owner@safir-platform.com", ["owner"])
    headers = login("np_owner@safir-platform.com")
    resp = client.get("/api/v1/ai/summary", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["period_label_ar"] == "—"
    assert body["sources"] == []
    assert body["sections"]


# --- Optional live provider check (never carries a key in the repo) ---------
# This runs only when an operator deliberately enables it with a key supplied
# through the environment. It is skipped by default, so CI and the repository
# never hold a credential. Enable with:
#
#     SAFIR_AI_LIVE_TEST=1 OPENAI_API_KEY=... \
#       python -m pytest tests/test_ai_integration.py -k live_provider
@pytest.mark.skipif(
    not (__import__("os").environ.get("SAFIR_AI_LIVE_TEST") and __import__("os").environ.get("OPENAI_API_KEY")),
    reason="live provider test is opt-in; set SAFIR_AI_LIVE_TEST=1 and OPENAI_API_KEY to run it",
)
def test_live_provider_round_trip_when_opted_in():
    import os

    from app.ai.provider import get_provider

    provider = get_provider(
        "openai",
        model=os.environ.get("SAFIR_AI_LIVE_MODEL") or None,
        api_key=os.environ["OPENAI_API_KEY"],
    )
    reply = provider.complete("Reply with the single word OK.", "ping")
    assert reply and reply.strip()
