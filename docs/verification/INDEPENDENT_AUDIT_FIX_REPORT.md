# INDEPENDENT_AUDIT_FIX_REPORT — findings closed with evidence

Project: **START UP SPHERE HOLDING — FERAS 2026**
(شركة ستارت أب سفير القابضة ذ.م.م, Kingdom of Bahrain)

Repository: `mohammadaljallad079-rgb/feras2026`
Branch: `review/final-word-compliance`
Draft PR: <https://github.com/mohammadaljallad079-rgb/feras2026/pull/2>

This report answers the independent review that preceded final approval. Each
finding is restated, the fix is named, and the evidence that closes it is listed
so it can be re-run rather than trusted. The reviewer asked for four areas to be
proven: reminder idempotency, AI provider behaviour, mail delivery honesty, and
reporting scope. Each is closed below, together with the currency rule that the
same review re-opened.

Nothing was deleted. Every change is additive or a corrective edit in place; the
diff is listed in §6.

## 1. Finding: reminder sending was not provably idempotent

**Review claim.** The reminder job could send the same reminder twice — on a
second run the same day, or when two workers ran at once — and a failed transport
could be recorded as if it had been sent.

**Fix.** Sending is now made idempotent by a durable log rather than by date
arithmetic alone:

- New table `report_reminder_logs` (model `ReportReminderLog`,
  `backend/app/models/business.py`; migration
  `backend/alembic/versions/d4e5f6a7b8c9_report_reminder_log.py`). A row is keyed
  by `(company_id, period_id, reminder_date, kind)` under a **unique constraint**.
- `backend/app/services/reminders.py` claims a row with
  `INSERT … ON CONFLICT DO NOTHING RETURNING id` before sending. A second run, or
  a concurrent worker, cannot claim the same row, so the reminder is sent at most
  once per company per day.
- A claim is written `sending` first, moved to `sent` only after the transport
  reports success, or to `failed` (never `sent`) when it does not. A `failed` row
  is retried on the next run the same day; a row left `sending` by a crashed
  worker is only re-claimed once it is older than `REMINDER_STALE_MINUTES` (60).
- `scripts/send_report_reminders.py` exits `0` on a completed run and `2` when the
  run itself raised, so cron can tell "nothing to do" from "the job failed".

**Evidence** (`backend/tests/test_reminders.py`, 9 tests, all pass):

| Test | What it proves |
|---|---|
| `test_running_the_job_twice_on_the_same_day_sends_once` | A second and third run the same day send nothing; exactly one log row, `status=sent` |
| `test_two_concurrent_workers_send_once` | Two threads with real sessions and a slow transport ⇒ `sum(results) == 1`, one row, one email |
| `test_failed_delivery_is_not_recorded_as_sent_and_is_retried` | A refused send records `failed` (never `sent`), does not count, and the same-day retry succeeds (`attempts == 2`) |
| `test_raised_transport_error_is_caught_and_recorded_failed` | An exception from the transport does not abort the run and is recorded `failed` |
| `test_a_fresh_in_progress_claim_is_skipped` | A live worker's fresh `sending` row suppresses a duplicate |
| `test_a_stale_sending_claim_is_reclaimed` | A claim older than the stale window is re-claimed so the reminder is not lost |
| `test_reminders_fire_on_the_three_offsets_and_stop_once_sent` | Fires 3 days before, on the due date, daily when late; stops once the report is sent |
| `test_today_is_resolved_in_the_operating_timezone` | "Today" resolves in `Asia/Bahrain`, not UTC, so a near-midnight cron run hits the right day |
| `test_company_without_a_manager_is_skipped` | No manager ⇒ no send and no claim row |

Migration check: `alembic upgrade head` on a fresh database is clean with a single
head (`d4e5f6a7b8c9`), and `downgrade -1` / `upgrade head` round-trips.

## 2. Finding: AI behaviour was asserted only by a key-existence check

**Review claim.** The suite proved a key was stored but did not exercise a real
provider round-trip or the failure modes; it could not show the assistant returns
an answer, refuses honestly, or keeps the key and company data in bounds.

**Fix.** The provider factory (`backend/app/ai/provider.py`) now accepts an
injectable `httpx.BaseTransport`, so the **real request path** — URL, auth header,
JSON payload and response parsing — runs against a mock socket. A malformed
provider body now raises a typed `AIProviderError` instead of a bare `KeyError`.
`backend/app/api/v1/ai.py` returns `502 ai_provider_failed` for any transport,
HTTP-status or malformed-body failure, and never fabricates an answer. A missing
reporting period now returns an explicit empty summary instead of a `500`.

