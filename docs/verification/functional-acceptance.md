# Functional acceptance report

Automated evidence for the journeys listed in section 24 of the delivery brief.
Every assertion below runs against a real PostgreSQL database and the real HTTP
API — there is no in-memory substitute and no mocked business logic.

## How to reproduce

```bash
cd backend
cp .env.example .env          # set DATABASE_URL / SECRET_KEY
alembic upgrade head
python scripts/seed.py        # system roles + demonstration accounts
uvicorn app.main:app --port 8000 &

# Journey suite (drives a live server over HTTP)
SAFIR_BASE_URL=http://localhost:8000 pytest tests/test_e2e_journeys.py -v

# Full suite (auth, RBAC, reporting state machine, operations)
pytest -q
```

Result at the time of writing: `44 passed` — 13 end-to-end journeys in
`tests/test_e2e_journeys.py`, 8 reporting-workflow tests in
`tests/test_reporting_workflow.py`, 12 in `tests/test_auth_rbac.py` and 10 in
`tests/test_operations.py`.

## Journey coverage

| # | Required journey | Test | Result |
|---|---|---|---|
| 1 | Owner creates and activates a company | `test_owner_creates_and_activates_company` | PASS |
| 2 | Owner invites a user | `_invite_and_login` (used by all scoped journeys) | PASS |
| 3 | User receives a scoped role | `_invite_and_login` → password set through single-use link | PASS |
| 4 | Manager submits a monthly report (with bank statement) | `test_reporting_lifecycle_with_return_and_forward` | PASS |
| 5 | Accountant returns a report with a reason | same | PASS |
| 6 | Manager corrects and resubmits | same | PASS |
| 7 | Accountant approves and forwards | same | PASS |
| 8 | Owner views the forwarded report | same | PASS |
| 9 | Approved report is locked against edits | same (`409`) | PASS |
| 10 | Accountant records an expense/invoice/commission | `test_accountant_records_accounting_entries` | PASS |
| 11 | Business developer creates an opportunity | `test_business_developer_opportunity_and_owner_decision` | PASS |
| 12 | Owner makes an opportunity decision | same | PASS |
| 13 | Non-decision-maker cannot decide | same (`403`) | PASS |
| 14 | Executive directive received and completed | `test_directive_receipt_and_completion` | PASS |
| 15 | Specialist processes a service request | `test_specialist_service_request_thread` | PASS |
| 16 | Marketer creates a lead | `test_marketer_lead_and_advisor_recommendation` | PASS |
| 17 | Advisor submits a recommendation | same | PASS |
| 18 | Owner creates a dynamic reporting field | `test_owner_creates_dynamic_form_field` | PASS |
| 19 | Definition change bumps the version (history safe) | same (`version` 1→2) | PASS |
| 20 | Public submission converted to an internal record | `test_public_submission_converted_to_internal_record` | PASS |
| 21 | Unauthorized cross-company access is denied | `test_cross_company_access_is_denied` (`404`, no leak) | PASS |
| 22 | AI reports configuration status; never fabricates | `test_ai_reports_configuration_status_without_fabricating` | PASS |
| 23 | Audit log is read-only | `test_audit_log_is_read_only_and_scoped` | PASS |
| 24 | Owner and developer see only reports sent to management | `test_owner_and_developer_see_only_reports_sent_to_management` | PASS |
| 25 | Accountant can open the review queue | `test_accountant_can_list_reports_for_review` | PASS |
| 26 | Owner cannot approve or forward (accountant's duty) | `test_owner_does_not_hold_the_accountants_review_duties` | PASS |
| 27 | Accountant opens a submitted report for review | `test_accountant_can_open_a_submitted_report_for_review` | PASS |
| 28 | Accountant exports a validated report to Excel | `test_accountant_exports_a_report_to_excel` | PASS |
| 29 | Every permission name used in code exists in the catalog | `test_every_permission_checked_in_code_is_in_the_catalog` | PASS |
| 30 | Every `can()` gate in the UI is a permission the backend defines | `test_frontend_permission_gates_are_names_the_backend_can_grant` | PASS |

## Browser verification

Recorded in `docs/screenshots/impl/`:

46 captures, produced by `scripts/capture_screens.py` against the live app.

| File | What it shows |
|---|---|
| `05-owner-dashboard.png` | Owner dashboard, permission-filtered sidebar on the right |
| `06-companies.png` | Companies list rendering rows persisted by the API |
| `22-manager-dashboard.png` | Manager dashboard with the period banner and five actions |
| `23-report-submission.png` | Report screen with the mandatory bank-statement upload |
| `25-report-review.png` | Accountant review queue |
| `30-owner-dashboard-mobile.png` | 400px viewport, no horizontal page scroll |
| `31-owner-dashboard-en.png` | English LTR: sidebar moves to the left, all labels translated |
| `32-05-owner-dashboard-dark.png` | Dark theme applied through the token set |

`scripts/check_mobile.py` asserts the 400px claim rather than leaving it to
inspection: it reports `400 = 400` on all nine main routes.

## Bugs found and fixed during this pass

1. **Assigned recipients could not see their own service requests.** The list
   query applied company isolation *after* the recipient/creator filter, so a
   specialist with no company-scope row saw an empty inbox. Fixed in
   `app/api/v1/service_requests.py`.
2. **The bank statement could not be attached.** The submit step requires a bank
   statement, but no endpoint accepted one, so a report could never be
   submitted. `ReportValuesUpdate` now carries `bank_statement_file_id` and the
   save-values endpoint persists it.
3. **Business developer lacked `website:manage`.** The brief assigns public
   submission handling to this role, but the permission template withheld it, so
   conversion always returned `403`. Fixed in `app/core/permissions.py`.
4. **Untranslated app-name key** rendered the literal `app` in the header.
   Replaced with an `appName(locale)` helper.

## Bugs found and fixed in the permission audit

A later pass checked every `can()` gate in the UI and every permission name in
the API against the catalog. It found five permission names that no role could
ever hold, plus two routes that demanded the wrong one:

5. **`report:export` did not exist.** The accountant's Excel button called a
   route gated on a permission missing from `ALL_PERMISSIONS` and from every
   template, so export answered `403` for everyone. Added to the catalog and to
   the accountant template; `test_accountant_exports_a_report_to_excel` asserts
   a real xlsx comes back.
6. **The accountant could not open a report to review.** `GET /reports/{id}` and
   `/history` required `report:view_own`, which the accountant does not hold — it
   holds `report:view_all` — so the review screen's own detail call `403`'d.
   Both routes now accept either permission, and a `view_all`-only reader is
   held to the same visibility rule as the list: drafts and merely-submitted
   reports are not reachable by id.
7. **Six UI gates named permissions that were never defined** (`advisor:send`,
   `company:edit`, `company:activate`, `company:close`, `lead:create`,
   `report:create`). The controls were therefore invisible to every role. Each
   gate now names the real permission that guards the action.
8. **`forms.py` used `require_any` without importing it**, so the form-field
   list raised `NameError` on every call.
9. **The assistant's "open the source record" links 404'd.** Sources are cited
   as `kind` plus a `url`, but accounting entries, service requests and
   directives have no per-record route — the links were built as
   `/accounting/{id}` and similar, which the app answers with 404. The links
   now point at the list screen with the record selected
   (`/accounting?entry=<id>`, `/service-requests?open=<id>`,
   `/directives?open=<id>`), and each screen reads that parameter to open and
   scroll to the cited record. A source the platform cannot open is rendered as
   plain text rather than a link that goes nowhere. `test_every_ai_source_link_points_at_a_real_screen`
   now fails if a source URL stops mapping to a real route.
