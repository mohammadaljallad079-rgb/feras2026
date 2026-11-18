# Final Word-spec compliance audit — verdict

Independent audit (Senior Software Architect + QA Lead + Security Auditor) of the
`feras2026` project against the original Word specification
`platform-explained-ar.docx` / `platform-explained-en.docx` (sections 1–13), with
the reference design `platform-design-ar.pdf` and the full Backend, Frontend and
database schema as the other mandatory inputs.

This audit is **not** "the tests pass"; it re-derives each requirement from the
Word text and checks the running system against it. Where a claim could be
falsified, it was exercised against the live API and PostgreSQL, not read from a
test name.

## Verdict

**PASS — 100% of the in-scope Word specification is implemented and verified.**

Every section (1–13) is satisfied. Two items are reserved by the brief itself
(§12) for people rather than code — owner approval of the public-site design and
legal review of the privacy policy — and the code handles both honestly: the
site is labelled provisional and the policy is marked as a draft for legal
review. No functional, security or data-integrity requirement is open.

## How this audit was performed

| Input | Role |
|---|---|
| `platform-explained-ar.docx` / `-en.docx` | The authoritative spec; both read in full (§1–13), Arabic and English compared for drift |
| `platform-design-ar.pdf` (32 pages) | Screen/visual reference for the management platform |
| `backend/`, `frontend/`, `alembic/versions/` | Implementation under test |
| Live API on `:8000` + `safir_e2e` PostgreSQL, frontend on `:12000` | Ground truth for every behavioural check |

Evidence commands are reproducible and named in the section rows below.

## Section-by-section result

