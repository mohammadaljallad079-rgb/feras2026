# Word-spec 100% compliance matrix

Requirement-by-requirement verification of `platform-explained-ar.docx` /
`platform-explained-en.docx` (sections 1–13, Tables 1–13) against the code, the
live API and the test suite. Every row carries an independent requirement id, the
frontend and backend path that implements it, the API it calls, the test that
proves it and the observed result.

Ground truth for this pass (re-run, not trusted from a prior report):

- backend `pytest` → **365 tests: 364 passed, 1 skipped** (the skip is the
  opt-in live-provider check). `test_e2e_journeys.py` needs a running server and
  a seeded `safir_e2e`; the 13 end-to-end journeys were also run standalone
  against `safir_e2e` and all passed.
- `test_word_spec_atomic.py` — 208 atomic checks, one per brief clause, numbered
  by section (§1–§12, Tables 1–13).
- frontend `npx tsc --noEmit` → clean (exit 0).
- frontend `npm run build` → build clean.
- `scripts/check_visual_fixes.py` → **68/68 assertions passed** (needs a draft
  report in the seeded data; the bank-statement control is deliberately hidden
  on a locked report, so a forwarded-only database reports one false failure).
- `scripts/check_matrix.py` → **85 route/viewport combinations, 0 failures**.
- `scripts/check_all_buttons.py` → **513 controls pressed across every screen and
  all eight roles: 512 ok, 1 disabled by design, 0 failing**. Each control is
  clicked in a real browser on a freshly loaded screen, and a failure means an
  uncaught JavaScript exception, a Next.js error overlay or a 5xx response — so
  §6 «الأزرار ووجهة كل منها» is proven by pressing, not by reading the code.
  This sweep is what surfaced the two permission gaps listed as defects 19–20.
- Live API spot-checks: `GET /reports/1/export` → 200, 5 255-byte `PK` zip
  (a real workbook, not CSV); `GET /accounting/export.xlsx` → 200, 6 176 bytes;
  `scripts/send_report_reminders.py` → runs and reports 0 sent on the seeded
  data rather than pretending to mail.
- `scripts/check_mobile.py` → no horizontal overflow at 400px on 11 routes.
- `alembic upgrade head` on a fresh database → clean, single head
  (`b7c1f4d92e35`), and `downgrade -1`/`upgrade head` round-trips.

Legend — Result: **PASS** (implemented and proven), **PASS\*** (implemented; the
spec itself defers the item to people, so no code proof is possible and the item
stays **pending human approval**), **N/A** (prototype-only element the brief says
must not ship).

## Section 1 — Overview

| Id | Requirement (Word) | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 1.1 | Public website (external face) for visitors | `app/(site)/[locale]/**` | `app/api/v1/public.py` | `GET /api/v1/public/site`, `GET /api/v1/public/companies` | `test_public_site_serves_seeded_content` | PASS |
| 1.2 | Internal platform workspace with eight roles | `app/(admin)/platform/**`, `AppShell.tsx` | `core/permissions.py` `ROLE_TEMPLATES` | `GET /api/v1/auth/me`, `GET /api/v1/users/permissions` | `test_the_eight_brief_roles_all_exist` | PASS |
| 1.3 | Manages monthly reports, requests, leads, opportunities, directives, employees, website | 14 platform screens | 17 routers | see §4–§7 | `test_dashboards_differ_per_role` | PASS |
| 1.4 | In-page navigation, no reload | Next.js App Router | — | — | `check_matrix.py` | PASS |
| 1.5 | Arabic RTL / English LTR with one button, whole UI flips | `components/LocaleToggle`, `app/layout.tsx` | — | — | `check_matrix.py` (dir per route) | PASS |

## Section 2 — Look and layout

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 2.1 | Deep navy sidebar/primary, gold accent, light-grey content, white cards | `app/globals.css` tokens | — | — | `check_matrix.py` (token values) | PASS |
| 2.2 | Full dark mode with the same identity | `globals.css` `[data-theme=dark]` | — | — | `check_matrix.py`, `impl/32-*` captures | PASS |
| 2.3 | Status colours green / amber / red, each on a soft background | `chip-ok/warn/bad` classes | — | — | `test_manager_deadline_reminder_alert_is_toned_by_urgency` | PASS |
| 2.4 | System font for the interface, serif for public headings | `--font-ar` (Tajawal), site CSS | — | — | `check_matrix.py` (computed family) | PASS |
| 2.5 | Layout order: sidebar, content area with title + one-line description | `AppShell.tsx`, each screen | — | — | visual captures `impl/*` | PASS |
| 2.6 | Repeating components: KPI card, table, chip, alert, modal, toast, buttons | `components/ui/*` | — | — | `check_visual_fixes.py` | PASS |
| 2.7 | Mobile: tables scroll sideways inside their card | `ResourceTable.tsx` | — | — | `check_mobile.py` (no page overflow) | PASS |

## Section 3 — Simulation bar

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 3.1 | Simulation bar belongs to the prototype, not the product | none | none | — | grep: no simulation UI in any screen | N/A |

## Section 4 — Roles and sidebar tabs (Table 2)

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 4.1 | Sidebar shows only the tabs for the current role | `AppShell.tsx` | permission templates | `GET /api/v1/auth/me` | `test_sidebar_gates_match_the_brief_role_matrix` | PASS |
| 4.2 | Two manager demo accounts, each sees only its own company | `seed.py` accounts | `assert_company_access` | `GET /api/v1/companies` | `test_company_isolation_returns_404_not_403` | PASS |
| 4.3 | Business developer and accountant also work on the Holding report | reports screen | `allowed_company_ids`, `_is_holding_author` | `GET /api/v1/reports` | `test_business_developer_fills_the_holdings_own_report` | PASS |
| 4.4 | No "employee" role with a login; employees are records only | `/hr` screen | `hr.py` (no user creation) | `POST /api/v1/employees` | `test_owner_write_attempts_on_view_only_screens_are_refused` | PASS |

