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
                      FINAL_HANDOFF_REPORT.md (independent-review package)
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
  `scripts/send_report_reminders.py` runs it from cron (idempotent per day).

## Known gaps

- The brand logo is delivered: `frontend/public/brand/holding-logo.png` is
  committed and `BrandMark` serves it. The component still re-checks on mount
  and falls back to a neutral `data-logo="missing"` mark, because the
  server-rendered `<img>` can 404 before hydration and `onError` never fires for
  that first failure.
- The public holding website has no approved specification from the designer
  (§12 defers it), and the privacy-policy text is a draft pending legal review
  (§12, §9). Both are the two non-code items the brief reserves for people.
