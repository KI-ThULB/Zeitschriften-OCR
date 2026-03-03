# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-02)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.6 Structured Text & TEI Export — Phase 21 Plans 01 and 02 complete (human-verify checkpoint pending)

## Current Position

Phase: Phase 21 of 21 (TEI P5 Export)
Plan: Plan 02 automation complete (21-02-PLAN.md Tasks 1-2 executed) — checkpoint:human-verify pending for Task 3
Status: Phase 21 automation complete — awaiting user browser verification of TEI download
Last activity: 2026-03-03 — 21-02: GET /tei/<stem> endpoint, Download TEI button, 3 new endpoint tests; 156 tests green

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
| 20. Structure Detection and Viewer | 2/2 | ~8 min | ~4 min |

| 21. TEI P5 Export | 2/2 (P02 automation done, verify pending) | 32 min | 16 min |

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
- [Phase 20-01]: currentBlocks promoted to module-level state so loadArticles() can rebuild paraBlocks after async VLM fetch resolves
- [Phase 20-01]: buildParaBlocks called as dry-run in Plan 01 result discarded; Plan 02 adds renderBlocks() replacing renderWords()
- [Phase 20-01]: VLM coordinate conversion: bb.x * pageWidth not jpeg_width — ALTO pixel space differs from JPEG when TIFF > 1600px
- [Phase 20-02]: renderBlocks() writes data-wc on spans identical to renderWords() — applyConfidenceStyling() finds .word[data-wc] without change
- [Phase 20-02]: wordListClickHandler re-attached after renderBlocks() innerHTML write — delegated click-to-edit preserved across renders
- [Phase 20-02]: struct-summary in #wc-settings (sibling of #word-list) — survives renderBlocks() innerHTML overwrites
- [Phase 21-01]: ALTO fixture for hyphen-rejoin test: "Ver-" must be sole word in TextLine so line_end=True; otherwise rejoin cannot trigger
- [Phase 21-01]: lb mixed-content semantics: lb IS the last child element when final line text is in lb.tail — test checks empty tail, not element presence
- [Phase 21-01]: facs on surface uses ../uploads/{stem}.tif (matches app.py UPLOAD_SUBDIR); CONTEXT.md ../scans/ was illustrative
- [Phase 21-02]: TestExportTei in test_app.py (not test_mets.py) — per plan spec; path traversal test uses URL-encoded stem (%2F) since Flask normalises raw slashes
- [Phase 21-02]: tei-btn positioned between segment-btn and segment-status span; encodeURIComponent(currentStem) in downloadTei()

### Pending Todos

None.

### Blockers/Concerns

- Phase 19-01 resolved: blocks array verified working; TextBlock elements returned as expected
- Phase 20 STRUCT-08: VLM segment JSON stores bounding boxes per page; coordinate-overlap mapping from ALTO TextBlock HPOS/VPOS to segment regions needs a tolerance strategy for partial overlaps
- Phase 21: TEI export depends on Phases 19+20 being complete; plan Phase 21 last

## Session Continuity

Last session: 2026-03-03
Stopped at: 21-02-PLAN.md Task 3 checkpoint:human-verify — browser verification of TEI download required
Resume at: User verifies TEI download in browser, then mark Phase 21 complete
