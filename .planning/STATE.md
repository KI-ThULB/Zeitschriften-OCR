# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.3 Operator Experience — Phase 8: Config File Support

## Current Position

Phase: 8 of 8 in v1.3 (Config File Support) — COMPLETE
Plan: 2 of 2 complete (08-01 and 08-02 done)
Status: Phase 8 complete — v1.3 Operator Experience fully shipped
Last activity: 2026-02-26 — 08-02 (--config flag wiring + integration tests) complete

Progress: [████████████████████] 100% (all 8 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 2.2 min
- Total execution time: 28 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Single-File Pipeline | 2/2 | 4 min | 2 min |
| 2. Batch Orchestration and CLI | 2/2 | 4 min | 2 min |
| 3. Validation and Reporting | 2/2 | 6 min | 3 min |
| 4. Deskew | 1/1 | 6 min | 6 min |
| 5. Adaptive Thresholding | 1/1 | 2 min | 2 min |
| 6. Diagnostic Flags | 2/2 | 6 min | 3 min |
| 7. Live Progress Display | 1/1 | 2 min | 2 min |
| 8. Config File Support | 2/2 | 11 min | 5.5 min |

**Recent Trend:**
- Last 5 plans: 06-01 (2 min), 06-02 (4 min), 07-01 (2 min), 08-01 (5 min), 08-02 (6 min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- process_tiff() uses raise (not sys.exit) — safe for ProcessPoolExecutor spawn on macOS
- executor.submit() + as_completed() — chosen for per-file error isolation; progress updates slot into this loop
- [Phase 04-01]: Deskew before detect_crop_box() — ordering invariant; verbose timing must respect this order
- [Phase 05-01]: ADAPTIVE_BLOCK_SIZE = 51, ADAPTIVE_C = 10 — need empirical tuning before production
- [Phase 06-01]: validate_tesseract() runs before dry-run gate so operators get Tesseract errors even in dry-run mode
- [Phase 06-01]: --verbose silently ignored in dry-run path (no OCR runs, nothing verbose to report)
- [Phase 06-01]: dry-run skip-check replicates exact run_batch() condition: `if not args.force and out_path.exists()`
- [Phase 06-diagnostic-flags]: run_ocr() returns tuple[bytes, str] in both modes — capture_output=False returns empty string as second element
- [Phase 06-diagnostic-flags]: verbose_block built as single string and printed atomically to reduce stdout interleaving when workers > 1
- [Phase 07-01]: tracker.update(duration) placed after try/except (not in finally) — both success and failure update rolling average
- [Phase 07-01]: show_progress = (not verbose) and sys.stderr.isatty() and len(to_process) > 0 — three independent suppression conditions
- [Phase 07-01]: submit_times dict provides accurate per-file duration even with parallel workers (captures queue wait + OCR time)
- [Phase 08-01]: CONFIG_TYPES placed after ADAPTIVE_C block; load_config() placed between write_error_log() and load_xsd()
- [Phase 08-01]: bool-for-int rejection: `not isinstance(value, int) or isinstance(value, bool)` — bool is subclass of int in Python
- [Phase 08-01]: Error messages use "Error:" prefix (capital E, lowercase r) — locked decisions take precedence over validate_tesseract() "ERROR:" style
- [Phase 08-02]: Two-pass pre-parse uses parse_known_args() silently ignoring all other flags — avoids reimplementing argparse logic
- [Phase 08-02]: set_defaults() called before parse_args() — standard argparse mechanism giving CLI flags automatic precedence
- [Phase 08-02]: Verbose config summary after validate_tesseract(), before is_dir() — only shows when run will actually proceed

### Pending Todos

None.

### Blockers/Concerns

- ADAPTIVE_BLOCK_SIZE = 51 and ADAPTIVE_C = 10 need empirical tuning against real Zeitschriften corpus scans before production use of --adaptive-threshold

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 08-02-PLAN.md (--config flag wiring + integration tests) — Phase 8 complete
Resume file: None
