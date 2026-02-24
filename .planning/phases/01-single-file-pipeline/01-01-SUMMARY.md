---
phase: 01-single-file-pipeline
plan: "01"
subsystem: ocr-pipeline
tags: [pillow, opencv, pytesseract, lxml, alto21, tiff, ocr]

# Dependency graph
requires: []
provides:
  - requirements.txt with pinned Pillow, opencv-python-headless, pytesseract, lxml
  - pipeline.py with load_tiff() returning (image, dpi_tuple, warnings)
  - pipeline.py with detect_crop_box() using THRESH_BINARY + THRESH_OTSU
  - ALTO3_NS and ALTO21_NS constants (CCS-GmbH namespace)
  - argparse skeleton with all Phase 1 CLI flags
affects:
  - 01-02-PLAN (completes pipeline.py: run_ocr, build_alto21, process_tiff, main wiring)

# Tech tracking
tech-stack:
  added:
    - Pillow>=11.1.0 (TIFF loading, DPI extraction, PIL Image)
    - opencv-python-headless>=4.9.0 (contour detection, Otsu threshold)
    - pytesseract>=0.3.13 (OCR interface — used in Plan 02)
    - lxml>=5.3.0 (ALTO XML generation — used in Plan 02)
  patterns:
    - "load_tiff returns (image, dpi, warnings) 3-tuple — warnings accumulate rather than raise"
    - "detect_crop_box returns (box, fallback_used) 2-tuple — caller checks fallback_used flag"
    - "THRESH_BINARY + THRESH_OTSU: light page content becomes white largest-contour (not INV)"
    - "Padding applied to detected box with explicit bounds clamping before return"

key-files:
  created:
    - requirements.txt
    - pipeline.py
  modified: []

key-decisions:
  - "THRESH_BINARY (not THRESH_BINARY_INV): archival scans have dark border, light page — light page becomes white so largest contour is the page area"
  - "ALTO21_NS = http://schema.ccs-gmbh.com/ALTO — CCS-GmbH namespace, not Tesseract ALTO 3.x default"
  - "opencv-python-headless used (not opencv-python) for server/batch use without display dependency"
  - "load_tiff does not call .load() — keeps image lazy for large TIFF files"
  - "DPI fallback to (300.0, 300.0) logged as warning string, not exception — pipeline continues"

patterns-established:
  - "Warning accumulation: functions append to warnings list and return it rather than printing or raising"
  - "Fallback signalling: return boolean fallback_used flag alongside primary result"
  - "Bounds clamping: padding is always clamped to image dimensions before returning crop box"

requirements-completed: [PIPE-01, PIPE-02]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 1 Plan 01: Single-File Pipeline Skeleton Summary

**Pillow-based TIFF loader with DPI fallback and OpenCV THRESH_BINARY contour crop-box detection, establishing the foundation data contracts for all downstream Plan 02 functions**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-24T16:45:14Z
- **Completed:** 2026-02-24T16:46:47Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created requirements.txt with four pinned dependencies for reproducible environments
- Implemented load_tiff() with lazy PIL Image loading, DPI extraction from TIFF metadata tags, and (300.0, 300.0) fallback with warning accumulation
- Implemented detect_crop_box() using THRESH_BINARY + THRESH_OTSU for archival scans (dark scanner bed, light page content), with ratio-based fallback guard (40%-98%) and padding with bounds clamping
- Established argparse skeleton with all six Phase 1 CLI flags: --input, --output, --lang, --psm, --padding, --no-crop

## Task Commits

Each task was committed atomically:

1. **Task 1: Create requirements.txt with pinned library versions** - `24a10a4` (chore)
2. **Task 2: Implement pipeline.py skeleton with load_tiff() and detect_crop_box()** - `ff24a8e` (feat)

## Files Created/Modified
- `requirements.txt` - Four pinned library versions for reproducible installs (Pillow, opencv-python-headless, pytesseract, lxml)
- `pipeline.py` - Skeleton with load_tiff(), detect_crop_box(), ALTO namespace constants, argparse skeleton (142 lines)

## Decisions Made
- THRESH_BINARY chosen over THRESH_BINARY_INV: archival scans have a dark scanner bed with a light page — THRESH_BINARY makes the light page white so it registers as the largest contour
- ALTO21_NS set to http://schema.ccs-gmbh.com/ALTO (CCS-GmbH namespace per locked user decision, not Tesseract's ALTO 3.x default)
- opencv-python-headless selected for server/batch use without a display dependency
- load_tiff does not call .load() to preserve lazy loading for large TIFF files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed THRESH_BINARY_INV string from detect_crop_box docstring**
- **Found during:** Task 2 (automated verification)
- **Issue:** The plan's verification check uses `assert 'THRESH_BINARY_INV' not in src` on the function source. The docstring originally included the phrase "THRESH_BINARY_INV is intentionally NOT used here" which triggered the assertion even though the actual code correctly uses THRESH_BINARY.
- **Fix:** Rewrote the docstring phrase to "The inverse variant is intentionally NOT used here" — preserving intent without triggering the source inspection check.
- **Files modified:** pipeline.py
- **Verification:** Automated verification check re-run; PASS
- **Committed in:** ff24a8e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary for verification correctness. No scope creep.

## Issues Encountered
None - all verification steps passed after the docstring fix.

## User Setup Required
None - no external service configuration required. All libraries were already available in the local environment.

## Next Phase Readiness
- Plan 02 (01-02-PLAN.md) can now implement run_ocr(), build_alto21(), count_words(), and process_tiff() using the load_tiff() and detect_crop_box() functions established here
- The ALTO21_NS constant and POSITIONAL_TAGS set are ready for ALTO XML generation
- argparse skeleton is complete; main() just needs to call process_tiff() once Plan 02 wires it

---
*Phase: 01-single-file-pipeline*
*Completed: 2026-02-24*
