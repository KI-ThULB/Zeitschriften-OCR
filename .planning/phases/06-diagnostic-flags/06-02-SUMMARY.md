---
phase: 06-diagnostic-flags
plan: 02
subsystem: cli
tags: [argparse, verbose, timing, tesseract, subprocess, diagnostic, operator-experience]

# Dependency graph
requires:
  - phase: 06-01
    provides: --dry-run flag and argparse block this plan extends
provides:
  - --verbose flag in pipeline.py argparse block
  - Per-stage wall-clock timing in process_tiff() (deskew, crop, ocr, write)
  - Tesseract stdout/stderr capture via subprocess.run() in run_ocr()
  - OPER-02 requirement satisfied
affects: [future-pipeline-flags, 07-batch-progress, 08-config-file]

# Tech tracking
tech-stack:
  added: [subprocess (stdlib, now explicitly imported)]
  patterns:
    - "Atomic verbose_block string built before single print() call to minimize stdout interleaving in parallel mode"
    - "Subprocess Tesseract invocation for verbose mode: tesseract FILE stdout -l LANG --psm N --dpi N alto"
    - "run_ocr() returns (bytes, str) tuple; capture_output=False returns empty string as second element"

key-files:
  created: []
  modified: [pipeline.py]

key-decisions:
  - "run_ocr() returns tuple[bytes, str] in both modes — consistent call site, capture_output=False just returns empty string"
  - "capture_output path uses subprocess.run() tesseract CLI directly to capture stderr; falls back to pytesseract if stdout is empty"
  - "verbose_block built as single string and printed atomically to reduce stdout interleaving when workers > 1"
  - "t_crop stage wraps adaptive_threshold_image + detect_crop_box + img.crop() — the entire pre-OCR image prep between deskew and OCR"
  - "t_ocr stage wraps both run_ocr() and build_alto21() — both are CPU-bound Tesseract output processing"
  - "--verbose silently ignored in --dry-run path (no OCR runs, nothing verbose to report; verified by code path)"

patterns-established:
  - "Timing bracket pattern: t_X_start = time.monotonic() ... t_X = time.monotonic() - t_X_start"
  - "Verbose output always additive: existing per-file result line unchanged"

requirements-completed: [OPER-02]

# Metrics
duration: 4min
completed: 2026-02-26
---

# Phase 6 Plan 02: Verbose Flag Summary

**--verbose flag added to pipeline.py: per-stage wall-clock timing (deskew/crop/ocr/write) and Tesseract stdout/stderr capture via subprocess.run(), threaded from argparse through run_batch() into process_tiff()**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-26T06:07:03Z
- **Completed:** 2026-02-26T06:11:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Modified `run_ocr()` to return `tuple[bytes, str]` with `capture_output` parameter — subprocess Tesseract invocation captures stderr for verbose mode, pytesseract path used otherwise
- Added four timing brackets in `process_tiff()` (deskew, crop, ocr, write) using `time.monotonic()`
- Verbose output block printed atomically after each file's result line: four indented timing lines, tesseract stdout/stderr section, blank line separator
- Added `verbose` parameter to `process_tiff()` and `run_batch()`; added `--verbose` argparse flag wired through `main()` → `run_batch()` → `executor.submit()` → `process_tiff()`
- Added `subprocess` to top-level imports

## Task Commits

Each task was committed atomically:

1. **Task 1: Add per-stage timing brackets and verbose output to process_tiff()** - `f8e6ad6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `/Users/zu54tav/Zeitschriften-OCR/pipeline.py` - Added `subprocess` import, modified `run_ocr()` signature and return type, added timing brackets and verbose output block to `process_tiff()`, added `verbose` param to `run_batch()` and its `executor.submit()` call, added `--verbose` argparse flag in `main()` and wired to `run_batch()`

## Decisions Made

- `run_ocr()` returns `(bytes, str)` in both capture paths — the empty-string second element for `capture_output=False` makes call sites uniform and avoids conditional unpacking
- The `t_crop` stage bracket wraps `adaptive_threshold_image()` + `detect_crop_box()` + `img.crop()` because these are all the pre-OCR image preparation steps between deskew and OCR — grouping them as "crop" matches the CONTEXT.md stage naming
- The `t_ocr` stage bracket wraps both `run_ocr()` and `build_alto21()` because build_alto21() is immediate post-processing of Tesseract output with no I/O
- Verbose block is assembled as one string before `print()` to reduce interleaved stdout lines when `--workers > 1`
- `--verbose` silently ignored in `--dry-run` path by code structure: `sys.exit(0)` in dry-run branch before `run_batch()` is ever called

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both `--dry-run` (OPER-01) and `--verbose` (OPER-02) flags are complete. Phase 6 diagnostic flags are done.
- No blockers for Phase 7.

---
*Phase: 06-diagnostic-flags*
*Completed: 2026-02-26*

## Self-Check: PASSED

- pipeline.py: FOUND
- Commit f8e6ad6: FOUND
- 06-02-SUMMARY.md: FOUND
