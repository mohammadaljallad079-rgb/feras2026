"""Verify direction, theme and layout across every route, locale and viewport.

Checks the properties the specification fixes rather than eyeballing them:

  * `dir` is `rtl` in Arabic and `ltr` in English, on every route;
  * the sidebar sits on the right in Arabic and the left in English;
  * the active theme resolves to the specified token values;
  * the sidebar is exactly 240px wide on desktop;
  * nothing scrolls horizontally at a 400px viewport;
  * English is translated rather than left in Arabic.

    python3 scripts/check_matrix.py [--json out.json]

Needs a seeded backend on :8000 and a frontend on :12000.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

from playwright.sync_api import Browser, sync_playwright

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
}

# (route, role) for every screen the reference defines.
ROUTES = [
    ("/dashboard", "owner"),
    ("/companies", "owner"),
    ("/companies/new", "owner"),
    ("/reports", "owner"),
    ("/accounting", "accountant"),
    ("/service-requests", "owner"),
    ("/leads", "owner"),
    ("/opportunities", "owner"),
    ("/directives", "owner"),
    ("/hr", "owner"),
    ("/website", "owner"),
    ("/advisor", "owner"),
    ("/assistant", "owner"),
    ("/form-builder", "owner"),
    ("/users", "owner"),
    ("/users/new", "owner"),
    ("/audit", "owner"),
]

# Light-mode tokens from the specification, and their dark counterparts.
LIGHT = {"--bg": "#f4f6f8", "--card": "#ffffff", "--ink": "#0b192c", "--gold": "#c3a36b", "--side": "#0b192c"}
DARK = {"--bg": "#0a1220", "--card": "#111d30", "--ink": "#e8ebf0", "--gold": "#c3a36b", "--side": "#060d18"}

# Arabic strings that must not appear on an English screen (translation gaps).
ARABIC_LEAK_MARKERS = ["الشركات", "التقارير", "الموظفون", "المستخدمون", "سجل النشاط"]


@dataclass
class Row:
    route: str
    locale: str
    theme: str
    viewport: str
    direction: str
    sidebar_side: str
    sidebar_width: int
    h_overflow: bool
    token_mismatches: list
    arabic_leak: list
    errors: list


def _token_probe(page) -> dict:
    return page.evaluate(
        """() => {
        const cs = getComputedStyle(document.documentElement);
        return {'--bg': cs.getPropertyValue('--bg').trim(),
                '--card': cs.getPropertyValue('--card').trim(),
                '--ink': cs.getPropertyValue('--ink').trim(),
                '--gold': cs.getPropertyValue('--gold').trim(),
                '--side': cs.getPropertyValue('--side').trim()};
    }"""
    )


def _hex(value: str) -> str:
    """Normalise `rgb(244, 246, 248)` / `#f4f6f8` to a lowercase hex string."""
    value = value.strip()
    if value.startswith("#"):
        return value.lower()
    if value.startswith("rgb"):
        nums = [int(n) for n in value[value.index("(") + 1 : value.index(")")].replace("%", "").split(",")[:3]]
        return "#%02x%02x%02x" % tuple(nums)
    return value


def _sign_in(browser: Browser, role: str, locale: str, theme: str, width: int, height: int):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)[:160]))
    page.goto(f"{BASE}/login")
    page.fill("#email", ACCOUNTS[role])
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard", timeout=25000)
    if locale == "en":
        page.select_option("#locale-select", "en")
        page.wait_for_timeout(700)
    # Drive the real control rather than forcing the attribute, so the check
    # covers the user's path (the toggle persists the choice and re-applies it).
    # The header renders only once the session resolves, so wait for the control
    # instead of sampling the DOM immediately — `query_selector` does not wait
    # and would otherwise fail intermittently.
    if theme == "dark":
        toggle = page.wait_for_selector("button[aria-pressed]", timeout=20000)
        if toggle.get_attribute("aria-pressed") != "true":
            toggle.click()
            page.wait_for_timeout(500)
    return ctx, page, errors


def _inspect(page, route: str, locale: str, theme: str, viewport: str, errors: list) -> Row:
    page.goto(f"{BASE}{route}")
    page.wait_for_timeout(1100)
    direction = page.evaluate("document.documentElement.dir")

    aside = page.evaluate(
        """() => {
        const a = document.querySelector('aside');
        if (!a) return null;
        const r = a.getBoundingClientRect();
        return {left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width),
                winW: window.innerWidth, visible: r.width > 0};
    }"""
    )
    if aside and aside["visible"]:
        # RTL: the sidebar hugs the right edge. LTR: it hugs the left edge.
        side = "right" if aside["left"] > aside["winW"] / 2 else "left"
        width = aside["width"]
    else:
        side, width = "hidden", 0

    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
    )

    expected = DARK if theme == "dark" else LIGHT
    actual = _token_probe(page)
    mismatches = [
        f"{k}: expected {v}, got {_hex(actual.get(k, ''))}"
        for k, v in expected.items()
        if _hex(actual.get(k, "")) != v
    ]

    leak: list[str] = []
    if locale == "en":
        body = page.inner_text("body")
        leak = [m for m in ARABIC_LEAK_MARKERS if m in body]

    return Row(route, locale, theme, viewport, direction, side, width, overflow, mismatches, leak, list(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="")
    args = parser.parse_args()

    rows: list[Row] = []
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])

        # Every route, Arabic, light, desktop.
        ctx, page, errs = _sign_in(browser, "owner", "ar", "light", 1440, 1000)
        for route, role in ROUTES:
            rows.append(_inspect(page, route, "ar", "light", "desktop", errs))

        # Every route, English, light, desktop (page 31).
        ctx_en, page_en, errs_en = _sign_in(browser, "owner", "en", "light", 1440, 1000)
        for route, role in ROUTES:
            rows.append(_inspect(page_en, route, "en", "light", "desktop", errs_en))

        # Every route, Arabic, dark, desktop (page 32).
        ctx_dk, page_dk, errs_dk = _sign_in(browser, "owner", "ar", "dark", 1440, 1000)
        for route, role in ROUTES:
            rows.append(_inspect(page_dk, route, "ar", "dark", "desktop", errs_dk))

        # Every route, Arabic, light, mobile 400px (page 30).
        ctx_mb, page_mb, errs_mb = _sign_in(browser, "owner", "ar", "light", 400, 900)
        for route, role in ROUTES:
            rows.append(_inspect(page_mb, route, "ar", "light", "mobile", errs_mb))

        # Every route, English, light, mobile.
        ctx_mb_en, page_mb_en, errs_mb_en = _sign_in(browser, "owner", "en", "light", 400, 900)
        for route, role in ROUTES:
            rows.append(_inspect(page_mb_en, route, "en", "light", "mobile", errs_mb_en))

        browser.close()

    for r in rows:
        if r.direction != ("rtl" if r.locale == "ar" else "ltr"):
            failures.append(f"{r.route} [{r.locale}/{r.theme}/{r.viewport}] dir={r.direction}")
        if r.viewport == "desktop" and r.sidebar_side != ("right" if r.locale == "ar" else "left"):
            failures.append(f"{r.route} [{r.locale}] sidebar on {r.sidebar_side}")
        if r.viewport == "desktop" and r.sidebar_width != 240:
            failures.append(f"{r.route} [{r.locale}] sidebar width {r.sidebar_width}px, expected 240px")
        if r.h_overflow:
            failures.append(f"{r.route} [{r.locale}/{r.theme}/{r.viewport}] horizontal overflow")
        for m in r.token_mismatches:
            failures.append(f"{r.route} [{r.theme}] token {m}")
        if r.arabic_leak:
            failures.append(f"{r.route} [en] untranslated: {r.arabic_leak}")
        if r.errors:
            failures.append(f"{r.route} [{r.locale}/{r.theme}/{r.viewport}] console: {r.errors[:1]}")

    print(f"{len(rows)} route/viewport combinations inspected")
    print(f"{len(failures)} failures")
    for f in failures:
        print("  FAIL " + f)

    if args.json:
        with open(args.json, "w") as fh:
            json.dump([asdict(r) for r in rows], fh, ensure_ascii=False, indent=1)
        print(f"wrote {args.json}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
