# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.3 Operator Experience — Phase 6: Diagnostic Flags

## Current Position

Phase: 6 of 8 in v1.3 (Diagnostic Flags)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-02-25 — v1.3 roadmap created (phases 6–8)

Progress: [██████████░░░░░░░░░░] 50% (5/8 phases complete across all milestones)

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

- process_tiff() uses raise (not sys.exit) — safe for ProcessPoolExecutor spawn on macOS
- executor.submit() + as_completed() — chosen for per-file error isolation; progress updates slot into this loop
- [Phase 04-01]: Deskew before detect_crop_box() — ordering invariant; verbose timing must respect this order
- [Phase 05-01]: ADAPTIVE_BLOCK_SIZE = 51, ADAPTIVE_C = 10 — need empirical tuning before production

### Pending Todos

None.

### Blockers/Concerns

- ADAPTIVE_BLOCK_SIZE = 51 and ADAPTIVE_C = 10 need empirical tuning against real Zeitschriften corpus scans before production use of --adaptive-threshold

## Session Continuity

Last session: 2026-02-25
Stopped at: v1.3 roadmap written — Phase 6 (Diagnostic Flags) ready to plan
Resume file: None
