# Reference asset status

## Summary

The delivery specification names two authoritative inputs, and both are now in
the repository:

| Asset | Path in this repository | Status |
|---|---|---|
| Authoritative design document (32 pages) | `platform-design-ar.pdf` | **Present** (repository root) |
| Official brand logo | `frontend/public/brand/holding-logo.png` | **Present** (served at `/brand/holding-logo.png`) |

The specification quoted `assets/brand/holding-logo.png` as the expected path.
The file is kept in the Next.js public directory so the browser can fetch it
directly, which is the only path the running application can serve; no copy is
recoloured or redrawn. Nothing else about the asset is transformed.

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

## Brand logo — resolved

The asset was supplied and is committed at
`frontend/public/brand/holding-logo.png` (14 KB, PNG RGBA, 245×132). It was
first absent, and that gap is recorded here rather than deleted, because the
fallback path it produced is still live code:

- `components/BrandMark.tsx` still re-checks `img.complete && img.naturalWidth
  === 0` in a mount effect. The `<img>` is server-rendered, so a missing file
  returns 404 *before* React hydrates and `onError` never fires for that first
  failure; without the check the page would show a browser broken-image icon.
  With the check it degrades to the platform name alone.
- The `data-logo` placeholder attribute was removed once the asset shipped, and
  the "no placeholder logo remains in the DOM" assertion now guards that.

### How the supplied artwork is used

The lockup is dark teal on transparency, drawn for a light background, and it
contains its own wordmark in Arabic and English. Two consequences shaped the
integration:

- On the navy sidebar (`--side`, `#0b192c`) the artwork measured 3.85:1 on
  average with 22.4% of its opaque pixels below 3:1. It is therefore seated on a
  light plate on that surface, where the same pixels measure 4.83:1 with 4.9%
  below 3:1; the file itself is untouched. On light cards and in light mode it
  sits directly on the surface.
- Because the artwork carries the wordmark, the auth cards no longer print the
  platform name a second time beside it.

The rendered height is the only property constrained, so the artwork always
keeps its own aspect ratio. A browser assertion set covers the sidebar, the auth
cards, the aspect ratio, the plate and the absence of a placeholder; see
`scripts/check_visual_fixes.py`, section "page 32 — official brand logo".
