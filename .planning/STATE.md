# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** Phase 2 in progress — Plan 01 complete (pipeline bug fixes and batch helpers)

## Current Position

Phase: 02-batch-orchestration-and-cli — Plan 01 complete
Status: Ready for Plan 02 (batch orchestrator implementation)
Last activity: 2026-02-24 — Completed 02-01 pipeline bug fixes and batch helpers

Progress: [███░░░░░░░] 33% (1/3 phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 2 min
- Total execution time: 6 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Single-File Pipeline | 2/2 | 4 min | 2 min |
| 2. Batch Orchestration and CLI | 1/? | 2 min | 2 min |

**Recent Trend:**
- Last 5 plans: 01-01 (2 min), 01-02 (2 min), 02-01 (2 min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Stack confirmed: Pillow, opencv-python-headless, pytesseract, lxml, ProcessPoolExecutor, tqdm, argparse
- Build order is a correctness constraint: single-file pipeline must be correct before parallelism is introduced
- THRESH_BINARY (not THRESH_BINARY_INV): archival scans have dark border, light page — light page becomes white largest-contour
- ALTO21_NS = http://schema.ccs-gmbh.com/ALTO (CCS-GmbH namespace, not Tesseract ALTO 3.x default)
- opencv-python-headless chosen over opencv-python for server/batch use without display dependency
- load_tiff keeps image lazy (no .load() call) to handle large TIFF files efficiently
- Crop offset applied BEFORE namespace rewrite in build_alto21: ALTO3_NS element lookup must precede string replace
- WIDTH and HEIGHT NOT offset by crop box — only HPOS and VPOS get crop_box[0]/crop_box[1] added
- xsi:schemaLocation for ALTO 3 stripped from ALTO 2.1 output to avoid contradictory schema references
- run_ocr passes PIL Image directly to pytesseract (not numpy array) — pytesseract writes temp PNG internally
- process_tiff() uses raise (not sys.exit) in except block — safe for ProcessPoolExecutor spawn on macOS (02-01)
- xsi:schemaLocation stripped via root.attrib.pop BEFORE serialization, not string-replace after namespace rewrite (02-01)
- validate_tesseract() calls sys.exit(1) directly — it is a pre-flight guard, not a worker function (02-01)

### Pending Todos

None yet.

### Blockers/Concerns

- Validate DPI metadata on 20-30 actual Zeitschriften TIFFs before Phase 1 cutover (some may have no DPI tag or misconfigured 72 DPI values)
- Confirm Goobi coordinate system: research assumes original-TIFF coordinates require crop offset; verify with actual Goobi instance before Phase 1 is considered complete
- Confirm ALTO 2.1 MeasurementUnit expected by target Goobi instance (mm10 vs pixel) — affects coordinate conversion formula
- Validate crop detection fallback thresholds (40%/98%) against 10-20 representative Zeitschriften samples

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 02-01 (pipeline bug fixes and batch helpers)
Resume file: None
