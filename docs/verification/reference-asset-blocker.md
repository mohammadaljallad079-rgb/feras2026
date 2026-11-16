# Reference asset blocker

## Summary

The delivery specification names two authoritative inputs:

| Asset | Expected path | Status |
|---|---|---|
| Authoritative design document (32 pages) | `platform-design-ar.pdf` | **MISSING** |
| Official brand logo | `assets/brand/holding-logo.png` | **MISSING** |

## How this was verified

- The repository was cloned from `mohammadaljallad079-rgb/feras2026`.
- `git ls-files` returns only `README.md`; the full git history contains a single
  commit (`83913ad`) that adds `README.md` and nothing else.
- The GitHub contents API for the repository root returns only `README.md`.
- A filesystem search for `platform-design*` and `holding-logo*` across the whole
  build machine returns no match.
- There is no `assets/` directory in the repository; `assets/brand/` exists only
  as an empty directory created for the expected logo.

## Impact

1. **Visual fidelity cannot be certified.** The specification requires that every
   screen match the PDF's layout, colours, typography, spacing, sidebar, content,
   buttons, forms, tables and status chips, with a side-by-side comparison report.
   Without the PDF this comparison is impossible.
2. **Exact Arabic micro-copy cannot be transcribed.** Screen titles, captions and
   labels that exist only inside the PDF screenshots cannot be reproduced verbatim.
   Nothing has been invented to fill the gap.
3. **Branding cannot be applied.** The official logo must be used unaltered; the
   file is not available.

## What was done instead

The platform was implemented against the parts of the specification that are
fully self-contained — the design tokens (spec §3), the screen matrix (spec §4),
the permission model (spec §5), the workflow rules (spec §6–§19) and the
production requirements (spec §20–§22). All of these are implemented in code and
covered by automated tests.

Per the specification ("Record unresolved ambiguity rather than inventing an exact
transcription"), every row whose fidelity depends on the PDF is marked
**UNVERIFIED** in `docs/reference/TRACEABILITY.md`.

## Action required

Commit the two assets to the repository, then the visual verification pass in
`docs/verification/` can be completed:

```
docs/reference/platform-design-ar.pdf
assets/brand/holding-logo.png
```