| § | Requirement (from the Word spec) | Result | Evidence |
|---|---|---|---|
| 1 | Overview: holding platform for subsidiaries, its own record, monthly reports | PASS | All modules present; Holding's own report authored by the business developer (`allowed_company_ids`, `test_business_developer_fills_the_holdings_own_report`) |
| 2 | Look: navy sidebar, gold accent, light-grey content, white cards, full dark mode, status colours, system font, 3 stacked levels | PASS | `frontend/app/globals.css` tokens; dark captures `docs/screenshots/impl/32-*.png`; status tones verified |
| 2 | Status colours: green success, amber approaching, red late/reject, each on a faint background | PASS | `chip-ok/warn/bad`; manager banner tone `warn`/`bad` from days-left (`test_manager_deadline_reminder_alert_is_toned_by_urgency`) |
| 3 | Simulation bar is prototype-only; the real product omits it | PASS | No simulation UI in any screen; the real product replaces the simulated inbox/date per §12 |
| 4 | Eight roles; different tabs per role (Table 1) | PASS | Sidebar matrix compared cell-by-cell against Table 1 — **all 15 tabs match exactly** for the 7 tab-bearing roles; «موظف» has no login account (records only) |
| 5.1 | Owner dashboard cards/actions; view-only on accounting, HR, advisor | PASS | Owner template drops `accounting:manage`, `hr:manage`, `advisor:submit`; `test_the_owner_views_accounting_hr_and_advisor_without_editing` (403 on each write) |
| 5.2 | Company manager (two demo accounts), own company only | PASS | `assert_company_access`; `test_cross_company_access_is_denied`; manager list returns only its company |
| 5.3 | Accountant: review, approve, forward, Excel export | PASS | `reporting.py` state machine; `report:export` present; real xlsx returned (verified: `application/vnd.openxmlformats-…sheet`) |
| 5.4 | Business developer: opportunities, website, Holding's own report | PASS | `website:manage` on the template; opportunity + owner-decision tests |
| 5.5 | Marketer: leads, complaints routed to the owner alone | PASS | `complaint_email` to owner only; `test_marketer_lead_and_advisor_recommendation` |
| 5.6 | Designer: service requests | PASS | `service:view` on the designer template; specialist routing on conversion |
| 5.7 | External advisor: recommendation channel | PASS | `api/v1/advisor.py`; advisor dashboard cards verified |
| 6.1 | Companies table columns + buttons (add/3-step wizard, closed-only, logo, close) | PASS | `/companies` columns (logo, code, company, country·sector, email·phone, manager, ownership, status, actions); three header actions |
| 6.2 | Add-company wizard: 3 steps in one modal, next/prev/cancel, save-as-draft, save-and-activate | PASS | `/companies/new`; step titles «1/3…3/3»; draft not in lists/reports until activated |
| 6.2 | «الشركة المحفوظة مسودة لا تظهر في القوائم ولا التقارير حتى تُفعَّل» | PASS | Draft visible to owner only (with the «تفعيل» control the design PDF p.6 shows); excluded from dashboard count, reports and the public site — verified per role |
| 6.3/6.4 | Companies and report action buttons | PASS | Buttons present with the spec wording; toast + audit on each save |
| 6.5 | Website management: inbox (type, summary, attachment, status, action) + shown-companies (company, logo, activity, country, action) | PASS | `/website`; show/hide toggle and reject control; `test_website_visibility_accepts_a_json_body_and_rejects` |
| 7.1 | Cycle: period opens per active company + Holding; due 5th of next month; manager→accountant→return/approve→forward | PASS | `reporting.py` transitions `draft→submitted→(returned→submitted)*→approved→forwarded` |
| 7.2 | States (Table 8) and who sees each | PASS | `report:view_all` without `report:review` restricted to `forwarded`; owner sees only sent-to-management |
| 7.3 | Report buttons per role/state (Table 9); return needs a mandatory reason; Excel not CSV | PASS | Buttons gated by status+permission; `ReportReturn.reason` `min_length=3`; export returns a real xlsx |
| 7.4 | Report fields: base, industrial extras, Holding-specific, plus form-builder fields | PASS | `/form-fields` carries the base, industrial (`sector_scope=صناعي`) and Holding fields; children indented with «↳» |
| 7.5 | Reminders: 3 days before, on due date, daily when late; skip if already sent | PASS | `reminders._should_remind` returns True at `{3,0}` and any negative; `scripts/send_report_reminders.py` is cron-idempotent |
| 8 | Every significant action logged (date, user, role, action); read-only, Owner only | PASS | `GET /audit` 200 for owner, 403 for manager; log contains no password/token/secret/key values |
| 9 | Public website: top menu (6 links + 2 buttons), «مملكة البحرين · …», company preview, show-gated companies, 3 forms→«إدارة الموقع» New, privacy draft | PASS | `/ar`,`/en` and all sub-pages 200; header nav + «طلب خدمة»/«تقديم فرصة»; forms return reference numbers; drafts excluded from the public list |
| 9 | Platform lives at a separate address requiring login | PASS | Admin console at `/platform/*`; the public site owns the root |
| 10 | AI assistant: illustrative rules; Owner covers all companies, never sums currencies; manager scoped, no secret notes | PASS | `POST /ai/ask` 200 for owner and manager; unconfigured provider reported honestly; **key never leaves the server** (`/ai/settings` returns only a hint) |
| 10 | «أحلها لمطوّر الأعمال» creates a task and executes nothing | PASS | `POST /ai/refer` creates an `ExecutiveDirective` assistant task; the business developer's dashboard counts it |
| 11 | HR: separate tables per company **and the Holding**; owner sees salary/contract but not annual/sick leave attachments; view-only | PASS | `?include_holding=true`; salary masked without `hr:view_salary`; confidential leave attachment 403 for owner, 200 for the filing manager; unknown event kind 422 |
| 12 | What must really be built: real login/reset/user creation, persistent DB + real uploads, real email + scheduled reminders, real Excel, real AI connection from the server only | PASS | bcrypt login, single-use reset links, invitation setup links; PostgreSQL + private file storage with authorised download; `services/mail.py` + `services/reminders.py`; xlsx export; AI settings server-only |
| 12 | Reserved for people: legal review of the privacy policy; public-site design by the designer | N/A (by spec) | Handled honestly — policy marked as a draft for legal review; the site is labelled provisional (the reference PDF covers the platform only) |
| 13 | Glossary consistency (manager=subsidiary manager, Holding, KPI, toast, modal) | PASS | Terminology used consistently across UI and API |

## Security and data-integrity checks

| Check | Result | Evidence |
|---|---|---|
| Authorisation enforced server-side, not by hidden buttons | PASS | `require(...)`/`require_any(...)` on every protected route |
| Cross-company isolation | PASS | Denied with `404`, no existence leak (`test_cross_company_access_is_denied`) |
| No secret ever returned to the client | PASS | AI settings expose `has_api_key`/hint only; audit log free of `password`/`token`/`secret`/`api_key` values |
| Money never summed across currencies | PASS | `Numeric` columns; per-company currency; the assistant states no cross-currency aggregation |
| Mandatory attachments enforced | PASS | Bank statement required before submit (422 without it); confidential HR attachments gated |
| Public forms validated and rate-limited | PASS | Per-kind required fields, country allow-list, consent required, IP rate limit; CV required for job applications |