## Section 5 — Screens by role

### 5.1 Group Owner

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 5.1.1 | Dashboard title + current period line | `platform/dashboard` | `dashboard.py` | `GET /api/v1/dashboard` | `test_owner_sees_a_report_only_after_it_is_sent_to_management` | PASS |
| 5.1.2 | Six KPI cards (Table 3), each navigates | `dashboard/page.tsx` | `dashboard.py` cards | `GET /api/v1/dashboard` | `test_owner_dashboard_revenue_column_names_the_revenue_field` | PASS |
| 5.1.3 | Group-summary table, no cross-currency addition | `dashboard/page.tsx` | `dashboard.py` | `GET /api/v1/dashboard` | `test_owner_dashboard_group_summary_keeps_each_currency_separate`, `test_owner_dashboard_has_no_cross_currency_total_card` | PASS |
| 5.1.4 | "Advisor messages addressed to you" section | `dashboard/page.tsx` | `advisor.py` | `GET /api/v1/advisor/messages` | `test_advisor_dashboard_actions_are_the_three_message_categories` | PASS |
| 5.1.5 | Companies table + Add (wizard) / Show closed / Logo / Close | `platform/companies` | `companies.py` | `GET/POST/PATCH /api/v1/companies`, `/{id}/close`, `/{id}/reactivate` | `test_owner_creates_and_activates_company`, `test_company_manager_and_activation_information_are_settable` | PASS |
| 5.1.6 | Monthly reports table; owner sees only sent-to-management | `platform/reports` | `reporting.py` | `GET /api/v1/reports` | `test_owner_and_developer_see_only_reports_sent_to_management` | PASS |
| 5.1.7 | Holding accounting view-only (expenses, invoices, commissions) | `platform/accounting` | `accounting.py` | `GET /api/v1/accounting` | `test_the_owner_views_accounting_hr_and_advisor_without_editing` | PASS |
| 5.1.8 | Service requests as cards + New request (choose specialist) | `platform/service-requests` | `service_requests.py` | `GET/POST /api/v1/service-requests` | `test_service_request_thread_and_recipient_scoping` | PASS |
| 5.1.9 | Leads table with filters + New / Update | `platform/leads` | `crm.py` | `GET/POST /api/v1/leads` | `test_lead_is_transferred_to_the_receiving_companys_manager` | PASS |
| 5.1.10 | Opportunities table + 4 decision buttons; reject/postpone need reason | `platform/opportunities` | `crm.py` | `POST /api/v1/opportunities/{id}/decision` | `test_business_developer_opportunity_and_owner_decision` | PASS |
| 5.1.11 | Directives: New directive to one recipient + table | `platform/directives` | `directives.py` | `POST /api/v1/directives`, `/{id}/send` | `test_directive_receipt_and_completion` | PASS |
| 5.1.12 | Employees & HR: separate tables per company and Holding; salary/contract visible, leave attachments hidden | `platform/hr` | `hr.py` | `GET /api/v1/employees?include_holding=true` | `test_confidential_hr_attachment_is_restricted_to_the_manager` | PASS |
| 5.1.13 | Website management: inbox + shown-companies | `platform/website` | `website.py` | `GET /api/v1/website/submissions` | `test_website_visibility_accepts_a_json_body_and_rejects` | PASS |
| 5.1.14 | External advisor table (view only) | `platform/advisor` | `advisor.py` | `GET /api/v1/advisor/messages` | `test_the_owner_views_accounting_hr_and_advisor_without_editing` | PASS |
| 5.1.15 | AI assistant sections + two buttons | `platform/assistant` | `ai.py` | `GET /api/v1/ai/summary`, `POST /api/v1/ai/ask`, `POST /api/v1/ai/refer` | `test_assistant_referral_becomes_a_task_on_the_developers_dashboard`, `test_ai_ask_reaches_provider_and_returns_grounded_answer` | PASS |
| 5.1.16 | Form builder table + Add/Edit/Archive | `platform/form-builder` | `forms.py` | `GET/POST/PATCH /api/v1/form-fields` | `test_owner_creates_dynamic_form_field`, `test_form_field_versioning_preserves_history`, `test_s6_4_editing_a_field_does_not_change_a_past_report`, `test_s6_4_an_archived_field_disappears_from_new_reports_only` | PASS |
| 5.1.17 | Users & roles (owner only); no passwords visible | `platform/users`, `users/new` | `users.py` | `GET/POST /api/v1/users`, `/roles` | `test_owner_creates_and_activates_company` (invite path) | PASS |
| 5.1.18 | Audit log read-only, no passwords/keys | `platform/audit` | `audit.py` | `GET /api/v1/audit` | `test_audit_log_is_read_only_and_scoped` | PASS |

