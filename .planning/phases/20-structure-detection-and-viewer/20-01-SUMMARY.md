---
phase: 20-structure-detection-and-viewer
plan: 01
subsystem: ui
tags: [javascript, paragraph-detection, vpos-gap-analysis, vlm-role-assignment, alto-coordinates, viewer]

# Dependency graph
requires:
  - phase: 19-text-normalization
    provides: "blocks array in serve_alto() with HPOS/VPOS/WIDTH/HEIGHT/word_ids; wordById lookup pattern; currentArticles VLM data already loaded"
provides:
  - "detectParagraphs() — splits TextBlock into paragraph groups by VPOS gap > 1.5x median inter-line gap"
  - "intersectionArea() — axis-aligned rectangle overlap computation"
  - "assignRoles() — maps TextBlocks to structural roles via VLM region bounding-box overlap (ALTO pixel coords)"
  - "buildParaBlocks() — coordinator returning [{block, role, words}] with orphan word fallback"
  - "VLM_TYPE_TO_ROLE constant — maps headline/article/advertisement/illustration/caption to structural roles"
  - "currentBlocks module-level state variable — populated in loadFile(), read in loadArticles() for re-render"
affects:
  - "20-02 (structured rendering — Plan 02 calls renderBlocks(paraBlocks) replacing renderWords)"
  - "21-tei-export (paragraph structure feeds TEI paragraph elements)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure function pattern: detectParagraphs/assignRoles/buildParaBlocks have no side effects and are independently testable"
    - "Module-level state pattern: currentBlocks joins stems/wordById/currentArticles as page-scoped shared state"
    - "Dry-run wiring pattern: buildParaBlocks called in Plan 01 with result discarded; Plan 02 replaces renderWords with renderBlocks"
    - "Coordinate conversion pattern: VLM bounding boxes (0.0–1.0 fractions) * pageWidth/pageHeight (ALTO pixel coords) — NOT jpeg dimensions"

key-files:
  created: []
  modified:
    - "templates/viewer.html — added VLM_TYPE_TO_ROLE, detectParagraphs, intersectionArea, assignRoles, buildParaBlocks; currentBlocks state; loadFile/loadArticles wiring"

key-decisions:
  - "currentBlocks promoted to module-level state (alongside stems/wordById/currentArticles) so loadArticles() can access data.blocks after async VLM fetch resolves — following established pattern"
  - "buildParaBlocks called as dry-run in Plan 01 with result discarded; Plan 02 adds renderBlocks() replacing renderWords()"
  - "VPOS gap threshold: median * 1.5 (locked in CONTEXT.md) — median chosen over mean for robustness against outlier line spacing"
  - "VLM coordinate conversion: bb.x * pageWidth not bb.x * jpeg_width — ALTO pixel space differs from JPEG when TIFF > 1600px"

patterns-established:
  - "Paragraph detection: unique VPOS values proxy for TextLines; median gap of successive VPOS values sets adaptive threshold"
  - "Role assignment: max-overlap wins; no minimum threshold; default 'paragraph' when no VLM data"
  - "Orphan word fallback: words not in any block.word_ids appended as final {block:null, role:'paragraph', words:orphans} entry"

requirements-completed: [STRUCT-07, STRUCT-08]

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 20 Plan 01: Structure Detection and Viewer Summary

**Pure JS paragraph detection (VPOS gap analysis) and VLM role assignment algorithms added to viewer.html, with currentBlocks module-level state wired into loadFile() and loadArticles() as dry-run foundation for Plan 02 structured rendering**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T21:34:34Z
- **Completed:** 2026-03-02T21:37:49Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `VLM_TYPE_TO_ROLE` constant mapping all 5 VLM region types to structural roles (headline→heading, article/illustration→paragraph, advertisement→advertisement, caption→caption)
- Implemented `detectParagraphs()` splitting TextBlocks on VPOS gaps exceeding 1.5x the median inter-line gap, with guards for empty blocks and single-line blocks
- Implemented `intersectionArea()` for axis-aligned bounding box overlap and `assignRoles()` mapping TextBlocks to structural roles via max-overlap VLM region matching in ALTO pixel coordinate space
- Implemented `buildParaBlocks()` coordinator returning structured `[{block, role, words}]` entries with orphan word fallback
- Added `currentBlocks` module-level state variable; wired assignment in `loadFile()` and guarded re-compute in `loadArticles()` after VLM data resolves

## Task Commits

Each task was committed atomically:

1. **Task 1: Add detectParagraphs, intersectionArea, assignRoles, buildParaBlocks** - `fe87c63` (feat)
2. **Task 2: Wire currentBlocks state and call buildParaBlocks in loadFile() and loadArticles()** - `01fcd06` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `templates/viewer.html` — Added 122 lines: VLM_TYPE_TO_ROLE constant, detectParagraphs, intersectionArea, assignRoles, buildParaBlocks functions, currentBlocks state declaration, loadFile wiring, loadArticles guarded re-compute

## Decisions Made

- `currentBlocks` promoted to module-level state alongside `stems`/`wordById`/`currentArticles` — same pattern as existing async-resolved state; allows `loadArticles()` to rebuild paraBlocks after VLM fetch resolves
- `buildParaBlocks()` called as dry-run in Plan 01 with result discarded — Plan 02 will add `renderBlocks(paraBlocks)` replacing `renderWords(displayWords)`; this sequencing enables independent verification of algorithm correctness before rendering changes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 5 pure functions and VLM_TYPE_TO_ROLE constant are ready for Plan 02 to call
- `currentBlocks` is populated on every file load; `loadArticles()` will trigger re-render once Plan 02 adds `renderBlocks()`
- `renderWords()` remains the active renderer until Plan 02 replaces it — no visual change from Plan 01
- 136 pytest tests green; no JS errors (dry-run verified algorithm correctness with live data)

---
*Phase: 20-structure-detection-and-viewer*
*Completed: 2026-03-02*