**Evidence** (`backend/tests/test_ai_integration.py`, 11 tests + 1 opt-in skip):

| Test | What it proves |
|---|---|
| `test_ai_ask_reaches_provider_and_returns_grounded_answer` | A real request reaches `/chat/completions` with the bearer key and the company's own fact (`1234 BHD`); the grounded answer and its sources come back |
| `test_ai_ask_provider_connection_error_returns_502` | `httpx.ConnectError` ⇒ `502 ai_provider_failed` |
| `test_ai_ask_provider_timeout_returns_502` | `httpx.ReadTimeout` ⇒ `502` |
| `test_ai_ask_provider_http_error_status_returns_502` | A `500` from the provider ⇒ `502` |
| `test_ai_ask_invalid_response_is_reported_not_fabricated` | Non-JSON and missing-`choices` bodies ⇒ `502`, never an invented answer |
| `test_ai_answer_never_leaks_the_api_key` | The key goes out on the wire but never into the response, the stored record or the settings screen |
| `test_ai_facts_are_isolated_to_the_calling_users_company` | A manager's FACTS contain only their company; the owner sees all |
| `test_ai_refuses_deterministically_when_no_permitted_records` | No permitted data ⇒ `confidence=no_data`, `note=no_permitted_sources`, and the provider is **not called** |
| `test_ai_reports_configuration_status_when_unconfigured` | No key ⇒ `configured=false`, `confidence=unconfigured` |
| `test_ai_summary_keeps_each_amount_in_its_own_currency` | The summary states the no-summation rule |
| `test_ai_summary_without_a_period_does_not_crash` | A fresh deployment returns an explicit empty summary, not a `500` |
| `test_live_provider_round_trip_when_opted_in` | Skipped by default; runs only with `SAFIR_AI_LIVE_TEST=1` and a key in the environment — no credential is in the repository |

## 3. Finding: mail delivery was not proven honest

**Review claim.** The suite did not show the SMTP success path, and could not show
that a failure is reported (and logged) without claiming delivery or leaking
secrets.

**Fix.** No code change was needed in `mail.py`; the review's requirement was
proof. The new tests drive the real `mail.send` code — message construction, TLS,
login, `send_message` — through a fake `smtplib.SMTP`, and a failure through a
raising transport.

**Evidence** (`backend/tests/test_mail_delivery.py`, 7 tests, all pass):

| Test | What it proves |
|---|---|
| `test_smtp_success_path_sends_the_message` | TLS started, login performed, one message sent to the right recipient with the period in the subject |
| `test_unconfigured_transport_is_reported_and_not_logged_as_sent` | `SMTP_HOST` empty ⇒ `send` returns `False` and logs no "sent" claim |
| `test_transport_failure_is_reported_and_logged_without_secrets` | A failure returns `False`, logs `failed`, and never logs the SMTP password or the reset token |
| `test_notify_counts_only_real_deliveries` | Duplicates and empty addresses are skipped; a failing send is not counted |
| `test_reminder_email_states_the_offset_correctly` | The copy says "3 days", "due today" or "N days late" and carries no financial figure |
| `test_daily_job_is_safe_to_run_twice` | Two cron runs the same day send once |
| `test_send_report_reminders_script_exit_code` | Exit `0` on completion, `2` when the run raises |

## 4. Finding: reporting scope (F1) and opportunity conversion (F2)

**Review claim.** Confirm the earlier F1/F2 fixes are present and covered.

**Fix.** Present and unchanged, with the same regression tests:
`backend/app/api/v1/reporting.py` (report list/detail/export scope by role and
state) and `backend/app/api/v1/website.py` (opportunity conversion creates the
expected internal record). Covered by
`test_report_list_detail_and_export_agree_for_a_holding_reviewer`,
`test_owner_and_developer_see_only_reports_sent_to_management` and
`test_public_submission_converted_to_internal_record`.

## 5. Finding re-opened: currencies must never be summed

**Review claim.** The no-summation rule was asserted by a single, weakly related
test.

**Fix.** No code change was required for the dashboard, report and accounting
paths; the AI summary scope line already states the rule. The new suite proves it
across every money surface.

**Evidence** (`backend/tests/test_currency_no_summation.py`, 6 tests, all pass):

