"""Authentication, RBAC and company-isolation tests."""

from __future__ import annotations

import re
from pathlib import Path

from app.core.permissions import ALL_PERMISSIONS, ROLE_TEMPLATES
from app.models.identity import User


def test_login_and_me(client, make_user, login):
    make_user("owner1@safir-platform.com", ["owner"])
    headers = login("owner1@safir-platform.com")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert "owner" in body["roles"]
    assert "company:manage" in body["permissions"]


def test_login_rejects_bad_password(client, make_user):
    make_user("owner2@safir-platform.com", ["owner"])
    resp = client.post("/api/v1/auth/login", json={"email": "owner2@safir-platform.com", "password": "wrong"})
    assert resp.status_code == 401


def test_unauthenticated_is_401(client):
    assert client.get("/api/v1/companies").status_code == 401


def test_permission_enforced_on_backend(client, make_user, login):
    # A designer lacks user:manage; hiding the button is not the enforcement.
    make_user("designer1@safir-platform.com", ["designer"])
    headers = login("designer1@safir-platform.com")
    resp = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "x@safir-platform.com",
            "full_name_ar": "x",
            "full_name_en": "x",
            "role_slugs": ["designer"],
        },
    )
    assert resp.status_code == 403
    assert "missing_permissions" in resp.json()["detail"]


def test_company_isolation_returns_404_not_403(client, make_user, login, db):
    owner = make_user("owner3@safir-platform.com", ["owner"])
    manager = make_user("manager3@safir-platform.com", ["company_manager"])
    headers_owner = login("owner3@safir-platform.com")
    created = client.post(
        "/api/v1/companies",
        headers=headers_owner,
        json={
            "code": "C-ISO-1",
            "name_ar": "شركة معزولة",
            "name_en": "Isolated Co",
            "country": "SA",
            "sector": "tech",
        },
    )
    assert created.status_code == 201, created.text
    cid = created.json()["id"]

    # Manager has no grant for this company.
    headers_manager = login("manager3@safir-platform.com")
    resp = client.get(f"/api/v1/companies/{cid}", headers=headers_manager)
    assert resp.status_code == 404


def test_owner_can_access_all_companies(client, make_user, login):
    make_user("owner4@safir-platform.com", ["owner"])
    headers = login("owner4@safir-platform.com")
    created = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"code": "C-OWN-1", "name_ar": "أ", "name_en": "A", "country": "SA", "sector": "tech"},
    )
    assert created.status_code == 201
    assert client.get(f"/api/v1/companies/{created.json()['id']}", headers=headers).status_code == 200


def test_password_reset_single_use(client, make_user, db):
    make_user("reset@safir-platform.com", ["owner"])
    issued = client.post("/api/v1/auth/password-reset/request", json={"email": "reset@safir-platform.com"})
    token = issued.json()["reset_token"]
    assert token
    first = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "NewPassw0rd!"})
    assert first.status_code == 204
    second = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "Another1!"})
    assert second.status_code == 400
    assert client.post("/api/v1/auth/login", json={"email": "reset@safir-platform.com", "password": "NewPassw0rd!"}).status_code == 200


def test_password_reset_does_not_enumerate(client):
    resp = client.post("/api/v1/auth/password-reset/request", json={"email": "nobody@safir-platform.com"})
    assert resp.status_code == 200
    assert resp.json()["reset_token"] is None


def test_password_reset_never_hands_the_token_to_the_caller(client, make_user, monkeypatch):
    """An anonymous caller must not receive a reset token.

    Returning it would let anyone who knows an email address set that account's
    password — a full takeover of, say, the owner. The echo is off by default and
    only an explicit opt-in for local testing turns it on.
    """
    from app.core.config import settings

    make_user("victim@safir-platform.com", ["owner"])
    monkeypatch.setattr(settings, "expose_reset_token", False)
    issued = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "victim@safir-platform.com"}
    )
    assert issued.status_code == 200
    assert issued.json()["reset_token"] is None
    # And the account still logs in with its original password.
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "victim@safir-platform.com", "password": "Passw0rd!"},
    ).status_code == 200


