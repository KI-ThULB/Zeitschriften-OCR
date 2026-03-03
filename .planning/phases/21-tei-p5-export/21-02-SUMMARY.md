---
phase: 21-tei-p5-export
plan: 02
subsystem: api
tags: [tei, flask, endpoint, viewer, html, javascript]

requires:
  - phase: 21-tei-p5-export/21-01
    provides: tei.py module with build_tei(output_dir, stem) -> bytes
  - phase: 16-mets-mods-output
    provides: dual-write pattern (write to disk + serve as attachment in same request)

provides:
  - GET /tei/<stem> Flask endpoint in app.py
  - output/tei/<stem>.xml written to disk on each download
  - Download TEI button in viewer.html #nav-bar (green, disabled until file loaded)
  - downloadTei() JS function in viewer

affects: []

tech-stack:
  added: []
  patterns:
    - "TEI endpoint mirrors METS pattern: validate stem, check ALTO exists, call builder, write to disk, serve as attachment"
    - "Viewer button enable pattern: disabled in HTML, enabled in loadFile() alongside segment-btn"
    - "encodeURIComponent(currentStem) for safe URL construction in downloadTei()"

key-files:
  created: []
  modified:
    - app.py
    - templates/viewer.html
    - tests/test_app.py

key-decisions:
  - "TestExportTei placed in tests/test_app.py (plan spec) not test_mets.py — TEI endpoint test stays alongside app endpoint tests"
  - "Path traversal test uses URL-encoded stem (%2F) since Flask normalises raw slashes in URL segments"
  - "tei-btn positioned between segment-btn and segment-status span to match toolbar flow"

patterns-established:
  - "Pattern: per-page download endpoint — GET /<format>/<stem> validates, builds, writes disk copy, returns attachment"

requirements-completed: [TEI-01, TEI-02, TEI-03]

duration: 10min
completed: 2026-03-03
---

# Phase 21 Plan 02: TEI Flask Endpoint and Viewer Button Summary

**GET /tei/<stem> Flask endpoint with disk write + browser download, and green Download TEI button in viewer toolbar — wires tei.py builder into the UI**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-03T12:30:00Z
- **Completed:** 2026-03-03T12:40:00Z
- **Tasks:** 2 automated + 1 checkpoint (human-verify pending)
- **Files modified:** 3

## Accomplishments

- GET /tei/<stem> endpoint: validates stem (path traversal blocked with 400), checks ALTO exists (404 if missing), calls tei_module.build_tei(), writes output/tei/<stem>.xml to disk, returns XML as downloadable attachment named <stem>_tei.xml
- TestExportTei: 3 new endpoint tests covering success download, 404 for missing, 400 for traversal — all pass
- Download TEI button in viewer #nav-bar: green (#2e7d32), disabled on init, enabled in loadFile(), triggers downloadTei() which sets window.location = '/tei/' + encodeURIComponent(currentStem)
- Full suite: 156 tests green (153 before + 3 new, no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GET /tei/<stem> endpoint to app.py** - `e255cf1` (feat)
2. **Task 2: Add Download TEI button to viewer.html #nav-bar** - `3e843c9` (feat)
3. **Task 3: Human-verify TEI download end-to-end** - (checkpoint: human-verify pending)

## Files Created/Modified

- `/Users/zu54tav/Zeitschriften-OCR/app.py` — added `import tei as tei_module`, added export_tei() endpoint after export_mets()
- `/Users/zu54tav/Zeitschriften-OCR/templates/viewer.html` — added #tei-btn, CSS, downloadTei() JS function, enable in loadFile()
- `/Users/zu54tav/Zeitschriften-OCR/tests/test_app.py` — added _TEI_ALTO_FIXTURE constant and TestExportTei class (3 tests)

## Decisions Made

- **TestExportTei in test_app.py:** Plan explicitly specified tests/test_app.py. TestGetMetsEndpoint lives in test_mets.py, but the TEI plan is for the app endpoint tests to live in test_app.py alongside other app route tests.

- **Path traversal test with encoded slash:** Flask normalises raw slashes in URL path segments (a GET to /tei/../../etc/passwd gets rerouted), so the test uses URL-encoded form (%2F) to exercise the endpoint's stem validation logic directly.

- **tei-btn placement:** Inserted between segment-btn and segment-status span so toolbar reads: Prev | Next | Segment | Download TEI | [status]. Keeps status span adjacent to segment actions.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 21 automation complete — human verification of browser download pending (Task 3 checkpoint)
- After user confirms TEI download works end-to-end, Phase 21 TEI P5 Export is fully complete
- Requirements TEI-01, TEI-02, TEI-03 satisfied by Plans 01 and 02 combined

## Self-Check: PASSED

- app.py: FOUND (export_tei at line 861)
- templates/viewer.html: FOUND (#tei-btn, downloadTei(), CSS, loadFile enable)
- tests/test_app.py: FOUND (TestExportTei, _TEI_ALTO_FIXTURE)
- 21-02-SUMMARY.md: FOUND
- Commit e255cf1: FOUND (feat: endpoint)
- Commit 3e843c9: FOUND (feat: viewer button)

---
*Phase: 21-tei-p5-export*
*Completed: 2026-03-03*
