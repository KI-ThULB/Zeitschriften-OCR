# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** Phase 3 complete — all plans done (XSD validation + JSON reporting wired into pipeline.py)

## Current Position

Phase: 03-validation-and-reporting — Plan 02 complete (2/2 plans done)
Status: Phase 3 complete — 03-01 done (XSD validation layer); 03-02 done (JSON report writer + main() wiring)
Last activity: 2026-02-25 — Completed 03-02 write_report(), --validate-only mode, and post-OCR validation pass

Progress: [██████████] 100% (Phase 1 done, Phase 2 done, Phase 3 done)

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 2 min
- Total execution time: 10 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Single-File Pipeline | 2/2 | 4 min | 2 min |
| 2. Batch Orchestration and CLI | 2/2 | 4 min | 2 min |
| 3. Validation and Reporting | 2/2 | 6 min | 3 min |

**Recent Trend:**
- Last 5 plans: 01-02 (2 min), 02-01 (2 min), 02-02 (2 min), 03-01 (4 min), 03-02 (2 min)
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
- executor.submit() + as_completed() chosen over executor.map() — map() aborts on first exception (02-02)
- --workers default=None resolved at runtime as min(os.cpu_count() or 1, 4) — not evaluated at import time (02-02)
- Skip-if-exists check before ProcessPoolExecutor creation — avoids spawning workers when all files already processed (02-02)
- no_crop=False passed in run_batch submit() — batch mode always attempts crop detection, same as single-file default (02-02)
- [Phase 03-01]: load_xsd() returns None when XSD missing — caller warns and skips validation rather than aborting batch
- [Phase 03-01]: validate_batch() sets schema_valid=None (not False) for non-ok records — None distinguishes skip from pass/fail
- [Phase 03-02]: write_report() called only when file_records is non-empty — pure skip runs produce no report file
- [Phase 03-02]: validation_warnings=0 initialised before if-block so summary line always defined even on pure-skip runs
- [Phase 03-02]: --validate-only globs alto/*.xml from output dir directly, skipping discover_tiffs() entirely
- [Phase 03-02]: import time as _time inside main() avoids shadowing top-level `import time` used by process_tiff()

### Pending Todos

None yet.

### Blockers/Concerns

- Validate DPI metadata on 20-30 actual Zeitschriften TIFFs before Phase 1 cutover (some may have no DPI tag or misconfigured 72 DPI values)
- Confirm Goobi coordinate system: research assumes original-TIFF coordinates require crop offset; verify with actual Goobi instance before Phase 1 is considered complete
- Confirm ALTO 2.1 MeasurementUnit expected by target Goobi instance (mm10 vs pixel) — affects coordinate conversion formula
- Validate crop detection fallback thresholds (40%/98%) against 10-20 representative Zeitschriften samples

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 03-02 (write_report(), --validate-only mode, post-OCR validation pass in main())
Resume file: None
