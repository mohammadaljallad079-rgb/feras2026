# Repository guide

Arabic-first, bilingual holding-company platform. `platform-design-ar.pdf` at
the repository root is the authoritative design reference for the **management
platform only** — it specifies nothing about the public holding website, so no
website screen may claim fidelity to it.

## Layout

```
backend/    FastAPI + SQLAlchemy + Alembic; the API package is `app`
frontend/   Next.js App Router, Arabic RTL default, English LTR
docs/reference/       TRACEABILITY.md — PDF page to screen to status
docs/verification/    completion-matrix.md, visual-comparison.md,
                      functional-acceptance.md, website-cms.md,
                      final-spec-compliance.md (the section-by-section verdict),
                      WORD_SPEC_100_PERCENT_MATRIX.md (requirement-by-requirement),
                      FINAL_HANDOFF_REPORT.md (independent-review package),
                      INDEPENDENT_AUDIT_FIX_REPORT.md (findings closed with evidence)
docs/screenshots/     pdf/ (rendered reference) and impl/ (live captures)
scripts/              capture_screens.py, check_matrix.py, check_mobile.py,
                      check_visual_fixes.py
```

## Commands

```bash
# backend
cd backend && . .venv/bin/activate
alembic upgrade head
python scripts/seed.py                      # 8 roles, 8 demo accounts
uvicorn app.main:app --port 8000

# frontend
cd frontend && npm run dev                  # or: next start -p 12000
npx tsc --noEmit && npm run build
```

Demo password is `Safir!2026` for every seeded account.

## Testing

`pytest.ini` sets `pythonpath = .`, so never pass `PYTHONPATH=.` — the suite is
run the same way in CI.

Two databases, and the split is load-bearing:

- `safir_test` — the in-process suite (`test_auth_rbac`, `test_operations`,
  `test_reporting_workflow`). Fixtures truncate every table between tests.
- `safir_e2e` — the live API that `test_e2e_journeys.py` drives over HTTP.
  Point `SAFIR_BASE_URL` at it.

If the journey server shares `safir_test`, the truncation deletes the seeded
accounts mid-run and the journeys fail with confusing 401s. `conftest.py`
refuses any database whose name does not end in `_test`, so the e2e database is
migrated and seeded separately and the server is started with `DATABASE_URL`
overridden for that one process.

### `npm run lint` is not wired up

There is no ESLint config or `eslint` dependency in `frontend/`, so
`npm run lint` (which runs `next lint`) stops on an interactive
*"How would you like to configure ESLint?"* prompt and never finishes. Don't
treat that as a failure and don't add a config just to silence it: `npx tsc
--noEmit` plus `npm run build` are the gates that actually run here.

### A test that needs the schema must request a fixture that creates it

`Base.metadata.create_all` runs in the session-scoped `engine` fixture, not at
import time. A test that touches the database without requesting `engine` (or
`db`, which depends on it) passes only when some earlier test happened to create
the tables, and fails when the file is run alone. `test_scheduler.py` had two
such tests; they now take `engine`.

### Rebuilding the databases after the container restarts

Postgres runs in Docker and nothing starts it again on its own, so a restarted
workspace answers `Cannot assign requested address` / `Is the server running`.
`sudo dockerd &` first (the socket is root-owned), then either
`sudo docker compose up -d db` after copying `.env.example` to `.env`, or a
standalone `sudo docker run -d --name safir-db -e POSTGRES_USER=safir
-e POSTGRES_PASSWORD=safir -e POSTGRES_DB=safir -p 5432:5432 postgres:16-alpine`.
Create `safir_test` by hand — `conftest.py` does not create it. For the journey
suite, `alembic upgrade head` and `scripts/seed.py` must run against `safir_e2e`
before `uvicorn` is pointed at it, or every journey fails on missing accounts.

### Browser checks read the built bundle, not the sources

`scripts/check_visual_fixes.py`, `check_matrix.py` and `check_mobile.py` drive
`next start` on `:12000`, which serves the last `npm run build` output. A label
edit is invisible to them — and to a manual browser check — until the bundle is
rebuilt and the server restarted, so an edit can look unfixed while the source
is already correct. Rebuild, kill the old `next-server` (it keeps the port even
after the `npx` parent dies), restart, then re-run. The same applies to the
FastAPI process: it is started without `--reload`, so backend changes need a
restart too.

### The public-submission sweep hits the hourly IP cap

`_check_rate_limit` in `backend/app/api/v1/public.py` counts rows by `source_ip`
in the last hour and answers `429 {"error": "rate_limited"}` past
`public_rate_limit_per_hour` (default 20). Every form submit the sweep makes —
public site, dashboard flow, and `test_e2e_journeys` — comes from `127.0.0.1`,
so a few runs in one hour starve the next one and it fails with a 429 that
looks like a broken form.

Both checkers therefore delete their own earlier rows before submitting, gated
on `CHECKER_DB_URL` so a plain run never touches the database:

```bash
CHECKER_DB_URL=postgresql://safir:safir@127.0.0.1:5432/safir_e2e \
  backend/.venv/bin/python scripts/check_public_site.py