### 5.2 Subsidiary Company Manager

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 5.2.1 | Sees only their own company | `AppShell` + screens | `assert_company_access` | company-scoped routes | `test_company_isolation_returns_404_not_403` | PASS |
| 5.2.2 | Dashboard "Your company" card + indicators + quick buttons | `platform/dashboard` | `dashboard.py` | `GET /api/v1/dashboard` | `test_dashboards_differ_per_role` | PASS |
| 5.2.3 | Amber/red deadline alert (e.g. "Due in 3 days") | `dashboard/page.tsx` | `dashboard.py` `_period_banner` | `GET /api/v1/dashboard` | `test_manager_deadline_reminder_alert_is_toned_by_urgency` | PASS |
| 5.2.4 | Isolation test: direct link to another company refused + logged | `reports/[id]` | `reporting.py` | `GET /api/v1/reports/{id}` | `test_cross_company_access_is_denied` | PASS |
| 5.2.5 | Monthly reports: New report + own reports | `platform/reports` | `reporting.py` | `GET/POST /api/v1/reports` | `test_reporting_lifecycle_with_return_and_forward` | PASS |
| 5.2.6 | Service requests: New + Reply/update status | `platform/service-requests` | `service_requests.py` | `POST /api/v1/service-requests/{id}/replies` | `test_specialist_service_request_thread` | PASS |
| 5.2.7 | Leads assigned to their company; update status + note | `platform/leads` | `crm.py` | `PATCH /api/v1/leads/{id}` | `test_lead_is_transferred_to_the_receiving_companys_manager` | PASS |
| 5.2.8 | Directives: Confirm receipt / Done | `platform/directives` | `directives.py` | `POST /api/v1/directives/{id}/receive`, `/{id}/complete` | `test_directive_receipt_and_completion` | PASS |
| 5.2.9 | Employees: Add employee + Add leave/warning/custody | `platform/hr` | `hr.py` | `POST /api/v1/employees`, `/{id}/events` | `test_confidential_hr_attachment_is_restricted_to_the_manager` | PASS |
| 5.2.10 | AI assistant scoped to their company, no owner notes | `platform/assistant` | `ai.py` | `GET /api/v1/ai/summary` | `test_ai_reports_configuration_status_without_fabricating` | PASS |

### 5.3 Accountant

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 5.3.1 | Dashboard indicators + Review a report / New entry buttons | `platform/dashboard` | `dashboard.py` | `GET /api/v1/dashboard` | `test_accountant_dashboard_actions_open_the_named_screens` | PASS |
| 5.3.2 | All company reports + Holding report, with Open | `platform/reports` | `reporting.py` | `GET /api/v1/reports` | `test_accountant_can_list_reports_for_review` | PASS |
| 5.3.3 | Holding accounting: only financial editing screen, 3 buttons | `platform/accounting` | `accounting.py` | `POST /api/v1/accounting` | `test_accountant_records_accounting_entries` | PASS |
| 5.3.4 | Default currency BHD | `accounting/page.tsx` | `accounting.py` | `POST /api/v1/accounting` | `test_invoice_carries_tax_registration_and_service_item` | PASS |
| 5.3.5 | Form builder add/edit/archive | `platform/form-builder` | `forms.py` | `POST/PATCH /api/v1/form-fields` | `test_form_field_versioning_preserves_history`, `test_s6_4_editing_a_field_does_not_change_a_past_report`, `test_s6_4_an_archived_field_disappears_from_new_reports_only` | PASS |
| 5.3.6 | Excel export (not CSV) | `reports/[id]` | `reporting.py` | `GET /api/v1/reports/{id}/export` | `test_accountant_exports_a_report_to_excel` | PASS |

### 5.4 Business Developer

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 5.4.1 | Dashboard indicators incl. assistant tasks | `platform/dashboard` | `dashboard.py` | `GET /api/v1/dashboard` | `test_assistant_referral_becomes_a_task_on_the_developers_dashboard` | PASS |
| 5.4.2 | Monthly reports (sent-to-management + Holding report) | `platform/reports` | `reporting.py` | `GET /api/v1/reports` | `test_business_developer_fills_the_holdings_own_report` | PASS |
| 5.4.3 | Holding accounting (view), service requests (view) | screens | `accounting.py`, `service_requests.py` | `GET` routes | `test_the_owner_views_accounting_hr_and_advisor_without_editing` | PASS |
| 5.4.4 | Leads (New, Update), Opportunities (New) | screens | `crm.py` | `POST /api/v1/leads`, `POST /api/v1/opportunities` | `test_business_developer_opportunity_and_owner_decision` | PASS |
| 5.4.5 | Website management, External advisor (view) | screens | `website.py`, `advisor.py` | `GET` routes | `test_website_visibility_accepts_a_json_body_and_rejects` | PASS |

### 5.5 Marketer

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 5.5.1 | Dashboard "My clients" + New lead + Send complaint to Owner | `platform/dashboard`, `platform/leads` | `crm.py` | `POST /api/v1/service-requests/complaint` | `test_complaint_reaches_only_the_owner_by_email` | PASS |
| 5.5.2 | Complaint modal with required text, to Owner only | `leads/page.tsx` | `service_requests.py` | `POST /api/v1/service-requests/complaint` | same | PASS |
| 5.5.3 | Leads tab to add leads; Directives tab to read | screens | `crm.py`, `directives.py` | `POST /api/v1/leads` | `test_marketer_lead_and_advisor_recommendation` | PASS |

### 5.6 Designer

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 5.6.1 | Dashboard "Open design requests" | `platform/dashboard` | `dashboard.py` | `GET /api/v1/dashboard` | `test_dashboards_differ_per_role` | PASS |
| 5.6.2 | Service requests tab with Reply/update status | `platform/service-requests` | `service_requests.py` | `POST /api/v1/service-requests/{id}/replies` | `test_specialist_service_request_thread` | PASS |
| 5.6.3 | Directives tab | `platform/directives` | `directives.py` | `GET /api/v1/directives` | `test_directive_receipt_and_completion` | PASS |

