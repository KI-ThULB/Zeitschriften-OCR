---
phase: 02-batch-orchestration-and-cli
plan: "02"
subsystem: batch-processing
tags: [ProcessPoolExecutor, tqdm, argparse, batch, ocr, alto-xml, pipeline]

# Dependency graph
requires:
  - phase: 02-01
    provides: validate_tesseract, discover_tiffs, write_error_log, process_tiff (raises not exits)
provides:
  - run_batch() parallel batch orchestrator using ProcessPoolExecutor.submit() + as_completed()
  - Rewritten main() accepting --input DIR batch mode with full CLI flag surface
  - Complete BATC-01..04 and CLI-01..05 requirements satisfied
affects:
  - 03-xsd-validation-and-reporting

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ProcessPoolExecutor.submit() + as_completed() for per-file error isolation (not executor.map())
    - Skip-if-exists check before pool creation to avoid spinning up workers for nothing
    - --workers default=None resolved at runtime with min(os.cpu_count() or 1, 4) to avoid import-time evaluation
    - tqdm wrapping as_completed iterator with explicit total= (as_completed has no __len__)

key-files:
  created: []
  modified:
    - pipeline.py

key-decisions:
  - "executor.submit() + as_completed() chosen over executor.map() — map() raises on first exception and aborts remaining results"
  - "--workers default=None (not default=min(os.cpu_count(), 4)) — avoids hardcoded value evaluated at import time"
  - "Skip-if-exists check happens before executor creation — avoids spinning up pool for an all-skip run"
  - "False passed as no_crop to process_tiff in run_batch — batch mode always attempts crop detection (same as single-file default)"

patterns-established:
  - "Per-file error isolation: submit() + as_completed() with try/except around fut.result() per file"
  - "Error dicts: {file, exc_type, exc_message, traceback} — traceback.format_exc() captures RemoteTraceback chain"
  - "Batch summary line: 'Done: N processed, N skipped, N failed' followed by error log path if applicable"

requirements-completed: [BATC-01, BATC-02, BATC-03, BATC-04, CLI-01, CLI-02, CLI-03, CLI-04, CLI-05]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 2 Plan 02: Batch Orchestration and CLI Summary

**ProcessPoolExecutor batch orchestrator with tqdm progress bar, skip-if-exists, per-file error isolation, and full argparse CLI surface wired into pipeline.py main()**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T21:27:05Z
- **Completed:** 2026-02-24T21:29:26Z
- **Tasks:** 2 completed
- **Files modified:** 1

## Accomplishments

- Added `run_batch()` using ProcessPoolExecutor.submit() + as_completed() — one TIFF failure does not abort the batch
- Skip-if-exists logic before pool creation (bypassed by --force) satisfies BATC-02
- Rewrote `main()` to accept --input DIR with --workers, --force, --lang, --padding, --psm flags
- End-to-end verified: first pass (1 processed), second pass (1 skipped), --force pass (1 reprocessed)
- ALTO 2.1 output confirmed: correct CCS-GmbH namespace, no xsi:schemaLocation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add run_batch() batch orchestrator** - `2e1b0b3` (feat)
2. **Task 2: Rewrite main() for batch CLI and run end-to-end batch verification** - `5382781` (feat)

**Plan metadata:** (docs commit — see state updates below)

## Files Created/Modified

- `/Users/zu54tav/Zeitschriften-OCR/pipeline.py` - Added run_batch() (70 lines) and replaced single-file main() with batch CLI main() (50 lines)

## Decisions Made

- `executor.submit()` + `as_completed()` chosen over `executor.map()`: map() raises on first exception, aborting remaining work; submit/as_completed isolates each file
- `--workers default=None` resolved at runtime to avoid `min(os.cpu_count(), 4)` being evaluated at module import time
- Skip check runs before ProcessPoolExecutor context manager — avoids spawning worker processes when all files are already processed
- `no_crop=False` passed in run_batch submit() call — batch mode always attempts crop detection, matching single-file default behavior

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2 complete: all 9 requirements satisfied (BATC-01..04, CLI-01..05)
- `python pipeline.py --input DIR --output DIR` is the stable batch interface for Phase 3
- Phase 3 (XSD validation and reporting) can now wrap run_batch() output with per-file ALTO 2.1 XSD validation and JSON summary reports

---
*Phase: 02-batch-orchestration-and-cli*
*Completed: 2026-02-24*