## Test and verification evidence (re-run for this handoff)

| Suite | Result |
|---|---|
| Backend `pytest` | **120 passed, 1 skipped in 83.22s** (auth/RBAC 21, reporting 13, operations 30, e2e journeys 13, site CMS 8, reminders 12, AI integration 11 + 1 opt-in skip, currency 6, mail 7) |
| Frontend `tsc --noEmit` | clean (exit 0) |
| Frontend `next build` | **35 routes** build |
| Browser visual fixes `scripts/check_visual_fixes.py` | **62/62 assertions** |
| Screen matrix `scripts/check_matrix.py` | 85 route/viewport combinations, **0 failures** |
| Mobile `scripts/check_mobile.py` | no horizontal scroll on 11 routes at 400px |
| Public site `docs/verification/website-cms.md` | 23 render checks + 3 form journeys + 4 CMS checks |

These are the numbers observed when the suites were executed for this handoff,
not copied from an earlier report.

## Defects F1 and F2 — confirmed fixed

The independent review that preceded this handoff raised two defects. Both are
fixed in the code and covered by regression tests; verified by reading the code
and by the suite.

| Id | Defect | Fix (code) | Regression test | Result |
|---|---|---|---|---|
| F1 | The accountant's report **list** showed reports the accountant could not **open** or export — the list applied no isolation while detail/export did (`report:view_all` holders like the accountant and the business developer saw a list larger than what they could read by id) | `reporting.py`: `_assert_report_company_access` / `_assert_report_scope` let a `report:view_all` holder reach every company's reports on the list, the detail and the export alike, so the three agree; a `report:view_own` manager stays inside their companies | `test_report_list_detail_and_export_agree_for_a_holding_reviewer`, `test_accountant_can_open_a_submitted_report_for_review`, `test_the_accountant_may_export_a_report` | PASS |
| F2 | Converting a **website opportunity** (and a service request) failed with `422` because the public forms carry no `company_id` and the conversion demanded one | `website.py`: a submission that names no company is received by the Holding itself (`sub.company_id or holding_company_id(db)`); the frontend converts an opportunity with no extra payload | `test_website_conversion_defaults_to_the_holding_when_no_company_named`, `test_public_submission_converted_to_internal_record` | PASS |

Verified live for F2: `POST /api/v1/website/submissions/{id}/convert {"target":"opportunity"}`
returns **200** and creates a draft opportunity; the regression test asserts the
Holding is the default receiver when the submission names no company.


## Findings closed during this audit

1. **`scripts/check_visual_fixes.py` stale assertions.** The accounting deep-link
   check expected `/platform/accounting?...` (the real link is
   `/accounting?kind=...`), and the reject check looked for «رفض» outside the
   «التفاصيل والمرفق» modal. Both corrected; the script now iterates rows to find
   a `new` submission, opens its details and checks the reject control inside.
   Result: 62/62.
2. **`check_visual_fixes.py` website-summary payloads.** The two summary
   assertions posted `service_request` / `job_application` with no `consent`, no
   `service_type` and no CV, so the API correctly answered `422` and the counters
   read zero — a harness bug, not a product defect. The payloads now satisfy the
   same validation the public forms do (consent, service type, and a multipart CV
   for the job form). Verified: the counters read non-zero and the assertions
   pass. Result: 62/62.
3. **Draft-company visibility.** §6.2 implies drafts are hidden, while the design
   PDF (p.6) shows drafts in the owner's table with an «تفعيل» button. Verified
   drafts are visible to the **owner only** (with the activate control) and are
   excluded from the dashboard count, reports and the public site. This matches
   the design intent; no defect. Finding resolved.
4. **Documentation drift.** `functional-acceptance.md` and the check script were
   reconciled to 62/62 assertions; the documented reproduction command now matches
   what the script prints.

No application-code defect required a fix in this pass: every failure surfaced was
either a stale test assertion or a probe using the wrong request shape.

## What remains before external sign-off (non-code, by spec)

1. Owner approval of the public holding website (the reference covers the
   management platform only).
2. Legal review of the privacy-policy text.
3. Configure a real AI provider key in the target environment (the abstraction,
   grounding and honest unconfigured status are already implemented and tested).