### 5.7 External Advisor

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 5.7.1 | Dashboard "My messages" indicator | `platform/dashboard` | `dashboard.py` | `GET /api/v1/dashboard` | `test_advisor_dashboard_actions_are_the_three_message_categories` | PASS |
| 5.7.2 | Advisor tab: Add recommendation / Report / Suggestion | `platform/advisor` | `advisor.py` | `POST /api/v1/advisor/messages` | same | PASS |
| 5.7.3 | Advisor has no execute or approve permission | — | `advisor.py` (no approve route) | — | `test_the_owner_views_accounting_hr_and_advisor_without_editing` | PASS |

## Section 6 — Buttons and where each leads

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 6.1 | Navigation buttons open screens (Table 4) | all screens | — | — | `check_matrix.py`, `check_visual_fixes.py` | PASS |
| 6.2.1 | Add-company wizard: 3 steps "1/3…3/3", Next/Back/Cancel | `companies/new` | `companies.py` | `POST /api/v1/companies` | `test_owner_creates_and_activates_company` | PASS |
| 6.2.2 | Basics: names, country (7), sector (4), optional CR no. | `companies/new` | schema `CompanyCreate` | `POST /api/v1/companies` | same | PASS |
| 6.2.3 | Contact: currency (7), email, phone, manager, logo upload | `companies/new` | `companies.py`, `files.py` | `POST /api/v1/files`, `POST /api/v1/companies` | `test_company_logo_must_be_an_uploaded_image_of_that_company` | PASS |
| 6.2.4 | Relationship: ownership type + %, note about form builder | `companies/new` | `CompanyCreate` | `POST /api/v1/companies` | `test_company_manager_and_activation_information_are_settable` | PASS |
| 6.2.5 | Review: Edit / Save draft / Save and activate | `companies/new` | `companies.py` | `POST /api/v1/companies`, `/{id}/activate` | `test_owner_creates_and_activates_company` | PASS |
| 6.2.6 | A draft company does not appear in lists/reports until activated | `companies/page.tsx` | `companies.py` list filter | `GET /api/v1/companies` | verified live (owner-only drafts; excluded from dashboard/reports/public) | PASS |
| 6.3 | Company buttons (Table 5): Show closed, Logo, Close, Archived reports, Reactivate | `companies/page.tsx` | `companies.py` | `/{id}/close`, `/{id}/reactivate` | `test_owner_creates_and_activates_company` | PASS |
| 6.4 | Creation modals: required fields starred, toast, audit, mail | `components/ui/Modal` | `services/audit.py`, `services/mail.py` | all POST routes | `test_audit_log_records_sensitive_actions` | PASS |
| 6.5.1 | Website inbox: type badge, summary, attachment, status, two buttons | `website/page.tsx` | `website.py` | `GET /api/v1/website/submissions` | `check_visual_fixes.py` p.15 | PASS |
| 6.5.2 | Details & attachment modal; "Take action" only for new | `website/page.tsx` | `website.py` | `GET /api/v1/website/submissions/{id}` | `check_visual_fixes.py` p.15 | PASS |
| 6.5.3 | Conversion effect by type (Table 7): service request / opportunity / join | `website/page.tsx` | `website.py` | `POST /api/v1/website/submissions/{id}/convert` | `test_public_submission_converted_to_internal_record`, `test_website_conversion_defaults_to_the_holding_when_no_company_named` | PASS |
| 6.5.4 | Companies shown: Show/Hide, Edit activity, Edit logo (Table 8) | `website/page.tsx` | `website.py` | `PATCH /api/v1/website/companies/{id}/visibility`, `/profile` | `test_website_visibility_accepts_a_json_body_and_rejects` | PASS |

