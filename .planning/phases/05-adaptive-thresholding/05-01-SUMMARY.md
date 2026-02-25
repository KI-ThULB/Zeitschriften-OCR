---
phase: 05-adaptive-thresholding
plan: 01
subsystem: pipeline
tags: [opencv, cv2, adaptive-threshold, binarization, preprocessing, ocr]

# Dependency graph
requires:
  - phase: 04-deskew
    provides: deskew_image() integrated into process_tiff() before crop — adaptive threshold slot sits immediately after deskew
provides:
  - ADAPTIVE_BLOCK_SIZE = 51 and ADAPTIVE_C = 10 named constants in pipeline.py
  - adaptive_threshold_image() pure function (PIL Image in, binary PIL Image out, mode L, values 0/255)
  - --adaptive-threshold CLI flag wired end-to-end: main() -> run_batch() -> executor.submit() -> process_tiff()
affects:
  - future tuning / empirical testing phases for ADAPTIVE_BLOCK_SIZE and ADAPTIVE_C

# Tech tracking
tech-stack:
  added: []
  patterns:
    - opt-in preprocessing flag pattern: argparse store_true -> run_batch() param -> executor.submit() positional arg -> process_tiff() guard
    - pure function preprocessing step: function accepts PIL Image, returns PIL Image, no side effects

key-files:
  created: []
  modified:
    - pipeline.py

key-decisions:
  - "cv2.THRESH_BINARY (not THRESH_BINARY_INV) — consistent with crop detection; dark border, light page"
  - "ADAPTIVE_BLOCK_SIZE = 51 (odd, required by cv2.adaptiveThreshold at runtime); tuning deferred to real corpus"
  - "adaptive_threshold_image() inserted AFTER deskew, BEFORE detect_crop_box — binarized image feeds crop contour detection"
  - "In-memory only — no disk writes of thresholded image (out of scope per REQUIREMENTS.md)"
  - "adaptive_threshold: bool is last positional arg in process_tiff(); no_crop stays hardcoded False in submit()"

patterns-established:
  - "Optional preprocessing step pattern: named bool param as last arg in process_tiff(), guarded by 'if flag:'"
  - "End-to-end flag propagation: argparse -> run_batch() -> executor.submit() -> process_tiff()"

requirements-completed: [PREP-04, PREP-05]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 5 Plan 01: Adaptive Thresholding Summary

**Opt-in adaptive Gaussian binarization via cv2.ADAPTIVE_THRESH_GAUSSIAN_C wired end-to-end with --adaptive-threshold flag; default pipeline unchanged**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-25T21:34:05Z
- **Completed:** 2026-02-25T21:36:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `adaptive_threshold_image()` pure function added between `deskew_image()` and `detect_crop_box()` in function order
- `ADAPTIVE_BLOCK_SIZE = 51` and `ADAPTIVE_C = 10` named constants with tuning notes added after `DESKEW_MAX_ANGLE`
- `--adaptive-threshold` flag fully wired from argparse through `run_batch()` to `process_tiff()` via `executor.submit()`
- Default pipeline path unchanged — `adaptive_threshold_image()` only called when `--adaptive-threshold` is passed
- All 7 structural checks and 4 functional checks pass; `python -m py_compile pipeline.py` exits 0

## Task Commits

Each task was committed atomically:

1. **Task 1: Add adaptive_threshold_image() pure function and named constants** - `fb904d5` (feat)
2. **Task 2: Wire adaptive_threshold_image() into process_tiff(), run_batch(), and argparse** - `3d5bbe8` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `pipeline.py` - Added ADAPTIVE_BLOCK_SIZE/ADAPTIVE_C constants, adaptive_threshold_image() function, --adaptive-threshold flag, and full wiring through process_tiff()/run_batch()/main()

## Decisions Made

- `cv2.THRESH_BINARY` (not `THRESH_BINARY_INV`): consistent with existing crop detection decision; archival scans have dark border, light page
- `ADAPTIVE_BLOCK_SIZE = 51`: odd integer (cv2 requirement), approximately 4.3 mm at 300 DPI; annotated as needing empirical tuning
- `adaptive_threshold_image()` positioned after deskew and before crop: ensures the binarized image feeds `detect_crop_box()` for contour detection when the flag is active
- `adaptive_threshold: bool` is the last positional arg in `process_tiff()`: `no_crop` stays hardcoded `False` in `executor.submit()` as existing behavior

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- PREP-04 (Gaussian adaptive thresholding applied before OCR when requested) satisfied
- PREP-05 (feature off by default; --adaptive-threshold enables it) satisfied
- `ADAPTIVE_BLOCK_SIZE` and `ADAPTIVE_C` values marked for empirical tuning against real Zeitschriften corpus scans (noted in STATE.md blockers)
- Phase 5 plan 01 is the only plan for this phase; phase is complete

---
*Phase: 05-adaptive-thresholding*
*Completed: 2026-02-25*

## Self-Check: PASSED

- pipeline.py: FOUND
- 05-01-SUMMARY.md: FOUND
- Commit fb904d5 (Task 1): FOUND
- Commit 3d5bbe8 (Task 2): FOUND
