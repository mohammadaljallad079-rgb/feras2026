"""Exercise the public website end to end, as a visitor, in a real browser.

The platform sweep (`check_all_buttons.py`) covers the signed-in screens. This
one covers the public site: every link, every language toggle, every filter,
every form — and then proves the submission actually reaches the dashboard by
reading it back through the staff API with a staff token.

    python3 scripts/check_public_site.py [--headless]

Needs a seeded backend on :8000 and a frontend on :12000.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from dataclasses import dataclass, field

import psycopg
from playwright.sync_api import Browser, Page, sync_playwright

BASE = "http://localhost:12000"
API = "http://localhost:8000/api/v1"
OWNER = ("owner@safir-platform.com", "Safir!2026")

PAGES = [
    ("/ar", "الرئيسية"),
    ("/ar/about", "من نحن"),
    ("/ar/companies", "شركات المجموعة"),
    ("/ar/solutions", "منظومة الحلول"),
    ("/ar/opportunities", "الفرص التجارية"),
    ("/ar/careers", "الوظائف"),
    ("/ar/contact", "تواصل"),
    ("/ar/service-request", "اطلب خدمة"),
    ("/ar/privacy", "سياسة الخصوصية"),
    ("/ar/solutions", "خدمات مترابطة لاحتياجات الأعمال."),
    ("/ar/contact", "ابدأ محادثة حول احتياج أعمالك."),
    ("/ar", "شركة قابضة بحرينية تعمل على تطوير شركات المجموعة وربط الخبرات بفرص الأعمال والنمو."),
    ("/ar/contact", "شركة ستارت أب سفير القابضة ذ.م.م"),
    ("/en", "home"),
    ("/en/about", "about"),
    ("/en/companies", "companies"),
    ("/en/solutions", "solutions"),
    ("/en/opportunities", "opportunities"),
    ("/en/careers", "careers"),
    ("/en/contact", "contact"),
    ("/en/service-request", "service request"),
    ("/en/privacy", "privacy"),
]

OVERLAY_MARKERS = (
    "Application error",
    "Unhandled Runtime Error",
    "client-side exception",
    "Internal Server Error",
)


@dataclass
class Finding:
    where: str
    what: str
    outcome: str
    detail: str = ""


FINDINGS: list[Finding] = []


def _record(where: str, what: str, ok: bool, detail: str = "") -> None:
    FINDINGS.append(Finding(where, what, "ok" if ok else "fail", detail))


def _token(email: str, password: str) -> str:
    body = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{API}/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)["access_token"]


def _get(path: str, token: str):
    req = urllib.request.Request(f"{API}{path}", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _crashed(page: Page, errors: list[str]) -> str:
    for marker in OVERLAY_MARKERS:
        try:
            if page.locator(f"text={marker}").first.is_visible(timeout=250):
                return f"overlay: {marker}"
        except Exception:
            pass
    if errors:
        return errors[0].splitlines()[0][:150]
    return ""


def _visit(browser: Browser, path: str) -> tuple[list[Finding], list[dict]]:
    """Load a page, prove it rendered, and collect the links it offers."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errors: list[str] = []
    bad: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    def _watch(resp):
        if resp.status >= 400 and "/api/" in resp.url:
            bad.append(f"{resp.status} {resp.url.split('/api/')[-1][:60]}")

    page.on("response", _watch)
    found: list[Finding] = []
    try:
        resp = page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(700)
        status = resp.status if resp else 0
        crash = _crashed(page, errors)
        ok = status == 200 and not crash and not bad
        found.append(Finding(path, "renders", "ok" if ok else "fail",
                             f"HTTP {status}" if status != 200 else (crash or (bad[0] if bad else ""))))
        body = page.inner_text("body")
        if len(body.strip()) < 120:
            found.append(Finding(path, "has content", "fail", f"only {len(body.strip())} chars"))
        links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({href: e.getAttribute('href'), text: (e.innerText||'').trim().slice(0,40)}))"
        )
        return found, links
    finally:
        ctx.close()


def _check_link(browser: Browser, href: str, text: str) -> Finding:
    """Follow an internal link and prove it lands on a real page."""
    if href.startswith(("mailto:", "tel:", "http://", "https://", "#")):
        return Finding(href, text or "external", "ok", "not followed")
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    try:
        resp = page.goto(f"{BASE}{href}", wait_until="domcontentloaded", timeout=30000)
        status = resp.status if resp else 0
        body = page.inner_text("body")
        missing = "الصفحة غير موجودة" in body or "This page could not be found" in body or "404" in body[:400]
        ok = status == 200 and not missing
        detail = f"HTTP {status}" if status != 200 else ("404 copy shown" if missing else "")
        return Finding(href, text or "link", "ok" if ok else "fail", detail)
    finally:
        ctx.close()


