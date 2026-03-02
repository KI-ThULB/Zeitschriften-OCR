---
phase: 12-word-correction
plan: 01
subsystem: api
tags: [flask, lxml, alto-xml, xsd-validation, atomic-write, tdd]

# Dependency graph
requires:
  - phase: 10-tiff-and-alto-data-endpoints
    provides: GET /alto/<stem> ALTO JSON endpoint with word_id indexing
  - phase: 03-validation-and-reporting
    provides: load_xsd(), validate_alto_file(), schemas/alto-2-1.xsd
provides:
  - POST /save/<stem> endpoint for atomic ALTO word correction
  - pipeline.SCHEMA_PATH module-level constant
  - XSD-valid ALTO fixture pattern for TestSaveEndpoint
affects: [12-02-ui, future ALTO editing features]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic write: tempfile.mkstemp in same directory + os.replace to prevent partial-write corruption"
    - "XSD gate before write: serialize to bytes, validate, only write if valid"
    - "word_id 'wN' positional index: zero-based into root.iter(String) flat list (same as GET /alto/ response)"
    - "XSD-valid test fixture: include ID, PHYSICAL_IMG_NR on Page; HEIGHT/WIDTH/HPOS/VPOS on PrintSpace/TextBlock/TextLine"

key-files:
  created: []
  modified:
    - app.py
    - pipeline.py
    - tests/test_app.py

key-decisions:
  - "pipeline.SCHEMA_PATH added as module-level Path constant (was local variable in main()) — needed for app.py access"
  - "XSD-valid fixture in TestSaveEndpoint requires Page ID + PHYSICAL_IMG_NR and positional element attributes — minimal fixture fails validation gate"
  - "os and tempfile promoted to module-level imports in app.py (were inline in plan) — consistent with project import style"

patterns-established:
  - "POST /save/<stem>: validate fields → parse XML → mutate → XSD gate → atomic write"
  - "save_word() guard: '/' or '..' in stem returns 400 before any file access"

requirements-completed: [EDIT-02, EDIT-03]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 12 Plan 01: Word Correction Save Endpoint Summary

**POST /save/<stem> endpoint with atomic tempfile+os.replace write and XSD validation gate, backed by 9-test pytest suite using TDD (RED/GREEN pattern)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-28T22:25:05Z
- **Completed:** 2026-02-28T22:27:25Z
- **Tasks:** 3 (RED, GREEN, REFACTOR)
- **Files modified:** 3

## Accomplishments
- POST /save/<stem> endpoint implemented in app.py with full validation chain
- Atomic write via tempfile.mkstemp + os.replace (no partial-write corruption possible)
- XSD validation gate: serialized bytes validated before disk write; 422 if schema fails
- 9 TestSaveEndpoint tests all pass; full suite 35/35 tests pass

## Task Commits

Each task was committed atomically:

1. **RED: TestSaveEndpoint (9 failing tests)** - `7d83e4d` (test)
2. **GREEN: save_word() endpoint + SCHEMA_PATH constant** - `0816b95` (feat)

**Plan metadata:** *(docs commit follows)*

_Note: TDD tasks — test commit then feat commit; no separate refactor commit needed_

## Files Created/Modified
- `app.py` - Added `os`, `tempfile` module imports; `save_word()` route after `serve_alto()`
- `pipeline.py` - Added `SCHEMA_PATH = Path(__file__).parent / 'schemas' / 'alto-2-1.xsd'` module constant
- `tests/test_app.py` - Added `TestSaveEndpoint` class (9 tests); `_write_alto_fixture()` XSD-valid helper

## Decisions Made
- `pipeline.SCHEMA_PATH` promoted to module-level constant — was only a local variable in `main()`, needed as a module attribute for `app.py` to reference without reimplementing the path logic
- Test ALTO fixture in `TestSaveEndpoint._write_alto_fixture()` must include all XSD-required attributes (Page ID, PHYSICAL_IMG_NR; PrintSpace/TextBlock/TextLine dimensions) — the simpler `_write_alto` helper used by earlier test classes skips these and would cause the XSD gate to always reject in tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated `_write_alto_fixture` to produce XSD-valid ALTO XML**
- **Found during:** GREEN phase (first test run after implementing endpoint)
- **Issue:** Minimal ALTO fixture used in TestSaveEndpoint lacked required XSD attributes: `ID`, `PHYSICAL_IMG_NR` on `Page`; `HEIGHT`/`WIDTH`/`HPOS`/`VPOS` on `PrintSpace`, `TextBlock`, `TextLine`. The XSD gate in `save_word()` correctly rejected the fixture, returning 422 instead of 200.
- **Fix:** Added all required attributes to `_write_alto_fixture()`. Verified XSD validation passes on the updated fixture.
- **Files modified:** `tests/test_app.py`
- **Verification:** `python -m pytest tests/test_app.py::TestSaveEndpoint -v` — 9/9 pass
- **Committed in:** `0816b95` (GREEN task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test fixture)
**Impact on plan:** Fix was necessary for correctness — the test fixture was too minimal to pass the XSD gate the endpoint correctly enforces. No scope creep.

## Issues Encountered
- None beyond the auto-fixed fixture issue above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- POST /save/<stem> endpoint is live and fully tested — ready for Plan 12-02 (viewer UI wiring)
- word_id indexing is identical to GET /alto/<stem> response — frontend can POST w{i} directly from the words array index
- XSD gate ensures disk state is always schema-valid after any save

---
*Phase: 12-word-correction*
*Completed: 2026-02-28*
