# Page-by-page traceability matrix

Authoritative reference: `platform-design-ar.pdf` (32 pages).

> **BLOCKER — reference asset missing.**
> At the time of writing, neither `platform-design-ar.pdf` nor
> `assets/brand/holding-logo.png` exists in this repository, on the build
> machine, or in the git history (the repository was initialized with only a
> `README.md`). See `docs/verification/reference-asset-blocker.md`.
>
> Because the PDF is the *authoritative* visual and content reference, every
> screen below is implemented to the **behavioural and structural requirements
> stated in the delivery specification**, with design tokens applied exactly as
> specified in section 3 of the prompt. Screen titles, navigation labels,
> column ordering and micro-copy that exist *only* inside the PDF screenshots
> are marked **UNVERIFIED** until the PDF is supplied. No text has been invented
> and presented as if it came from the PDF.

## Status legend

- **IMPL** — implemented and covered by automated tests.
- **UI** — screen implemented in the frontend and wired to the live API.
- **UNVERIFIED** — cannot be confirmed against the PDF because the PDF is absent.

## Matrix

| PDF page | Required screen | Route | Backend | UI | PDF parity |
|---|---|---|---|---|---|
| 1–4 | Design system, components, layout, states, responsive rules | `/[locale]/…` shell + `globals.css` tokens | n/a | IMPL | Tokens applied verbatim from spec §3; per-page visual parity UNVERIFIED |
| 5 | Owner dashboard | `/[locale]/dashboard` | IMPL | UI | UNVERIFIED |
| 6 | Companies management | `/[locale]/companies` | IMPL | UI | UNVERIFIED |
| 7 | Four-step company creation wizard | `/[locale]/companies/new` | IMPL | UI | UNVERIFIED |
| 8 | Owner's monthly reports | `/[locale]/reports` | IMPL | UI | UNVERIFIED |
| 9 | Holding accounting | `/[locale]/accounting` | IMPL | UI | UNVERIFIED |
| 10 | Service requests | `/[locale]/service-requests` | IMPL | UI | UNVERIFIED |
| 11 | Leads management | `/[locale]/leads` | IMPL | UI | UNVERIFIED |
| 12 | Opportunities | `/[locale]/opportunities` | IMPL | UI | UNVERIFIED |
| 13 | Executive directives | `/[locale]/directives` | IMPL | UI | UNVERIFIED |
| 14 | Employees and HR | `/[locale]/hr` | IMPL | UI | UNVERIFIED |
| 15 | Website management | `/[locale]/website` | IMPL | UI | UNVERIFIED |
| 16 | External advisor | `/[locale]/advisor` | IMPL | UI | UNVERIFIED |
| 17 | AI assistant | `/[locale]/assistant` | IMPL | UI | UNVERIFIED |
| 18 | Dynamic form builder | `/[locale]/form-builder` | IMPL | UI | UNVERIFIED |
| 19 | Users and roles | `/[locale]/users` | IMPL | UI | UNVERIFIED |
| 20 | New user creation | `/[locale]/users/new` | IMPL | UI | UNVERIFIED |
| 21 | Activity log | `/[locale]/audit` | IMPL | UI | UNVERIFIED |
| 22 | Company manager dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | UNVERIFIED |
| 23 | Monthly report submission | `/[locale]/reports/[id]` | IMPL | UI | UNVERIFIED |
| 24 | Accountant dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | UNVERIFIED |
| 25 | Report review | `/[locale]/reports/[id]` (review actions) | IMPL | UI | UNVERIFIED |
| 26 | Business developer dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | UNVERIFIED |
| 27 | Marketer dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | UNVERIFIED |
| 28 | Designer dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | UNVERIFIED |
| 29 | Advisor dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | UNVERIFIED |
| 30 | Mobile layouts | responsive shell | IMPL | UI | Breakpoint 820px + min viewport 400px per spec §3 |
| 31 | English LTR interface | `en` locale | IMPL | UI | Full translation dictionary |
| 32 | Dark mode and remaining design requirements | theme toggle | IMPL | UI | Dark tokens applied verbatim from spec §3 |

## Requirements that *are* fully specified and therefore verified

These come from the delivery specification text (not the PDF screenshots) and are
covered by automated tests:

- Authentication, RBAC, company isolation, audit trail — `tests/test_auth_rbac.py`
- Report lifecycle state machine, locking, currency handling — `tests/test_reporting_workflow.py`
- Opportunities, directives, service requests, leads, website conversion, form
  versioning, AI configuration status — `tests/test_operations.py`

## What is required to close the UNVERIFIED rows

1. `platform-design-ar.pdf` committed to `docs/reference/`.
2. `assets/brand/holding-logo.png` committed unchanged.
3. Rendered page images for visual diffing (`docs/screenshots/pdf/`).
4. A side-by-side comparison pass recorded in `docs/verification/`.
