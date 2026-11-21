# Phase 1 — Audit & Integration Plan

Audit of the existing repository against the corporate-website brief, and the
plan for adding the public website and its CMS without disturbing the running
admin platform.

## 1. Blocking input gap — the content files are missing

The brief names two **authoritative, mandatory** content files:

1. `content-ar.md` — Arabic copy
2. `content-en.md` — English copy

They are **not present** in the repository, in the working tree, in git history
(any branch), or anywhere on the filesystem:

```text
find / -iname 'content-ar.md' -o -iname 'content-en.md'      → no results
git log --all -- '*content-ar*' '*content-en*'               → no results
grep -r 'ابدأ طلب الخدمة' (outside the PDF)                  → no results
```

The brief says the copy must be followed exactly and that inventing content is
forbidden. The only website copy that exists in the repository today is:

- the brand name — «ستارت أب سفير القابضة» / "Start Up Sphere Holding";
- the contact details quoted inline in the brief itself (Kingdom of Bahrain,
  `info@sup-edu.com`, `+973 17626990`);
- the six approved service names, the three hero-slide headlines, the section
  headings, the three form field sets, and the legal notice — all quoted inline
  in the brief.

**Consequence.** Phases 3–4 are implemented against a single, explicit content
source (`backend/app/content/site_content.py`) seeded with *only* what the brief
states, and every string that the missing files would have supplied is marked
`needs_review: true` in the seed so the owner can supply or approve it from the
CMS before launch. No copy, number, statistic, company name, service description
or claim has been invented. If `content-ar.md` / `content-en.md` are provided,
they are the intended input for that seed and nothing else changes.

## 2. What already exists (reused, not rebuilt)

| Area | Present | Evidence |
|---|---|---|
| Stack | Next.js 15 App Router + FastAPI + PostgreSQL + Alembic + Docker Compose + Nginx | `frontend/`, `backend/`, `docker-compose.yml`, `deploy/nginx.conf` |
| Auth | JWT access/refresh, password hashing, reset links, server-side session enforcement | `backend/app/api/v1/auth.py`, `app/core/security.py` |
| RBAC | 8 system roles, permission catalog, per-route `require(...)` / `require_any(...)` | `app/core/permissions.py`, `app/api/deps.py` |
| Companies module | Full CRUD, 3-step wizard, status, `public_visible` flag, logo file | `app/api/v1/companies.py`, `models/business.py:Company` |
| Public API (partial) | `GET /public/companies` (visible+active only), `POST /public/submissions` with rate limit | `app/api/v1/public.py` |
| Submissions store | `website_submissions` table (kind, name, email, phone, message, status, source_ip) | `models/operations.py:WebsiteSubmission` |
| Website admin (partial) | Submission list, convert/reject, company visibility toggle | `app/api/v1/website.py`, `frontend/app/(app)/website/page.tsx` |
| File storage | Private storage, randomised names, type/size validation, authorised download | `app/api/v1/files.py`, `app/models/business.py:StoredFile` |
| Audit | `audit_events` table + writers | `app/models/identity.py`, `app/api/v1/audit.py` |
| i18n | AR/EN dictionary, RTL/LTR, locale persistence | `frontend/lib/i18n.ts`, `frontend/lib/auth.tsx` |
| Brand | Official logo committed and served at `/brand/holding-logo.png` (245×132) | `frontend/public/brand/holding-logo.png` |
| Arabic font | Tajawal self-hosted (SIL OFL 1.1) | `frontend/public/fonts/` |

## 3. What is missing (to be built)