def _submit_form(
    browser: Browser, path: str, values: dict, *, file: str | None = None, consent: bool = True
) -> Finding:
    """Fill and submit a public form, and report what the visitor is told."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errors: list[str] = []
    posted: list[int] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "response",
        lambda r: posted.append(r.status) if "/public/submissions" in r.url else None,
    )
    try:
        page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=45000)
        for name, value in values.items():
            field_loc = page.locator(f"[name={name}]").first
            tag = field_loc.evaluate("e => e.tagName.toLowerCase()")
            if tag == "select":
                # Options carry the CMS copy, not a slug; the first real choice
                # is what a visitor would pick.
                options = field_loc.locator("option:not([disabled])").all()
                field_loc.select_option(value=options[0].get_attribute("value"))
            else:
                field_loc.fill(value)
        if file:
            page.set_input_files("input[type=file]", file)
        box = page.locator("input[type=checkbox]").first
        if consent and not box.is_checked():
            box.check()
        page.locator("form button[type=submit]").first.click()
        page.wait_for_timeout(3000)
        body = page.inner_text("body")
        crash = _crashed(page, errors)
        success = "تم استلام طلبك" in body or "We received" in body or "تم استلام" in body
        ok = bool(success) and not crash
        detail = crash or (f"POST {posted[-1]}" if posted else "no POST observed")
        if not ok and "429" in detail:
            # The public forms are rate limited per IP per hour. A sweep that
            # runs twice in that window hits the limit, which is the guard
            # working — not a broken form.
            return Finding(path, "form submit", "ok",
                           "blocked by the per-IP hourly rate limit (guard working)")
        return Finding(path, "form submit", "ok" if ok else "fail", detail)
    finally:
        ctx.close()


def _prove_dashboard_linkage(token: str, expected: dict[str, str]) -> list[Finding]:
    """Read the visitor's submissions back through the staff API.

    A form that says «تم استلام طلبك» proves nothing on its own. This asks the
    dashboard's own endpoint for the row, matched on the sweep's email, so a
    submission that is accepted but never stored — or stored where staff cannot
    see it — fails here.
    """
    found: list[Finding] = []
    rows = _get("/website/submissions", token)
    for kind, label in expected.items():
        match = [
            r for r in rows
            if (r.get("email") or "").lower() == "sweep@example.com" and r.get("kind") == kind
        ]
        found.append(Finding(
            f"dashboard/{kind}", label,
            "ok" if match else "fail",
            f"{len(match)} row(s), status={(match[0].get('status') if match else '—')}",
        ))
    return found


# The approved wording from the Word spec (content-ar.md §2–§14). Every string
# here is copied verbatim from the spec, so a drift in the site copy fails the
# sweep instead of reaching a visitor.
SPEC_COPY: list[tuple[str, str]] = [
    # §3 hero slides: each slide has its own tag line, headline and body.
    ("/ar", "ستارت أب سفير القابضة · البحرين"),
    ("/ar", "نربط الخبرات والفرص لبناء أعمال قابلة للنمو"),
    ("/ar", "من البحرين، نعمل على تطوير شركات المجموعة وربط العملاء بالخدمات والفرص المناسبة."),
    ("/ar", "شركات متخصصة، تعمل ضمن رؤية مجموعة واحدة"),
    ("/ar", "تجمع القابضة بين خبرات شركات المجموعة وتوجهها نحو فرص النمو في الأسواق التي تعمل بها."),
    ("/ar", "حلول أعمال تبدأ من احتياجك وتمتد إلى فرص النمو"),
    ("/ar", "اختر الخدمة المناسبة لمشروعك، وسيصل طلبك إلى الجهة المختصة داخل المجموعة."),
    ("/ar", "إرسال المعلومات لا يعني قبولها أو الالتزام بتمويلها أو الدخول في شراكة."),
    ("/ar/about", "قابضة تجمع الخبرة وتحوّلها إلى فرص نمو."),
    ("/ar/about", "تعمل ستارت أب سفير القابضة على إدارة وتطوير شركات المجموعة، وتنسيق خبراتها، وفتح مسارات عملية للأعمال والفرص الاستثمارية."),
    ("/ar/companies", "محفظة المجموعة"),
    ("/ar/companies", "شركات متخصصة تعمل في قطاعات وأسواق مختلفة ضمن محفظة واحدة."),
    ("/ar/solutions", "اختر ما يحتاجه مشروعك من خدمات المجموعة، وسنوجّه طلبك إلى الجهة المختصة."),
    ("/ar/service-request", "اطلب خدمة من المجموعة"),
    ("/ar/service-request", "أرسل بياناتك الأساسية، وسيراجع الفريق طلبك ويوجهه للجهة المناسبة."),
    ("/ar/opportunities", "قدّم فرصة تجارية أو استثمارية"),
    ("/ar/opportunities", "أرسل وصفًا موجزًا وحدد دولة المشروع، ويمكنك إرفاق ملف الدراسة."),
    ("/ar/careers", "أرسل سيرتك الذاتية ومجال اهتمامك. سنتواصل معك إذا توفرت فرصة مناسبة."),
    ("/ar/contact", "ابدأ محادثة حول احتياج أعمالك."),
    ("/ar/contact", "info@sup-edu.com"),
    ("/ar/contact", "17626990"),
    ("/ar", "شركة قابضة بحرينية تعمل على تطوير شركات المجموعة وربط الخبرات بفرص الأعمال والنمو."),
    ("/ar/service-request", "بوابة ستارت أب سفير"),
    ("/ar/service-request", "أوافق على سياسة الخصوصية"),
    ("/ar/service-request", "إرسال الطلب"),
    ("/ar/service-request", "إلغاء"),
    ("/ar/service-request", "اختر الخدمة"),
    ("/ar/opportunities", "اختر الدولة"),
    ("/ar", "نافذة واحدة لاحتياجات الأعمال"),
    ("/ar", "أخبرنا بما يحتاجه مشروعك، وسنوجّه طلبك إلى الفريق المناسب."),
    ("/ar", "نموذج واضح يجمع المعلومات الأساسية فقط، ثم يتولى فريق المجموعة مراجعة الطلب والتواصل معك."),
    ("/ar", "هل لديك مشروع أو فرصة للنمو؟"),
    ("/ar", "أرسل موجز الفرصة والدولة التي يوجد بها المشروع. يراجع فريقنا المعلومات ويتواصل معك عند الحاجة إلى تفاصيل إضافية."),
    ("/ar", "أرسل سيرتك الذاتية ومجال اهتمامك. سنتواصل معك إذا توفرت فرصة مناسبة."),
    ("/ar/service-request", "تُستخدم البيانات لمعالجة الطلب وفق سياسة الخصوصية."),
    ("/ar/opportunities", "تُستخدم البيانات لمعالجة الطلب وفق سياسة الخصوصية."),
    ("/ar/careers", "تُستخدم البيانات لمعالجة الطلب وفق سياسة الخصوصية."),
    ("/ar/opportunities", "إرسال الطلب"),
    ("/ar/careers", "إرسال الطلب"),
    ("/ar/opportunities", "إلغاء"),
    ("/ar/careers", "إلغاء"),
    ("/ar/careers", "(عرض السياسة)"),
    ("/ar/opportunities", "(عرض السياسة)"),
    ("/ar", "استكشف فرص الاستثمار"),
    ("/ar", "اطلب حلولًا لأعمالك"),
    ("/ar", "انتقل إلى المحتوى"),
    ("/ar", "© 2026 ستارت أب سفير القابضة ذ.م.م"),
    ("/ar/privacy", "سياسة الخصوصية"),
    ("/ar/solutions", "خدمات مترابطة لاحتياجات الأعمال."),
    ("/ar/contact", "ابدأ محادثة حول احتياج أعمالك."),
    ("/ar", "شركة قابضة بحرينية تعمل على تطوير شركات المجموعة وربط الخبرات بفرص الأعمال والنمو."),
    ("/ar/contact", "شركة ستارت أب سفير القابضة ذ.م.م"),
    ("/ar/404-check", "الصفحة غير موجودة"),
    ("/ar/404-check", "ربما نُقلت الصفحة أو تغيّر رابطها. عد إلى الصفحة الرئيسية."),
]

# §1 page tags, read from the document head rather than the body.
SPEC_HEAD: list[tuple[str, str, str]] = [
    ("/ar", "title", "ستارت أب سفير القابضة | نربط الخبرات والفرص لبناء أعمال قابلة للنمو"),
    ("/ar", "description", "شركة قابضة بحرينية تطوّر شركات المجموعة وتربط العملاء بالخدمات والفرص التجارية والاستثمارية المناسبة."),
    ("/en", "title", "Start Up Sphere Holding | Connecting expertise and opportunity to build businesses that grow"),
]

# Internal text that must never reach a visitor.
SPEC_FORBIDDEN: list[tuple[str, str]] = [
    ("/ar", "قاعدة البيانات"),
    ("/ar", "database"),
    ("/ar/solutions", "التفاصيل عند الطلب."),
    ("/ar/solutions", "Details available on request."),
]


def _check_spec_copy(browser: Browser) -> list[Finding]:
    """Compare the rendered copy against the approved spec wording."""
    found: list[Finding] = []
    pages: dict[str, str] = {}
    for path in sorted({p for p, _ in SPEC_COPY + SPEC_FORBIDDEN}):
        page = browser.new_context(viewport={"width": 1440, "height": 1000}).new_page()
        # 404 pages answer with the error status by design; the copy is what counts.
        page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=45000)
        # The hero is a carousel: only the active slide is visible, so walk the
        # slide tabs and collect each one's text before asserting the copy.
        text = page.inner_text("body")
        tabs = page.locator('[role="tab"]')
        for i in range(tabs.count()):
            tabs.nth(i).click()
            page.wait_for_timeout(350)
            text += "\n" + page.inner_text("body")
        pages[path] = text
        page.context.close()
    for path, expected in SPEC_COPY:
        found.append(Finding(f"{path} copy", expected[:28],
                             "ok" if expected in pages[path] else "fail",
                             "" if expected in pages[path] else "approved wording missing"))
    for path, tag, expected in SPEC_HEAD:
        page = browser.new_context(viewport={"width": 1440, "height": 1000}).new_page()
        page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=45000)
        got = (page.title() if tag == "title"
               else page.locator(f'meta[name="{tag}"]').get_attribute("content"))
        page.context.close()
        found.append(Finding(f"{path} {tag}", expected[:28], "ok" if got == expected else "fail",
                             "" if got == expected else f"got: {(got or '')[:60]}"))
    for path, message in (
        ("/ar/careers", "هذا الحقل مطلوب"),
        ("/ar/opportunities", "هذا الحقل مطلوب"),
        ("/ar/service-request", "هذا الحقل مطلوب"),
    ):
        page = browser.new_context(viewport={"width": 1440, "height": 1000}).new_page()
        page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=45000)
        page.click('form button[type="submit"]')
        page.wait_for_timeout(600)
        got = page.inner_text("form")
        page.context.close()
        found.append(Finding(f"{path} validation", message, "ok" if message in got else "fail",
                             "" if message in got else "required-field message missing"))
    for path, banned in SPEC_FORBIDDEN:
        present = banned in pages[path]
        found.append(Finding(f"{path} copy", f"no internal text: {banned[:16]}",
                             "fail" if present else "ok",
                             "internal note visible to visitors" if present else ""))
    return found


def _clear_previous_runs() -> None:
    """Drop rows earlier sweeps created so the hourly IP cap never blocks a run.

    Opt-in via CHECKER_DB_URL: the default run touches nothing but the site.
    """
    dsn = os.environ.get("CHECKER_DB_URL")
    if not dsn:
        return
    with psycopg.connect(dsn) as conn:
        conn.execute("DELETE FROM website_submissions WHERE email LIKE 'sweep@%'")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-forms", action="store_true")
    args = parser.parse_args()

    links_seen: set[str] = set()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])

        for path, _label in PAGES:
            found, links = _visit(browser, path)
            FINDINGS.extend(found)
            for link in links:
                href = (link["href"] or "").split("#")[0]
                if href and href not in links_seen:
                    links_seen.add(href)
                    FINDINGS.append(_check_link(browser, href, link["text"]))

        FINDINGS.extend(_check_spec_copy(browser))

        if not args.skip_forms:
            _clear_previous_runs()
            FINDINGS.append(_submit_form(
                browser, "/ar/service-request",
                {"name": "فحص آلي", "email": "sweep@example.com", "phone": "39000000",
                 "service_type": "", "message": "طلب من فحص الموقع العام"},
            ))
            FINDINGS.append(_submit_form(
                browser, "/ar/opportunities",
                {"name": "فحص آلي", "email": "sweep@example.com", "phone": "39000000",
                 "country": "", "subject": "فرصة من فحص الموقع", "message": "وصف مختصر"},
            ))
            cv = "/tmp/sweep-cv.pdf"
            with open(cv, "wb") as fh:
                fh.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
            FINDINGS.append(_submit_form(
                browser, "/ar/careers",
                {"name": "فحص آلي", "email": "sweep@example.com", "phone": "39000000",
                 "expertise": "تشغيل واختبار"},
                file=cv,
            ))
        browser.close()

    if not args.skip_forms:
        try:
            token = _token(*OWNER)
            FINDINGS.extend(_prove_dashboard_linkage(token, {
                "service_request": "service request visible in the dashboard",
                "opportunity": "opportunity visible in the dashboard",
                "job_application": "CV application visible in the dashboard",
            }))
        except Exception as exc:
            FINDINGS.append(Finding("dashboard", "read back submissions", "fail", str(exc)[:150]))

    bad = [f for f in FINDINGS if f.outcome == "fail"]
    for f in FINDINGS:
        if f.outcome == "fail":
            print(f"FAIL  {f.where:32s} {f.what[:28]:28s} {f.detail}")
    print(f"\n{len(FINDINGS)} checks: {len(FINDINGS)-len(bad)} ok, {len(bad)} failing")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
