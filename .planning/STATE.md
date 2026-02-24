# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** Phase 1 complete — ready for Phase 2 (Batch Processor)

## Current Position

Phase: 1 of 3 (Single-File Pipeline) — COMPLETE
Plan: 2 of 2 in current phase — COMPLETE
Status: Phase 1 complete
Last activity: 2026-02-24 — Completed 01-02: run_ocr, build_alto21, count_words, process_tiff, main()

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 2 min
- Total execution time: 4 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Single-File Pipeline | 2/2 | 4 min | 2 min |

**Recent Trend:**
- Last 5 plans: 01-01 (2 min), 01-02 (2 min)
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

### Pending Todos

None yet.

### Blockers/Concerns

- Validate DPI metadata on 20-30 actual Zeitschriften TIFFs before Phase 1 cutover (some may have no DPI tag or misconfigured 72 DPI values)
- Confirm Goobi coordinate system: research assumes original-TIFF coordinates require crop offset; verify with actual Goobi instance before Phase 1 is considered complete
- Confirm ALTO 2.1 MeasurementUnit expected by target Goobi instance (mm10 vs pixel) — affects coordinate conversion formula
- Validate crop detection fallback thresholds (40%/98%) against 10-20 representative Zeitschriften samples

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 01-02-PLAN.md — full pipeline.py with run_ocr, build_alto21, count_words, process_tiff, main()
Resume file: None
