# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** Phase 1 — Single-File Pipeline

## Current Position

Phase: 1 of 3 (Single-File Pipeline)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-02-24 — Roadmap created (3 phases)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Stack confirmed: Pillow, opencv-python-headless, pytesseract, lxml, ProcessPoolExecutor, tqdm, argparse
- Build order is a correctness constraint: single-file pipeline must be correct before parallelism is introduced

### Pending Todos

None yet.

### Blockers/Concerns

- Validate DPI metadata on 20–30 actual Zeitschriften TIFFs before Phase 1 cutover (some may have no DPI tag or misconfigured 72 DPI values)
- Confirm Goobi coordinate system: research assumes original-TIFF coordinates require crop offset; verify with actual Goobi instance before Phase 1 is considered complete
- Confirm ALTO 2.1 MeasurementUnit expected by target Goobi instance (`mm10` vs `pixel`) — affects coordinate conversion formula
- Validate crop detection fallback thresholds (40%/98%) against 10–20 representative Zeitschriften samples

## Session Continuity

Last session: 2026-02-24
Stopped at: Roadmap written; ready to plan Phase 1
Resume file: None
