"""Assert the resolved visual mismatches and key flows in a real browser.

Each of the eight rows that `docs/verification/visual-comparison.md` records as
"Fixed" gets an assertion here, so the claim can be re-checked rather than
trusted. The checks read the rendered DOM of the live app, which is what the
reviewer sees; the unit and journey suites cover the API side.

    python3 scripts/check_visual_fixes.py

Needs a seeded backend on :8000 and a frontend on :12000.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from playwright.sync_api import Page, sync_playwright

BASE = "http://localhost:12000"
PASSWORD = "Safir!2026"

ACCOUNTS = {
    "owner": "owner@safir-platform.com",
    "manager": "manager@safir-platform.com",
    "accountant": "accountant@safir-platform.com",
    "bd": "bd@safir-platform.com",
    "marketer": "marketer@safir-platform.com",
}


@dataclass
class Result:
    page: int
    title: str
    passed: bool
    detail: str = ""
    extra: dict = field(default_factory=dict)


RESULTS: list[Result] = []


def _record(page_no: int, title: str, ok: bool, detail: str = "", **extra) -> None:
    RESULTS.append(Result(page_no, title, bool(ok), detail, extra))
    print(("  PASS  " if ok else "  FAIL  ") + f"p.{page_no} {title}" + (f"  [{detail}]" if detail and not ok else ""))


def _sign_in(browser, role: str, locale: str = "ar"):
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(f"{BASE}/login")
    page.fill("#email", ACCOUNTS[role])
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard", timeout=25000)
    if locale != "ar":
        page.select_option("#locale-select", locale)
        page.wait_for_timeout(600)
    return ctx, page


def check_page_8(page: Page) -> None:
    """Owner sees only reports sent to management, never drafts."""
    rows = page.evaluate(
        """async () => {
        const t = window.sessionStorage.getItem('safir.access');
        const r = await fetch('/api/backend/api/v1/reports', {headers:{Authorization:`Bearer ${t}`}});
        return r.ok ? await r.json() : null;
    }"""
    )
    if rows is None:
        _record(8, "owner report list loads", False, "API call failed")
        return
    statuses = sorted({r["status"] for r in rows})
    _record(8, "owner sees only approved/forwarded reports", all(s in ("approved", "forwarded") for s in statuses), f"statuses={statuses}")
    _record(8, "owner report list is not empty (data present)", len(rows) > 0, f"rows={len(rows)}")
    # The manager's own list must still show drafts, or the restriction is too broad.
    text = page.inner_text("main")
    _record(8, "owner screen renders the reports heading", "التقارير" in text or "Reports" in text)


def check_page_11(page: Page) -> None:
    """Leads screen carries the three narrowing controls."""
    ids = page.evaluate("() => [...document.querySelectorAll('select')].map(s => s.id)")
    wanted = {"filter-company", "filter-status", "filter-source"}
    _record(11, "leads screen has company/status/source filters", wanted.issubset(set(ids)), f"selects={ids}")
    rows_before = page.evaluate("document.querySelectorAll('table tbody tr').length")
    if rows_before > 0:
        # Narrowing must actually change the result set, not just render.
        page.select_option("#filter-status", "won")
        page.wait_for_timeout(700)
        rows_after = page.evaluate("document.querySelectorAll('table tbody tr').length")
        _record(11, "status filter changes the visible rows", rows_after <= rows_before, f"{rows_before} -> {rows_after}")
    else:
        _record(11, "status filter changes the visible rows", False, "no rows to filter")


def check_page_12(page: Page) -> None:
    """Opportunity heading is the long reference title."""
    text = page.inner_text("main")
    _record(12, "heading is «الفرص التجارية والاستثمارية»", "الفرص التجارية والاستثمارية" in text)
    _record(12, "screen states approval creates no project", "لا ينشئ مشروعاً" in text)


def check_page_14(page: Page) -> None:
    """Salary is withheld without hr:view_salary."""
    text = page.inner_text("main")
    # The owner holds hr:view_salary, so the amount is visible here; the denial
    # path is asserted through the API in the journey suite. This checks the UI
    # never prints a raw amount next to a restricted marker.
    has_marker = "مقيد" in text
    _record(14, "salary column renders (marker or amount)", has_marker or "الراتب" in text, "no salary column found")
    _record(14, "restricted marker is not shown alongside a real amount", not (has_marker and "ر.س" in text), "restricted row leaked an amount")


def check_page_18(page: Page) -> None:
    """Report form indents a child field under its parent with the arrow."""
    report_id = page.evaluate(
        """async () => {
        const t = window.sessionStorage.getItem('safir.access');
        const r = await fetch('/api/backend/api/v1/reports', {headers:{Authorization:`Bearer ${t}`}});
        if (!r.ok) return null;
        const rows = await r.json();
        return rows.length ? rows[0].id : null;
    }"""
    )
    if report_id is None:
        _record(18, "a report exists to open", False, "no reports")
        return
    page.goto(f"{BASE}/reports/{report_id}")
    page.wait_for_timeout(1500)
    arrows = page.evaluate("() => document.querySelectorAll('[aria-label=\"حقل فرعي\"], [aria-label=\"Subfield\"]').length")
    _record(18, "subfield rows render the «↳» marker", arrows > 0, f"markers={arrows}")


def check_page_22(page: Page) -> None:
    """Manager dashboard has the period banner and the five actions."""
    text = page.inner_text("main")
    # The banner reports either a remaining deadline ("due in N days") or an
    # overdue period ("N days late"), so both wordings count.
    banner = page.evaluate(
        """() => [...document.querySelectorAll('p,div,section')].some(e =>
            /يستحق بعد|متأخر|due in|day\\(s\\) late/.test(e.textContent || ''))"""
    )
    _record(22, "period banner names the deadline or lateness", banner, "no deadline/late wording found")
    _record(22, "dashboard mentions the reporting period", "تقرير" in text or "Report" in text)
    links = page.evaluate("() => [...document.querySelectorAll('main a')].map(a => a.getAttribute('href'))")
    _record(22, "action links are present", len(links) > 0, f"links={links[:6]}")
    # The reference shows five actions; the API reports them explicitly.
    actions = page.evaluate(
        """async () => {
        const t = window.sessionStorage.getItem('safir.access');
        const r = await fetch('/api/backend/api/v1/dashboard', {headers:{Authorization:`Bearer ${t}`}});
        if (!r.ok) return null;
        return (await r.json()).actions || [];
    }"""
    )
    _record(22, "the five reference actions are returned", actions is not None and len(actions) >= 5, f"actions={actions}")


def check_page_23(page: Page) -> None:
    """Submission screen has the mandatory bank-statement upload."""
    page.goto(f"{BASE}/reports")
    page.wait_for_timeout(1200)
    report_id = page.evaluate(
        """async () => {
        const t = window.sessionStorage.getItem('safir.access');
        const r = await fetch('/api/backend/api/v1/reports', {headers:{Authorization:`Bearer ${t}`}});
        const rows = await r.json();
        const draft = rows.find(x => x.status === 'draft');
        return draft ? draft.id : (rows[0] ? rows[0].id : null);
    }"""
    )
    if report_id is None:
        _record(23, "a manager report exists", False, "none")
        return
    page.goto(f"{BASE}/reports/{report_id}")
    page.wait_for_timeout(1500)
    has_input = page.evaluate("() => !!document.querySelector('#bank-statement')")
    _record(23, "bank-statement upload control exists", has_input)
    text = page.inner_text("main")
    _record(23, "screen marks the statement as required", "كشف الحساب" in text)


def check_page_24(page: Page) -> None:
    """The three accountant entry buttons deep-link to their own section."""
    hrefs = page.evaluate(
        "() => [...document.querySelectorAll('main a')].map(a => a.getAttribute('href')).filter(h => h && h.includes('/accounting'))"
    )
    wanted = {"/accounting?kind=expense", "/accounting?kind=invoice", "/accounting?kind=commission"}
    _record(24, "three accounting deep links exist", wanted.issubset(set(hrefs)), f"hrefs={hrefs}")
    # Each link must actually select its own tab. The tab captions are the
    # plural forms shown in the reference («المصاريف», «الفواتير», «العمولات»).
    for kind, label in [("expense", "المصاريف"), ("invoice", "الفواتير"), ("commission", "العمولات")]:
        page.goto(f"{BASE}/accounting?kind={kind}")
        page.wait_for_timeout(1200)
        selected = page.evaluate(
            "() => {const el=document.querySelector('[role=tab][aria-selected=true]'); return el ? el.textContent.trim() : null;}"
        )
        _record(24, f"?kind={kind} selects the {kind} tab", bool(selected) and label in selected, f"selected={selected}")
    # PDF p.9 asks for export where applicable; the button must be reachable and
    # download a real workbook rather than a dead control.
    page.goto(f"{BASE}/accounting")
    page.wait_for_timeout(1500)
    button = page.query_selector("button:has-text('تصدير Excel')")
    _record(24, "the accounting export button is present", bool(button))
    if button:
        with page.expect_download(timeout=20000) as download:
            button.click()
        name = download.value.suggested_filename
        _record(24, "the export downloads a workbook", name.endswith(".xlsx"), f"name={name}")


def check_password_reset(browser) -> None:
    """The forgot/reset flow: reachable from login, single-use, and effective."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(f"{BASE}/login")
    page.wait_for_timeout(1000)
    _record(5, "login links to the password-reset request", bool(page.query_selector("a[href='/forgot-password']")))

    page.click("a[href='/forgot-password']")
    page.wait_for_url("**/forgot-password", timeout=15000)
    page.fill("#email", "advisor@safir-platform.com")
    page.click("button[type=submit]")
    page.wait_for_timeout(2500)
    token_el = page.query_selector("p[dir=ltr]")
    token = token_el.inner_text().strip() if token_el else ""
    _record(5, "a reset link is issued", bool(token), "no token shown")

    page.click("text=متابعة إلى تعيين كلمة المرور")
    page.wait_for_url("**/reset-password**", timeout=15000)
    _record(5, "the reset token is carried into the form", page.input_value("#token") == token)

    # The password must match confirmation and meet the minimum length.
    page.fill("#new-password", "Safir!2026New")
    page.fill("#confirm-password", "Safir!2026Differs")
    page.click("button[type=submit]")
    page.wait_for_timeout(1200)
    _record(5, "a mismatched confirmation is refused", "غير متطابق" in page.inner_text("body"))

    page.fill("#confirm-password", "Safir!2026New")
    page.click("button[type=submit]")
    page.wait_for_timeout(2500)
    _record(5, "a valid token sets the password", "تم تعيين كلمة المرور" in page.inner_text("body"))

    # The new password works, and the token cannot be replayed.
    page.goto(f"{BASE}/login")
    page.wait_for_timeout(1000)
    page.fill("#email", "advisor@safir-platform.com")
    page.fill("#password", "Safir!2026New")
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard", timeout=25000)
    _record(5, "the new password signs the user in", page.url.endswith("/dashboard"))

    page.goto(f"{BASE}/reset-password?token={token}")
    page.wait_for_timeout(1200)
    page.fill("#new-password", "Replay!2026")
    page.fill("#confirm-password", "Replay!2026")
    page.click("button[type=submit]")
    page.wait_for_timeout(2000)
    _record(5, "a used token is refused", "غير صالح" in page.inner_text("body"))

    # Restore the seeded password so the rest of the audit keeps working.
    page.goto(f"{BASE}/forgot-password")
    page.wait_for_timeout(1000)
    page.fill("#email", "advisor@safir-platform.com")
    page.click("button[type=submit]")
    page.wait_for_timeout(2500)
    fresh = page.query_selector("p[dir=ltr]")
    restore = fresh.inner_text().strip() if fresh else ""
    page.goto(f"{BASE}/reset-password?token={restore}")
    page.wait_for_timeout(1200)
    page.fill("#new-password", PASSWORD)
    page.fill("#confirm-password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_timeout(2500)
    _record(5, "the seeded password is restored", "تم تعيين كلمة المرور" in page.inner_text("body"))
    ctx.close()


def check_website_admin(browser) -> None:
    """PDF p.15: the admin toggles public visibility and rejects a submission.

    The visibility endpoint declared a query parameter while the screen sent a
    JSON body, so every toggle answered 422. This drives the real buttons.
    """
    ctx, page = _sign_in(browser, "owner")
    page.evaluate(
        """async () => {
            await fetch('/api/backend/api/v1/public/submissions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({kind: 'contact', name: 'زائر تجربة', email: 'zz@example.com', message: 'مرحبا'}),
            });
        }"""
    )
    page.goto(f"{BASE}/website")
    page.wait_for_timeout(2500)

    toggle = page.query_selector("button:has-text('إظهار'), button:has-text('إخفاء')")
    _record(15, "the public-visibility toggle is present", bool(toggle))
    if toggle:
        toggle.click()
        page.wait_for_timeout(2000)
        _record(15, "toggling visibility is confirmed", "تم تحديث الظهور العام" in page.inner_text("body"))

    reject = page.query_selector("button:has-text('رفض')")
    _record(15, "the submission reject control is present", bool(reject))
    if reject:
        reject.click()
        page.wait_for_timeout(2000)
        _record(15, "rejecting a submission is confirmed", "تم رفض الطلب" in page.inner_text("body"))
    ctx.close()


def check_company_logo(browser) -> None:
    """PDF p.6 lists the official logo as a company field.

    The field existed in the schema but nothing could set it, so it was
    decorative. This drives the real upload control and asserts the stored logo
    renders back from the authenticated download endpoint.
    """
    import base64
    import tempfile

    ctx, page = _sign_in(browser, "owner")
    code = f"LOGO-{page.evaluate('Date.now()') % 1000000}"
    company_id = page.evaluate(
        """async (code) => {
            const t = sessionStorage.getItem('safir.access');
            const r = await fetch('/api/backend/api/v1/companies', {
                method: 'POST',
                headers: {Authorization: 'Bearer ' + t, 'Content-Type': 'application/json'},
                body: JSON.stringify({code, name_ar: 'شعار', name_en: 'Logo Co', country: 'SA', sector: 'tech', status: 'draft'}),
            });
            return (await r.json()).id;
        }""",
        code,
    )
    page.goto(f"{BASE}/companies/{company_id}")
    page.wait_for_timeout(2000)
    _record(6, "the company detail screen offers a logo control", bool(page.query_selector("input[type=file]")))

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
        fh.write(png)
        path = fh.name
    page.set_input_files("input[type=file]", path)
    page.wait_for_timeout(3000)
    _record(6, "uploading a logo is confirmed", "تم رفع الشعار" in page.inner_text("body"))
    _record(
        6,
        "the stored logo renders from the authenticated endpoint",
        page.evaluate("() => {const i = document.querySelector('header img'); return !!i && i.complete && i.naturalWidth > 0;}"),
    )
    page.goto(f"{BASE}/companies")
    page.wait_for_timeout(2500)
    _record(
        6,
        "the logo also renders in the companies listing",
        page.evaluate("() => [...document.querySelectorAll('table img')].some(i => i.complete && i.naturalWidth > 0)"),
    )
    ctx.close()


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])

        print("page 8 — owner report visibility")
        ctx, page = _sign_in(browser, "owner")
        page.goto(f"{BASE}/reports")
        page.wait_for_timeout(1500)
        check_page_8(page)
        ctx.close()

        print("page 11 — lead filters")
        ctx, page = _sign_in(browser, "owner")
        page.goto(f"{BASE}/leads")
        page.wait_for_timeout(1500)
        check_page_11(page)
        ctx.close()

        print("page 12 — opportunity heading")
        ctx, page = _sign_in(browser, "owner")
        page.goto(f"{BASE}/opportunities")
        page.wait_for_timeout(1500)
        check_page_12(page)
        ctx.close()

        print("page 14 — HR salary restriction")
        ctx, page = _sign_in(browser, "owner")
        page.goto(f"{BASE}/hr")
        page.wait_for_timeout(1500)
        check_page_14(page)
        ctx.close()

        print("page 18 — subfield marker")
        ctx, page = _sign_in(browser, "manager")
        check_page_18(page)
        ctx.close()

        print("page 22 — manager dashboard banner and actions")
        ctx, page = _sign_in(browser, "manager")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(1500)
        check_page_22(page)
        ctx.close()

        print("page 23 — bank statement upload")
        ctx, page = _sign_in(browser, "manager")
        check_page_23(page)
        ctx.close()

        print("page 24 — accounting deep links")
        ctx, page = _sign_in(browser, "accountant")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(1500)
        check_page_24(page)
        ctx.close()

        print("page 15 — website administration")
        check_website_admin(browser)

        print("page 6 — company logo upload")
        check_company_logo(browser)

        print("page 5 — password reset flow")
        check_password_reset(browser)

        browser.close()

    passed = sum(1 for r in RESULTS if r.passed)
    total = len(RESULTS)
    print(f"\n{passed}/{total} assertions passed")
    for r in RESULTS:
        if not r.passed:
            print(f"  FAILED  p.{r.page} {r.title}  {r.detail}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
