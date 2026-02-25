---
phase: 04-deskew
plan: 01
subsystem: pipeline
tags: [deskew, ocr, pillow, scikit-image, numpy, image-preprocessing]

# Dependency graph
requires:
  - phase: 03-validation
    provides: process_tiff() and pipeline.py foundation that deskew integrates into
provides:
  - deskew_image() function in pipeline.py (Hough-transform skew detection + PIL rotation)
  - DESKEW_MAX_ANGLE = 10.0 constant for plausibility gating
  - deskew>=1.5.0 declared in requirements.txt
  - process_tiff() calls deskew_image() after load_tiff() and before detect_crop_box()
  - Per-file result line includes [deskew: N.N°] on success and [WARN: deskew: ...] on fallback
affects: [05-adaptive-thresholding, pipeline.py]

# Tech tracking
tech-stack:
  added: [deskew>=1.5.0 (transitively: scikit-image, numpy already present)]
  patterns:
    - "Pure function pattern: deskew_image() returns (corrected_image, angle_or_None, fallback_bool) — caller decides how to use flags"
    - "Named constant for tunable threshold: DESKEW_MAX_ANGLE = 10.0 makes plausibility gate explicit and adjustable"
    - "Mode-aware fillcolor: detect image.mode before rotate to avoid PIL TypeError on L vs RGB images"
    - "Near-zero guard: abs(angle) < 0.05 skips rotation to avoid resampling artifact on already-straight scans"
    - "deskew_str separate from warnings_list: diagnostic angle info appears unconditionally; warnings only for fallback/failure"

key-files:
  created: []
  modified:
    - requirements.txt
    - pipeline.py

key-decisions:
  - "deskew_str initialized to '' at top of process_tiff() so variable is always defined even if exception occurs before deskew block"
  - "Deskew inserted between load_tiff() and detect_crop_box() — not after crop — so page contour is axis-aligned when crop detection runs"
  - "DESKEW_MAX_ANGLE = 10.0 chosen as named constant (not magic number) — appropriate for archival periodicals where genuine skew is under 5°"
  - "fillcolor detection by image.mode (L -> 255, RGB -> (255,255,255)) — archival TIFFs can be either mode"
  - "Image.Resampling.BICUBIC used (not deprecated Image.BICUBIC) per Pillow 10+ requirement"

patterns-established:
  - "Preprocessing steps in process_tiff() order: load_tiff() -> deskew_image() -> detect_crop_box() -> crop -> run_ocr()"
  - "Separate annotation string (deskew_str) vs warnings_list for diagnostic vs warning distinction in result lines"

requirements-completed: [PREP-01, PREP-02, PREP-03]

# Metrics
duration: 6min
completed: 2026-02-25
---

# Phase 4 Plan 01: Deskew Integration Summary

**Hough-transform deskew correction added to pipeline using deskew 1.5.3 library: angle detected per TIFF, applied before crop, reported in result line, with safe fallback on failure or implausible angle**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-25T16:28:32Z
- **Completed:** 2026-02-25T16:34:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `deskew>=1.5.0` to requirements.txt; library installed (1.5.3)
- Implemented `deskew_image()` as a pure function wrapping `determine_skew()` and `Image.rotate()`, with full handling for None return, implausible angle (>10°), near-zero angle (<0.05°), and mode-aware fillcolor
- Wired `deskew_image()` into `process_tiff()` at the correct position: after `load_tiff()`, before `detect_crop_box()` — satisfying PREP-01
- Result line now includes `[deskew: N.N°]` on success and `[WARN: deskew: ...]` on fallback — satisfying PREP-02 and PREP-03
- All four full-suite verification checks pass (syntax, unit, dependency, structural order)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add deskew dependency and implement deskew_image()** - `7536e86` (feat)
2. **Task 2: Wire deskew_image() into process_tiff() with angle reporting** - `e8db9d9` (feat)

**Plan metadata:** (docs commit — see state update)

## Files Created/Modified
- `requirements.txt` - Added `deskew>=1.5.0` after opencv-python-headless line
- `pipeline.py` - Added import, DESKEW_MAX_ANGLE constant, deskew_image() function, and process_tiff() integration

## Decisions Made
- `deskew_str = ''` initialized at top of `process_tiff()` (before try block) so the variable is always defined even if an exception occurs before the deskew step runs — prevents NameError in error-path result line construction
- Deskew before crop (not after): inserting deskew_image() before detect_crop_box() ensures the page contour is axis-aligned, making crop detection more reliable
- Separate `deskew_str` from `warnings_list`: diagnostic angle info (PREP-02) should appear unconditionally in the result line; only fallback/failure cases append to warnings_list (which gets the [WARN: ...] prefix)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The `deskew` library (1.5.3) was already installable with no conflicts. All verification assertions passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 5 (Adaptive Thresholding) can proceed immediately — pipeline.py foundation with deskew is stable
- The established preprocessing order (load → deskew → crop → OCR) must be maintained in Phase 5 when adaptive thresholding is inserted before run_ocr()
- DESKEW_MAX_ANGLE = 10.0 is exposed as a named constant; a future `--deskew-max-angle` CLI flag could be added if corpus tuning reveals edge cases (out of scope for Phase 4)

---
*Phase: 04-deskew*
*Completed: 2026-02-25*
