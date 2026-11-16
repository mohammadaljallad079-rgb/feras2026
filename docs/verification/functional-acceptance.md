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

Result at the time of writing: `32 passed`, of which 12 are the end-to-end
journeys in `tests/test_e2e_journeys.py`.

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

## Browser verification

Recorded in `docs/screenshots/app/`:

| File | What it shows |
|---|---|
| `03-login-ar-light.png` | Arabic RTL sign-in, brand mark, no simulation controls |
| `01-owner-dashboard-ar-light.png` | Owner dashboard, permission-filtered sidebar on the right |
| `02-companies-ar-light.png` | Companies list rendering rows persisted by the API |
| `05-owner-dashboard-ar-dark.png` | Dark theme applied through the token set |
| `06-owner-dashboard-en-dark.png` | English LTR: sidebar moves to the left, all labels translated |

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
