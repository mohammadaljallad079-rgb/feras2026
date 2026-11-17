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
docs/verification/    completion-matrix.md, visual-comparison.md, functional-acceptance.md
docs/screenshots/     pdf/ (rendered reference) and impl/ (live captures)
scripts/              capture_screens.py, check_mobile.py
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

## Known gaps

- `assets/brand/holding-logo.png` is not in the repository. The header renders a
  neutral mark with `data-logo="missing"` rather than an unapproved stand-in.
  `BrandMark` already points at `/brand/holding-logo.png`; adding the file to
  `frontend/public/brand/` completes the requirement with no code change.
  `BrandMark` re-checks on mount, because the server-rendered `<img>` 404s before
  hydration and `onError` never fires for that first failure.
- The public holding website has no approved specification.
