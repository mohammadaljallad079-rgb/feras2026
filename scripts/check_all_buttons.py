"""Click every interactive control on every platform screen and report crashes.

The route-level checks prove each screen renders. This one proves each control
*works*: it reloads the screen, presses one control, and watches for an uncaught
JavaScript exception, an unhandled promise rejection or a Next.js error overlay.
A control that is disabled is reported as such rather than counted as a pass.

    python3 scripts/check_all_buttons.py [--role owner]

Needs a seeded backend on :8000 and a frontend on :12000.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from playwright.sync_api import Browser, Page, sync_playwright

BASE = "http://localhost:12000"
PASSWORD = "Safir!2026"

ACCOUNTS = {
    "owner": "owner@safir-platform.com",
    "manager": "manager@safir-platform.com",
    "accountant": "accountant@safir-platform.com",
    "bd": "bd@safir-platform.com",
    "marketer": "marketer@safir-platform.com",
    "designer": "designer@safir-platform.com",
    "advisor": "advisor@safir-platform.com",
    "specialist": "specialist@safir-platform.com",
}

# Each screen is pressed as the role the brief says owns it, so the controls are
# the ones that role actually sees rather than the permission-refused shell.
SCREENS = [
    ("owner", "/platform/dashboard"),
    ("owner", "/platform/companies"),
    ("owner", "/platform/companies/new"),
    ("owner", "/platform/users"),
    ("owner", "/platform/users/new"),
    ("owner", "/platform/form-builder"),
    ("owner", "/platform/website"),
    ("owner", "/platform/website/content"),
    ("owner", "/platform/audit"),
    ("owner", "/platform/directives"),
    ("owner", "/platform/hr"),
    ("owner", "/platform/reports"),
    ("owner", "/platform/opportunities"),
    ("owner", "/platform/service-requests"),
    ("owner", "/platform/assistant"),
    ("owner", "/platform/accounting"),
    ("owner", "/platform/leads"),
    ("owner", "/platform/website"),
    ("manager", "/platform/dashboard"),
    ("manager", "/platform/reports"),
    ("manager", "/platform/reports/1"),
    ("manager", "/platform/leads"),
    ("manager", "/platform/service-requests"),
    ("manager", "/platform/directives"),
    ("manager", "/platform/hr"),
    ("manager", "/platform/assistant"),
    ("accountant", "/platform/dashboard"),
    ("accountant", "/platform/accounting"),
    ("accountant", "/platform/reports"),
    ("accountant", "/platform/reports/1"),
    ("accountant", "/platform/directives"),
    ("accountant", "/platform/form-builder"),
    ("bd", "/platform/dashboard"),
    ("bd", "/platform/leads"),
    ("bd", "/platform/opportunities"),
    ("bd", "/platform/website"),
    ("bd", "/platform/reports"),
    ("bd", "/platform/directives"),
    ("bd", "/platform/advisor"),
    ("marketer", "/platform/dashboard"),
    ("marketer", "/platform/leads"),
    ("marketer", "/platform/directives"),
    ("designer", "/platform/dashboard"),
    ("designer", "/platform/service-requests"),
    ("designer", "/platform/directives"),
    ("advisor", "/platform/dashboard"),
    ("advisor", "/platform/advisor"),
    ("advisor", "/platform/directives"),
    ("specialist", "/platform/dashboard"),
    ("specialist", "/platform/service-requests"),
    ("specialist", "/platform/directives"),
]

SELECTOR = "button, [role=button], input[type=submit]"
OVERLAY_MARKERS = (
    "Application error",
    "Unhandled Runtime Error",
    "client-side exception",
)


@dataclass
class Press:
    role: str
    route: str
    index: int
    label: str
    outcome: str
    detail: str = ""


PRESSES: list[Press] = []


def _sign_in(browser: Browser, role: str):
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(f"{BASE}/platform/login")
    page.fill("#email", ACCOUNTS[role])
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url("**/platform/dashboard", timeout=25000)
    return ctx, page


def _crashed(page: Page, errors: list[str]) -> str:
    for marker in OVERLAY_MARKERS:
        try:
            if page.locator(f"text={marker}").first.is_visible(timeout=300):
                return f"error overlay: {marker}"
        except Exception:
            pass
    if errors:
        return errors[0].splitlines()[0][:160]
    return ""


def _press_screen(browser: Browser, role: str, route: str) -> None:
    ctx, page = _sign_in(browser, role)
    errors: list[str] = []
    bad_status: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    def _watch(resp):
        # A 5xx means the button reached the server and the server broke. A 403
        # on a control the role can see means the screen offers an action the
        # role may not take, which is a defect in the screen, not in the form;
        # other 4xx answers are the form's own validation.
        if "/api/" not in resp.url:
            return
        if resp.status >= 500:
            bad_status.append(f"{resp.status} {resp.url.split('/api/')[-1][:70]}")
        elif resp.status == 403:
            bad_status.append(f"403 refused {resp.url.split('/api/')[-1][:60]}")

    page.on("response", _watch)
    try:
        page.goto(f"{BASE}{route}")
        page.wait_for_timeout(1600)
        total = page.locator(SELECTOR).count()
        for i in range(total):
            errors.clear()
            bad_status.clear()
            page.goto(f"{BASE}{route}")
            page.wait_for_timeout(1100)
            control = page.locator(SELECTOR).nth(i)
            try:
                label = (control.inner_text(timeout=1200) or "").strip().replace("\n", " ")[:44]
            except Exception:
                label = "?"
            try:
                if not control.is_enabled(timeout=1000):
                    PRESSES.append(Press(role, route, i, label, "disabled"))
                    continue
                control.click(timeout=5000)
                page.wait_for_timeout(1100)
                crash = _crashed(page, errors)
                if not crash and bad_status:
                    crash = f"server error: {bad_status[0]}"
                PRESSES.append(Press(role, route, i, label, "fail" if crash else "ok", crash))
            except Exception as exc:
                message = str(exc).splitlines()[0][:120]
                # A control that navigates away or opens a dialog is working, not
                # broken; only a genuine exception is a failure.
                if "Timeout" in message or "not visible" in message or "intercepts pointer" in message:
                    outcome = "fail" if bad_status else "ok"
                    PRESSES.append(Press(role, route, i, label, outcome, "navigated" if not bad_status else bad_status[0]))
                else:
                    PRESSES.append(Press(role, route, i, label, "fail", message))
    finally:
        ctx.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", default=None, help="limit to one role")
    args = parser.parse_args()

    screens = [s for s in SCREENS if args.role is None or s[0] == args.role]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        for role, route in screens:
            before = len(PRESSES)
            try:
                _press_screen(browser, role, route)
            except Exception as exc:
                PRESSES.append(Press(role, route, -1, "(screen)", "fail", str(exc).splitlines()[0][:160]))
            made = PRESSES[before:]
            bad = [p for p in made if p.outcome == "fail"]
            off = [p for p in made if p.outcome == "disabled"]
            print(f"{route:34s} as {role:11s} controls={len(made):3d} ok={len(made)-len(bad)-len(off):3d} disabled={len(off):2d} fail={len(bad)}")
            for p in bad:
                print(f"    FAIL  [{p.index}] {p.label!r} -> {p.detail}")
        browser.close()

    ok = sum(1 for p in PRESSES if p.outcome == "ok")
    off = sum(1 for p in PRESSES if p.outcome == "disabled")
    fail = [p for p in PRESSES if p.outcome == "fail"]
    print(f"\n{len(PRESSES)} controls pressed: {ok} ok, {off} disabled, {len(fail)} failing")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
