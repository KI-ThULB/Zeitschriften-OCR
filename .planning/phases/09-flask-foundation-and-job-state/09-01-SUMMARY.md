---
phase: 09-flask-foundation-and-job-state
plan: 01
subsystem: testing
tags: [flask, werkzeug, pytest, tdd, sse, job-state]

# Dependency graph
requires:
  - phase: 08-config-file-support
    provides: complete pipeline.py with run_batch, process_tiff, and config support
provides:
  - RED test suite for PROC-03 (skip already-processed TIFFs) and PROC-04 (per-file error isolation)
  - pytest-flask conftest fixtures (flask_app, client) with deferred app import
  - requirements.txt updated with flask>=3.1.0 and werkzeug>=3.1.0
affects:
  - 09-02-app-implementation (provides the exact behavioral contract the implementation must satisfy)

# Tech tracking
tech-stack:
  added: [flask>=3.1.0, werkzeug>=3.1.0, pytest-flask]
  patterns: [TDD red-green, importlib deferred import for fixture isolation, monkeypatch on module attributes]

key-files:
  created:
    - tests/conftest.py
    - tests/test_app.py
  modified:
    - requirements.txt

key-decisions:
  - "Use importlib.import_module('app') inside fixture body (not module-level import) so ImportError is deferred to test time — conftest errors would break ALL tests"
  - "monkeypatch.setattr(app_module.pipeline, 'process_tiff', mock) pattern established for OCR worker isolation"
  - "SSE events checked as raw strings with 'event: file_done' and '\"state\": \"error\"' substrings — matches server-side format spec"

patterns-established:
  - "Flask fixture pattern: importlib.import_module inside fixture, clear _jobs and _run_active in teardown"
  - "TDD RED state: 7 ModuleNotFoundError failures (not syntax errors) confirm tests are syntactically correct"

requirements-completed: [PROC-03, PROC-04]

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 9 Plan 01: Flask Foundation and Job State Summary

**7 RED pytest tests establishing behavioral contracts for skip-already-processed (PROC-03) and per-file error isolation (PROC-04) via pytest-flask fixtures with deferred importlib import**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T13:40:35Z
- **Completed:** 2026-02-27T13:42:15Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created tests/conftest.py with flask_app and client pytest fixtures using importlib deferred import pattern — ImportError only fires at test collection time, not conftest load time
- Created tests/test_app.py with 7 failing tests covering PROC-03 (4 tests: already_processed flag, job state done, /run 400, lowercase normalization) and PROC-04 (3 tests: error event + continue, _run_active cleared in finally, /run 409)
- Updated requirements.txt with flask>=3.1.0 and werkzeug>=3.1.0 as explicit dependencies
- RED state confirmed: all 7 tests fail with ModuleNotFoundError (not syntax errors); existing 21 tests still GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Update requirements.txt and create pytest-flask conftest** - `c586d54` (chore)
2. **Task 2: Write RED failing tests for PROC-03 and PROC-04** - `0e81fad` (test)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks produce test-only commits at RED stage; feat commits will come in Plan 02 (implementation)_

## Files Created/Modified
- `requirements.txt` - Added flask>=3.1.0 and werkzeug>=3.1.0
- `tests/conftest.py` - pytest-flask app and client fixtures with deferred importlib import
- `tests/test_app.py` - 7 RED tests: TestSkipAlreadyProcessed (4) and TestErrorIsolation (3)

## Decisions Made
- Used `importlib.import_module('app')` inside fixture body rather than top-level import — prevents conftest errors from breaking unrelated test files when app.py does not exist yet
- Tests reference `app_module.pipeline` attribute (not direct import) so monkeypatch can intercept `process_tiff` calls in the OCR worker
- SSE events verified as raw strings matching format `event: file_done\ndata: {...}` to keep assertion logic independent of serialization details

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RED test suite complete — Plan 02 can begin implementing app.py to turn these tests GREEN
- Fixture pattern (flask_app, client, monkeypatch on pipeline) is established and ready to reuse in future tests
- tests/conftest.py is isolated: conftest errors will NOT occur until app.py exists, so existing batch pipeline tests remain unaffected

---
*Phase: 09-flask-foundation-and-job-state*
*Completed: 2026-02-27*
