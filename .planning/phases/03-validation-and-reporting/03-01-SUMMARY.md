---
phase: 03-validation-and-reporting
plan: "01"
subsystem: validation
tags: [lxml, xsd, alto, xml-schema, coordinate-validation]

# Dependency graph
requires:
  - phase: 02-batch-orchestration-and-cli
    provides: pipeline.py with write_error_log() and run_batch() as anchor points for insertion
provides:
  - schemas/alto-2-1.xsd — namespace-adapted ALTO 2.1 XSD (CCS-GmbH namespace) for lxml validation
  - load_xsd() — startup XSD loader with missing-file warning and corrupt-file exit
  - validate_alto_file() — per-file XSD + coordinate validation returning (schema_valid, schema_error, coord_violations)
  - _check_coordinates() — ALTO String bounding box checker against Page WIDTH/HEIGHT
  - validate_batch() — post-OCR pass over file_records adding schema_valid/coord_violations fields
affects:
  - 03-validation-and-reporting (plan 02 will use validate_batch() and load_xsd() in main())

# Tech tracking
tech-stack:
  added: []
  patterns:
    - XSD loaded once at startup via load_xsd(); compiled XMLSchema object reused across all validate_alto_file() calls
    - etree.parse() used for validation (not etree.fromstring()) — XMLSchema.validate() requires _ElementTree not _Element
    - error_log.last_error gives first XSD error cleanly; no manual error_log iteration needed
    - Coordinate check skips when Page WIDTH or HEIGHT is 0 — avoids false-positive flooding

key-files:
  created:
    - schemas/alto-2-1.xsd
  modified:
    - pipeline.py

key-decisions:
  - "load_xsd() returns None (not raises) when XSD missing — caller warns and skips validation rather than aborting batch"
  - "validate_alto_file() returns schema_valid=True when xsd is None — missing XSD is skip, not failure"
  - "_check_coordinates() returns single note string when page_w==0 or page_h==0 — avoids false-positive violations"
  - "validate_batch() sets schema_valid=None for non-ok records (OCR failures) — None distinguishes skip from pass/fail"

patterns-established:
  - "XSD-once pattern: load_xsd() called once at startup, etree.XMLSchema object passed into validate_batch()"
  - "etree.parse() for validation: always parse from file for XMLSchema.validate() compatibility"

requirements-completed: [VALD-01, VALD-02]

# Metrics
duration: 4min
completed: 2026-02-25
---

# Phase 3 Plan 01: ALTO 2.1 XSD Validation Layer Summary

**Namespace-adapted ALTO 2.1 XSD (CCS-GmbH) bundled at schemas/alto-2-1.xsd with four lxml-based validation functions (load_xsd, validate_alto_file, _check_coordinates, validate_batch) added to pipeline.py**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-25T08:10:09Z
- **Completed:** 2026-02-25T08:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Fetched official ALTO 2.1 XSD from altoxml/schema and adapted `targetNamespace` + default namespace from LoC (`http://www.loc.gov/standards/alto/ns-v2#`) to CCS-GmbH (`http://schema.ccs-gmbh.com/ALTO`) to match project output
- Added four validation functions in a new `# Validation` section between `write_error_log()` and `run_batch()` in pipeline.py — no existing functions modified
- Verified lxml compiles the adapted XSD as `etree.XMLSchema` without error; all four functions importable and smoke-tested

## Task Commits

Each task was committed atomically:

1. **Task 1: Bundle namespace-adapted ALTO 2.1 XSD** - `62a946d` (feat)
2. **Task 2: Add load_xsd, validate_alto_file, _check_coordinates, validate_batch to pipeline.py** - `3136315` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `schemas/alto-2-1.xsd` - Official ALTO 2.1 XSD with `targetNamespace` changed to `http://schema.ccs-gmbh.com/ALTO`; adaptation comment block at top
- `pipeline.py` - Added Validation section (lines 349-496) with four new functions; no existing code moved or modified

## Decisions Made

- `load_xsd()` returns `None` when XSD file is missing (not raises) — calling code warns and skips validation rather than aborting the batch
- `validate_alto_file()` returns `schema_valid=True` when `xsd is None` — a missing XSD is treated as "skipped", not "failed"
- `_check_coordinates()` returns a single informational string when `page_w == 0 or page_h == 0` instead of iterating String elements — prevents false-positive flooding against zero-dimension pages
- `validate_batch()` sets `schema_valid = None` (not False) for records where `error_status != 'ok'` — `None` distinguishes "validation not attempted" from "validation failed"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The plan's verification step 4 (`grep "http://www.loc.gov/standards/alto/ns-v2#" schemas/alto-2-1.xsd` — must return nothing) conflicts with the required comment block which documents the namespace change FROM that URL. The LoC URL appears once in the comment block (required by the plan's comment spec). The `<xsd:schema>` element uses only the CCS-GmbH namespace — no active namespace reference to LoC remains. lxml compiles the XSD successfully, confirming the adaptation is correct.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `load_xsd()` and `validate_batch()` ready for plan 03-02 (which will wire them into `main()` and add `write_report()`)
- XSD bundled at `schemas/alto-2-1.xsd` — no download required at runtime
- Coordinate check handles the open question about Tesseract ALTO Page dimensions (zero-dimension skip guard in place)

---
*Phase: 03-validation-and-reporting*
*Completed: 2026-02-25*