```

`test_e2e_journeys.py` has no such hook — clear `website_submissions` rows whose
email starts with `visitor-` before running it after a sweep.

## Conventions

- Authorization is enforced in the backend. The permission-filtered sidebar is
  a convenience, never the control. New endpoints take an explicit
  `require(...)` / `require_any(...)` dependency from `app/api/deps.py`.
- Permissions live in `app/core/permissions.py`. `ensure_system_roles` makes the
  database match `ROLE_TEMPLATES` exactly — it removes grants that a template no
  longer lists, so editing a template is enough; custom roles are left alone.
- Monetary amounts are `Numeric`, never float. Never sum across currencies.
- `frontend/components/ResourceTable.tsx` is the shared list: pass `columns` in
  the reference's order and an optional `filter` for narrowing controls.
- A failed read is worded by `loadError(e, locale)` in `frontend/lib/api.ts`:
  a `403` reads as «لا تملك صلاحية عرض هذه البيانات.» and a caller may pass the
  `404` wording. Do not inline the generic «تعذّر تحميل البيانات.», which hides a
  refusal behind what looks like a broken screen.
- Bilingual fields are `*_ar` / `*_en`; UI strings come from the locale
  dictionaries, not inline literals.
- Arabic uses the self-hosted Tajawal face (SIL OFL 1.1, `frontend/public/fonts/`),
  declared in `app/globals.css` and applied through `--font-ar`. English keeps the
  system stack the reference names. Page 32 defers the licensed Arabic font to the
  designer; Tajawal is that licensed choice.
- Sidebar icons come from `components/NavIcon.tsx`, a self-contained SVG set keyed
  by `NavIconName`; `NAV` entries carry an `icon` field and `AppShell` renders it.
  No icon font or external icon dependency.
- Global loading/error states live in `app/loading.tsx` and `app/error.tsx`.
- Outbound mail is `backend/app/services/mail.py`: bilingual templates for password
  reset and invitation, one secure link each and no financial detail (page 32).
  SMTP is optional — with no `SMTP_HOST`, `send()` returns `False` and the caller
  returns the link for out-of-band delivery instead of claiming a message.
- Workflow notification emails (Tables 5/6/10, §12) live in the same module as
  short-subject templates that carry only the detail needed to act, never an
  amount or a report value: `service_request_routed_email`, `complaint_email`,
  `directive_email`, `assistant_task_email`, `conversion_copy_email`. Use
  `mail.notify([...])` for a multi-recipient event (it dedupes and returns how
  many went out). Wired in `service_requests.py` (routed specialist, complaint to
  the owner only), `directives.py` (single recipient), `ai.py` (assistant
  referral to the business developer), `website.py` (`convert_submission` →
  company manager + specialist copy).
- Monthly-report deadline reminders (§7.5, §12) are scheduled, not simulated:
  `app/services/reminders.py` fires three days before the due date, on the due
  date, and daily once late, and skips a company that already sent its report.
  Sending is idempotent through the durable `report_reminder_logs` table (unique
  on company+period+day+kind). Every claim/retry is a single atomic statement —
  `INSERT … ON CONFLICT DO NOTHING` for a fresh reminder, and a conditional
  `UPDATE … WHERE status='failed' OR (status='sending' AND updated_at < now() -
  stale) RETURNING id` for a retry or a crashed worker's reclaim — so under READ
  COMMITTED exactly one worker is handed the row and two workers cannot both
  send. `updated_at` is stamped on every claim and retry. A failed transport is
  recorded `failed` (never `sent`) and retried, not counted.
  `scripts/send_report_reminders.py` runs it from cron and exits `0` on a
  completed run, `2` when the run raised. "Today" resolves in `REMINDERS_TIMEZONE`
  (default `Asia/Bahrain`), not the server's zone. The guarantee is **at-most-once
  per day**, not exactly-once: if SMTP accepts a message and the process dies
  before the `sent` commit, a later run retries it and the recipient can get it
  twice. Do not claim exactly-once without an idempotent transport or a
  transactional outbox.
- The AI provider (`app/ai/provider.py`) takes an injectable `httpx` transport so
  tests exercise the real request path against a mock socket
  (`tests/test_ai_integration.py`); a malformed body raises `AIProviderError` and
  `ai.py` answers `502 ai_provider_failed`, never a fabricated answer.
- Currency safety is proven, not just asserted: `tests/test_currency_no_summation.py`
  checks the dashboard group summary, the report detail and Excel export, the
  accounting export and the AI facts/summary keep each amount in its own currency
  with no combined total.

## Known gaps

- A change to `ROLE_TEMPLATES` does not reach a running database on its own:
  `ensure_system_roles()` reconciles `RolePermission` rows to the template, but
  only `scripts/seed.py` and the tests call it. Re-run the seed after editing a
  template, or the old grant survives and the tab stays visible to a role the
  brief excludes (this is how the service specialist kept the assistant tab).
- Permission gating belongs in the page, not only in the nav: a screen that fires
  its requests before checking the grant shows two or three 403s and looks
  broken to a role that is simply not allowed in. `directives/page.tsx` and
  `assistant/page.tsx` gate first and state the rule; follow that pattern.
- The brand logo is delivered: `frontend/public/brand/holding-logo.png` is
  committed and `BrandMark` serves it. The component still re-checks on mount
  and falls back to a neutral `data-logo="missing"` mark, because the
  server-rendered `<img>` can 404 before hydration and `onError` never fires for
  that first failure.
- The public holding website has no approved specification from the designer
  (§12 defers it), and the privacy-policy text is a draft pending legal review
  (§12, §9). Both are the two non-code items the brief reserves for people.
- Draft companies are a two-sided rule: §6.2 hides them from lists and reports,
  but the design (p.6) shows them in the owner's table with an «تفعيل» control.
  `list_companies()` resolves it by returning drafts only to the holder of
  `company:manage`. Do not "simplify" this to hide drafts from everyone — that
  makes «حفظ مسودة» a dead end, since the activate button lives on the row.

- Two conflicts inside the source documents are **known and recorded**, not
  open questions. §6.2 prose says «ثلاث خطوات … 1/3» but lists four blocks; the
  design (p.7) says «من 1/4 إلى 4/4 … الخطوة الأخيرة مراجعة» and the prototype
  formats `— ${step}/4`, so the wizard is four steps. §12 asks for a daily
  reminder job; the scheduler uses a fixed hour plus bounded retry rather than a
  drifting 24-hour sleep. Both are written up in
  `docs/verification/FINAL_HANDOFF_REPORT.md` §9 — read it before "fixing" either.
- Report values snapshot `field_name_ar` / `field_name_en` at save time
  (§6.4 / Table 6). The snapshot is what a past report renders; the live field
  name is only a fallback for rows written before migration `d5b8e2f61a37`.
  Reverting to `field.name_ar` on read silently rewrites history when a field is
  renamed, and `test_s6_4_editing_a_field_does_not_change_a_past_report` will
  catch it.
- The test suite refuses to run against a database whose name does not end in
  `_test` (`tests/conftest.py`), so the destructive fixtures cannot touch
  `safir_e2e`. To exercise the 13 live journeys, start the API on `safir_e2e` and
  pass `SAFIR_BASE_URL=http://127.0.0.1:8011`; without a server they error with
  `ConnectError`, which is an environment precondition, not a failure.
