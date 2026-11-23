"""Exercise the dashboard workflow on the submissions the public forms create.

The public sweep proves a visitor's form reaches the database. This proves the
staff side can then work the row: move it through the status workflow, convert
it into a lead / opportunity / service request, and reject it — with the audit
trail recording each move.

    python3 scripts/check_dashboard_flow.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

import psycopg

API = "http://127.0.0.1:8000/api/v1"
OWNER = ("owner@safir-platform.com", "Safir!2026")

results: list[tuple[str, str, bool, str]] = []


def _call(method: str, path: str, body=None, token: str = "") -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:200]


def _post_multipart(email: str, kind: str, extra: dict) -> tuple[int, object]:
    """Submit with an attachment, the way the careers form sends a CV."""
    boundary = "----flowcheckboundary"
    fields = {"kind": kind, "name": "فحص اللوحة", "email": email, "phone": "39000000",
              "consent": "true", **extra}
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="attachment"; '
        f'filename="cv.txt"\r\nContent-Type: text/plain\r\n\r\n'
        f"CV for the flow check\r\n".encode()
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        f"{API}/public/submissions/with-file",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:200]


def _check(label: str, method: str, path: str, body, token: str, expect=(200, 201)) -> object:
    code, payload = _call(method, path, body, token)
    ok = code in expect
    results.append((label, f"{method} {path}", ok, f"HTTP {code}" if ok else f"HTTP {code} {payload}"))
    return payload if ok else None


def _clear_previous_runs() -> None:
    """Drop rows this checker created earlier so the hourly IP cap never blocks it.

    Opt-in via CHECKER_DB_URL: the default run touches nothing but the API.
    """
    dsn = os.environ.get("CHECKER_DB_URL")
    if not dsn:
        return
    with psycopg.connect(dsn) as conn:
        conn.execute("DELETE FROM website_submissions WHERE email LIKE 'flow-%@example.com'")


def main() -> int:
    code, auth = _call("POST", "/auth/login", {"email": OWNER[0], "password": OWNER[1]})
    if code != 200:
        print(f"login failed: HTTP {code}")
        return 1
    token = auth["access_token"]

    _clear_previous_runs()

    # Fresh rows every run, so the checker is repeatable and never re-uses a
    # submission an earlier run already converted.
    marker = f"flow-{int(time.time())}@example.com"
    created: dict[str, dict] = {}
    for kind, extra in (
        ("service_request", {"service_type": "الاستشارات", "message": "فحص مسار لوحة التحكم"}),
        ("opportunity", {"country": "البحرين", "subject": "فرصة فحص",
                         "message": "فحص مسار لوحة التحكم"}),
        ("job_application", {"expertise": "إدارة", "message": "فحص مسار لوحة التحكم"}),
    ):
        # A job application is rejected without a CV, so it goes through the
        # multipart endpoint the public careers form uses.
        if kind == "job_application":
            code, row = _post_multipart(marker, kind, extra)
        else:
            code, row = _call("POST", "/public/submissions",
                              {"kind": kind, "name": "فحص اللوحة", "email": marker,
                               "phone": "39000000", "consent": True, **extra})
        results.append((f"public form creates {kind}", "POST /public/submissions", code == 201,
                        f"HTTP {code}"))
        if code == 201:
            created[kind] = row

    subs = _call("GET", "/website/submissions", token=token)[1]
    sweep = {s["kind"]: s for s in subs if s["email"] == marker}
    if not sweep:
        print("the staff inbox does not show the rows the public form just created")
        return 1

    # 1. The inbox lists every kind the public site can produce.
    for kind in ("service_request", "opportunity", "job_application"):
        results.append((f"inbox lists {kind}", "GET /website/submissions", kind in sweep,
                        "present" if kind in sweep else "missing"))
    results.append(("inbox shows a reference number", "GET /website/submissions",
                    all(s.get("reference_no") for s in sweep.values()),
                    ", ".join(s.get("reference_no") or "-" for s in sweep.values())))

    # 2. Status workflow: new -> in_review -> contacted, each recorded in history.
    sr = sweep["service_request"]
    _check("move to in_review", "PATCH", f"/website/submissions/{sr['id']}", {"status": "in_review"}, token)
    _check("move to needs_followup", "PATCH", f"/website/submissions/{sr['id']}",
           {"status": "needs_followup"}, token)
    history = _call("GET", f"/website/submissions/{sr['id']}/history", token=token)[1] or []
    moved = {h.get("to_status") for h in history}
    results.append(("history records the moves", "GET .../history",
                    {"in_review", "needs_followup"} <= moved, f"statuses: {sorted(moved)}"))

    # 3. A converted service request becomes a routed request the group can work.
    companies = _call("GET", "/companies?include_holding=true", token=token)[1] or []
    company_id = companies[0]["id"] if companies else None
    results.append(("a company can receive the request", "GET /companies", company_id is not None,
                    f"company_id={company_id}"))
    converted = _check("convert service request", "POST", f"/website/submissions/{sr['id']}/convert",
                       {"target": "service_request", "company_id": company_id}, token)
    if converted:
        results.append(("submission marked converted", "POST .../convert",
                        converted.get("status") == "converted", f"status={converted.get('status')}"))

    # 4. An opportunity converts into a draft opportunity record.
    op = sweep["opportunity"]
    conv_op = _check("convert opportunity", "POST", f"/website/submissions/{op['id']}/convert",
                     {"target": "opportunity"}, token)
    if conv_op:
        results.append(("opportunity converted", "POST .../convert",
                        conv_op.get("status") == "converted", f"status={conv_op.get('status')}"))

    # 5. Rejection is a first-class outcome with a reason, not a silent delete.
    ja = sweep["job_application"]
    rej = _check("reject application", "POST", f"/website/submissions/{ja['id']}/reject", None, token)
    if rej:
        results.append(("rejection recorded", "POST .../reject",
                        rej.get("status") == "rejected", f"status={rej.get('status')}"))

    # 6. The audit log carries the staff actions.
    audit = _call("GET", "/audit?limit=100", token=token)[1]
    rows = audit if isinstance(audit, list) else (audit or {}).get("items", [])
    actions = {r.get("action") for r in rows}
    results.append(("audit log written", "GET /audit",
                    any("website" in (a or "") for a in actions),
                    f"{sum('website' in (a or '') for a in actions)} website entries"))

    bad = [r for r in results if not r[2]]
    for label, path, ok, detail in results:
        print(f"{'ok  ' if ok else 'FAIL'} {label:32s} {detail}")
    print(f"\n{len(results)} checks: {len(results)-len(bad)} ok, {len(bad)} failing")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
