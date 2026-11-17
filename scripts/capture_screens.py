"""Capture the implementation screens for the page-by-page visual audit.

Signs in as each demo role, walks the routes that role can reach, and writes a
full-page PNG per (page, locale, theme) into `docs/screenshots/impl/`. Needs a
seeded backend on :8000 and a running frontend on BASE.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright

BASE = "http://localhost:12000"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots" / "impl"
PASSWORD = "Safir!2026"

EMAILS = {
    "owner": "owner@safir-platform.com",
    "company_manager": "manager@safir-platform.com",
    "accountant": "accountant@safir-platform.com",
    "business_developer": "bd@safir-platform.com",
    "marketer": "marketer@safir-platform.com",
    "designer": "designer@safir-platform.com",
    "advisor": "advisor@safir-platform.com",
}

# (name, route, role, locale, theme, viewport)
SHOTS: list[tuple[str, str, str, str, str, tuple[int, int]]] = [
    ("05-owner-dashboard", "/dashboard", "owner", "ar", "light", (1440, 1000)),
    ("06-companies", "/companies", "owner", "ar", "light", (1440, 1000)),
    ("07-company-wizard", "/companies/new", "owner", "ar", "light", (1440, 1000)),
    ("08-owner-reports", "/reports", "owner", "ar", "light", (1440, 1000)),
    ("09-accounting", "/accounting", "accountant", "ar", "light", (1440, 1000)),
    ("10-service-requests", "/service-requests", "owner", "ar", "light", (1440, 1000)),
    ("11-leads", "/leads", "owner", "ar", "light", (1440, 1000)),
    ("12-opportunities", "/opportunities", "owner", "ar", "light", (1440, 1000)),
    ("13-directives", "/directives", "owner", "ar", "light", (1440, 1000)),
    ("14-hr", "/hr", "owner", "ar", "light", (1440, 1000)),
    ("15-website", "/website", "owner", "ar", "light", (1440, 1000)),
    ("16-advisor", "/advisor", "owner", "ar", "light", (1440, 1000)),
    ("17-assistant", "/assistant", "owner", "ar", "light", (1440, 1000)),
    ("18-form-builder", "/form-builder", "owner", "ar", "light", (1440, 1000)),
    ("19-users", "/users", "owner", "ar", "light", (1440, 1000)),
    ("20-user-new", "/users/new", "owner", "ar", "light", (1440, 1000)),
    ("21-audit", "/audit", "owner", "ar", "light", (1440, 1000)),
    ("22-manager-dashboard", "/dashboard", "company_manager", "ar", "light", (1440, 1000)),
    ("24-accountant-dashboard", "/dashboard", "accountant", "ar", "light", (1440, 1000)),
    ("26-bd-dashboard", "/dashboard", "business_developer", "ar", "light", (1440, 1000)),
    ("27-marketer-dashboard", "/dashboard", "marketer", "ar", "light", (1440, 1000)),
    ("28-designer-dashboard", "/dashboard", "designer", "ar", "light", (1440, 1000)),
    ("29-advisor-dashboard", "/dashboard", "advisor", "ar", "light", (1440, 1000)),
    ("30-owner-dashboard-mobile", "/dashboard", "owner", "ar", "light", (400, 900)),
    ("30-manager-dashboard-mobile", "/dashboard", "company_manager", "ar", "light", (400, 900)),
    ("31-owner-dashboard-en", "/dashboard", "owner", "en", "light", (1440, 1000)),
    ("31-companies-en", "/companies", "owner", "en", "light", (1440, 1000)),
]



# Page 32: the whole application in dark mode, one capture per screen.
DARK_ROUTES = [
    ("05-owner-dashboard", "/dashboard"),
    ("06-companies", "/companies"),
    ("07-company-wizard", "/companies/new"),
    ("08-owner-reports", "/reports"),
    ("09-accounting", "/accounting"),
    ("10-service-requests", "/service-requests"),
    ("11-leads", "/leads"),
    ("12-opportunities", "/opportunities"),
    ("13-directives", "/directives"),
    ("14-hr", "/hr"),
    ("15-website", "/website"),
    ("16-advisor", "/advisor"),
    ("17-assistant", "/assistant"),
    ("18-form-builder", "/form-builder"),
    ("19-users", "/users"),
    ("20-user-new", "/users/new"),
    ("21-audit", "/audit"),
]

def _open(browser, role: str, locale: str, theme: str, viewport: tuple[int, int]):
    ctx: BrowserContext = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = ctx.new_page()
    page.goto(f"{BASE}/login")
    page.fill("#email", EMAILS[role])
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard", timeout=20000)
    if locale == "en":
        page.select_option("#locale-select", "en")
        page.wait_for_timeout(500)
    if theme == "dark":
        page.click("button:has-text('الوضع الداكن')")
        page.wait_for_timeout(500)
    return ctx, page


def _first_report_id(page: Page, status: str) -> int | None:
    """Resolve a report id of the given status through the API the app itself uses."""
    return page.evaluate(
        """async (status) => {
        const token = window.sessionStorage.getItem('safir.access');
        const r = await fetch(`/api/backend/api/v1/reports?status=${status}`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) return null;
        const rows = await r.json();
        return rows.length ? rows[0].id : null;
    }""",
        status,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        sessions: dict[tuple[str, str, str, tuple[int, int]], tuple[BrowserContext, Page]] = {}
        for name, route, role, locale, theme, viewport in SHOTS:
            key = (role, locale, theme, viewport)
            if key not in sessions:
                sessions[key] = _open(browser, role, locale, theme, viewport)
            _, page = sessions[key]
            page.goto(f"{BASE}{route}")
            page.wait_for_timeout(1200)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
            print(f"captured {name}.png")

        # Page 32: every screen in dark mode.
        dark_key = ("owner", "ar", "dark", (1440, 1000))
        if dark_key not in sessions:
            sessions[dark_key] = _open(browser, "owner", "ar", "dark", (1440, 1000))
        _, dark_page = sessions[dark_key]
        for name, route in DARK_ROUTES:
            dark_page.goto(f"{BASE}{route}")
            dark_page.wait_for_timeout(1100)
            dark_page.screenshot(path=str(OUT / f"32-{name}-dark.png"), full_page=True)
            print(f"captured 32-{name}-dark.png")

        # Public authentication screens, including the password-reset flow.
        for locale in ("ar", "en"):
            ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = ctx.new_page()
            page.goto(f"{BASE}/login")
            page.wait_for_timeout(800)
            if locale == "en":
                page.click("button:has-text('English')")
                page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / f"login-{locale}.png"), full_page=True)
            print(f"captured login-{locale}.png")
            page.goto(f"{BASE}/forgot-password")
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / f"forgot-password-{locale}.png"), full_page=True)
            print(f"captured forgot-password-{locale}.png")
            ctx.close()

        # Pages 23 and 25: the report detail screen, in the state each role sees.
        for name, role, status in [
            ("23-report-submission", "company_manager", "draft"),
            ("25-report-review", "accountant", "submitted"),
        ]:
            key = (role, "ar", "light", (1440, 1000))
            if key not in sessions:
                sessions[key] = _open(browser, role, "ar", "light", (1440, 1000))
            _, page = sessions[key]
            page.goto(f"{BASE}/reports")
            page.wait_for_timeout(1200)
            report_id = _first_report_id(page, status)
            if report_id is None:
                print(f"skipped {name}: no {status} report in the database")
                continue
            page.goto(f"{BASE}/reports/{report_id}")
            page.wait_for_timeout(1200)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
            print(f"captured {name}.png")

        browser.close()

    # The handover set referenced by docs/verification/visual-comparison.md is a
    # subset of the audit captures; copy rather than shoot them twice so the two
    # directories cannot drift apart.
    deliverables = OUT.parent / "deliverables"
    deliverables.mkdir(parents=True, exist_ok=True)
    for source, target in [
        ("login-ar.png", "login-ar-desktop.png"),
        ("05-owner-dashboard.png", "dashboard-ar-desktop.png"),
        ("32-05-owner-dashboard-dark.png", "dashboard-ar-dark.png"),
        ("31-owner-dashboard-en.png", "dashboard-en-desktop.png"),
        ("30-owner-dashboard-mobile.png", "dashboard-ar-mobile-400.png"),
    ]:
        src, dst = OUT / source, deliverables / target
        if not src.exists():
            print(f"skipped {target}: {source} was not captured")
            continue
        shutil.copyfile(src, dst)
        print(f"copied {source} -> deliverables/{target}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
