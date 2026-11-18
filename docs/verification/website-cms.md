# Public website + CMS — verification record

Scope: the public corporate website for **START UP SPHERE HOLDING CO W.L.L**, the
CMS that drives it, and the `/platform` admin restructure that made room for it.

Everything below was exercised against a live stack: FastAPI on `:8000` against
PostgreSQL `safir_e2e`, Next.js on `:12000`, Chromium via Playwright.

## 1. Backend test suite

```
TEST_DATABASE_URL=postgresql+psycopg://safir:safir@127.0.0.1:5432/safir_test pytest
85 passed
```

New file `backend/tests/test_site_cms.py` (8 tests) covers:

| Test | What it proves |
|---|---|
| `test_public_site_serves_seeded_content` | `/api/v1/public/site` returns settings, sections, slides, services, header nav and the opportunity country list |
| `test_public_site_lists_only_published_companies` | A company needs **both** `status=active` **and** `public_visible=true`; unpublishing removes it again |
| `test_setting_edit_reaches_the_public_endpoint` | An owner edit to a setting is visible on `/api/v1/public/site` |
| `test_section_and_slide_and_service_and_nav_edits_persist` | All four content types accept and keep an edit |
| `test_hidden_section_is_not_published` | `is_visible=false` removes the section from the public payload |
| `test_site_management_requires_the_permission` | `marketer` gets 403 on every CMS read and write; anonymous gets 401 |
| `test_cms_writes_are_audited` | A CMS write lands in the audit log under a `site.*` action |
| `test_published_company_logo_is_served_publicly_but_only_when_published` | The logo the portfolio card and the preview modal need is reachable anonymously for a published company and 404 for an unpublished one |

`test_operations.py` gained two tests for the referral hand-offs the Word spec
lists in Table 6:

| Test | What it proves |
|---|---|
| `test_lead_is_transferred_to_the_receiving_companys_manager` | «حفظ وتحويل» assigns the lead to the receiving company's manager and the manager's dashboard counts it; an explicit assignee still wins |
| `test_assistant_referral_becomes_a_task_on_the_developers_dashboard` | «أحلها لمطوّر الأعمال» creates a directive that the business developer's «مهام من المساعد» card counts |

Three pre-existing tests were updated to the current contract, not weakened:

- public submissions now require `consent: true` (422 `consent_required` without
  it) — the tests that posted a submission now send consent;
- the AI source-link route scan followed admin pages to
  `frontend/app/(admin)/platform`, and now asserts the scanned tree is non-empty
  so a future move cannot pass silently.

## 2. Frontend build and type safety

```
npx tsc --noEmit          # clean
npm run build             # 25 pages, compiled successfully
```

Routes produced: 11 public (`/[locale]` and its children), 22 admin under
`/platform`, `/sitemap.xml`, and the global `/_not-found`.

## 3. Browser acceptance

### 3.1 Public site rendering — 23 checks, 0 failures

| Check | Result |
|---|---|
| `/ar` is `lang="ar" dir="rtl"`; `/en` is `lang="en" dir="ltr"` | pass |
| Public pages render no admin sidebar | pass |
| Primary button uses the logo-derived brand teal `rgb(7,94,115)` | pass |
| Logo aspect ratio 1.856 preserved (not stretched) | pass |
| English navigation is translated (`Home, About, Companies, Solutions`) | pass |
| Service-request form has name/email/phone/service/message + consent | pass |
| Careers CV file input is `required` | pass |
| Opportunities has a country select and subject field | pass |
| Unknown path under a locale returns **404** (not 200) | pass |
| No horizontal overflow at 400px on every public page | pass (0px) |

### 3.2 Form journeys — 3 checks, 0 failures

| Journey | Result |
|---|---|
| Contact form (AR) submits, returns a reference number | `CT-20261117-E96482` |
| Submitting without consent is refused with a visible alert | pass |
| Opportunity form (AR) submits | `OP-20261117-82A24C` |

Persistence confirmed directly in PostgreSQL: rows present in
`website_submissions` with `reference_no`, `consent=true`, `status='new'`, and a
matching append-only row in `website_submission_events`.

### 3.3 CMS authorisation and propagation — 4 checks, 0 failures

| Check | Result |
|---|---|
| `marketer` GET/PATCH `/api/v1/website/settings` | 403 |
| anonymous GET `/api/v1/website/settings` | 401 |
| owner PATCH `brand_short` → `/api/v1/public/site` reflects it | pass |
| owner PATCH `seo_description` → public page `<meta name="description">` after the 30s revalidate window | pass |

### 3.4 Layout matrix — 85 combinations, 0 failures

`python3 scripts/check_matrix.py` walks every admin screen in Arabic/English,
light/dark, desktop/mobile, asserting document direction, sidebar side and width,
the design tokens, and absence of page overflow.

```
85 route/viewport combinations inspected
0 failures
```

## 4. Deployment note

The frontend dev/start scripts listen on **12000**, matching the exposed host
`https://work-1-gbhfhfrydtkboznk.prod-runtime.all-hands.dev/`.

## 5. Not verified / open

- The public site's **visual design is provisional**. The reference PDF covers the
  management platform only; it does not specify the marketing site. Every string
  the missing `content-ar.md` / `content-en.md` would have supplied is seeded with
  `needs_review: true` and is editable from `/platform/website/content`.
- No published group companies exist in the database yet, so `/ar/companies`
  renders its empty state rather than a list. Publishing is owner-controlled and
  the path is covered by `test_public_site_lists_only_published_companies`.
