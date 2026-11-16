# Completion matrix

Status of every deliverable in the brief, with the evidence that supports it.
Two things block a fully certified delivery and are stated plainly rather than
papered over:

1. `platform-design-ar.pdf` is absent from the repository, so page-by-page
   *visual* parity cannot be certified. See
   `docs/verification/reference-asset-blocker.md`.
2. `assets/brand/holding-logo.png` is absent, so the official logo cannot be
   placed. The header uses a temporary brand mark, which the spec forbids as a
   final state; it must be replaced with the supplied asset unchanged.

Everything not dependent on those two files is implemented, wired to PostgreSQL
through the API, and covered by automated tests.

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

All 22 distinct routes exist and render live API data. Visual parity per page is
**UNVERIFIED** pending the PDF.

| PDF page | Screen | Route | UI | Backend |
|---|---|---|---|---|
| 1–4 | Design system / shell | global | Done | n/a |
| 5 | Owner dashboard | `/dashboard` | Done | Done |
| 6 | Companies | `/companies` | Done | Done |
| 7 | Company wizard | `/companies/new` | Done | Done |
| 8 | Owner monthly reports | `/reports` | Done | Done |
| 9 | Holding accounting | `/accounting` | Done | Done |
| 10 | Service requests | `/service-requests` | Done | Done |
| 11 | Leads | `/leads` | Done | Done |
| 12 | Opportunities | `/opportunities` | Done | Done |
| 13 | Executive directives | `/directives` | Done | Done |
| 14 | Employees and HR | `/hr` | Done | Done |
| 15 | Website management | `/website` | Done | Done |
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

## 3. Authentication and RBAC (spec §5)

| Requirement | Status | Evidence |
|---|---|---|
| Database-backed login/logout | Done | `api/v1/auth.py`, `test_auth_rbac.py` |
| Password hashing | Done | bcrypt via `core/security.py` |
| Password reset, single-use expiring links | Done | `auth.py`; exercised in `test_e2e_journeys.py` |
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

**Not certifiable.** The reference PDF is missing, so the required
reference-screenshot vs implementation-screenshot comparison cannot be produced.
Screenshots of the implementation are recorded in `docs/screenshots/app/` for
when the PDF arrives. This is an unresolved blocker, not a completed item.

## 7. Test results

```
backend:  32 passed  (includes 12 end-to-end journeys over live HTTP + PostgreSQL)
frontend: tsc --noEmit clean; next build generates all 22 routes
browser:  login, owner dashboard, companies, dark mode and EN/LTR verified
```

## 8. What remains before final sign-off

1. Commit `platform-design-ar.pdf` to `docs/reference/` and render its 32 pages.
2. Commit `assets/brand/holding-logo.png` unchanged and place it in the header.
3. Complete the page-by-page visual comparison and close the UNVERIFIED rows.
4. Supply an approved specification for the public holding website.