def test_every_permission_checked_in_code_is_in_the_catalog():
    """A permission string that no role can hold silently disables its feature.

    This is the bug that hid the accountant's Excel export (``report:export``)
    and four owner controls: the backend required a name that
    ``ALL_PERMISSIONS`` never contained, so the check could only ever 403.
    """
    repo = Path(__file__).resolve().parents[1]
    pattern = re.compile(r'require(?:_any)?\(([^)]*)\)')
    used: set[str] = set()
    for path in list((repo / "app").rglob("*.py")):
        for call in pattern.findall(path.read_text(encoding="utf-8")):
            used.update(re.findall(r'"([a-z_]+:[a-z_]+)"', call))
    assert used, "no require() permission strings found; the scan is broken"
    assert used <= set(ALL_PERMISSIONS), f"not in the catalog: {sorted(used - set(ALL_PERMISSIONS))}"


def test_frontend_permission_gates_are_names_the_backend_can_grant():
    """Every ``can("...")`` in the UI must be a permission the backend defines.

    Otherwise the control never renders — the user loses the feature and no
    error is raised anywhere.
    """
    repo = Path(__file__).resolve().parents[2]
    frontend = repo / "frontend"
    gates: set[str] = set()
    for path in list(frontend.rglob("*.tsx")) + list(frontend.rglob("*.ts")):
        if ".next" in path.parts or "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        gates.update(re.findall(r'can\(\s*"([^"]+)"', text))
        # Sidebar entries gate on a list of permissions (any-of), e.g.
        # ``permissions: ["report:view_own", "report:view_all"]``.
        for group in re.findall(r"permissions:\s*\[([^\]]*)\]", text):
            gates.update(re.findall(r'"([^"]+)"', group))
    assert gates, "no can() gates found; the scan is broken"
    assert gates <= set(ALL_PERMISSIONS), f"not in the catalog: {sorted(gates - set(ALL_PERMISSIONS))}"


def test_the_directory_serves_pickers_without_the_admin_listing(client, make_user, login):
    """The recipient and assignee pickers on pages 10, 11 and 13 need to name a
    colleague, but their roles (marketer, designer, advisor) hold no ``user:view``,
    so ``/users`` answered 403 and every picker rendered empty. The directory
    answers with a minimal identity and no privileged fields.
    """
    make_user("dir_marketer@safir-platform.com", ["marketer"])

    marketer = login("dir_marketer@safir-platform.com")
    assert client.get("/api/v1/users", headers=marketer).status_code == 403

    directory = client.get("/api/v1/users/directory", headers=marketer)
    assert directory.status_code == 200, directory.text
    assert directory.json(), "the directory must not be empty"
    assert set(directory.json()[0]) == {"id", "full_name_ar", "full_name_en"}

    # An advisor, who only submits recommendations, also needs recipients.
    make_user("dir_advisor@safir-platform.com", ["advisor"])
    advisor = login("dir_advisor@safir-platform.com")
    assert client.get("/api/v1/users/directory", headers=advisor).status_code == 200


def test_the_accountant_may_export_a_report(client, make_user, login):
    """The accountant validates reports and exports Excel (design page 25)."""
    accountant = make_user("acct-export@safir-platform.com", ["accountant"])
    assert "report:export" in ROLE_TEMPLATES["accountant"]["permissions"]
    headers = login(accountant.email)
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert "report:export" in me["permissions"]
    # A designer, who has no reporting duties, must not be able to export.
    make_user("designer-export@safir-platform.com", ["designer"])
    other = client.get("/api/v1/reports/1/export", headers=login("designer-export@safir-platform.com"))
    assert other.status_code == 403


def test_the_owner_may_manage_companies_but_not_review_or_forward_reports():
    """Owner oversight is broad, yet review/forward stay with the accountant."""
    owner = set(ROLE_TEMPLATES["owner"]["permissions"])
    assert "company:manage" in owner
    assert "report:review" not in owner and "report:forward" not in owner


def test_the_owner_views_accounting_hr_and_advisor_without_editing():
    """§5.1 names three owner screens «عرض فقط» (view only): Holding accounting,
    Employees & HR and the External advisor.

    The owner must hold the matching view permissions and never the write ones:
    §5.3 makes the accountant the only financial editor, employees are added by
    the manager and the business developer (§5.2, §5.4), and only the advisor
    composes advisor messages (§5.7).
    """
    owner = set(ROLE_TEMPLATES["owner"]["permissions"])
    assert {"accounting:view", "hr:view", "advisor:view"} <= owner
    assert owner.isdisjoint({"accounting:manage", "hr:manage", "advisor:submit"})


def test_owner_write_attempts_on_view_only_screens_are_refused(client, make_user, login):
    """The three view-only owner screens must refuse a write on the server, not
    merely hide the control in the interface (§11)."""
    make_user("vo_owner@safir-platform.com", ["owner"])
    h = login("vo_owner@safir-platform.com")
    # The owner may still manage companies, so it can set up the target.
    cid = client.post(
        "/api/v1/companies",
        headers=h,
        json={"code": "VO-1", "name_ar": "شركة VO-1", "name_en": "Co VO-1", "country": "SA", "sector": "tech", "status": "active"},
    ).json()["id"]

    entry = client.post(
        "/api/v1/accounting",
        headers=h,
        json={"kind": "expense", "company_id": cid, "reference": "VO-EXP", "description": "x", "amount": "1.00", "currency": "BHD", "entry_date": "2026-01-01"},
    )
    assert entry.status_code == 403, entry.text

    employee = client.post(
        "/api/v1/employees",
        headers=h,
        json={"name_ar": "موظف", "name_en": "Staff", "job_title": "محلل", "company_id": cid},
    )
    assert employee.status_code == 403, employee.text

    advisor = client.post(
        "/api/v1/advisor/messages",
        headers=h,
        json={"recipient_id": 1, "category": "suggestion", "subject": "s", "body": "b"},
    )
    assert advisor.status_code == 403, advisor.text


# --- Table 1 of the brief: which tab each of the eight roles sees -----------
# The grid is written out in full so a future edit to a permission template or
# to a sidebar gate that changes who sees which tab fails here, loudly.
TAB_MATRIX: dict[str, dict[str, bool]] = {
    "owner":             {"companies": True,  "reports": True,  "accounting": True,  "service-requests": True,  "leads": True,  "opportunities": True,  "directives": True,  "hr": True,  "website": True,  "advisor": True,  "assistant": True,  "form-builder": True,  "users": True,  "audit": True},
    "company_manager":   {"companies": False, "reports": True,  "accounting": False, "service-requests": True,  "leads": True,  "opportunities": False, "directives": True,  "hr": True,  "website": False, "advisor": False, "assistant": True,  "form-builder": False, "users": False, "audit": False},
    "accountant":        {"companies": False, "reports": True,  "accounting": True,  "service-requests": True,  "leads": False, "opportunities": False, "directives": True,  "hr": False, "website": False, "advisor": False, "assistant": False, "form-builder": True,  "users": False, "audit": False},
    "business_developer":{"companies": False, "reports": True,  "accounting": True,  "service-requests": True,  "leads": True,  "opportunities": True,  "directives": True,  "hr": True,  "website": True,  "advisor": True,  "assistant": False, "form-builder": False, "users": False, "audit": False},
    "marketer":          {"companies": False, "reports": False, "accounting": False, "service-requests": False, "leads": True,  "opportunities": False, "directives": True,  "hr": False, "website": False, "advisor": False, "assistant": False, "form-builder": False, "users": False, "audit": False},
    "designer":          {"companies": False, "reports": False, "accounting": False, "service-requests": True,  "leads": False, "opportunities": False, "directives": True,  "hr": False, "website": False, "advisor": False, "assistant": False, "form-builder": False, "users": False, "audit": False},
    "advisor":           {"companies": False, "reports": False, "accounting": False, "service-requests": False, "leads": False, "opportunities": False, "directives": False, "hr": False, "website": False, "advisor": True,  "assistant": False, "form-builder": False, "users": False, "audit": False},
}


def _sidebar_gates() -> dict[str, list[str]]:
    """The sidebar's tab -> permission(s) map, parsed from AppShell.tsx.

    Reading the real source keeps the test honest: it checks the shipped gates,
    not a copy that could drift from them.
    """
    repo = Path(__file__).resolve().parents[2]
    text = (repo / "frontend" / "components" / "AppShell.tsx").read_text(encoding="utf-8")
    gates: dict[str, list[str]] = {}
    for href, group in re.findall(
        r'href:\s*"([^"]+)"[^}]*permissions:\s*\[([^\]]*)\]', text
    ):
        gates[href.replace("/platform/", "")] = re.findall(r'"([^"]+)"', group)
    return gates


def test_sidebar_gates_match_the_brief_role_matrix():
    gates = _sidebar_gates()
    assert set(TAB_MATRIX["owner"]) <= set(gates), (
        f"the sidebar is missing tabs: {sorted(set(TAB_MATRIX['owner']) - set(gates))}"
    )
    for role, expected in TAB_MATRIX.items():
        held = set(ROLE_TEMPLATES[role]["permissions"])
        for tab, should_see in expected.items():
            tab_gate = gates[tab]
            sees = (not tab_gate) or bool(set(tab_gate) & held)
            assert sees is should_see, (
                f"{role} {'should' if should_see else 'must not'} see the {tab} tab "
                f"(gate={tab_gate}, held={sorted(set(tab_gate) & held)})"
            )


def test_the_eight_brief_roles_all_exist():
    """Table 1 names eight personas; the catalog must define each one."""
    expected = {
        "owner", "company_manager", "accountant", "business_developer",
        "marketer", "designer", "advisor",
    }
    assert expected <= set(ROLE_TEMPLATES)
    # There is deliberately no employee login role: employees are records only.
    assert "employee" not in ROLE_TEMPLATES


def test_account_emails_carry_a_brief_secure_link_and_no_financial_detail():
    """Reference page 32: «تصميم رسائل البريد — نص موجز ورابط آمن، بلا تفاصيل مالية».

    Both account messages must carry exactly one absolute link to a route the
    frontend actually serves, and neither may mention a currency, an amount or a
    report value.
    """
    from app.services import mail

    reset = mail.password_reset_email("ar", "tok-123")
    invite = mail.invitation_email("en", "tok-456", "accountant")

    for content in (reset, invite):
        links = re.findall(r"https?://\S+", content.body)
        assert len(links) == 1, f"expected one link, got {links}"
        # The link must point at the password screen the app really serves.
        assert "/reset-password?token=" in links[0], links[0]
        assert not re.search(r"[$€£]|\bSAR\b|\bUSD\b|\d+\.\d{2}\b", content.body)

    # The two messages are the two languages, not one reused body.
    assert "إعادة تعيين كلمة المرور" in reset.subject
    assert "reset" not in reset.subject.lower() or "كلمة" in reset.subject
    assert "set up your account" in invite.subject
    assert "no password is ever sent by email" in invite.body


def test_invitation_returns_a_link_the_frontend_serves(client, make_user, login):
    """The invitation used to hand back ``/{locale}/set-password``, a route that
    does not exist, so every invited user met a 404. The link must resolve to the
    real password screen.
    """
    make_user("owner-invite@safir-platform.com", ["owner"])
    owner = login("owner-invite@safir-platform.com")
    resp = client.post(
        "/api/v1/users",
        headers=owner,
        json={
            "email": "invited-setup@safir-platform.com",
            "full_name_ar": "مدعو",
            "full_name_en": "Invited",
            "locale": "ar",
            "role_slugs": ["designer"],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["setup_url"].startswith("/reset-password?token="), body["setup_url"]
    # The token in the URL is the one the confirm endpoint accepts.
    token = body["setup_url"].split("token=", 1)[1]
    assert token == body["setup_token"]
    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "Invited!2026"},
    )
    assert confirm.status_code == 204, confirm.text


def test_mail_is_reported_as_unconfigured_rather_than_pretending_to_send(monkeypatch):
    """With no SMTP host the sender must answer False, so the caller tells the
    user the link is delivered out-of-band instead of claiming a message.
    """
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "smtp_host", "", raising=False)
    assert settings.mail_configured is False
    assert mail.send("someone@safir-platform.com", mail.password_reset_email("ar", "t")) is False


def test_mail_delivery_failure_does_not_raise(monkeypatch):
    """A mail outage must never turn an account operation into a 500."""
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "smtp_host", "smtp.invalid", raising=False)

    def boom(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(mail.smtplib, "SMTP", boom)
    assert mail.send("someone@safir-platform.com", mail.password_reset_email("ar", "t")) is False
