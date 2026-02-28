---
phase: 11-side-by-side-viewer-ui
plan: 02
subsystem: ui
tags: [flask, html, javascript, svg, alto-xml, resizeobserver, vanilla-js]

# Dependency graph
requires:
  - phase: 11-01
    provides: GET /files endpoint, GET / viewer route, templates/viewer.html stub, GET /alto/<stem> and GET /image/<stem> endpoints
provides:
  - templates/viewer.html — complete single-page viewer with CSS flexbox layout, file loading, word spans, SVG overlay, resize handling, keyboard navigation
  - --input CLI flag for app.py (enables serving CLI-processed TIFFs via web viewer)
  - INPUT_DIR fallback scan in serve_image() for CLI-processed TIFFs not in uploads/
affects:
  - Phase 12 (ALTO XML editor): viewer provides the browsing/cross-reference foundation that Phase 12 will extend with inline editing

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vanilla JS event delegation on text-panel container instead of per-word listeners (avoids N listener allocations)"
    - "ResizeObserver on image element to recompute SVG scale factors on window resize without polling"
    - "Generation counter (loadGen) to discard stale async fetch results when user clicks rapidly between files"
    - "SVG overlay inside position:relative; display:inline-block wrapper — tracks image automatically without JS position sync"
    - "pointer-events:none on SVG overlay; pointer-events:all on highlight rect only when visible"

key-files:
  created:
    - templates/viewer.html
    - .planning/phases/11-side-by-side-viewer-ui/11-02-SUMMARY.md
  modified:
    - app.py

key-decisions:
  - "Generation counter (loadGen++) in loadFile() prevents stale fetch results when user clicks multiple sidebar items quickly"
  - "escapeHtml() helper required — OCR content may contain <, >, & characters from source documents"
  - "--input CLI flag + INPUT_DIR fallback added to serve_image() so viewer works for CLI-processed TIFF directories without re-uploading"
  - "img.clientWidth (not naturalWidth) used for scale factors — clientWidth reflects CSS display size; naturalWidth is original pixel size"

patterns-established:
  - "SVG overlay pattern: position:relative wrapper + absolute SVG + pointer-events guard — reusable for Phase 12 ALTO editing overlay"
  - "Bidirectional cross-reference: word span click draws SVG rect; SVG rect click scrolls text panel — pattern for any ALTO coordinate viewer"

requirements-completed:
  - VIEW-01
  - VIEW-04
  - OVLY-01
  - OVLY-02

# Metrics
duration: ~60 min (including human browser verification)
completed: 2026-02-28
---

# Phase 11 Plan 02: Side-by-Side Viewer UI Summary

**Three-column ALTO viewer in pure vanilla JS — sidebar file list, JPEG image panel with SVG bounding box overlay, flowing OCR text panel with bidirectional word-to-box cross-reference, ResizeObserver-driven resize safety, and Prev/Next keyboard navigation**

## Performance

- **Duration:** ~60 min (including human browser verification checkpoint)
- **Started:** 2026-02-28T07:00:00Z (approx — continuation plan)
- **Completed:** 2026-02-28T11:03:37Z
- **Tasks:** 2 (Task 1 implementation + Task 2 human-verify checkpoint)
- **Files modified:** 2 (templates/viewer.html created/replaced, app.py modified)

## Accomplishments
- Replaced templates/viewer.html stub with complete 300+ line implementation: CSS flexbox three-column layout (sidebar 220px / image panel flex:1 / text panel 380px), all CSS and JS inline with no external dependencies
- Implemented full fetch-based file loading with generation counter to prevent stale async responses, ResizeObserver for resize-safe SVG scale recomputation, and bidirectional click cross-reference (word span -> SVG rect, SVG rect -> text panel scroll)
- Added `--input` CLI flag and INPUT_DIR fallback scan to serve_image() so the viewer can display JPEG thumbnails for files processed via pipeline.py (not uploaded through the web UI)
- All 47 tests continue to pass after both task commits

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement complete side-by-side viewer in templates/viewer.html** - `72e1abb` (feat)
2. **Post-checkpoint fix: --input flag and INPUT_DIR fallback in serve_image()** - `f6712fb` (fix)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `templates/viewer.html` — Complete single-page viewer: CSS flexbox three-column layout, JS file loading with generation counter, word span rendering via event delegation, SVG bounding box overlay with pointer-events guard, ResizeObserver-driven scale recomputation, Prev/Next buttons, Left/Right arrow keyboard navigation with INPUT element guard, escapeHtml() for safe OCR content rendering
- `app.py` — Added `--input` argparse argument; added `INPUT_DIR` config key; added INPUT_DIR fallback scan in serve_image() after uploads/ scan fails

## Decisions Made
- **Generation counter in loadFile():** `const gen = ++loadGen` prevents stale fetch results from overwriting a later file load when user clicks rapidly. Checked after every await — if gen !== loadGen, result is silently discarded.
- **escapeHtml() helper required:** ALTO String CONTENT attributes can contain `<`, `>`, `&` from source OCR. Injecting these raw into innerHTML would create broken DOM or XSS.
- **`--input` CLI flag + INPUT_DIR fallback:** Browser verification revealed that CLI-processed TIFFs (run via `pipeline.py --input ./scans`) are not in uploads/ so serve_image() returned 404 for image panel. Fix added a third lookup tier after the uploads/ scan.
- **img.clientWidth for scale factors (not naturalWidth):** clientWidth is the CSS-rendered width in pixels; naturalWidth is the original TIFF pixel size. Scale factor must map ALTO coordinates (in original pixel space) to the rendered image size, so clientWidth / pageWidth is correct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added INPUT_DIR fallback scan in serve_image() for CLI-processed TIFFs**
- **Found during:** Human verification checkpoint (Task 2) — image panel showed broken image for CLI-processed stems
- **Issue:** serve_image() only scanned uploads/ directory for source TIFFs. Files processed via `python pipeline.py --input ./scans` are not in uploads/, so serve_image() returned 404 for their image panel.
- **Fix:** Added third lookup tier: if INPUT_DIR config key is set (from `--input` CLI arg), scan that directory for a TIFF matching the stem. Added `--input` argparse argument and INPUT_DIR config key to CLI entrypoint.
- **Files modified:** app.py
- **Verification:** All 47 tests pass; human verification confirmed image panel loads for CLI-processed TIFFs when server started with `python app.py --input ./scans`
- **Committed in:** f6712fb

---

**Total deviations:** 1 auto-fixed (1 bug discovered during browser verification)
**Impact on plan:** Fix necessary for viewer to work with the primary CLI workflow. No scope creep — pure bug fix for the stated use case in the plan's img error handler note ("Stems in alto/ may have no corresponding TIFF in uploads/").

## Issues Encountered

None — browser verification passed all 10 checks after the INPUT_DIR fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Complete side-by-side viewer is live and verified in browser; all 47 tests passing
- Phase 12 (ALTO XML editor) can build on the SVG overlay pattern — the position:relative wrapper + absolute SVG structure is already established
- The lxml namespace round-trip blocker noted in STATE.md (spike-test etree.tostring against a real ALTO file) should be the first task of Phase 12

## Self-Check: PASSED

- FOUND: templates/viewer.html
- FOUND: app.py (modified)
- FOUND: 11-02-SUMMARY.md
- FOUND commit: 72e1abb (feat — viewer.html implementation)
- FOUND commit: f6712fb (fix — INPUT_DIR fallback)

---
*Phase: 11-side-by-side-viewer-ui*
*Completed: 2026-02-28*
