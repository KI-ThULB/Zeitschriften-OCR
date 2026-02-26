---
phase: 06-diagnostic-flags
plan: 01
subsystem: cli
tags: [argparse, dry-run, pre-flight, batch-pipeline, operator-experience]

# Dependency graph
requires:
  - phase: 05-adaptive-thresholding
    provides: --adaptive-threshold flag and argparse block this plan extends
provides:
  - --dry-run flag in pipeline.py argparse block
  - Pre-flight scan block in main() listing would-process / would-skip split
  - OPER-01 requirement satisfied
affects: [06-02-verbose, future-pipeline-flags]

# Tech tracking
tech-stack:
  added: []
  patterns: [dry-run pre-flight mirrors run_batch() skip-check condition without writing output]

key-files:
  created: []
  modified: [pipeline.py]

key-decisions:
  - "validate_tesseract() runs before dry-run gate so operators get Tesseract errors even in dry-run mode"
  - "--verbose silently ignored in dry-run path (no OCR runs, nothing for verbose to report)"
  - "skip-check in dry-run replicates exact run_batch() condition: `if not args.force and out_path.exists()`"
  - "Empty sections still print their header (e.g., Would skip (0): with no entries below)"

patterns-established:
  - "Pre-flight scan pattern: replicate skip-check condition without actually invoking workers"

requirements-completed: [OPER-01]

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 6 Plan 01: Dry-Run Pre-Flight Scan Summary

**--dry-run flag added to pipeline.py: two-section stdout output (would-process / would-skip) with --force integration, exits code 0 with no files written**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T06:02:59Z
- **Completed:** 2026-02-26T06:05:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `--dry-run` argparse flag to `pipeline.py` after `--adaptive-threshold`
- Added pre-flight scan block in `main()` that lists TIFFs to process vs skip without running OCR
- Integrated `--force` flag: with `--force`, all TIFFs appear in the would-process list
- Verified no ALTO XML files are written during any dry-run invocation
- Confirmed clean combination with all existing flags (`--lang`, `--workers`, `--padding`, `--psm`, `--adaptive-threshold`)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --dry-run argparse flag and pre-flight scan to main()** - `5438481` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `/Users/zu54tav/Zeitschriften-OCR/pipeline.py` - Added `--dry-run` argparse argument and pre-flight scan block in `main()`

## Decisions Made

- `validate_tesseract()` still runs before the dry-run gate per RESEARCH.md open question 3 decision: dry-run validates the full run would succeed (Tesseract available), not just that files exist
- `--verbose` silently ignored in dry-run path per CONTEXT.md locked decision
- Empty would-skip or would-process sections still print their header line (consistent structure)
- 2-space indentation for file entries (Claude's discretion per CONTEXT.md)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `--dry-run` is complete and tested. Plan 06-02 (`--verbose` flag) can proceed.
- No blockers.

---
*Phase: 06-diagnostic-flags*
*Completed: 2026-02-26*

## Self-Check: PASSED

- pipeline.py: FOUND
- Commit 5438481: FOUND
