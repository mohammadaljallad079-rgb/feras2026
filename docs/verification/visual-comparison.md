# Visual comparison record

For each design-reference page: the reference image, the implemented route, the
implementation capture, the mismatches found and how each was resolved.

- Reference images: `docs/screenshots/pdf/page-NN.png` (rendered from
  `platform-design-ar.pdf`, repository root).
- Implementation captures: `docs/screenshots/impl/<page>-<screen>.png`, produced
  by `scripts/capture_screens.py` against the live app (real PostgreSQL data).
- Capture viewport: 1440×1000, full page. Mobile pass at 400px in §3.

Where the reference micro-copy is not legible enough to transcribe exactly, the
row says so rather than inventing a wording.

## 1. Screen-by-screen

| PDF page | Implemented route | Reference | Implementation | Mismatches found | Resolution | Status |
|---|---|---|---|---|---|---|
| 5 | `/dashboard` (owner) | `pdf/page-05.png` | `impl/05-owner-dashboard.png` | KPI set and order matched; group-summary table matched | — | Verified |
| 6 | `/companies` | `pdf/page-06.png` | `impl/06-companies.png` | Columns (logo, code, country, sector, manager, ownership, status) and the three header actions matched | — | Verified |
| 7 | `/companies/new` | `pdf/page-07.png` | `impl/07-company-wizard.png` | Three steps («1/3» basic data, «2/3» contact and management, «3/3» holding relationship with the review), draft save and final review matched | — | Verified |
| 8 | `/reports` (owner) | `pdf/page-08.png` | `impl/08-owner-reports.png` | Owner saw every draft; the reference shows only reports sent to management. Table 8 also marks «معتمد» as the accountant's, so the owner must not see a merely approved report either | `reporting.py` now restricts a `report:view_all` holder without `report:review` to `forwarded` (sent to management) on the list, detail, history and export routes; the owner template no longer carries the accountant's review/forward duties. The Holding's report stays reachable by its author, the business developer (§7.1) | Fixed |
| 9 | `/accounting` | `pdf/page-09.png` | `impl/09-accounting.png` | Three sections (expenses, invoices, commissions) and the per-section columns matched | — | Verified |
| 10 | `/service-requests` | `pdf/page-10.png` | `impl/10-service-requests.png` | Card per request with subject, status, company, recipient, priority, deadline, reply thread and status control matched | — | Verified |
| 11 | `/leads` | `pdf/page-11.png` | `impl/11-leads.png` | The three narrowing controls (all companies / all statuses / all sources) were absent | Added the three filters above the table plus a `filter` prop on `ResourceTable`; column order matches the reference | Fixed |
| 12 | `/opportunities` | `pdf/page-12.png` | `impl/12-opportunities.png` | Title was the short «الفرص»; the reference heading is «الفرص التجارية والاستثمارية». The reference also notes approval creates no project. The table listed topic, country, file, source, company, value, status and decision date, but the reference columns are topic, country, file, source, status and reason — the recorded reason was not shown | Title corrected; the screen states that a decision records the decision and timestamp only; a «السبب» column now prints `decision_note` beside the status | Fixed |
| 13 | `/directives` | `pdf/page-13.png` | `impl/13-directives.png` | Sent / received / completed / overdue indicators and the escalation record matched | — | Verified |
| 14 | `/hr` | `pdf/page-14.png` | `impl/14-hr.png` | The reference §5.1 asks for «جداول مستقلة لكل شركة وللقابضة» (a separate table for each company **and for the Holding**), but the screen rendered only the subsidiaries' tables; salary was also returned to any holder of `hr:view`, and leave attachments (which the reference says read «مرفق مقيد» to the owner) were downloadable by the owner | The screen requests `?include_holding=true` and renders the Holding's own employee table alongside the subsidiaries. `hr:view_salary` was added to the permission catalog and enforced in `hr.py`; the UI prints «مقيد» without the amount when it is not permitted. The owner template no longer carries `hr:view_confidential`, so a confidential attachment reads «مرفق مقيد» to the owner and downloads only for the manager who filed it; the employee-event form gained the upload control that makes the state reachable | Fixed |
| 15 | `/website` | `pdf/page-15.png` | `impl/15-website.png` | Public inbox and conversion actions matched, but the companies-shown table carried company, activity, sector, status and actions, while the reference columns are company, logo, activity, country and action — the logo and country were missing | The table now shows the uploaded logo (or «بلا شعار») and the country in place of the sector column | Fixed |
| 16 | `/advisor` | `pdf/page-16.png` | `impl/16-advisor.png` | Company select plus the النوع / العنوان / النص / إلى columns matched | — | Verified |
| 17 | `/assistant` | `pdf/page-17.png` | `impl/17-assistant.png` | Provider settings (masked key, connection test, model class) and grounded answers with sources and confidence matched | — | Verified |
| 18 | `/form-builder` | `pdf/page-18.png` | `impl/18-form-builder.png` | Subfields were rendered without the reference's arrow marker | Report form renders a child field indented with a «↳» marker and sorts children under their parent | Fixed |
| 19 | `/users` | `pdf/page-19.png` | `impl/19-users.png` | Users, multiple roles, company scope, status and permission assignment matched | — | Verified |
| 20 | `/users/new` | `pdf/page-20.png` | `impl/20-user-new.png` | Invitation fields and the password-setup link matched | — | Verified |
| 21 | `/audit` | `pdf/page-21.png` | `impl/21-audit.png` | Read-only log with timestamp, user, role, action, target and company scope matched | — | Verified |
| 22 | `/dashboard` (manager) | `pdf/page-22.png` | `impl/22-manager-dashboard.png` | The period banner and the five action buttons were missing; only four KPI cards were shown | `DashboardOut` gained `banner_ar/en` and `actions`; the manager dashboard now shows «تقرير YYYY-MM — <company>: يستحق بعد N أيام» and the five actions from the reference | Fixed |
| 22 | `/dashboard` (manager) | `pdf/page-22.png` | `impl/22-manager-dashboard.png` | The deadline banner was a neutral grey strip, but §2 makes a reminder an alert — amber while the deadline approaches and red once it is late | The banner now carries a `banner_tone` (`warn`/`bad`) and renders with the matching §2 alert colours, covered by `test_manager_deadline_reminder_alert_is_toned_by_urgency` | Fixed |
| 23 | `/reports/[id]` (manager) | `pdf/page-23.png` | `impl/23-report-submission.png` | No upload control for the mandatory bank statement | The report screen now has a required bank-statement field with upload, an «مرفق» chip and a download button; the API already rejects submission without it | Fixed |
| 23 | `/reports/[id]` (manager) | `pdf/page-23.png` | `impl/23-report-submission.png` | A report returned for correction carried `returned_reason` in the API, but the screen never showed it, although Table 8 requires the reason «يظهر السبب في تنبيه أعلى الصفحة» | The report screen prints the accountant's reason in a warning alert at the top whenever the status is «أُعيد للتعديل», so the manager sees why before editing and resubmitting | Fixed |
| 24 | `/dashboard` (accountant) | `pdf/page-24.png` | `impl/24-accountant-dashboard.png` | The dashboard carried three separate entry buttons, but Table 3 and §5.3 name a single button «مصروف / فاتورة / عمولة جديدة» that opens holding accounting, where the three forms live (Table 5) | The dashboard now has the two actions the brief names — «مراجعة تقرير» and «مصروف / فاتورة / عمولة جديدة» — and the accounting screen keeps the three separate entry buttons, each opening its form with the kind pre-selected via `?kind=`. Covered by `test_accountant_dashboard_actions_open_the_named_screens` and `test_s5_3_the_three_entry_kinds_exist` | Fixed |
| 25 | `/reports/[id]` (accountant) | `pdf/page-25.png` | `impl/25-report-review.png` | The screen rendered its controls, but every one of them failed on the server: the accountant could not open a submitted report at all, and the Excel export answered 403 | `GET /reports/{id}` and `/history` now accept `report:view_all`, which is what the accountant holds; `report:export` was added to the permission catalog and to the accountant template. An earlier pass called this page Verified on the strength of the controls rendering, which was wrong — a control that always 403s is not working | Fixed |
| 26 | `/dashboard` (business developer) | `pdf/page-26.png` | `impl/26-bd-dashboard.png` | Six cards matched | — | Verified |
| 27 | `/dashboard` (marketer) | `pdf/page-27.png` | `impl/27-marketer-dashboard.png` | Assigned leads and owner complaints matched | — | Verified |
| 28 | `/dashboard` (designer) | `pdf/page-28.png` | `impl/28-designer-dashboard.png` | Assigned design requests only | — | Verified |
| 29 | `/dashboard` (advisor) | `pdf/page-29.png` | `impl/29-advisor-dashboard.png` | Own messages only | — | Verified |
| 30 | responsive shell | `pdf/page-30.png` | `impl/30-owner-dashboard-mobile.png`, `impl/30-manager-dashboard-mobile.png` | Breakpoint and min-width matched | — | Verified |
| 31 | `en` locale | `pdf/page-31.png` | `impl/31-owner-dashboard-en.png`, `impl/31-companies-en.png` | Sidebar moves to the left, labels translate fully, numbers keep LTR direction | — | Verified |
| 32 | dark theme | `pdf/page-32.png` | `impl/32-NN-<screen>-dark.png` (17 screens) | Dark tokens applied verbatim | Every screen captured in dark mode; the first pixel of the dark dashboard is `#111d30`, the dark `--card` token, against white in light mode | Verified |