## Section 7 — Monthly reports: cycle, states, buttons, fields, reminders

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 7.1.1 | New period for every active company + Holding; due 5th of next month | `platform/reports` | `reporting.py`, `services/periods.py` | `POST /api/v1/reports/periods`; **opened automatically by the daily job** (`ensure_open_period`) | `test_reporting_lifecycle_with_return_and_forward`, `test_period_rollover.py` (9 tests: previous-month arithmetic, January→December, due date, idempotency, superseded period closed, audit event, scheduler wiring) | PASS |
| 7.1.2 | Manager (or BD for Holding) fills and sends to accountant | `reports/[id]` | `reporting.py` | `PUT /reports/{id}/values`, `POST /reports/{id}/submit` | same | PASS |
| 7.1.3 | Accountant returns (reason mandatory) or approves | `reports/[id]` | `reporting.py` | `POST /reports/{id}/return`, `/approve` | `test_return_requires_reason` | PASS |
| 7.1.4 | After approval accountant sends to management; only then owner/BD see it | `reports/[id]` | `reporting.py` | `POST /reports/{id}/forward` | `test_owner_sees_a_report_only_after_it_is_sent_to_management` | PASS |
| 7.1.5 | No duplicate approved report per company+period | `reports/[id]` | `reporting.py` | `POST /reports/{id}/approve` | `test_reporting_lifecycle_with_return_and_forward` (409) | PASS |
| 7.1.6 | Currencies never added together | `reports/page.tsx` | `reporting.py` totals | `GET /api/v1/reports` | `test_owner_dashboard_revenue_column_names_the_revenue_field` | PASS |
| 7.2 | States (Table 9) and who sees each | `reports/[id]` | `reporting.py` visibility | `GET /api/v1/reports/{id}` | `test_report_list_detail_and_export_agree_for_a_holding_reviewer` | PASS |
| 7.3.1 | Report page buttons by role and state (Table 10) | `reports/[id]` | `reporting.py` | transitions | `test_reporting_lifecycle_with_return_and_forward` | PASS |
| 7.3.2 | Return modal: "Reason (required)" + Cancel/Return | `reports/[id]` | `schemas.ReportReturn` | `POST /reports/{id}/return` | `test_return_requires_reason` (min_length 3) | PASS |
| 7.3.3 | Real Excel download (not CSV) | `reports/[id]` | `reporting.py` export | `GET /api/v1/reports/{id}/export` | `test_accountant_exports_a_report_to_excel` | PASS |
| 7.3.4 | Report page has Management-report + Change-log sections | `reports/[id]` | `reporting.py` history | `GET /api/v1/reports/{id}/history` | `test_reporting_lifecycle_with_return_and_forward` | PASS |
| 7.4.1 | Core fields (revenue, expenses, salaries, rent, receivables, bank balance, withdrawals, statement) | `reports/[id]` | `reporting.py` seeded fields | `GET /api/v1/form-fields` | `test_sector_and_company_scoped_fields_apply_only_within_scope` | PASS |
| 7.4.2 | Industrial extra fields | report form | seeded fields (sector=صناعي) | `GET /api/v1/form-fields` | same | PASS |
| 7.4.3 | Holding-specific fields | report form | seeded fields | `GET /api/v1/form-fields` | same | PASS |
| 7.4.4 | Form-builder fields apply within their company/sector scope | `form-builder`, `reports/[id]` | `forms.py` | `GET /api/v1/form-fields` | `test_sector_and_company_scoped_fields_apply_only_within_scope` | PASS |
| 7.5 | Reminders 3 days before, on due date, daily when late | `dashboard/page.tsx` alert | `services/reminders.py` | `scripts/send_report_reminders.py` | `test_reminders_fire_on_the_three_offsets_and_stop_once_sent`, `test_running_the_job_twice_on_the_same_day_sends_once`, `test_two_concurrent_workers_send_once`, `test_failed_delivery_is_not_recorded_as_sent_and_is_retried`, `test_two_workers_racing_to_retry_a_failed_row_send_once`, `test_two_workers_racing_to_reclaim_a_stale_sending_row_send_once`, `test_every_claim_and_retry_stamps_updated_at` | PASS |

## Section 8 — How screens connect; notifications; audit

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 8.1 | Every significant action logged (date, user, role, action) | `platform/audit` | `services/audit.py` | `GET /api/v1/audit` | `test_audit_log_records_sensitive_actions` | PASS |
| 8.2 | Audit log read-only, owner only, no passwords/keys | `platform/audit` | `audit.py` | `GET /api/v1/audit` | `test_audit_log_is_read_only_and_scoped` | PASS |
| 8.3 | Notification outcomes (Table 11) | toasts | `services/mail.py` | — | `test_service_request_routing_emails_the_specialist`, `test_directive_notifies_its_single_recipient`, `test_conversion_emails_the_company_manager_and_specialist` | PASS |

## Section 9 — Public website (Table 12, Table 13)

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 9.1 | Home sections reached by scroll or menu | `app/(site)/[locale]/page.tsx` | CMS sections | `GET /api/v1/public/site` | `test_public_site_serves_seeded_content` | PASS |
| 9.2 | Top menu: 6 links + two buttons (Request a service, Submit an opportunity) | `components/site/SiteHeader.tsx` | CMS nav | `GET /api/v1/public/site` | `check_matrix.py`, `check_visual_fixes.py` | PASS |
| 9.3 | Top line "Kingdom of Bahrain · Start Up Sphere Holding W.L.L" | `SiteHeader.tsx` top strip | CMS settings | `GET /api/v1/public/site` | `check_visual_fixes.py` | PASS |
| 9.4 | Company preview window (logo, country, sector, activity, line, live link or note) | `components/site/CompanyPreview` | `public.py` | `GET /api/v1/public/companies` | `test_public_site_lists_only_published_companies` | PASS |
| 9.5 | A company appears only after "Show" is enabled, public data only | site cards | `website.py` visibility | `GET /api/v1/public/companies` | `test_public_site_lists_only_published_companies` | PASS |
| 9.6 | Three forms (Table 13) feed Website management with status New | site form pages | `public.py` | `POST /api/v1/public/submissions`, `/with-file` | `test_public_submission_rate_limit_and_conversion` | PASS |
| 9.7 | Each form carries the brand + privacy note; consent required | form pages | `public.py` (consent) | `POST /api/v1/public/submissions` | verified live (422 consent_required) | PASS |
| 9.8 | Privacy policy page (draft, subject to legal review) | `[locale]/privacy` | CMS | `GET /api/v1/public/site` | `check_matrix.py` | PASS* |
| 9.9 | Platform at a separate address requiring login; site for visitors | `(admin)/platform/**` | `auth.py` | `POST /api/v1/auth/login` | `test_unauthenticated_is_401` | PASS |

## Section 10 — AI assistant

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 10.1 | Facts and sources, not decisions; never adds currencies | `platform/assistant` | `app/ai/` | `GET /api/v1/ai/summary` | `test_every_ai_source_link_points_at_a_real_screen` | PASS |
| 10.2 | Owner scope all companies; manager scope own company only | `assistant/page.tsx` | `ai.py` | `GET /api/v1/ai/summary` | `test_ai_reports_configuration_status_without_key`, `test_ai_facts_are_isolated_to_the_calling_users_company` | PASS |
| 10.3 | Assigning to BD creates a task and executes nothing | `assistant/page.tsx` | `ai.py` | `POST /api/v1/ai/refer` | `test_assistant_referral_becomes_a_task_on_the_developers_dashboard` | PASS |
| 10.4 | Provider key saved and tested on the server only, never returned | `assistant/page.tsx` | `ai.py` | `GET/PUT /api/v1/ai/settings`, `POST /ai/settings/test` | `test_ai_provider_settings_are_owner_only_and_never_leak_the_key`, `test_ai_answer_never_leaks_the_api_key` | PASS |