- Two copy sources describe the public site and they disagree in places. The
  Word spec (`platform-explained-*.docx`) and the prototype
  (`safir_platform_prototype_v10_fixed.html`) are the product authority;
  `content-*.md` is the copy deck and only restates the website face. Where they
  differ the Word spec wins: Table 13 names the phone field «رقم التواصل» on the
  service form but «الهاتف» / "Phone" on the opportunity and CV forms, even
  though the deck and the prototype use «رقم التواصل» everywhere. Do not
  "unify" the label — `phoneLabel` in `PublicForm.tsx` branches on `needsService`
  for exactly this reason.
- The footer is deck §11, not a generic site footer: one Explore column of three
  links (About, Group companies, Solutions), then Contact with email and phone
  only, then the privacy link and the copyright line. It deliberately does not
  repeat the six header links, does not carry a separate Solutions column, and
  does not print the country inside Contact — `test_site_cms.py` pins the nav
  content, and the country lives in the bottom bar.
- There is no PostgreSQL server installed in this container, and the workspace
  is restarted between sessions, so a dead `127.0.0.1:5432` is the normal state,
  not a broken repo. Bring it up with Docker: `sudo -n dockerd &`, then
  `sudo -n docker run -d --name safir-db -e POSTGRES_USER=safir
  -e POSTGRES_PASSWORD=safir -e POSTGRES_DB=safir -p 127.0.0.1:5432:5432
  postgres:16-alpine`. After that: `.venv/bin/python -m alembic upgrade head`,
  `.venv/bin/python scripts/seed.py`, `.venv/bin/python scripts/demo_data.py`
  (the manager's company assignment lives in `demo_data.py`, not `seed.py`), and
  create `safir_test` before running pytest. `scripts/demo_data.py` talks to the
  running API, so start uvicorn first.
