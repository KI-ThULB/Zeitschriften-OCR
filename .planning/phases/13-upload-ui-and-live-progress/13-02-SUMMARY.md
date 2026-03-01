---
phase: 13-upload-ui-and-live-progress
plan: "02"
subsystem: ui
tags: [html, javascript, sse, eventsource, drag-and-drop, formdata, flask]

requires:
  - phase: 13-01
    provides: GET / rerouted to upload.html, GET /viewer/<stem> added, POST /upload, POST /run, GET /stream endpoints

provides:
  - templates/upload.html — complete upload dashboard with drag zone, file queue, live SSE progress, and viewer links

affects:
  - phase-14-and-beyond

tech-stack:
  added: []
  patterns:
    - "Vanilla JS EventSource for SSE consumption — no external libraries"
    - "FormData built from stored File objects in queue Map — deferred upload at run time"
    - "CSS.escape(filename) for safe DOM id construction with arbitrary filenames"
    - "stem() normalization matches secure_filename lowercase convention in app.py"
    - "New-batch trigger: first drop after doneCount > 0 clears old queue before adding"

key-files:
  created:
    - templates/upload.html
  modified: []

key-decisions:
  - "File objects stored in queue Map entries so FormData can be built at startRun() time (not at drop time)"
  - "Skipped state treated as done with null word count (shows '(skipped)' in UI)"
  - "SSE error handler closes EventSource and shows 'Connection lost — reload to retry'"
  - "Template is standalone HTML (no Jinja2 inheritance from viewer.html) — self-contained"

patterns-established:
  - "Queue-then-run: upload files first via POST /upload FormData, then POST /run to trigger OCR"
  - "SSE file_done events matched by stem() comparison between queue filenames and d.stem"

requirements-completed: [INGEST-01, INGEST-02, INGEST-03, PROC-01, PROC-02]

duration: 2min
completed: 2026-03-01
---

# Phase 13 Plan 02: Upload UI and Live Progress Summary

**Drag-and-drop upload dashboard with live SSE progress rows, de-duplication, error flash rows, and clickable /viewer/ links on completion**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T08:03:25Z
- **Completed:** 2026-03-01T08:05:30Z
- **Tasks:** 1 (Task 2 is a human-verify checkpoint — paused)
- **Files modified:** 1

## Accomplishments

- Created `templates/upload.html` (490 lines) — complete upload dashboard
- GET / now returns the upload dashboard (TestViewerRoute tests pass: 2/2)
- Drop zone: drag or click-to-browse, dragover visual feedback, non-TIFF flash rows auto-remove after 3s
- File queue: pending/processing/done/error states, x remove buttons, silent de-duplication
- Start OCR: POSTs files via FormData to /upload, then POST /run, opens EventSource(/stream)
- SSE handlers: file_done updates rows in real time; run_complete re-enables button, clears status line
- Done rows become clickable /viewer/<stem> links with word count
- New-batch trigger: first drop after completed run clears old queue

## Task Commits

1. **Task 1: Create templates/upload.html** - `bc663cf` (feat)

## Files Created/Modified

- `templates/upload.html` — Upload and live progress dashboard; standalone HTML with inline CSS and JS; talks to existing /upload, /run, /stream endpoints

## Decisions Made

- File objects stored in queue Map entries so FormData can be built at startRun() time. This is required because drag-and-drop provides File objects from the browser, which cannot be reconstructed from just filenames.
- Template is standalone HTML (not a Jinja2 child of viewer.html) — avoids coupling the upload flow to the viewer's full-page layout.
- Skipped state is treated as done with null word count (shows "(skipped)" in the done row).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Upload dashboard complete; human verification checkpoint pending (Task 2)
- After verification approval, Phase 13 is complete and Phase 14 can begin
- All 38 tests passing

---
*Phase: 13-upload-ui-and-live-progress*
*Completed: 2026-03-01*
