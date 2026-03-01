---
phase: 15-vlm-article-segmentation
plan: 02
subsystem: ui
tags: [javascript, svg, fetch, viewer, segmentation, region-overlay]

# Dependency graph
requires:
  - phase: 15-01
    provides: POST/GET /segment/<stem> endpoints, VLM segmentation JSON with normalized bounding_box coords
  - phase: 14-viewer-zoom-and-pan
    provides: shared-container CSS transform (#image-container) that auto-zooms SVG overlay with image
  - phase: 10-tiff-and-alto-data-endpoints
    provides: jpeg_width/jpeg_height in GET /alto/<stem> response for coordinate scaling
provides:
  - Segment button in viewer toolbar (disabled until file loaded, enabled by loadFile())
  - segmentPage(): POST /segment/<currentStem> with spinner state and error display
  - showSegmentRegions(regions): colored SVG rects+labels on #overlay using normalized coords
  - clearSegmentRegions(): removes all .segment-region/.segment-label from overlay
  - loadSegments(stem): GET /segment/<stem> to restore stored regions on file switch
  - loadFile() integration: clears regions at start, captures jpeg_width/jpeg_height, calls loadSegments after ALTO loads
affects: [16-mets-mods, any future viewer phase]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SVG region overlay using createElementNS with normalized 0-1 coords scaled by jpeg_width/jpeg_height"
    - "Spinner pattern: btn.disabled=true + btn.classList.add('running') with CSS ::after content"
    - "Silent 404 handling: loadSegments() ignores 404 (not yet segmented) without user-visible error"
    - "paint-order stroke fill on SVG text for white outline labels without extra DOM elements"

key-files:
  created: []
  modified:
    - templates/viewer.html

key-decisions:
  - "currentStem and jpeg_width/jpeg_height added as module-level JS vars — segment functions need them without passing through call chain"
  - "Segment button placed in nav-bar toolbar (not floating overlay) — consistent with existing nav pattern"
  - "loadSegments() called after renderWords() inside loadFile() ALTO success block — ensures jpeg_width/jpeg_height are set before showSegmentRegions() is called"
  - "segmentPage() re-enables button in finally block — ensures button is never permanently stuck disabled on network error"
  - "status.style.color = '#555' on success — overrides default red (#c00) set by CSS, no extra class needed"

patterns-established:
  - "Region overlay uses same #overlay SVG as word highlight-rect — shared-container transform applies to all children automatically"
  - "clearSegmentRegions() called at start of loadFile() — prevents stale regions from previous file persisting during fetch"

requirements-completed: [STRUCT-01, STRUCT-02, STRUCT-03]

# Metrics
duration: 20min
completed: 2026-03-01
---

# Phase 15 Plan 02: VLM Article Segmentation Region Overlay Summary

**Segment button in viewer toolbar with colored SVG region overlay — POST triggers VLM segmentation, GET restores stored regions on file switch, regions zoom/pan via shared-container transform**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-01T17:22:25Z
- **Completed:** 2026-03-01T17:42:43Z
- **Tasks:** 4 auto + 1 human-verify
- **Files modified:** 1

## Accomplishments
- Segment button added to nav-bar toolbar; starts disabled, enabled by loadFile() after stem is set
- segmentPage() POSTs to /segment/<currentStem>, shows spinner, draws colored SVG regions on success, shows red error on failure
- showSegmentRegions() draws per-region colored rect + type-prefixed label using normalized bounding_box coords scaled by jpeg_width/jpeg_height
- loadSegments() restores stored regions on every file switch via GET /segment/<stem>; 404 silently ignored
- loadFile() updated to clear stale regions at start, capture jpeg_width/jpeg_height from ALTO response, and call loadSegments after data loads
- All 79 existing pytest tests continue to pass (zero regressions)
- All 10 interactive browser checks verified by operator

## Task Commits

Each task was committed atomically:

1. **Task 1: Segment button and region overlay CSS** - `8d2744b` (feat)
2. **Task 2: Add Segment button to toolbar HTML** - `924c4cc` (feat)
3. **Task 3: segmentPage(), showSegmentRegions(), clearSegmentRegions(), loadSegments() JS** - `bcc07e5` (feat)
4. **Task 4: Wire loadFile() to enable button and restore segments** - `f58b709` (feat)

## Files Created/Modified
- `templates/viewer.html` - Added CSS, toolbar HTML, 4 JS functions, and loadFile() integration (161 lines added)

## Decisions Made
- `currentStem` and `jpeg_width`/`jpeg_height` added as module-level JS variables — needed by segment functions without threading through call chains
- Segment button placed in the existing `#nav-bar` toolbar alongside Previous/Next — consistent with existing nav control pattern
- `loadSegments()` called after `renderWords()` inside the ALTO fetch success block, ensuring `jpeg_width`/`jpeg_height` are populated before `showSegmentRegions()` runs
- `segmentPage()` re-enables the button in a `finally` block — prevents the button getting permanently stuck disabled after a network error
- `status.style.color = '#555'` on success directly overrides the default red set by CSS, avoiding an extra CSS class

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added currentStem and jpeg_width/jpeg_height module-level vars**
- **Found during:** Task 3 (JS functions) — plan stated these were "existing module-level variables" but they were absent from viewer.html
- **Issue:** showSegmentRegions() references jpeg_width/jpeg_height; segmentPage() references currentStem — neither existed as module-level vars in the current file
- **Fix:** Added `let currentStem = null; let jpeg_width = 0; let jpeg_height = 0;` to the var block at the top of the script; populated them in loadFile()
- **Files modified:** templates/viewer.html
- **Verification:** Functions reference the vars correctly; 79 tests pass
- **Committed in:** bcc07e5 + f58b709 (Tasks 3 and 4)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing required state variables)
**Impact on plan:** Necessary for correctness — without the vars the JS functions would reference undefined globals. No scope creep.

## Issues Encountered
None — all tasks executed cleanly after adding the missing state variables.

## User Setup Required
None - no external service configuration required for the viewer changes. VLM provider credentials are configured via CLI flags (--vlm-provider, --vlm-api-key) as established in Phase 15-01.

## Next Phase Readiness
- STRUCT-01, STRUCT-02, STRUCT-03 satisfied — VLM segmentation UI complete
- Phase 15 fully complete (2/2 plans done)
- Phase 16 (METS/MODS) can proceed — DFG Viewer newspaper profile XSD must be sourced and bundled before implementation begins

---
*Phase: 15-vlm-article-segmentation*
*Completed: 2026-03-01*
