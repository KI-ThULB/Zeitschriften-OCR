---
phase: 14-viewer-zoom-and-pan
plan: 01
subsystem: ui
tags: [javascript, css, svg, flask, viewer, zoom, pan]

# Dependency graph
requires:
  - phase: 12-word-correction
    provides: editingSpan/cancelEdit() integration point for zoom interactions
  - phase: 11-side-by-side-viewer-ui
    provides: viewer.html shared-container structure, image-panel, overlay SVG, loadFile(), setupResizeObserver()
provides:
  - Mouse-wheel zoom centered on cursor via CSS transform on shared #image-container
  - Click-drag pan with 5px disambiguation threshold and soft 20% visibility clamp
  - SVG word-overlay alignment at all zoom levels (no coordinate recalculation — shared transform)
  - Reset button overlay showing integer zoom% when zoomed away from fit-to-width
  - Keyboard +/-/0 zoom shortcuts (suppressed when INPUT is focused)
  - cancelEdit() fires before any zoom or pan transform
  - ResizeObserver and loadFile() both call recomputeFitScale() for fit-to-width baseline
affects: [15-vlm-region-detection, 16-mets-mods-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Shared-container CSS transform (translate + scale on wrapper div) keeps image and SVG overlay in sync without per-word coordinate recalculation
    - zoomLevel relative to fitScale baseline — zoomLevel=1.0 always means fit-to-width regardless of panel size
    - applyZoom(factor, origin) shared between wheel and keyboard so zoom logic is defined once
    - clampPan() soft bounds: 20% visibility minimum enforced after every pan or zoom
    - isDragging + 5px Math.hypot threshold disambiguates click from drag, suppressing word selection on pan

key-files:
  created: []
  modified:
    - templates/viewer.html

key-decisions:
  - "ZOOM_STEP increased from 1.1 to 1.3 after user verification — 1.1 per-tick feel was too subtle for newspaper inspection workflow"
  - "translate before scale in applyTransform() keeps panX/panY in screen pixels (pre-scale) for natural drag feel"
  - "overflow: hidden on #image-panel (not overflow: auto) required — scrollbars conflict with transform-based pan"
  - "ResizeObserver calls recomputeFitScale() before showHighlight(activeWord) to keep overlay aligned after resize"
  - "updateResetButton() called from both applyTransform() and recomputeFitScale() — single source of truth for button visibility"

patterns-established:
  - "Shared-container transform pattern: wrap image and SVG in one div, transform the div — zero per-word coordinate math"
  - "zoom relative to fit baseline: fitScale * zoomLevel = absolute CSS scale — zoomLevel=1.0 is always fit-to-width"
  - "cancelEdit-before-transform: every zoom/pan entry point calls cancelEdit() before mutating state"

requirements-completed: [VIEW-05, VIEW-06]

# Metrics
duration: ~25min
completed: 2026-03-01
---

# Phase 14 Plan 01: Viewer Zoom and Pan Summary

**Mouse-wheel zoom centered on cursor plus click-drag pan in the ALTO viewer, with SVG word-overlay staying pixel-accurate at all zoom levels via shared CSS transform on a single container div**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-01T13:00:00Z (estimated)
- **Completed:** 2026-03-01T13:33:45Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments

- Zoom engine: wheel handler calls `applyZoom()` with cursor origin, zoom stays centered on mouse position at all zoom levels
- Shared-container transform: `#image-container` wraps `<img>` and `<svg>` together so both move/scale identically with no per-word coordinate recalculation
- Pan engine: mousedown/mousemove/mouseup with 5px Math.hypot threshold; `clampPan()` keeps 20% of image visible on any edge
- Reset button overlay dynamically shows integer zoom% (`fitScale * zoomLevel * 100`) and hides at fit-to-width; clicking returns to baseline
- Keyboard shortcuts +/-/0 integrated into existing `setupKeyboard()` with INPUT focus guard already in place
- `recomputeFitScale()` wired into both `loadFile()` (file switch) and `ResizeObserver` (window resize) — zoom always resets to fit-to-width on either event
- `cancelEdit()` called before any zoom or pan transform fires — prevents orphaned edit inputs

## Task Commits

Each task was committed atomically:

1. **Task 1: Zoom and pan core — shared container, wheel handler, drag handler** - `539b569` (feat)
2. **Task 2: Reset button, zoom label, keyboard +/-/0 shortcuts** - `44dc87a` (feat)
3. **ZOOM_STEP tweak: 1.1 → 1.3 per user feedback during verification** - `1969646` (tweak)
4. **Task 3: Human verification checkpoint** - approved (no commit; browser-only)

**Plan metadata:** (docs commit follows this summary)

## Files Created/Modified

- `/Users/zu54tav/Zeitschriften-OCR/templates/viewer.html` - Added `#image-container` wrapper, `zoomLevel`/`fitScale`/`panX`/`panY` state, `applyTransform()`, `recomputeFitScale()`, `clampPan()`, `applyZoom()`, wheel handler, drag handler, `updateResetButton()`, `#zoom-reset-btn` CSS, keyboard +/-/0 in `setupKeyboard()`, ResizeObserver integration

## Decisions Made

- **ZOOM_STEP 1.1 → 1.3:** User found 1.1 per wheel-tick too subtle when inspecting small newspaper text; 1.3 gives a stronger per-tick feel while staying within ZOOM_MIN/ZOOM_MAX range.
- **translate before scale in `applyTransform()`:** `translate(panX, panY) scale(s)` means panX/panY are pre-scale screen pixels — dragging feels 1:1 with mouse movement regardless of zoom level. If scale were first, pan values would need to be divided by scale to feel natural.
- **overflow: hidden on `#image-panel`:** Overflow must be hidden (not auto) so scrollbars don't appear; scrollbars resist the transform-based pan and create layout jitter.
- **`updateResetButton()` called from `applyTransform()` and `recomputeFitScale()`:** Ensures button state is always in sync with current zoom, covering both the zoom path and the reset path without duplication.

## Deviations from Plan

### Auto-fixed Issues

**1. [User Request - Tweak] ZOOM_STEP increased from 1.1 to 1.3**
- **Found during:** Task 3 human verification
- **Issue:** User found 1.1 per-tick zoom too subtle; hard to reach useful zoom levels quickly for newspaper inspection
- **Fix:** Changed `const ZOOM_STEP = 1.1;` to `const ZOOM_STEP = 1.3;`
- **Files modified:** templates/viewer.html
- **Verification:** Browser zoom feel confirmed by user; ZOOM_MIN/ZOOM_MAX still respected
- **Committed in:** `1969646`

---

**Total deviations:** 1 user-requested tweak (not a plan deviation — plan left ZOOM_STEP at 1.1 as a starting value with expectation of tuning)
**Impact on plan:** No scope changes. One-line constant change requested after live verification.

## Issues Encountered

None — plan executed cleanly. The shared-container transform approach eliminated all SVG alignment issues at the design level.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- VIEW-05 and VIEW-06 satisfied: zoom/pan complete, SVG overlay pixel-accurate at all zoom levels
- `templates/viewer.html` is the fully capable viewer for Phase 15 (VLM region detection): operators can zoom to inspect regions, pan to target areas
- Phase 15 concern: VLM provider selection (Claude Vision vs GPT-4o vs Gemini) needs evaluation before committing to provider abstraction interface
- Phase 16 concern: DFG Viewer newspaper profile XSD must be sourced and bundled before METS/MODS implementation begins

---
*Phase: 14-viewer-zoom-and-pan*
*Completed: 2026-03-01*