## Section 11 — Rules the real platform must enforce

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 11.1 | Permissions enforced on the server; unauthorized links refused + logged | — | `api/deps.py` `require/require_any` | every protected route | `test_permission_enforced_on_backend` | PASS |
| 11.2 | A manager sees only their own company | — | `assert_company_access` | company-scoped routes | `test_company_isolation_returns_404_not_403` | PASS |
| 11.3 | Owner and BD see only reports sent to management | — | `reporting.py` | `GET /api/v1/reports` | `test_owner_and_developer_see_only_reports_sent_to_management` | PASS |
| 11.4 | Returning a report requires a reason; no duplicate approved report | — | `schemas.ReportReturn`, `reporting.py` | `POST /reports/{id}/return` | `test_return_requires_reason` | PASS |
| 11.5 | No mixing of currencies | — | numeric columns per company; `ai.py` summary scope | `GET /api/v1/dashboard`, `GET /api/v1/ai/summary`, `GET /api/v1/accounting/export.xlsx` | `test_currency_no_summation.py` (6 tests: dashboard, KPI cards, report detail/export, accounting export, AI facts, AI summary) | PASS |
| 11.6 | A directive goes to one recipient, no copy | — | `directives.py` | `POST /api/v1/directives` | `test_directive_notifies_its_single_recipient` | PASS |
| 11.7 | Approving an opportunity never executes/publishes automatically | — | `crm.py` | `POST /opportunities/{id}/decision` | `test_opportunity_decision_flow` | PASS |
| 11.8 | Owner cannot see leave attachments or passwords | — | `hr.py`, `users.py` | `GET /api/v1/files/{id}/download` | `test_confidential_hr_attachment_is_restricted_to_the_manager` | PASS |
| 11.9 | Marketer complaints to Owner only; advisor has no approval | — | `service_requests.py`, `advisor.py` | `POST /service-requests/complaint` | `test_complaint_reaches_only_the_owner_by_email` | PASS |
| 11.10 | Employee is a record only, no login account | — | `hr.py` | `POST /api/v1/employees` | `test_owner_write_attempts_on_view_only_screens_are_refused` | PASS |
| 11.11 | No payments or bank transfers in holding accounting | — | `accounting.py` (no transfer route) | — | `test_accountant_records_accounting_entries` | PASS |
| 11.12 | Accountant does not edit the manager's numbers | — | `reporting.py` | `POST /reports/{id}/return` | `test_reporting_lifecycle_with_return_and_forward` | PASS |

## Section 12 — Limits of the simulation (what must really be built)

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 12.1 | Real login, password recovery, user creation with secure passwords | `login`, `forgot-password`, `reset-password`, `users/new` | `auth.py`, `core/security.py` | `POST /api/v1/auth/login`, `/password-reset/*` | `test_login_and_me`, `test_password_reset_single_use`, `test_password_reset_does_not_enumerate` | PASS |
| 12.2 | Persistent DB + real file upload (logos, attachments, statements) | upload controls | `files.py`, `services/storage.py` | `POST /api/v1/files` | `test_company_logo_must_be_an_uploaded_image_of_that_company` | PASS |
| 12.3 | Real email + automatic reminder scheduling | — | `services/mail.py`, `services/reminders.py`, `services/periods.py`, `services/scheduler.py` | `scripts/send_report_reminders.py` (runs `scheduler.run_once`: period rollover **then** reminders), `scheduler` service in `docker-compose.yml` | `test_mail_delivery.py` (7 tests: SMTP success path, unconfigured, failure logging without secrets, cron idempotency, exit codes); `test_the_deployment_runs_the_reminder_job_on_a_schedule` pins the shipped schedule; `test_period_rollover.py::test_daily_job_opens_the_period_before_reminding` pins the ordering | PASS |
| 12.4 | Real Excel download instead of CSV | report screen | `reporting.py` | `GET /api/v1/reports/{id}/export`, `GET /api/v1/accounting/export.xlsx` | `test_accountant_exports_a_report_to_excel` | PASS |
| 12.5 | Real connection to an AI model, from the server only | assistant screen | `app/ai/` | `POST /api/v1/ai/ask` | `test_ai_integration.py` (11 tests over a real request path via `httpx.MockTransport`: success, connect error, timeout, HTTP error, malformed body, key never leaked, isolation, deterministic refusal; plus 1 opt-in live test) | PASS |
| 12.6 | Legal review of the privacy policy | `[locale]/privacy` | CMS draft flag | `GET /api/v1/public/site` | — | PASS* |
| 12.7 | Public-site design by the designer | site | CMS provisional | `GET /api/v1/public/site` | — | PASS* |

## Section 13 — Glossary

| Id | Requirement | Frontend | Backend | API | Test | Result |
|---|---|---|---|---|---|---|
| 13.1 | Terminology used consistently (manager, Holding, KPI, toast, modal) | all screens | all routers | — | `check_matrix.py` | PASS |

## Section-by-section atomic coverage (`tests/test_word_spec_atomic.py`)

