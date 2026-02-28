---
phase: 11-side-by-side-viewer-ui
plan: 01
subsystem: ui
tags: [flask, jinja2, pathlib, html, alto-xml]

# Dependency graph
requires:
  - phase: 10-tiff-and-alto-data-endpoints
    provides: GET /alto/<stem> and GET /image/<stem> endpoints; alto/ directory with ALTO XML files
provides:
  - GET /files endpoint returning alphabetically sorted list of ALTO stems
  - GET / route rendering templates/viewer.html
  - templates/viewer.html stub for render_template to succeed
  - TestFilesEndpoint (4 tests) and TestViewerRoute (2 tests)
affects:
  - 11-02 (plan 02 replaces stub viewer.html with full viewer implementation)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flask render_template for server-side HTML delivery"
    - "pathlib glob('*.xml') for listing ALTO stems from alto/ directory"

key-files:
  created:
    - templates/viewer.html
    - .planning/phases/11-side-by-side-viewer-ui/11-01-SUMMARY.md
  modified:
    - app.py
    - tests/test_app.py

key-decisions:
  - "GET /files returns empty stems list when alto/ directory does not exist (graceful no-dir handling)"
  - "templates/viewer.html is a stub in plan 01; full implementation delivered in plan 02"
  - "Added top-level 'from pathlib import Path' to tests/test_app.py — was only present inside test method bodies"

patterns-established:
  - "Phase 11 test classes: TestFilesEndpoint and TestViewerRoute follow same fixture usage pattern as existing Phase 10 tests"

requirements-completed:
  - VIEW-01

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 11 Plan 01: Side-by-Side Viewer UI Summary

**Flask GET /files JSON endpoint for sorted ALTO stems and GET / viewer route with Jinja2 templates/viewer.html stub, backed by 6 new pytest tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T07:09:42Z
- **Completed:** 2026-02-28T07:11:10Z
- **Tasks:** 1
- **Files modified:** 3 (app.py, tests/test_app.py, templates/viewer.html created)

## Accomplishments
- Added GET /files route returning alphabetically sorted ALTO XML stems from output/alto/; returns empty list when alto/ directory absent
- Added GET / viewer route rendering templates/viewer.html via render_template
- Created templates/viewer.html minimal stub enabling render_template to succeed without TemplateNotFound
- Added TestFilesEndpoint (4 tests) and TestViewerRoute (2 tests); all 47 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GET /files tests, GET / test, and update app.py with both routes + templates/viewer.html stub** - `e525066` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `app.py` - Added render_template import, GET /files (list_files), GET / (viewer) routes
- `tests/test_app.py` - Added top-level Path import, TestFilesEndpoint and TestViewerRoute test classes
- `templates/viewer.html` - Minimal HTML stub served by GET /

## Decisions Made
- GET /files returns `{'stems': []}` when alto/ does not exist — graceful handling matches the plan truth "returns {'stems': []} when alto/ directory does not exist"
- templates/viewer.html is a stub for plan 01 only; plan 02 will replace it with the full side-by-side viewer
- Added `from pathlib import Path` at module top level in tests/test_app.py — it was only inside test method bodies before; needed for the Phase 11 test classes which use Path at class scope

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- GET /files and GET / routes are live and tested; ready for plan 02 to replace viewer.html stub with full implementation
- All 47 tests passing (41 pre-existing + 6 new)

---
*Phase: 11-side-by-side-viewer-ui*
*Completed: 2026-02-28*
