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
        gates.update(re.findall(r'can\(\s*"([^"]+)"', path.read_text(encoding="utf-8")))
    assert gates, "no can() gates found; the scan is broken"
    assert gates <= set(ALL_PERMISSIONS), f"not in the catalog: {sorted(gates - set(ALL_PERMISSIONS))}"


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
