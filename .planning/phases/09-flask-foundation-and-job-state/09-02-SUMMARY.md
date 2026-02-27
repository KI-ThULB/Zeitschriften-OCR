---
phase: 09-flask-foundation-and-job-state
plan: 02
subsystem: web-server
tags: [flask, sse, threading, job-state, upload, ocr-worker]

# Dependency graph
requires:
  - phase: 09-01
    provides: RED test suite for PROC-03 and PROC-04 (7 failing tests)
  - phase: 08-config-file-support
    provides: pipeline.process_tiff, pipeline.count_words, pipeline.ALTO21_NS
provides:
  - app.py: Flask server with POST /upload, POST /run, GET /stream
  - PROC-03 and PROC-04 behavioral contracts verified GREEN
affects:
  - all subsequent phases (10-13): build on top of this app.py foundation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Flask module-level app with threading.Lock-protected job state dict
    - SSE via queue.Queue with 30s keepalive timeout in GET /stream
    - Background threading.Thread for sequential OCR with per-file SSE events
    - _run_active threading.Event as mutex guard for POST /run (409 on re-trigger)
    - stem.lower() normalization in /upload for skip-check consistency with pipeline

key-files:
  created:
    - app.py
  modified: []

key-decisions:
  - "Use threading.Thread (not ProcessPoolExecutor) for OCR worker — enables per-file SSE progress events; ProcessPoolExecutor cannot yield incrementally and causes OSError on macOS spawn from Flask thread"
  - "_run_active.clear() in finally block of _ocr_worker — PROC-04 contract: active flag clears even if all files fail"
  - "stem normalized to lowercase in /upload — pipeline writes lowercase stems, so skip-check must use same case"
  - "_sse_queue reassigned under _job_lock before thread launch — prevents GET /stream from reading stale queue from previous run"

requirements-completed: [PROC-03, PROC-04]

# Metrics
duration: 1min
completed: 2026-02-27
---

# Phase 9 Plan 02: Flask Foundation and Job State Summary

**Single-file Flask 3.1 server (app.py) with module-level threading state, sequential OCR worker posting per-file SSE events, and all 7 PROC-03/PROC-04 tests GREEN on first attempt**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-27T13:44:35Z
- **Completed:** 2026-02-27T13:45:35Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Created app.py (304 lines) at project root following flat-file convention matching pipeline.py
- Implemented POST /upload with multipart file handling, TIFF extension guard, lowercase stem normalization, and alto/<stem>.xml skip detection (PROC-03)
- Implemented POST /run with _run_active guard (409), pending-list guard (400), background threading.Thread launch, and SSE queue reset
- Implemented GET /stream with queue.Queue consumer, 30s keepalive, and run_complete terminator
- Implemented _ocr_worker with sequential pipeline.process_tiff() calls, per-file try/except error isolation (PROC-04), and finally: _run_active.clear()
- All 7 tests GREEN on first run — no iteration needed
- Full test suite (28 tests) passes — 21 existing + 7 new, zero regressions
- Smoke test: server starts on port 5001, GET /stream returns HTTP 200

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement app.py Flask server** - `436b72f` (feat)
2. **Task 2: Make tests GREEN and smoke-test** — no code changes needed; tests passed immediately

## Files Created/Modified

- `app.py` — Flask server with POST /upload, POST /run, GET /stream, _ocr_worker, _format_sse, module-level state

## Decisions Made

- Used `threading.Thread` for OCR worker (not ProcessPoolExecutor) — required for per-file SSE streaming and macOS spawn compatibility
- `_run_active.clear()` placed in `finally` block — ensures active flag resets even when all files raise exceptions (PROC-04)
- `stem = Path(filename).stem.lower()` in /upload — pipeline writes lowercase output file names; skip-check must match
- `_sse_queue` reassigned inside `_job_lock` before thread launch — prevents /stream consumer from reading old queue after re-trigger

## Deviations from Plan

None - plan executed exactly as written. All 7 tests passed on first run without any iteration.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Standard `pip install -r requirements.txt` installs Flask.

## Next Phase Readiness

- app.py is the load-bearing foundation for all v1.4 phases (10-13)
- Phase 10 can add static HTML/JS UI consuming GET /stream
- Phase 11 can add ALTO viewer endpoints building on the established job state dict
- Phase 12 can add JPEG thumbnail generation alongside ALTO processing in _ocr_worker
- Threading model, SSE format, skip logic, and error isolation are established and tested

---
*Phase: 09-flask-foundation-and-job-state*
*Completed: 2026-02-27*
