---
phase: 20-structure-detection-and-viewer
plan: 02
subsystem: ui
tags: [javascript, viewer, alto, vlm, structured-text, css]

# Dependency graph
requires:
  - phase: 20-01
    provides: detectParagraphs, assignRoles, buildParaBlocks algorithms and currentBlocks module-level state in viewer.html
  - phase: 19-02
    provides: "#word-list inner container pattern, wordById map, renderWords() baseline, delegated click handler"
provides:
  - renderBlocks() function rendering .para-block divs with data-role attributes replacing flat renderWords()
  - updateStructSummary() showing role count (headings/paragraphs/captions/ads) below confidence badge
  - CSS role styling — headings bold/1.1em, captions italic/0.9em, advertisements italic/0.9em/left-border
  - "#struct-summary HTML element persisted in #wc-settings across file loads"
  - VIEW-07 delivered — structured text panel with VLM-assigned visual role differentiation
affects:
  - 20-03 (if any)
  - 21-tei-export (reads structured blocks from viewer state)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "renderBlocks() targets #word-list (not #text-panel) — Phase 19 inner container invariant preserved"
    - "updateStructSummary() called after every renderBlocks() — two-pass render (loadFile + loadArticles async)"
    - "applyConfidenceStyling() always called after renderBlocks() — word span order invariant"
    - "data-role attribute on .para-block drives all CSS — no JS style manipulation"

key-files:
  created: []
  modified:
    - templates/viewer.html

key-decisions:
  - "renderBlocks() writes data-wc on each span identically to renderWords() — ensures applyConfidenceStyling() finds .word[data-wc] spans without changes to that function"
  - "escapeHtml() reused from Phase 12 scope — no new sanitisation code needed"
  - "wordListClickHandler re-attached to #word-list after each renderBlocks() innerHTML write — preserves delegated click-to-edit"
  - "struct-summary placed inside #wc-settings not #word-list — survives renderBlocks() innerHTML overwrites"

patterns-established:
  - "Structured text: renderBlocks(paraBlocks) -> updateStructSummary(paraBlocks) -> applyConfidenceStyling(wcThreshold) call sequence at every render site"

requirements-completed: [VIEW-07]

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 20 Plan 02: Structured Text Panel Summary

**renderBlocks() replaces renderWords() with CSS-styled .para-block[data-role] divs, updateStructSummary() shows role counts, and VLM-assigned headings/captions/advertisements render visually differentiated in the text panel**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-02T21:41:54Z
- **Completed:** 2026-03-02T22:43:00Z (including human-verify checkpoint)
- **Tasks:** 3 (2 auto + 1 human-verify)
- **Files modified:** 1

## Accomplishments
- renderBlocks() function renders paragraph blocks with margin-bottom gaps instead of a flat word stream
- CSS role styling: headings bold/1.1em, captions italic/0.9em, advertisements italic/0.9em with 3px solid left border
- updateStructSummary() displays live role count (e.g. "1 heading, 3 paragraphs") below confidence badge in #struct-summary
- Two-pass rendering: loadFile() renders on load, loadArticles() re-renders when VLM data arrives asynchronously
- All word-level features preserved: click-to-edit, confidence slider fading, SVG highlight, zoom/pan intact
- 136 pytest tests remain green

## Task Commits

Each task was committed atomically:

1. **Task 1: Add renderBlocks(), updateStructSummary(), CSS role styling, #struct-summary HTML** - `b5c9052` (feat)
2. **Task 2: Replace renderWords() calls with renderBlocks() in loadFile() and loadArticles()** - `02ab2b4` (feat)
3. **Task 3: Verify structured text panel visually and functionally** - human-verify checkpoint, user approved (no code commit needed)

## Files Created/Modified
- `templates/viewer.html` - renderBlocks(), updateStructSummary(), CSS .para-block/[data-role=...] rules, #struct-summary HTML element, wiring in loadFile() and loadArticles()

## Decisions Made
- renderBlocks() writes `data-wc` on each word span exactly as renderWords() did — applyConfidenceStyling() finds `.word[data-wc]` without any changes to that function
- wordListClickHandler re-attached after each `list.innerHTML` write — delegated click-to-edit preserved across renders
- #struct-summary placed inside #wc-settings (sibling of #word-list) — element survives renderBlocks() innerHTML overwrites because it is outside the rewritten container
- updateStructSummary() has a defensive null guard if #struct-summary element is not found — safe for future layout changes
- renderWords() function left in codebase — only its call site in loadFile() replaced; function may still be referenced by tests or future code

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- VIEW-07 complete. Structured text rendering with VLM role styling is live.
- Phase 20 both plans complete. Phase 21 (TEI Export) can now begin — it depends on Phases 19+20 being complete.
- No blockers. The currentBlocks state and paraBlocks pipeline are stable for TEI export to consume.

---
*Phase: 20-structure-detection-and-viewer*
*Completed: 2026-03-02*
