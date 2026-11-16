# Page-by-page traceability matrix

Authoritative reference: `platform-design-ar.pdf` (32 pages).

> **Reference status.** `platform-design-ar.pdf` (32 pages) is present at the
> repository root and rendered to `docs/screenshots/pdf/page-NN.png`; each page
> was read and its Arabic content transcribed before the screen was built. The
> only outstanding reference asset is `assets/brand/holding-logo.png`; see
> `docs/verification/reference-asset-blocker.md`.
>
> Page-by-page visual comparison is recorded in
> `docs/verification/visual-comparison.md`. Where a page's micro-copy is too
> small to transcribe with certainty, the row records the ambiguity instead of
> inventing an exact wording.

## Status legend

- **IMPL** — implemented and covered by automated tests.
- **UI** — screen implemented in the frontend and wired to the live API.
- **MATCH** — compared against the rendered PDF page; layout, content and actions correspond.
- **PARTIAL** — the screen is correct in substance; a specific detail still differs and is listed.
- **AMBIGUOUS** — the PDF text at that spot is not legible enough to confirm wording.

## Matrix

| PDF page | Required screen | Route | Backend | UI | PDF parity |
|---|---|---|---|---|---|
| 1–4 | Design system, components, layout, states, responsive rules | `/[locale]/…` shell + `globals.css` tokens | n/a | IMPL | Tokens applied verbatim from spec §3; per-page visual parity MATCH |
| 5 | Owner dashboard | `/[locale]/dashboard` | IMPL | UI | MATCH |
| 6 | Companies management | `/[locale]/companies` | IMPL | UI | MATCH |
| 7 | Four-step company creation wizard | `/[locale]/companies/new` | IMPL | UI | MATCH |
| 8 | Owner's monthly reports | `/[locale]/reports` | IMPL | UI | MATCH |
| 9 | Holding accounting | `/[locale]/accounting` | IMPL | UI | MATCH |
| 10 | Service requests | `/[locale]/service-requests` | IMPL | UI | MATCH |
| 11 | Leads management | `/[locale]/leads` | IMPL | UI | MATCH |
| 12 | Opportunities | `/[locale]/opportunities` | IMPL | UI | MATCH |
| 13 | Executive directives | `/[locale]/directives` | IMPL | UI | MATCH |
| 14 | Employees and HR | `/[locale]/hr` | IMPL | UI | MATCH |
| 15 | Website management | `/[locale]/website` | IMPL | UI | MATCH |
| 16 | External advisor | `/[locale]/advisor` | IMPL | UI | MATCH |
| 17 | AI assistant | `/[locale]/assistant` | IMPL | UI | MATCH |
| 18 | Dynamic form builder | `/[locale]/form-builder` | IMPL | UI | MATCH |
| 19 | Users and roles | `/[locale]/users` | IMPL | UI | MATCH |
| 20 | New user creation | `/[locale]/users/new` | IMPL | UI | MATCH |
| 21 | Activity log | `/[locale]/audit` | IMPL | UI | MATCH |
| 22 | Company manager dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | MATCH |
| 23 | Monthly report submission | `/[locale]/reports/[id]` | IMPL | UI | MATCH |
| 24 | Accountant dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | MATCH |
| 25 | Report review | `/[locale]/reports/[id]` (review actions) | IMPL | UI | MATCH |
| 26 | Business developer dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | MATCH |
| 27 | Marketer dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | MATCH |
| 28 | Designer dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | MATCH |
| 29 | Advisor dashboard | `/[locale]/dashboard` (role variant) | IMPL | UI | MATCH |
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

## What remains

1. `assets/brand/holding-logo.png` committed unchanged (see the asset-status note).
2. An approved specification for the public holding-company website. The PDF
   covers the management platform only, so no website screen claims fidelity.

Every screen row is now MATCH against its rendered reference page; the evidence
is `docs/verification/visual-comparison.md` and the captures in
`docs/screenshots/impl/`.
