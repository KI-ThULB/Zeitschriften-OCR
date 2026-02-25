# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.2 Image Preprocessing — Phase 4: Deskew (ready to plan)

## Current Position

Phase: 4 of 5 (Deskew)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-02-25 — Roadmap created for v1.2 Image Preprocessing (Phases 4–5)

Progress: [██████████░░░░░░░░░░] 50% (Phases 1–3 done, Phases 4–5 pending)

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 2 min
- Total execution time: 12 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Single-File Pipeline | 2/2 | 4 min | 2 min |
| 2. Batch Orchestration and CLI | 2/2 | 4 min | 2 min |
| 3. Validation and Reporting | 2/2 | 6 min | 3 min |
| 4. Deskew | 0/? | — | — |
| 5. Adaptive Thresholding | 0/? | — | — |

**Recent Trend:**
- Last 5 plans: 01-02 (2 min), 02-01 (2 min), 02-02 (2 min), 03-01 (4 min), 03-02 (2 min)
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

### Pending Todos

None.

### Blockers/Concerns

- Deskew: choose between Hough-line and projection-profile approaches — research needed before 04-01
- Adaptive threshold block size and C constant need tuning against real Zeitschriften scans
- Confirm deskew angle plausibility threshold (e.g. reject corrections > 10°) before implementation

## Session Continuity

Last session: 2026-02-25
Stopped at: v1.2 roadmap created — Phase 4 Deskew ready to plan
Resume file: None
