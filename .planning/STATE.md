# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.3 Operator Experience — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-25 — Milestone v1.3 started

Progress: [░░░░░░░░░░░░░░░░░░░░] 0% (Phases 6+ pending)

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: 2 min
- Total execution time: 20 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Single-File Pipeline | 2/2 | 4 min | 2 min |
| 2. Batch Orchestration and CLI | 2/2 | 4 min | 2 min |
| 3. Validation and Reporting | 2/2 | 6 min | 3 min |
| 4. Deskew | 1/1 | 6 min | 6 min |
| 5. Adaptive Thresholding | 1/1 | 2 min | 2 min |

**Recent Trend:**
- Last 5 plans: 02-02 (2 min), 03-01 (4 min), 03-02 (2 min), 04-01 (6 min), 05-01 (2 min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- THRESH_BINARY (not THRESH_BINARY_INV): archival scans have dark border, light page
- process_tiff() uses raise (not sys.exit) — safe for ProcessPoolExecutor spawn on macOS
- executor.submit() + as_completed() chosen over executor.map() — map() aborts on first exception
- [Phase 03-01]: load_xsd() returns None when XSD missing — caller warns and skips, does not abort
- [Phase 03-02]: write_report() called only when file_records is non-empty — pure skip runs produce no report
- [Phase 04-01]: deskew_str initialized to '' at top of process_tiff() — always defined even on exception paths
- [Phase 04-01]: Deskew inserted before detect_crop_box() — page contour must be axis-aligned for reliable crop detection
- [Phase 04-01]: DESKEW_MAX_ANGLE = 10.0 as named constant — appropriate plausibility gate for archival periodicals (genuine skew under 5°)
- [Phase 04-01]: Separate deskew_str from warnings_list — diagnostic angle info appears unconditionally; only fallback goes to [WARN: ...]
- [Phase 05-01]: cv2.THRESH_BINARY (not THRESH_BINARY_INV) for adaptive threshold — consistent with crop detection decision
- [Phase 05-01]: ADAPTIVE_BLOCK_SIZE = 51 (odd, required by cv2); ADAPTIVE_C = 10 — both need empirical tuning against real corpus
- [Phase 05-01]: adaptive_threshold_image() positioned after deskew, before detect_crop_box — binarized image feeds contour detection
- [Phase 05-01]: adaptive_threshold: bool is last positional arg in process_tiff(); no_crop stays hardcoded False in submit()

### Pending Todos

None.

### Blockers/Concerns

- ADAPTIVE_BLOCK_SIZE = 51 and ADAPTIVE_C = 10 need empirical tuning against real Zeitschriften corpus scans before production use of --adaptive-threshold

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 05-01-PLAN.md — adaptive thresholding integration complete, all phases done
Resume file: None
