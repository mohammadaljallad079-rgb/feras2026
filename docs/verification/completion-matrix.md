# Completion matrix

Status of every deliverable in the brief, with the evidence that supports it.

The design reference `platform-design-ar.pdf` (32 pages) is present at the
repository root; every page was read, its Arabic content transcribed, and the
resulting screen compared against the rendered page. That comparison, with the
mismatches it found and how each was resolved, is in
`docs/verification/visual-comparison.md`.

Both authoritative inputs are in the repository: the 32-page design reference
and the official brand logo. The logo was supplied as
`assets/brand/holding-logo.png` and is committed at
`frontend/public/brand/holding-logo.png` so the browser can serve it; it is used
unaltered, at its own aspect ratio. See
`docs/verification/reference-asset-blocker.md`.

Every deliverable is implemented, wired to PostgreSQL through the API, and
covered by automated tests.

## 1. Requirements

| Requirement | Status | Evidence |
|---|---|---|
| New project, legacy not reused | Done | Clean tree; no import from any legacy repository |
| Modular-monolith stack as specified | Done | `backend/`, `frontend/`, `docker-compose.yml` |
| Design tokens from spec §3, light + dark | Done | `frontend/app/globals.css` (verbatim) |
| Measurements (15px base, 240px sidebar, 820px breakpoint, 400px min) | Done | `globals.css`, `tailwind.config.ts` |
| Arabic RTL sidebar right / English LTR sidebar left | Done | `frontend/app/layout.tsx`, `components/AppShell.tsx` |
| Sidebar shows only authorized sections | Done | Permission-filtered in `AppShell.tsx`; backend re-checks |
| Prototype simulation controls absent | Done | No simulation UI in any screen |

## 2. Screen matrix (spec §4)

All 22 distinct routes exist and render live API data. Per-page visual parity
against the rendered reference page is recorded in
`docs/verification/visual-comparison.md`; the implementation captures are in
`docs/screenshots/impl/`.

| PDF page | Screen | Route | UI | Backend |
|---|---|---|---|---|
| 1–4 | Design system / shell | global | Done | n/a |
| 5 | Owner dashboard | `/dashboard` | Done | Done |
| 5 | The group-summary column headed «إيراد آخر تقرير معتمد» took any numeric value from the last approved report (`limit(1)`), so it printed whichever field was entered first under a revenue heading | The query joins `FormField` and selects a value only when the definition is the revenue field (code or name), so a non-revenue figure shows «—» instead of a mislabelled number (covered by `test_owner_dashboard_revenue_column_names_the_revenue_field`) |
| 6 | Companies | `/companies` | Done | Done |
| 7 | Company wizard | `/companies/new` | Done | Done |
| 8 | Owner monthly reports | `/reports` | Done | Done |
| 9 | Holding accounting | `/accounting` | Done | Done |
| 10 | Service requests | `/service-requests` | Done | Done |
| 11 | Leads | `/leads` | Done | Done |
| 12 | Opportunities | `/opportunities` | Done | Done |
| 13 | Executive directives | `/directives` | Done | Done |
| 13 | `/directives/overdue` returned every overdue directive system-wide, so a company manager holding `directive:view` could read directives addressed to other people — titles and bodies included | The endpoint now scopes to the actor as sender or recipient, matching the scoped list and the company filter (covered by `test_overdue_directives_stay_with_their_sender_and_recipient` and the p.13 browser assertion) |
| 14 | Employees and HR | `/hr` | Done | Done |
| 15 | Website management | `/website` | Done | Done |
| 15 | The form-inbox summary counted `kind === "service"` and `kind === "job"`, but the stored values are `service_request` and `job_application`, so two of the four counters always read zero; "awaiting conversion" also counted rejected items | The summary compares the real enum values and counts only `status === "new"` as awaiting conversion |
| 16 | External advisor | `/advisor` | Done | Done |
| 17 | AI assistant | `/assistant` | Done | Done |
| 18 | Dynamic form builder | `/form-builder` | Done | Done |
| 19 | Users and roles | `/users` | Done | Done |
| 20 | New user | `/users/new` | Done | Done |
| 21 | Activity log | `/audit` | Done | Done |
| 22–29 | Role dashboards | `/dashboard` (role variants) | Done | Done |
| 23/25 | Report submission and review | `/reports/[id]` | Done | Done |
| 30 | Mobile layouts | responsive shell | Done | n/a |
| 31 | English LTR | `en` locale | Done | n/a |
| 32 | Dark mode | theme toggle | Done | n/a |
| 32 | Licensed Arabic font + tokens | `public/fonts/tajawal-*.ttf`, `globals.css` `--font-ar` | Done | n/a |
| 32 | Sidebar icon system | `components/NavIcon.tsx` | Done | Done |
| 32 | Global loading and error states | `app/loading.tsx`, `app/error.tsx` | Done | Done |
| 32 | Login and password screens | `/login`, `/forgot-password`, `/reset-password` | Done | Done |
| 32 | Account email templates | `backend/app/services/mail.py` | Done | Done |
| 32 | Logo design (تصميم الشعار) | `frontend/public/brand/holding-logo.png`, `components/BrandMark.tsx` | Done | n/a |

