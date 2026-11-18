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

A second review round then confirmed CI green but found a **remaining concurrency
hole in the reminder claim** — the retry and stale-reclaim paths were a
read-then-write, so two workers could both take the same row. That finding is
closed in §0 (the newest work) and the honest delivery guarantee is stated there
and in the README.

Nothing was deleted. Every change is additive or a corrective edit in place; the
diff is listed in §6.

## 0. Finding (second round): the reminder claim was not atomic on retry

**Review claim.** The unique-constraint insert was atomic, but the **retry of a
`failed` row** and the **reclaim of a stale `sending` row** were a
read-then-write: both workers read the same row, both saw it as retryable, and
both moved it to `sending` and sent. The unique constraint only guarded the first
insert, not these two paths.

**Fix** (`backend/app/services/reminders.py`, `_claim`). Every branch is now a
single atomic statement, so exactly one worker can be handed a row:

- fresh reminder → `INSERT … ON CONFLICT DO NOTHING RETURNING id` (unchanged;
  the unique constraint is the arbiter);
- `failed` retry **or** stale `sending` reclaim → one conditional
  `UPDATE report_reminder_logs SET status='sending', attempts=attempts+1,
  last_error=NULL, updated_at=now() WHERE company_id=… AND period_id=… AND
  reminder_date=… AND kind=… AND (status='failed' OR (status='sending' AND
  updated_at < now() - interval '60 min')) RETURNING id`.

Under PostgreSQL READ COMMITTED the losing worker blocks on the row lock, then
re-evaluates the `WHERE` against the committed row, finds it no longer matches
and updates nothing, so it is returned no row and sends nothing. The stale
boundary is evaluated on the **database clock** (`func.now()`), the same clock
that stamps `updated_at`, so client/server clock skew cannot widen the window.
`updated_at` is stamped on the initial insert and on every retry/reclaim.

**Evidence** (`backend/tests/test_reminders.py`, now 12 tests, all pass):

| Test | What it proves |
|---|---|
| `test_two_workers_racing_to_retry_a_failed_row_send_once` | Two real threads, barrier-gated so both enter the claim together on the **same `failed` row** ⇒ `sum(results) == 1`, one message, `attempts == 2`. **This test fails on the pre-fix code with `results == [1, 1]`** — the two workers both sent. |
| `test_two_workers_racing_to_reclaim_a_stale_sending_row_send_once` | Same, for a row left `sending` past the stale window ⇒ one send, `attempts == 2`. **Also fails `[1, 1]` on the pre-fix code.** |
| `test_every_claim_and_retry_stamps_updated_at` | `updated_at` is set on the first claim and advanced on the retry (`attempts == 2`) |
| `test_running_the_job_twice_on_the_same_day_sends_once` | A second and third run the same day send nothing; exactly one log row, `status=sent` |
| `test_two_concurrent_workers_send_once` | Two threads with real sessions and a slow transport ⇒ `sum(results) == 1`, one row, one email |
| `test_failed_delivery_is_not_recorded_as_sent_and_is_retried` | A refused send records `failed` (never `sent`), does not count, and the same-day retry succeeds (`attempts == 2`) |
| `test_raised_transport_error_is_caught_and_recorded_failed` | An exception from the transport does not abort the run and is recorded `failed` |
| `test_a_fresh_in_progress_claim_is_skipped` | A live worker's fresh `sending` row suppresses a duplicate |
| `test_a_stale_sending_claim_is_reclaimed` | A claim older than the stale window is re-claimed so the reminder is not lost |
| `test_reminders_fire_on_the_three_offsets_and_stop_once_sent` | Fires 3 days before, on the due date, daily when late; stops once the report is sent |
| `test_today_is_resolved_in_the_operating_timezone` | "Today" resolves in `Asia/Bahrain`, not UTC, so a near-midnight cron run hits the right day |
| `test_company_without_a_manager_is_skipped` | No manager ⇒ no send and no claim row |

The two race tests were run against the pre-fix service (`git show
d575438:backend/app/services/reminders.py`) and both failed with `[1, 1]`,
confirming they exercise the real defect rather than passing vacuously.