## 2. Deliberate non-matches

- **Simulation controls.** Every reference screenshot carries a prototype banner
  (role switcher, "demo data" note, "no email is sent"). The specification
  forbids these in production, so they are intentionally absent from every
  capture.
- **Public website.** The reference covers the management platform only, so no
  public-site screen is presented as visually faithful.
- **Logo.** `assets/brand/holding-logo.png` was supplied later; it is committed
  at `frontend/public/brand/holding-logo.png` and `BrandMark` renders it. The
  `data-logo="missing"` fallback remains only as a guard so the placeholder
  cannot silently reappear; a browser assertion fails if it does.

## 3. Mobile pass (400px)

The shell collapses the sidebar into a drawer below 820px and the page never
scrolls horizontally at 400px; wide tables scroll inside their own container
(`.table-scroll`). The reference's mobile panels (owner and manager) correspond
to the same dashboard routes at the narrow viewport.

Checked rather than assumed: `scripts/check_mobile.py` walks the nine main
routes at a 400px viewport and compares `documentElement.scrollWidth` with
`clientWidth`. All nine report `400 = 400`, so there is no horizontal page
scroll.

```
/dashboard /companies /leads /reports /hr /users /audit /accounting /service-requests
HORIZONTAL OVERFLOW AT 400px: none
```