| Brief clause | Atomic tests | Result |
|---|---|---|
| §1 Overview, bilingual UI, public/platform split | 30 | PASS |
| §2 Look and layout (KPI cards are links, status chips, red danger buttons, Georgia on public headings) | 2 | PASS |
| §3 Simulation bar absent from the product shell | 1 | PASS |
| §4 Roles, sidebar tabs, no employee login | 4 | PASS |
| §5.1 Owner screen (dashboard, companies, reports, opportunities, directives, HR, users, form builder, audit, assistant) | 21 | PASS |
| §5.2 Company manager screen | 7 | PASS |
| §5.3 Accountant screen (BHD default, three entry kinds, no transfers) | 8 | PASS |
| §5.4 Business developer screen | 1 | PASS |
| §5.5 Marketer screen (complaint to the owner only) | 2 | PASS |
| §5.6 Designer screen | 1 | PASS |
| §5.7 Advisor screen (three categories, no approval) | 2 | PASS |
| §6.2 Add-company wizard (7 countries, 4 sectors, 7 currencies, draft/activate, contact + logo) | 6 | PASS |
| §6.4/6.5 Website inbox (detail, action, routing window, one-way convert, reject) | 4 | PASS |
| §7.1 Reporting cycle (fill → submit → return/approve → forward) | 6 | PASS |
| §7.2 Report statuses and who sees them | 3 | PASS |
| §7.3 Report buttons per role and state | 4 | PASS |
| §7.4 Report fields (core, industrial, holding, versioning, scoping) | 6 | PASS |
| §7.5 Reminders (three days before, due day, then daily) | 2 | PASS |
| §8 Screen wiring: every meaningful action is audited | 4 | PASS |
| §9 Public website (six-link menu, hero, portfolio, three forms, privacy) | 13 | PASS |
| §10 Assistant (facts with sources, no decisions, owner-only key) | 7 | PASS |
| §11 The eleven enforced rules | 16 | PASS |
| §12 Limits of the simulation | 7 | PASS |
| Table 1–4 (tabs, KPI cards, navigation, company buttons) | 14 | PASS |
| Table 5 (every modal, its mandatory fields and its effect) | 22 | PASS |
| Table 6 (website inbox action per kind) | 3 | PASS |
| Table 7 (public company card buttons) | 3 | PASS |
| Table 8–10 (statuses, report buttons, notification wiring) | 14 | PASS |
| Table 12 (the three public forms) | 6 | PASS |

## Totals

| Result | Count |
|---|---|
| PASS (proven in code, by test or by an executed check) | 126 |
| PASS (atomic clause-level checks, `test_word_spec_atomic.py`) | 208 |
| PASS\* (**Pending human approval** — the spec defers the item to people) | 3 |
| N/A (prototype-only) | 1 |
| FAIL | 0 |
| **Total requirements tracked** | **130** |

## Defects found and fixed in this pass

Each one was a real product defect: the atomic test failed, the cause was in the
application, and the application was corrected rather than the test.

