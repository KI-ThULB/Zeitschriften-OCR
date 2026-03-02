# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-02)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.6 Structured Text & TEI Export — Phase 19 in progress (Plan 02 complete)

## Current Position

Phase: Phase 19 of 21 (Text Normalization)
Plan: Plan 02 complete (19-02-PLAN.md executed)
Status: In progress — Plan 02 done, Plan 03 next (if applicable)
Last activity: 2026-03-02 — 19-02: normalizeWords pipeline (column sort + hyphen rejoin) and confidence threshold slider added to viewer.html; 136 tests green

Progress: [·················] 0/3 phases complete

## Performance Metrics

**Velocity:**
- Total plans completed: 17
- Average duration: ~6 min
- Total execution time: ~100 min

**By Phase (recent):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 15. VLM Article Segmentation | 2/2 | ~23 min | ~11.5 min |
| 16. METS/MODS Output | 2/2 | 27 min | 13.5 min |
| 17. VLM Settings UI | 2/2 | ~46 min | ~23 min |
| 18. Article Browser and Full-Text Search | 2/2 | ~7 min | ~3.5 min |
| 19. Text Normalization | 2/3 | ~6 min | ~3 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 18]: DELETE+INSERT for FTS5 idempotency; stem UNINDEXED; /articles reads JSON directly
- [Phase 18]: GET /search serves HTML; GET /api/search returns JSON — avoids route conflict
- [Phase 15]: _parse_regions uses re.search(r'\{[\s\S]*\}') for JSON extraction from VLM output
- [Phase 16]: mets.py ALTO21_NS matches pipeline.py — CCS-GmbH namespace for all project ALTO files
- [Phase 19-01]: lxml proxy recycling fix — materialise root.iter() into all_strings list once; use (CONTENT,HPOS,VPOS) tuple for block-membership lookup
- [Phase 19-01]: serve_alto() blocks array and line_end flag are additive (no existing keys removed)
- [Phase 19-02]: #word-list inner container isolates word span injection from #wc-settings slider — prevents renderWords() innerHTML from destroying persistent UI elements
- [Phase 19-02]: wordById maps original data.words (not displayWords) — edit/save operates on ALTO-original content; rejoinHyphens() joined word inherits first fragment ID

### Pending Todos

None.

### Blockers/Concerns

- Phase 19-01 resolved: blocks array verified working; TextBlock elements returned as expected
- Phase 20 STRUCT-08: VLM segment JSON stores bounding boxes per page; coordinate-overlap mapping from ALTO TextBlock HPOS/VPOS to segment regions needs a tolerance strategy for partial overlaps
- Phase 21: TEI export depends on Phases 19+20 being complete; plan Phase 21 last

## Session Continuity

Last session: 2026-03-02
Stopped at: Completed 19-02-PLAN.md — normalizeWords pipeline, confidence slider in viewer.html
Resume at: /gsd:execute-phase 19-text-normalization (Plan 03 next, if applicable)