## 4. Dark mode coverage (page 32)

Every screen is captured in dark mode (`impl/32-NN-<screen>-dark.png`, 17
screens). The tokens come from the specification verbatim; sampling the first
pixel of the dark owner dashboard returns `#111d30`, the dark `--card` token,
against `#ffffff` in light mode, which confirms the theme is actually applied
rather than merely toggled.

## 5. How to reproduce

```
# backend on :8000 (seeded), frontend on :12000
python3 scripts/capture_screens.py    # 46 captures: roles, locales, dark, mobile
python3 scripts/check_mobile.py       # asserts no horizontal scroll at 400px
```

The script signs in as each demo role, switches locale/theme, and writes one
full-page PNG per row of §1 into `docs/screenshots/impl/`.

## 6. Page-32 designer items — visual verification

The reference's final page lists outstanding design work. Four of those items
are now delivered and were checked against the running application, not assumed:

- **Licensed Arabic font.** Tajawal (SIL OFL 1.1) is self-hosted from
  `frontend/public/fonts/` and applied only to the Arabic interface. In the
  browser the three weights report `status: "loaded"` and the computed Arabic
  `font-family` is `Tajawal, system-ui, "Segoe UI", Tahoma, sans-serif`; the
  English interface keeps `system-ui, "Segoe UI", Tahoma, sans-serif`, which is
  the stack the reference names.
- **Sidebar icon system.** `components/NavIcon.tsx` supplies the glyphs; every
  one of the 15 nav entries renders an 18×18 `svg` that inherits `currentColor`,
  with no icon font and no network request.
- **Active navigation item.** The reference marks the current entry with the gold
  accent (`--gold`, "العنصر النشط في القائمة"). The item is now a gold pill with
  ink text, not a tint of the sidebar colour. Sampling the owner dashboard
  confirms the pill: gold pixels occupy x 1215–1424, a 37px-tall row on the
  sidebar, matching the reference's gold band (rows 197–233 of page 5).
- **Official brand logo.** The supplied asset
  `frontend/public/brand/holding-logo.png` (245×132) now ships and renders on
  every screen. It is used exactly as supplied — never recoloured, cropped or
  redrawn — and only its rendered height is constrained, so the artwork keeps
  its own aspect ratio (`width / height` measures 1.856 against the file's
  1.856). The artwork is dark teal on transparency (opaque pixels average RGB
  42/124/142), so it reads on a light card but not on the navy sidebar: measured
  against `#0b192c` it reaches only 3.85:1 on average, with 22.4% of its opaque
  pixels below the 3:1 that WCAG 1.4.11 asks of a graphical object. On a white
  plate those same pixels measure 4.83:1 with 4.9% below 3:1, so
  `components/BrandMark.tsx` seats the mark on a light plate there instead of
  recolouring it — the usual way a light-background logo is carried on dark
  chrome. The reference's sidebar header is navy with a light-tone logo (page 5,
  the top ~64 rows of the sidebar band are `#0b192c`), so the plate is a
  legibility device forced by the supplied artwork's own colours, not a
  redesign. The name is no longer printed beside the mark on the auth cards,
  because the artwork already carries the wordmark in both scripts. The browser
  assertions in `scripts/check_visual_fixes.py` ("page 32 — official brand
  logo") cover the sidebar, the auth cards, the aspect ratio, the plate and the
  absence of a placeholder.
- **Global loading and error states, login and password screens.** `app/loading.tsx`
  and `app/error.tsx` render bilingual, generic states; `/login`,
  `/forgot-password` and `/reset-password` all answer 200. The error state logs
  only the digest, never the message, which may carry protected data.
- **Account emails.** `backend/app/services/mail.py` produces bilingual reset and
  invitation messages, each with exactly one secure `/reset-password?token=` link
  and no amount, currency or report value.

Captures for these states are in `docs/screenshots/deliverables/`:
`login-ar-desktop.png`, `dashboard-ar-desktop.png`, `dashboard-ar-dark.png`,
`dashboard-en-desktop.png`, `dashboard-ar-mobile-400.png`.

All five page-32 designer items are now delivered; see
`docs/verification/reference-asset-blocker.md` for the asset history.