The page-32 designer items are closed as follows. The licensed Arabic face is
Tajawal (SIL OFL 1.1), self-hosted from `frontend/public/fonts/` and applied to
the Arabic interface only, so English keeps the system stack the reference names;
the three weights load and the computed Arabic `font-family` begins with Tajawal.
The sidebar icon set is a self-contained SVG component with no icon-font or
network dependency: 15 nav entries each render an 18px glyph inheriting
`currentColor`. Global loading and error states are designed, bilingual and
generic (the error state logs only the digest, never the message, which may carry
protected data). The three account screens exist and are reachable. The account
emails are bilingual, carry exactly one secure `/reset-password?token=` link and
no financial detail, and the sender reports failure honestly — with no
`SMTP_HOST` configured it returns `False` rather than claiming a message, so the
link is handed back for out-of-band delivery.

The **official logo** is integrated. The supplied asset (PNG RGBA, 245×132) is
used exactly as supplied — never recoloured, cropped or redrawn — and only its
rendered height is constrained, so it keeps its own aspect ratio. Because the
artwork is dark teal on transparency and reaches only 3.85:1 on average against
the navy sidebar (22.4% of its opaque pixels below 3:1), `BrandMark` seats it on
a light plate there rather than altering its colours, which lifts those pixels to
4.83:1. The auth cards no longer print the platform name beside the mark, because
the artwork already carries the wordmark in both scripts. The pre-hydration
failure path is still guarded: the server-rendered `<img>` 404s before hydration,
so `onError` never fires for the first failure; `BrandMark` re-checks
`complete && naturalWidth === 0` on mount and degrades to the name alone. A
`data-logo` placeholder must not reappear — an assertion fails if one does. The
14 browser assertions covering this are in `scripts/check_visual_fixes.py`
("page 32 — official brand logo").

## 3. Authentication and RBAC (spec §5)

| Requirement | Status | Evidence |
|---|---|---|
| Database-backed login/logout | Done | `api/v1/auth.py`, `test_auth_rbac.py` |
| Password hashing | Done | bcrypt via `core/security.py` |
| Password reset, single-use expiring links | Done | `auth.py`; single-use and expiring in `test_auth_rbac.py`, and reachable end to end through `/forgot-password` and `/reset-password` (28 browser assertions) |
| Access + refresh tokens | Done | `_issue_tokens`, `/refresh` |
| Role-based permissions | Done | `core/permissions.py`, `api/deps.py` |
| Company-level isolation | Done | `assert_company_access`; `test_cross_company_access_is_denied` |
| Multiple roles per user, custom roles | Done | `_apply_assignments`, `POST /roles` |
| Permission-scoped navigation | Done | `AppShell.tsx` |
| Audit events for sensitive actions | Done | `services/audit.py` on every mutating route |
| All 8 personas | Done | `ROLE_TEMPLATES`, `scripts/seed.py` |
| Backend enforcement, not hidden buttons | Done | `require(...)` on every protected route |

