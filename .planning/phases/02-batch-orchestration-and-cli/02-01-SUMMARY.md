---
phase: 02-batch-orchestration-and-cli
plan: "01"
subsystem: pipeline
tags: [python, lxml, pytesseract, tqdm, alto-xml, batch, process-pool]

# Dependency graph
requires:
  - phase: 01-single-file-pipeline
    provides: pipeline.py process_tiff(), build_alto21() single-file foundation
provides:
  - process_tiff() raises on error (safe ProcessPoolExecutor worker)
  - build_alto21() correctly strips xsi:schemaLocation via lxml attrib.pop before serialization
  - validate_tesseract(lang) — pre-flight Tesseract check before pool creation
  - discover_tiffs(input_dir) — sorted TIFF file discovery
  - write_error_log(output_dir, errors) — JSONL per-file error log writer
affects:
  - 02-02-batch-orchestrator
  - 02-03-cli

# Tech tracking
tech-stack:
  added: [tqdm>=4.67.0, json (stdlib), datetime (stdlib), concurrent.futures (stdlib), traceback (stdlib)]
  patterns:
    - "Worker functions raise exceptions instead of sys.exit for ProcessPoolExecutor safety"
    - "lxml attrib.pop for XML attribute removal BEFORE serialization (not string-replace post-serialize)"
    - "Tesseract validation runs before pool creation to avoid dangling workers"

key-files:
  created: []
  modified:
    - pipeline.py

key-decisions:
  - "process_tiff() uses raise (not sys.exit) in except block — safe for ProcessPoolExecutor spawn on macOS"
  - "xsi:schemaLocation stripped via root.attrib.pop BEFORE serialization, not string-replace after namespace rewrite"
  - "validate_tesseract() calls sys.exit(1) directly (not raise) — it is a pre-flight guard, not a worker function"
  - "tqdm added to requirements.txt as batch progress display dependency for Plan 02"

patterns-established:
  - "Pre-flight validation pattern: validate_tesseract exits before creating worker pool"
  - "Error isolation pattern: worker raises, caller catches and logs via write_error_log"
  - "Deterministic file ordering: discover_tiffs uses sorted() for reproducible batch runs"

requirements-completed: [BATC-03, BATC-04, CLI-05]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 2 Plan 01: Pipeline Bug Fixes and Batch Helper Functions Summary

**process_tiff() now raises instead of sys.exit (ProcessPoolExecutor-safe), build_alto21() fixes xsi:schemaLocation via lxml attrib.pop, and three batch helpers (validate_tesseract, discover_tiffs, write_error_log) added as pre-conditions for Plan 02 batch orchestrator**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T21:22:13Z
- **Completed:** 2026-02-24T21:24:20Z
- **Tasks:** 2
- **Files modified:** 2 (pipeline.py, requirements.txt)

## Accomplishments

- Fixed process_tiff() sys.exit(1) bug — workers now raise exceptions, enabling ProcessPoolExecutor on macOS/spawn to capture errors via Future objects without hanging pool shutdown
- Fixed build_alto21() xsi:schemaLocation bug — the Phase 1 known gap (silent no-op string-replace) replaced by lxml root.attrib.pop before serialization, verified via functional test producing clean ALTO 2.1 output
- Added three batch helper functions (validate_tesseract, discover_tiffs, write_error_log) that Plan 02 batch orchestrator depends on as pre-conditions
- Added tqdm to requirements.txt for batch progress display
- All new imports (json, os, traceback, concurrent.futures, datetime, tqdm) added at module top

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix process_tiff sys.exit bug and build_alto21 schemaLocation bug** - `1b7a273` (fix)
2. **Task 2: Add validate_tesseract, discover_tiffs, write_error_log batch helpers** - `25fc385` (feat)

## Files Created/Modified

- `/Users/zu54tav/Zeitschriften-OCR/pipeline.py` - Fixed two bugs; added three batch helper functions and six new imports
- `/Users/zu54tav/Zeitschriften-OCR/requirements.txt` - Added tqdm>=4.67.0

## Decisions Made

- process_tiff() uses `raise` (not sys.exit) in the except block — the exception propagates via the Future so run_batch() can catch and log it per BATC-03/BATC-04
- xsi:schemaLocation is stripped via `root.attrib.pop('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', None)` as the new Step 2, immediately after parsing, before any serialization or namespace rewrite
- validate_tesseract() is the one function that calls sys.exit(1) intentionally — it is a pre-flight guard called before pool creation, not a pool worker
- build_alto21() step order renumbered 1-6 in docstring to reflect the corrected flow

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both bugs were straightforward to fix as specified in the plan. All verification checks passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three batch helper functions are ready for use by Plan 02 (batch orchestrator)
- process_tiff() is safe to use as a ProcessPoolExecutor worker
- build_alto21() produces clean ALTO 2.1 XML with no xsi:schemaLocation contamination
- Single-file regression verified: 144528908_0019.tif processed successfully (11.0s, 46 words)

## Self-Check: PASSED

- FOUND: pipeline.py
- FOUND: requirements.txt
- FOUND: 02-01-SUMMARY.md
- FOUND: commit 1b7a273
- FOUND: commit 25fc385

---
*Phase: 02-batch-orchestration-and-cli*
*Completed: 2026-02-24*