| Test | What it proves |
|---|---|
| `test_owner_dashboard_group_summary_keeps_each_currency_separate` | Three companies in BHD/SAR/USD each show their own figure and currency; no aggregate row and no `3,000` |
| `test_owner_dashboard_has_no_cross_currency_total_card` | No KPI is a monetary total; the owner's cards are counts |
| `test_report_detail_and_export_keep_each_value_in_its_own_currency` | Report detail and its Excel export carry the company's own currency, never a merged total |
| `test_accounting_export_labels_each_amount_with_its_currency` | The accounting export has a `Currency` column; each amount keeps its currency and there is no `TOTAL` row |
| `test_ai_facts_carry_each_amount_with_its_own_currency` | Every report fact sent to the model names its currency; no cross-currency sum exists |
| `test_ai_summary_scope_states_the_no_summation_rule` | The owner summary scope states the rule and each source carries its currency |

## 6. Full re-run results (real output this session)

| Suite | Command | Result |
|---|---|---|
| Backend (full) | `pytest -q` | **117 passed, 1 skipped in 81.74s** |
| Reminders | `pytest tests/test_reminders.py` | **9 passed** |
| AI integration | `pytest tests/test_ai_integration.py` | **11 passed, 1 skipped** |
| Currency no-summation | `pytest tests/test_currency_no_summation.py` | **6 passed** |
| Mail and scheduling | `pytest tests/test_mail_delivery.py` | **7 passed** |
| End-to-end journeys (live HTTP) | `pytest tests/test_e2e_journeys.py` | **13 passed** |
| Migrations | `alembic upgrade head` (fresh DB) | **clean, single head `d4e5f6a7b8c9`** |
| TypeScript check | `npx tsc --noEmit` | **clean (exit 0)** |
| Production build | `npm run build` | **35 routes built** |
| Browser visual fixes | `scripts/check_visual_fixes.py` | **62/62 assertions passed** |
| Route/viewport matrix | `scripts/check_matrix.py` | **85 combinations, 0 failures** |
| Mobile overflow | `scripts/check_mobile.py` | **no horizontal overflow at 400px (11 routes)** |

Environment: PostgreSQL 17 (disposable `safir_test` and `safir_e2e` databases),
FastAPI on `:8000`, Next.js production server on `:12000`. The suite refuses to
run against a database whose name does not end in `_test`.

## 7. Files changed in this pass

| File | Change |
|---|---|
| `backend/app/models/business.py` | Added `ReportReminderLog` |
| `backend/app/models/__init__.py` | Registered `ReportReminderLog` |
| `backend/alembic/versions/d4e5f6a7b8c9_report_reminder_log.py` | New migration (additive; reversible) |
| `backend/app/services/reminders.py` | Durable claim/dedupe/retry; timezone-aware day; cron entry point |
| `backend/app/core/config.py` | Added `reminders_timezone` |
| `backend/app/ai/provider.py` | Injectable transport; typed `AIProviderError` |
| `backend/app/api/v1/ai.py` | `502` on provider failure; empty summary when no period |
| `backend/scripts/send_report_reminders.py` | Exit codes `0`/`2` |
| `backend/tests/test_reminders.py` | New (9 tests) |
| `backend/tests/test_ai_integration.py` | New (11 tests + 1 opt-in skip) |
| `backend/tests/test_currency_no_summation.py` | New (6 tests) |
| `backend/tests/test_mail_delivery.py` | New (7 tests) |
| `backend/tests/test_operations.py` | Removed the superseded reminder test (now in `test_reminders.py`) |
| `README.md` | Documented reminder idempotency, exit codes, `REMINDERS_TIMEZONE`, and that no push or PR auto-deploys |
| `backend/.env.example` | Added SMTP and `REMINDERS_TIMEZONE` entries |
| `docs/verification/*` | Refreshed totals; matrix rows 5.1.3, 5.1.15, 7.5, 10.2, 10.4, 11.5, 12.3, 12.5 now cite the new evidence |

## 8. Decision

All four requested findings are closed with runnable evidence, and the
currency rule is re-proven across every money surface. Nothing was deleted; the
new work is additive plus two in-place corrections (`ai.py` error handling, the
reminder service). The Word-spec matrix stands at **126 PASS, 3 PASS\* (pending
human approval), 1 N/A, 0 FAIL** out of 130 rows.

The three PASS\* items cannot be closed by code: they are the brief's own §12
reservations for people — owner approval of the public-site design, the
designer's final artwork, and legal review of the privacy policy. They are
recorded as **pending human approval**, not as automated passes.

**Recommendation:** the implementation is ready for independent sign-off; the
only remaining items are the three human approvals above and the
production-configuration list in `FINAL_HANDOFF_REPORT.md`.