| Gap | Plan |
|---|---|
| **No public website pages** | New route group `frontend/app/(site)/[locale]/…` — separate chrome from the admin shell |
| **No CMS tables** | New tables: `site_settings`, `site_sections`, `site_slides`, `site_services`, `site_nav_links` (+ `content_json` for editable copy) |
| **Submissions store too narrow** | Extend `website_submissions`: `reference_no`, `service_type`, `country`, `subject`, `expertise`, `attachment_file_id`, `assigned_user_id`, `internal_notes`, `consent`, `reviewed_at` |
| **No submission status workflow** | `SubmissionStatus` gains `in_review`, `needs_followup`, `completed`, `closed` |
| **No status history** | New `website_submission_events` table (append-only) |
| **No attachment on submissions** | Reuse `stored_files`; link optional study/resume via `attachment_file_id`; private download only |
| **No CMS API** | New endpoints under `/api/v1/website/*` for content, services, nav, slides, settings, submissions inbox |
| **No SEO surface** | `sitemap.ts`, `robots.ts`, per-page metadata, hreflang, canonical, Open Graph, Organization structured data |
| **No routing for two apps on one domain** | Nginx: `/platform/` → admin UI, `/` → public site, `/api/` → FastAPI (see Phase 6) |

## 4. Routing decision (least disruptive)

Today the Next.js app serves the admin UI at `/`. The brief requires the public
site at `/` and the admin at `/platform/`. The least disruptive change that
keeps every existing admin route working:

- Move the existing admin route group under a `/platform` path segment so its
  URLs become `/platform/dashboard`, `/platform/companies`, … .
- Add the public site under `/[locale]` (`/ar/…`, `/en/…`) with `/` redirecting
  to the detected/default locale.
- Nginx continues to serve **one** Next.js process; it only needs `server_name`
  `sup-edu.com` and the existing `/api/` proxy. No second app, no new origin,
  no CORS change.

A `redirects()` map in `next.config` preserves any bookmarked old admin path
(`/dashboard` → `/platform/dashboard`) so nothing breaks.

## 5. Data-model plan (additive only)

All changes are **additive**: new tables and new nullable columns. No column is
dropped, renamed or retyped, so existing rows and the running platform are
untouched. One Alembic revision.

```text
site_settings        singleton row per key: brand, contact, seo, legal notice
site_sections        ordered, toggleable homepage sections (about, service,
                     opportunities, careers, contact) with AR/EN copy
site_slides          hero slides: AR/EN headline+body, image, CTA labels, order
site_services        the six approved services: AR/EN name, optional AR/EN
                     description (owner-approved), icon key, order, active
site_nav_links       header/footer navigation, AR/EN label, href, order
website_submissions  + reference_no, service_type, country, subject, expertise,
                     attachment_file_id, assigned_user_id, internal_notes,
                     consent, reviewed_at   (all nullable)
website_submission_events   append-only status/assignment history
```

Company publishing reuses the existing `companies.public_visible` flag and the
existing sector/country/logo fields. **No company table is duplicated.**

## 6. Permission plan (existing catalog extended)

New permissions, granted to `owner` (and `admin` where applicable):

```text
site:manage        edit CMS content, services, nav, slides, settings
site:submissions   read the submission inbox
site:assign        assign a submission to a user
```

The public website and public API read **only** `public_visible` companies and
never expose financial, manager, address or internal fields. Submission
attachments are served only through the authenticated, authorised download
endpoint.

## 7. Security plan

- Public forms: server-side validation (Pydantic), per-IP rate limiting (already
  present, extended to attachments), file type/size validation, private storage,
  randomised names, no public path.
- A submission row is written first; the attachment is linked in the same
  transaction so a failed upload never loses the request (the row survives with
  a null attachment and is flagged for follow-up).
- No email is sent until an SMTP host is configured and verified; with no SMTP
  the submission still persists and the success message reflects a saved record.
- Every sensitive action writes an `audit_events` row.

## 8. Deployment plan (Phase 6, documented now)

- Back up `deploy/nginx.conf` and the production database before any change.
- Verify `server_name` conflicts before editing the live server block.
- Keep the old admin URLs working via redirects; keep a rollback image/commit.
- Never commit production secrets; never run demo seed on production.
- Migrations are additive and reversible.

## 9. What is explicitly provisional

- The visual design is proposed (brand colours derived from the logo; the
  brief's palette is used as the starting point) and is shown as a preview for
  owner approval before it is treated as final.
- Service descriptions, section body copy and SEO text are marked
  `needs_review` until the owner approves them in the CMS.
- The privacy-policy text is presented as requiring legal review, as the brief
  requires.