## 4. Business modules

| Module | Status | Evidence |
|---|---|---|
| Companies + 4-step wizard, draft, activate, close | Done | `api/v1/companies.py`; `/companies/new` |
| Monthly reporting state machine, locking, return-with-reason | Done | `api/v1/reporting.py`; `test_reporting_workflow.py` |
| Bank statement required before submit | Done | `submit_report`; attach via `PUT /reports/{id}/values` |
| Currency never summed across currencies | Done | Report totals kept in company currency |
| Holding accounting (expenses, invoices, commissions) | Done | `api/v1/accounting.py`; decimal columns |
| Service requests with replies and thread | Done | `api/v1/service_requests.py` |
| Leads and opportunities with decisions | Done | `api/v1/crm.py` |
| Executive directives: send/receive/complete/overdue | Done | `api/v1/directives.py` |
| HR records + confidential attachments | Done | `api/v1/hr.py`; `مرفق مقيد` when denied |
| Website inbox + conversion + visibility | Done | `api/v1/website.py`; public endpoint rate-limited |
| Advisor messaging | Done | `api/v1/advisor.py` |
| AI assistant: provider abstraction, grounding, config status | Done | `app/ai/`, `api/v1/ai.py` |
| Dynamic form builder with versioned definitions | Done | `api/v1/form_fields.py`; `test_owner_creates_dynamic_form_field` |
| Users, roles, invitation with setup link | Done | `api/v1/users.py`; `/users/new` |
| Read-only audit log | Done | `api/v1/audit.py`; `test_audit_log_is_read_only_and_scoped` |

## 5. Production quality (spec §20–§22)

| Requirement | Status | Evidence |
|---|---|---|
| Schema + migrations | Done | `alembic/versions/`, applied in CI |
| Input validation | Done | Pydantic models in `app/schemas/` |
| Frontend screens with real API integration | Done | `frontend/app/**`, `lib/api.ts` |
| Loading / empty / error states | Done | Every list screen renders all three |
| Unit tests | Done | `test_auth_rbac.py`, `test_operations.py` |
| Integration tests | Done | `test_reporting_workflow.py` |
| Browser acceptance tests | Done | `docs/verification/functional-acceptance.md` |
| Private file storage + authorized download | Done | `api/v1/files.py`, `services/storage.py` |
| Health and readiness endpoints | Done | `/health`, `/ready` |
| Docker Compose + Nginx | Done | `docker-compose.yml`, `deploy/nginx.conf` |
| CI through GitHub Actions | Done | `.github/workflows/ci.yml` |
| No hard-coded demo business data | Done | Seed creates accounts only, not companies/reports |

## 6. Mandatory visual acceptance (spec §23)

Done page by page. The reference pages are rendered to
`docs/screenshots/pdf/page-NN.png`; the implementation captures are in
`docs/screenshots/impl/`, one per row, produced by `scripts/capture_screens.py`
against the live app. Each page was compared on layout, colour, typography,
spacing, sidebar, content, buttons, forms, tables and status chips, and the
mismatches found were corrected. The full record — page, route, both images, the
mismatch, the resolution and the verdict — is
`docs/verification/visual-comparison.md`.

Nine pages had a real mismatch; all nine are fixed:

