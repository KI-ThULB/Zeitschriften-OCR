---
phase: 13-upload-ui-and-live-progress
plan: "01"
subsystem: ui
tags: [flask, routing, viewer, upload-dashboard]

# Dependency graph
requires:
  - phase: 12-word-correction
    provides: app.py with working viewer route at GET /
  - phase: 11-side-by-side-viewer-ui
    provides: viewer.html template
provides:
  - GET / rerouted to upload.html (upload dashboard entry point)
  - GET /viewer/<stem> serving viewer.html with path traversal guard
  - TestViewerStemRoute (3 tests) covering new /viewer/<stem> route
affects:
  - 13-02 (Plan 02 creates upload.html — TestViewerRoute tests become green)

# Tech tracking
tech-stack:
  added: []
  patterns: [path-traversal-guard on stem routes, render_template routing pattern]

key-files:
  created: []
  modified:
    - app.py
    - tests/test_app.py

key-decisions:
  - "GET / renamed from viewer() to index() — semantically correct for upload dashboard entry point"
  - "GET /viewer/<stem> path traversal guard uses same pattern as /image/<stem> and /alto/<stem>"
  - "TestViewerRoute tests left red (TemplateNotFound: upload.html) until Plan 02 creates the template — expected, not a regression"

patterns-established:
  - "All stem-based routes carry if '/' in stem or '..' in stem guard returning 400"

requirements-completed:
  - INGEST-01
  - INGEST-02
  - INGEST-03
  - PROC-01
  - PROC-02

# Metrics
duration: 1min
completed: 2026-03-01
---

# Phase 13 Plan 01: Upload UI and Live Progress — Routing Prerequisite Summary

**GET / rerouted to upload.html and GET /viewer/<stem> added with path traversal guard, enabling Phase 13 upload dashboard**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-01T08:00:33Z
- **Completed:** 2026-03-01T08:01:28Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Changed GET / from rendering viewer.html to upload.html (upload dashboard, Plan 02 creates the template)
- Added GET /viewer/<stem> with path traversal security check, rendering viewer.html (existing template)
- Added TestViewerStemRoute with 3 passing tests covering 200 HTML, non-empty body, and path traversal rejection
- Updated TestViewerRoute method names to reference "upload dashboard" for clarity

## Task Commits

Each task was committed atomically:

1. **Task 1: Add /viewer/<stem> route and reroute GET / to upload.html** - `833f5b5` (feat)
2. **Task 2: Update TestViewerRoute tests and add TestViewerStemRoute** - `2852559` (feat)

**Plan metadata:** `(pending final docs commit)` (docs: complete plan)

## Files Created/Modified
- `app.py` - GET / now index() renders upload.html; new GET /viewer/<stem> renders viewer.html
- `tests/test_app.py` - Updated TestViewerRoute docstrings; added TestViewerStemRoute (3 tests)

## Decisions Made
- Renamed `viewer()` function to `index()` to match the new semantic purpose of the route (upload/progress dashboard, not the viewer)
- Kept TestViewerRoute assertions identical — they still test `GET /` returns 200 HTML, which will be true once upload.html exists in Plan 02
- TestViewerRoute tests intentionally left red (2 failures) — TemplateNotFound for upload.html is expected until Plan 02 completes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The 2 TestViewerRoute test failures (TemplateNotFound: upload.html) are documented by the plan as expected behavior until Plan 02 creates the template.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can now create upload.html — GET / is ready to serve it
- viewer.html continues to work at GET /viewer/<stem>
- All 36 non-route tests pass; 3 new TestViewerStemRoute tests pass
- 2 TestViewerRoute tests are red (known-pending until Plan 02)

## Self-Check: PASSED

- app.py: FOUND
- tests/test_app.py: FOUND
- 13-01-SUMMARY.md: FOUND
- Commit 833f5b5: FOUND
- Commit 2852559: FOUND

---
*Phase: 13-upload-ui-and-live-progress*
*Completed: 2026-03-01*
