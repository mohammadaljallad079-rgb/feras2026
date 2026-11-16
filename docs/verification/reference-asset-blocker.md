# Reference asset status

## Summary

The delivery specification names two authoritative inputs:

| Asset | Expected path | Status |
|---|---|---|
| Authoritative design document (32 pages) | `platform-design-ar.pdf` | **Present** (repository root) |
| Official brand logo | `assets/brand/holding-logo.png` | **MISSING** |

## Design reference — resolved

`platform-design-ar.pdf` (2.4 MB, 32 pages) is committed at the repository root
and its pages are rendered to `docs/screenshots/pdf/page-NN.png`. Every page has
been read and its Arabic content transcribed, which is what the page-by-page
implementation and the fidelity record in
`docs/verification/visual-comparison.md` are built from. The earlier "reference
missing" blocker no longer applies to the design document.

Two page groups are explicitly *not* governed by the PDF, and are treated as
separately specified deliverables:

- The public holding-company **website**. The PDF states that it covers the
  management platform only; no website design is specified, so no website screen
  is presented as visually faithful.
- The prototype's **simulation controls** (role switcher banner, "demo data"
  notes). These must not appear in the production application and do not.

## Brand logo — still blocking

`assets/brand/holding-logo.png` does not exist. This was verified by:

- `git ls-files` and the full git history (three commits) — no logo file.
- A filesystem search for `holding-logo*` / `*.png` / `*.svg` outside
  `node_modules`, `.venv`, `.next` and `docs/screenshots` — no match.
- `frontend/public/brand/` is empty.

Impact: the specification requires the supplied logo to be used unaltered, with
its proportions, colours and internal artwork preserved. Until the file is
supplied, `components/BrandMark.tsx` renders a neutral text mark and sets
`data-logo="missing"` on the element, so the gap is visible in the DOM and in
every screenshot rather than silently passing as approved branding. The
component already points at `/brand/holding-logo.png`; dropping the file into
`frontend/public/brand/` completes the requirement with no code change.

## Action required

```
frontend/public/brand/holding-logo.png   # the supplied asset, unchanged
```
