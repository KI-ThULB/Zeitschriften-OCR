# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-02)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.6 Structured Text & TEI Export — Phase 19 ready to plan

## Current Position

Phase: Phase 19 of 21 (Text Normalization)
Plan: — (not started)
Status: Ready to plan — roadmap created, 133 tests green from v1.5
Last activity: 2026-03-02 — Milestone v1.6 roadmap created (Phases 19–21)

Progress: [·················] 0/3 phases complete

## Performance Metrics

**Velocity:**
- Total plans completed: 16
- Average duration: ~6 min
- Total execution time: ~97 min

**By Phase (recent):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 15. VLM Article Segmentation | 2/2 | ~23 min | ~11.5 min |
| 16. METS/MODS Output | 2/2 | 27 min | 13.5 min |
| 17. VLM Settings UI | 2/2 | ~46 min | ~23 min |
| 18. Article Browser and Full-Text Search | 2/2 | ~7 min | ~3.5 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 18]: DELETE+INSERT for FTS5 idempotency; stem UNINDEXED; /articles reads JSON directly
- [Phase 18]: GET /search serves HTML; GET /api/search returns JSON — avoids route conflict
- [Phase 15]: _parse_regions uses re.search(r'\{[\s\S]*\}') for JSON extraction from VLM output
- [Phase 16]: mets.py ALTO21_NS matches pipeline.py — CCS-GmbH namespace for all project ALTO files

### Pending Todos

None.

### Blockers/Concerns

- Phase 19 TEXT-01: Column detection relies on TextBlock HPOS — verify real project ALTO files contain TextBlock elements (not just String elements) before implementing sort logic
- Phase 20 STRUCT-08: VLM segment JSON stores bounding boxes per page; coordinate-overlap mapping from ALTO TextBlock HPOS/VPOS to segment regions needs a tolerance strategy for partial overlaps
- Phase 21: TEI export depends on Phases 19+20 being complete; plan Phase 21 last

## Session Continuity

Last session: 2026-03-02
Stopped at: v1.6 roadmap created — Phases 19, 20, 21 defined
Resume at: /gsd:plan-phase 19
