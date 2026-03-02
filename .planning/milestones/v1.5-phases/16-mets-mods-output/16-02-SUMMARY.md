---
phase: 16-mets-mods-output
plan: 02
status: complete
completed: 2026-03-01
tests_passing: 101
---

# 16-02 Summary: Download METS Button

## What Was Built

Added a "Download METS" green button to the upload dashboard (`templates/upload.html`).

## Artifacts

- `templates/upload.html` — `#btn-mets`, `#mets-export`, `#mets-toast`, `downloadMets()` function

## Key Behaviors

- Clicking "Download METS" calls `GET /mets`
- 200 response: browser downloads `mets.xml` via blob URL
- 204 response (no ALTO files yet): red toast "No processed files yet — run OCR first."
- Non-200/204: red toast `Export failed (N)`

## Tests

101 tests passing, no regressions. STRUCT-04 satisfied.
