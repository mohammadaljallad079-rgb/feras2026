# Safir Holding Platform — منصة صفير القابضة

An Arabic-first, bilingual (AR/EN) holding-company management platform: company
register, monthly reporting workflow, holding accounting, service requests,
CRM (leads and opportunities), executive directives, HR, website administration,
advisor messaging, a permission-scoped AI assistant, a dynamic report form
builder, users/roles and an audit trail.

- **Frontend** — Next.js 15 (App Router), TypeScript, Tailwind CSS, RTL/LTR
- **Backend** — FastAPI, SQLAlchemy 2, Alembic, Pydantic
- **Database** — PostgreSQL with foreign keys, transactional workflows and audit rows
- **Infrastructure** — Docker Compose, Nginx reverse proxy, GitHub Actions CI

Architecture is a modular monolith: one deployable API, one deployable UI, one
database, with domain modules under `backend/app/api/v1/`.

> **Design reference.** `platform-design-ar.pdf` (32 pages) is the authoritative
> visual reference for the *platform UI*. It is **not currently in this
> repository**, and neither is `assets/brand/holding-logo.png`. See
> `docs/verification/reference-asset-blocker.md`. Every screen whose fidelity
> depends on the PDF is marked **UNVERIFIED** in
> `docs/reference/TRACEABILITY.md`; nothing has been invented to fill the gap.
> The reference does **not** describe the public holding website, whose design
> is a separate, unapproved deliverable.

## Implementation rule

Rebuild the application from scratch against the owner's PDF reference, including
page-by-page design parity, content, roles, permissions, workflows, backend,
PostgreSQL schema, AR/EN locale support, light/dark modes, responsive design, and
end-to-end tests. Never invent missing text or features as if they appeared in
the PDF. Public website design requires a separate approved specification.

## Repository layout

```
backend/            FastAPI application
  app/api/v1/       domain routers (companies, reporting, crm, hr, ai, …)
  app/core/         config, db, security, permission catalog
  app/models/       SQLAlchemy models
  app/schemas/      Pydantic request/response models
  alembic/          migrations
  scripts/seed.py   system roles + demonstration accounts
  tests/            unit, integration and end-to-end journey tests
frontend/           Next.js application (app/, components/, lib/)
deploy/nginx.conf   reverse proxy
docs/               traceability, verification and screenshots
docker-compose.yml  development / reference deployment
```

## Local setup

Prerequisites: Python 3.12, Node 22, PostgreSQL 16.

```bash
# 1. Database
createdb safir
createdb safir_test          # used by the test suite

# 2. Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export DATABASE_URL="postgresql+psycopg://safir:safir@localhost:5432/safir"
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
export STORAGE_DIR=/tmp/safir-storage
alembic upgrade head
python scripts/seed.py       # creates 8 system roles and 8 demonstration accounts
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm ci
export BACKEND_URL=http://localhost:8000
npm run dev                  # http://localhost:3000
```

The frontend proxies `/api/backend/*` to the backend, so the browser talks to a
single origin.

### Demonstration accounts

`scripts/seed.py` creates these so the workflows can be exercised. They are
**not** presented as real business data, and no company or report rows are
invented — those are created through the application.

| Email | Role |
|---|---|
| `owner@safir-platform.com` | Holding owner |
| `manager@safir-platform.com` | Company manager |
| `accountant@safir-platform.com` | Accountant |
| `bd@safir-platform.com` | Business developer |
| `marketer@safir-platform.com` | Marketer |
| `designer@safir-platform.com` | Designer |
| `advisor@safir-platform.com` | External advisor |
| `specialist@safir-platform.com` | Service specialist |

Password for all: `Safir!2026`. Change or remove them before any real deployment.

## Tests

The suite has two halves. `tests/test_auth_rbac.py`, `tests/test_operations.py`
and `tests/test_reporting_workflow.py` run in-process against `safir_test`,
which they truncate between tests. `tests/test_e2e_journeys.py` drives the real
HTTP API, so it needs a running server and a *separate* database — if the live
server shared `safir_test`, the truncation would delete the seeded accounts
mid-run.

```bash
# 1. The journey database, once
createdb safir_e2e

# 2. Migrate and seed it, then start the API it will talk to
cd backend
export E2E_DATABASE_URL="postgresql+psycopg://safir:safir@localhost:5432/safir_e2e"
DATABASE_URL="$E2E_DATABASE_URL" alembic upgrade head
DATABASE_URL="$E2E_DATABASE_URL" python scripts/seed.py
DATABASE_URL="$E2E_DATABASE_URL" uvicorn app.main:app --port 8000 &

# 3. Run everything
pytest -q                                     # 37 tests
SAFIR_BASE_URL=http://localhost:8000 pytest tests/test_e2e_journeys.py -v
```

`pytest.ini` puts the backend root on `sys.path`, so the suite runs with no
`PYTHONPATH` set — the same way CI invokes it. Coverage is listed in
`docs/verification/functional-acceptance.md`; `.github/workflows/ci.yml` runs
exactly the sequence above.

### Browser captures

With both servers running and the journey database seeded:

```bash
python3 scripts/capture_screens.py   # 46 screenshots into docs/screenshots/impl/
python3 scripts/check_mobile.py      # asserts no horizontal scroll at 400px
```

```bash
cd frontend
npx tsc --noEmit
npm run build
```

## Configuration

All secrets come from the environment; nothing is committed with a real
credential. See `.env.example` for the full list. Key settings:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key — generate a long random value |
| `STORAGE_DIR` | Private root for uploaded files |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `AI_PROVIDER`, `AI_MODEL`, `AI_BASE_URL` | AI provider abstraction (default `openai`) |
| `OPENAI_API_KEY` | Provider key. **Empty ⇒ the assistant reports an unconfigured status and never fabricates an answer.** |

`ENVIRONMENT=production` rejects the development placeholder `SECRET_KEY`.

## Deployment

```bash
cp .env.example .env      # set POSTGRES_PASSWORD, SECRET_KEY, OPENAI_API_KEY
docker compose up --build -d
```

Nginx fronts both services on `${HTTP_PORT}` (default 8080). The backend applies
migrations on start. Health and readiness probes are available at `/health` and
`/ready`. Put a TLS terminator in front of Nginx for production.

## Security model

- Passwords hashed with bcrypt; never emailed in plain text.
- Access and refresh tokens; password reset uses single-use, expiring links.
- RBAC enforced **on the backend** for every protected route. Hiding a control in
  the UI is a convenience, never the enforcement point.
- Company-level isolation; cross-company access returns `404` without confirming
  the record exists.
- Sensitive uploads live in private storage and are served only through an
  authenticated, authorized download endpoint. Confidential HR attachments show
  `مرفق مقيد` when access is disallowed.
- Audit rows record timestamp, actor, role, action, target and company scope.
- Monetary amounts use decimal types and are never summed across currencies.