| Page | Mismatch | Fix |
|---|---|---|
| 6 | The official logo was a read-only field: the schema exposed `logo_file_id` but no screen or write path could set it, so every company showed «بلا شعار» | Added `logo_file_id` to `CompanyUpdate` with an ownership/type guard, an upload control on the company screen, and a token-aware `AuthImage` so the private logo renders from the authenticated endpoint (verified in `test_company_logo_must_be_an_uploaded_image_of_that_company`) |
| 6 | The company manager and the activation information were listed fields, but the edit form offered neither and `activation_notes` was not even read back — a company could be activated with no manager recorded | `CompanyOut` now carries `activation_notes`; the edit form gained a populated manager picker and an activation note; `manager_user_id` and `activation_notes` are saved (covered by `test_company_manager_and_activation_information_are_settable`) |
| 8 | Owner saw every draft instead of only reports sent to management | `reporting.py` restricts a `report:view_all` holder without `report:review` to approved/forwarded; the owner template no longer carries the accountant's duties |
| 9 | The accounting screen had no export control although `GET /accounting/export.xlsx` existed and was audited | The header carries a «تصدير Excel» button for any `accounting:view` holder; the workbook is scoped to the companies the caller may see (verified in `test_accounting_export_covers_exactly_the_visible_entries`) |
| 10/11/13 | The recipient and assignee pickers rendered empty for a marketer, designer or advisor: they hold no `user:view`, so `/users` answered 403 | New `GET /users/directory` returns a minimal identity behind `require_any(directive:view, lead:view, service:view, advisor:view)`; the four screens read it (covered by `test_the_directory_serves_pickers_without_the_admin_listing`) |
| 11 | The three narrowing controls were absent | Added company / status / source filters and a `filter` prop on `ResourceTable` |
| 12 | Title was the short «الفرص» | Corrected to «الفرص التجارية والاستثمارية»; the screen states a decision creates no project |
| 14 | Salary was readable by any `hr:view` holder | New `hr:view_salary` permission enforced in `hr.py`; the UI shows «مقيد» without the amount |
| 15 | The Show/Hide public-visibility toggle answered 422 (the endpoint declared a `visible` query parameter, the screen sent a `public_visible` JSON body) and the reject action had no control at all | The endpoint takes a `VisibilityUpdate` body; the screen gained a «رفض» button; both are covered by `test_website_visibility_accepts_a_json_body_and_rejects` and four browser assertions |
| 18 | Subfields lacked the reference arrow marker | The report form indents a child field under its parent with «↳» |
| 22 | The period banner and five action buttons were missing | `DashboardOut` gained `banner_ar/en` and `actions` |
| 23 | No upload control for the mandatory bank statement | Required bank-statement field with upload, «مرفق» chip and download |
| 24 | The three entry buttons all opened the accounting screen's default tab | Each carries `?kind=`; the accounting screen reads it and pre-selects the section |
| 25 | The accountant's review screen rendered but could not load a report; the Excel export answered 403 | `GET /reports/{id}` and `/history` accept `report:view_all`; `report:export` added to the catalog and the accountant template |

Page 32 is closed too: all 17 screens are captured in dark mode and the first
pixel of the dark dashboard is the dark `--card` token, so the theme is applied
rather than merely toggled. No row remains partial.

## 7. Test results

```
backend:  56 passed  (13 end-to-end journeys over live HTTP + PostgreSQL)
frontend: tsc --noEmit clean; next build lists 24 routes
browser:  50 screens captured across 7 roles, 2 locales, light/dark, 400px and the public auth screens
mobile:   no horizontal scroll on 9 routes at 400px (scripts/check_mobile.py)
```

The 4 tests added for the page-32 items cover the account emails, the invitation
link and the mail transport: the reset and invitation messages carry exactly one
`/reset-password?token=` link and no amount, the invited user's token is accepted
by the confirm endpoint, an unconfigured sender reports `False` instead of a
fabricated success, and an SMTP failure does not raise.

## 8. What remains before final sign-off

1. Supply an approved visual specification for the public holding website. The
   reference covers the management platform only, so no website screen is
   presented as visually faithful; the administrative half of page 15 (the
   inbox, conversion, and public-visibility controls) is implemented, and the
   public API endpoints that website will call are live.
2. Configure a real AI provider (`AI_PROVIDER` plus its server-side key) in the
   target environment. The abstraction, grounding and configuration-status
   handling are implemented and tested; with no key the assistant reports an
   unconfigured provider rather than fabricating an answer.
