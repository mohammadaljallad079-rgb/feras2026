"""§11 «فتح رابط غير مصرح به يرفض ويسجل» — a permission refusal is audited."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _denials(client: TestClient, headers: dict) -> int:
    rows = client.get("/api/v1/audit", headers=headers).json()
    return sum(1 for r in rows if r["action"] == "security.access_denied")


def test_a_missing_permission_is_refused_and_written_to_the_audit_log(
    client: TestClient, make_user, login
) -> None:
    make_user("owner-x@s.com", ["owner"])
    make_user("marketer-x@s.com", ["marketer"])
    owner = login("owner-x@s.com")
    before = _denials(client, owner)

    assert client.get("/api/v1/users", headers=login("marketer-x@s.com")).status_code == 403

    assert _denials(client, owner) == before + 1


def test_the_log_names_the_permissions_that_were_missing(
    client: TestClient, make_user, login
) -> None:
    make_user("owner-y@s.com", ["owner"])
    make_user("marketer-y@s.com", ["marketer"])
    client.get("/api/v1/users", headers=login("marketer-y@s.com"))

    rows = client.get("/api/v1/audit", headers=login("owner-y@s.com")).json()
    denial = next(r for r in rows if r["action"] == "security.access_denied")
    assert "user:view" in str(denial), denial