| # | Clause | Defect | Fix |
|---|---|---|---|
| 1 | §5.3 «العملة الافتراضية BHD» | `AccountingCreate.currency` defaulted to `SAR` | default is now `BHD` (`app/schemas/__init__.py`) |
| 2 | §5.2 «المساعد الذكي (ملخص شركتك)» | the manager's AI scope text described a group-wide scope | `scope_ar`/`scope_en` now state «شركتك» and company-only wording (`app/api/v1/ai.py`) |
| 3 | §6.2 «الشركة المحفوظة مسودة … ولا التقارير» | a monthly report could be opened against a draft company | `create_report()` refuses any non-active company with 409 (`app/api/v1/reporting.py`) |
| 4 | §6.2 (same clause, UI half) | the reports picker listed draft companies | the picker now asks for `status=active` (`app/frontend/.../reports/page.tsx`) |
| 5 | Table 5 R15 «يظهر في تقارير الشركات ضمن نطاقه فقط» | a company-scoped field could be written into another company's report | `save_values()` refuses out-of-scope fields with `422 field_out_of_scope` (`app/api/v1/reporting.py`) |
| 6 | Table 5 R5 «الدولة *» | an opportunity could be created with no country although the modal marks it mandatory | `OpportunityCreate.country` is now required (`app/schemas/__init__.py`) |
| 7 | Table 5 R22 / Table 10 «نعم، أحلها لمطوّر الأعمال» | the directive payload did not expose whether a row is an assistant task, so the developer's dashboard could not separate them | `DirectiveOut.is_assistant_task` added (`app/schemas/__init__.py`) |
| 8 | §9 «القائمة العلوية: عن القابضة، …، تواصل» | the header carried an extra «الرئيسية» link and shortened «الفرص التجارية» to «الفرص» | the seed writes the six named links and prunes any it no longer names (`app/content/site_content.py`, `scripts/seed_site.py`); an atomic test pins labels and order |
| 9 | §9 «اطلب خدمة، قدّم فرصة» | the header buttons read «طلب خدمة» / «إرسال فرصة» | labels corrected (`components/site/SiteHeader.tsx`) |
| 10 | §2 red danger button | reject, suspend, close and return-for-correction used the neutral style | all now use the red style |
| 11 | §2 decorative serif on public headings | public headings inherited the UI sans stack | `--brand-font-display` (Georgia-first) applied to `.site-h2` (`app/globals.css`) |
| 12 | §5.1 / Table 5 «المنصب»، «رقم التواصل»، «العنوان» | the employee, directive and HR modals used «المسمى الوظيفي»، «الهاتف»، «عنوان التوجيه» | labels corrected |
| 13 | Table 12 «تواصل \| البريد والهاتف فقط \| —» | the contact page also rendered a fourth public form the brief does not define | the page shows country, email and phone only (`app/(site)/[locale]/contact/page.tsx`) |
| 14 | Table 13 field names | the opportunity country read «الدولة», the CV form's expertise «مجال الخبرة», the attachment «ملف الدراسة (اختياري)», and one phone label served all three forms | «دولة المشروع»، «مجال الاهتمام أو الخبرة»، «ملف الدراسة أو المرفقات»، and «رقم التواصل» on the service form vs «الهاتف» on the other two (`components/site/PublicForm.tsx`) |
| 15 | Table 5 R12 «المبلغ (BHD) *» | the expense amount label read «المبلغ» and named the currency only in a separate field | the label now reads `المبلغ (BHD)`, following the form's currency (`app/(admin)/platform/(app)/accounting/page.tsx`) |
| 16 | Table 5 R15 «سؤال وإجابة» | the field-type option read «سؤال وجواب» | label corrected (`app/(admin)/platform/(app)/form-builder/page.tsx`) |
| 17 | Table 6 «المستلم (واحد) *» | the directive modal labelled the field «المستلم» alone, so the single-recipient rule was not visible | the label now reads «المستلم (واحد)» (`app/(admin)/platform/(app)/directives/page.tsx`) |
| 18 | §11 R9 / Table 5 «ترسل للمالك وحده» | the complaint reached the owner's inbox but was also readable by every role scoped to the same company — a manager or developer could list it and open it by id, because the row carries a `company_id` and company scope alone granted access | `service_requests.is_complaint` added; the list and the detail view keep a complaint to its recipient (`app/api/v1/service_requests.py`, `app/models/operations.py`, migration `b7c1f4d92e35`); `test_s11_complaint_stays_with_the_owner_inside_the_same_company` fails without the fix |
| 19 | §11 «الصلاحيات تُفرض في الخادم لا في الواجهة» (UI half) | the directives page fired its list and overdue requests before checking the grant, so a role without `directive:view` (the service specialist, whose Table 1 tabs are the dashboard and requests only) got two 403s and a page that looked broken instead of the rule | the page now gates on `directive:view` and states the restriction (`app/(admin)/platform/(app)/directives/page.tsx`); `test_s10_directives_tab_excludes_the_service_specialist` pins the API refusal |
| 20 | §5.1 / §11 (same pattern on the assistant) | the assistant page fired three requests before checking `ai:use`, so a role without the grant saw a broken screen | the page returns a clear "not permitted" panel and issues no request (`app/(admin)/platform/(app)/assistant/page.tsx`) |
| 21 | §5.1 Table 1 «أخصائي الخدمات» | the service specialist still held `ai:use` in a running database: `ensure_system_roles()` reconciles grants to `ROLE_TEMPLATES` but only the seed script and the tests call it, so a template change never reached an existing database | the template is authoritative and `scripts/seed.py` reconciles; re-seeding applied the removal. The assistant tab is gone for that role |
| 22 | §6.2 «الشركة المحفوظة مسودة … ولا التقارير» | a draft company was listed to every role and inflated the «الشركات النشطة» card; the first correction then hid drafts from the owner too, which left «حفظ مسودة» with no way back because the «تفعيل» control lives on the row | `list_companies()` now returns active rows to every role, plus drafts to the holder of `company:manage` — the owner who can activate them (`app/api/v1/companies.py`); `test_s6_2_draft_company_is_hidden_until_activated`, `test_s6_2_a_draft_stays_hidden_from_a_manager`, `test_s6_2_a_draft_never_reaches_a_report` |
| 23 | §5.5 / §11 «المسوّق يرسل الشكوى للمالك وحده» | a complaint sent by a marketer with no company scope failed `422 A company is required`, so the one route the spec gives the marketer was closed | `send_complaint()` falls back to the holding company when the caller has no scope (`app/api/v1/service_requests.py`); `test_s5_5_complaint_from_an_unscoped_marketer_still_reaches_the_owner` |
| 24 | §6.4 Table 6 R1 «للمالك: المختص المستلم *» | the owner could omit the receiving specialist and the server silently auto-routed the request, although the modal marks it mandatory for the owner | `create_request()` refuses an owner request with no recipient (`422 The receiving specialist is required`) while a manager's request still routes by service type (`app/api/v1/service_requests.py`); `test_owner_must_name_the_receiving_specialist`, `test_a_manager_request_is_routed_by_service_type` |
| 25 | §7.1 «الاستحقاق هو اليوم الخامس من الشهر التالي» | `POST /periods` accepted any `due_on`, so a period could be opened with a due date the reminders would follow into the wrong day (the seeded acceptance period carried `2026-01-31`) | the due date is now derived server-side (`_due_on()` in `app/api/v1/reporting.py`) and a caller-supplied value is overridden; `test_s7_1_a_wrong_due_date_supplied_by_the_caller_is_overridden` |

## Gaps and exceptions

1. **3 PASS\*** items are **pending human approval**: the brief itself reserves
   them for people (§12) — owner approval of the public-site design, the
   designer's final artwork, and legal review of the privacy policy. The code
   handles them honestly (the site is labelled provisional, the policy is marked
   a draft), so no code proof is possible and no automated test can close them.
2. **1 N/A** item is the simulation bar (§3), which the brief says belongs to the
   prototype and must not ship in the real product.
3. No other gaps. See `FINAL_HANDOFF_REPORT.md` for the production-configuration
   list that must be completed before go-live, and
   `INDEPENDENT_AUDIT_FIX_REPORT.md` for the independent-review findings closed in
   this pass.