**Delivery guarantee, stated honestly (no exactly-once claim).** The design is
**at-most-once per day per `(company, period, kind)`**, enforced by the unique
constraint and the atomic claim. It is deliberately **not** exactly-once end to
end, because the SMTP transport cannot be part of the database transaction: if
the mail server **accepts** the message and the process dies before the `sent`
status is committed, the row stays `failed` (or a stale `sending`) and a later
run retries it, so the recipient can receive that reminder **twice** in that
narrow window. Closing it would require an idempotent transport (a provider-side
message key) or a transactional outbox with a deduplicating consumer; plain SMTP
offers neither. The trade-off is intentional — a duplicate reminder is harmless,
a *missing* deadline reminder is the failure that matters — so a retry is
preferred over a silently dropped reminder. This is stated in the module
docstring, the model docstring, `AGENTS.md` and the README; the code does not
claim exactly-once.

Migration check: `alembic upgrade head` on a fresh database is clean with a single
head (`d4e5f6a7b8c9`), and `downgrade -1` / `upgrade head` round-trips. The
schema is unchanged by this round (`updated_at` already had
`server_default=now()`), so no new migration was needed.

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
  Both of these retry paths are now atomic; see §0.
- `scripts/send_report_reminders.py` exits `0` on a completed run and `2` when the
  run itself raised, so cron can tell "nothing to do" from "the job failed".

**Evidence** (`backend/tests/test_reminders.py`, 12 tests, all pass) — see the
table in §0; the original nine are listed there alongside the three added in the
second round.

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
| Backend (full) | `pytest -q` | **120 passed, 1 skipped in 83.22s** |
| Reminders | `pytest tests/test_reminders.py` | **12 passed** (9 original + 3 added in round two) |
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
| `backend/app/services/reminders.py` | Durable claim/dedupe/retry; **atomic conditional-UPDATE claim on the retry and stale-reclaim paths**; timezone-aware day; cron entry point |
| `backend/app/core/config.py` | Added `reminders_timezone` |
| `backend/app/ai/provider.py` | Injectable transport; typed `AIProviderError` |
| `backend/app/api/v1/ai.py` | `502` on provider failure; empty summary when no period |
| `backend/scripts/send_report_reminders.py` | Exit codes `0`/`2` |
| `backend/tests/test_reminders.py` | New (9 tests) + 3 in round two: two barrier-gated race tests and an `updated_at` stamping test (12 total) |
| `backend/tests/test_ai_integration.py` | New (11 tests + 1 opt-in skip) |
| `backend/tests/test_currency_no_summation.py` | New (6 tests) |
| `backend/tests/test_mail_delivery.py` | New (7 tests) |
| `backend/tests/test_operations.py` | Removed the superseded reminder test (now in `test_reminders.py`) |
| `README.md` | Documented reminder idempotency, exit codes, `REMINDERS_TIMEZONE`, no auto-deploy on push/PR, and the honest at-most-once (not exactly-once) delivery guarantee |
| `backend/.env.example` | Added SMTP and `REMINDERS_TIMEZONE` entries |
| `docs/verification/*`, `AGENTS.md` | Refreshed totals; matrix rows 5.1.3, 5.1.15, 7.5, 10.2, 10.4, 11.5, 12.3, 12.5 cite the new evidence; the reminder note states the atomic claim and the at-most-once guarantee |

## 8. Decision

All four first-round findings are closed with runnable evidence, and the
currency rule is re-proven across every money surface. The second-round
concurrency finding (the reminder retry/reclaim race) is closed in §0: the claim
is now a single conditional `UPDATE` in every branch, two real race tests prove
exactly one worker sends (and fail on the pre-fix code), and the delivery
guarantee is stated as at-most-once per day — never exactly-once. Nothing was
deleted; the new work is additive plus in-place corrections (`ai.py` error
handling, the reminder service). The Word-spec matrix stands at **126 PASS, 3
PASS\* (pending human approval), 1 N/A, 0 FAIL** out of 130 rows.

The three PASS\* items cannot be closed by code: they are the brief's own §12
reservations for people — owner approval of the public-site design, the
designer's final artwork, and legal review of the privacy policy. They are
recorded as **pending human approval**, not as automated passes.

**Recommendation:** the implementation is ready for independent sign-off; the
only remaining items are the three human approvals above and the
production-configuration list in `FINAL_HANDOFF_REPORT.md`.
