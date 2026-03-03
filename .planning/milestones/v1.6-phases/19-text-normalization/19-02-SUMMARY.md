---
phase: 19-text-normalization
plan: 02
subsystem: ui
tags: [javascript, viewer, alto-xml, column-sort, hyphen-rejoin, confidence-threshold, localStorage]

# Dependency graph
requires:
  - phase: 19-01
    provides: blocks array (TextBlock geometry + word_ids) and per-word line_end boolean in GET /alto/<stem>
  - phase: 10-viewer
    provides: viewer.html base with renderWords(), loadFile(), wordById
provides:
  - normalizeWords() pipeline: columnSort() + rejoinHyphens() in viewer.html
  - clusterByHpos() helper for multi-column newspaper layout
  - applyConfidenceStyling() — opacity fading on .word[data-wc] spans, no re-render
  - Confidence threshold slider (range 0–1 step 0.05, localStorage-persisted)
  - wc-badge showing low-confidence word count
  - data-wc attribute on all word spans from renderWords()
affects:
  - 19-03 (any further text normalization can rely on normalized displayWords and confidence UI)
  - 20-struct (structured text export may use normalizeWords output ordering)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inner container pattern: #word-list inside #text-panel keeps persistent UI elements (slider) alive across panel refresh cycles"
    - "Display-only normalization: wordById always maps original IDs — displayWords is ephemeral, built per-file"
    - "applyConfidenceStyling mutates opacity on existing spans — no DOM rebuild from slider events"
    - "columnSort: full-width blocks (>60% page width AND hpos < 5% pageWidth) sorted top-to-bottom first; column blocks clustered by HPOS gap of 5% pageWidth, sorted left-to-right then top-to-bottom"

key-files:
  created: []
  modified:
    - templates/viewer.html

key-decisions:
  - "Used #word-list inner container to isolate word span injection from #wc-settings slider, so renderWords() panel.innerHTML does not destroy the persistent slider HTML"
  - "Implemented both tasks in one commit since applyConfidenceStyling() / wcThreshold are required by Task 1's loadFile() wiring — tasks are logically inseparable"
  - "Fallback: columnSort returns words unchanged when blocks is empty — single-column files work transparently"
  - "rejoinHyphens only joins when w.line_end AND w.content.endsWith('-') — strict guard prevents spurious joins on legitimate mid-word hyphens not at line end"

patterns-established:
  - "Slider persistence: const KEY = 'wc_threshold'; let val = parseFloat(localStorage.getItem(KEY) ?? '0.5'); — init pattern for localStorage-backed range inputs"
  - "Inner container pattern for persistent panel UI: wrap word spans in #word-list, leave controls outside"

requirements-completed: [TEXT-01, TEXT-02, TEXT-03]

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 19 Plan 02: Text Normalization Client Pipeline Summary

**Client-side column sort, hyphen rejoin, and confidence threshold slider added to viewer.html — multi-column OCR pages now display in left-column-first reading order with faded low-confidence words**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T16:51:49Z
- **Completed:** 2026-03-02T16:54:49Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Implemented normalizeWords() pipeline: columnSort() clusters TextBlocks by HPOS gap, sorts left-column-first; rejoinHyphens() uses line_end flag from Plan 01 to merge hyphenated word fragments
- Added applyConfidenceStyling() that mutates opacity on existing .word[data-wc] spans — no DOM rebuild on slider drag
- Added confidence threshold slider (#wc-settings) with localStorage persistence and real-time 'input' event; wc-badge shows live low-confidence word count
- Introduced #word-list inner container so the persistent slider HTML survives panel refresh cycles
- wordById unchanged: maps original data.words (not displayWords) — edit/save always operates on ALTO-original content
- All 136 pytest tests remain green

## Task Commits

Both tasks committed atomically as one cohesive unit (applyConfidenceStyling and wcThreshold are required by Task 1's loadFile() wiring):

1. **Task 1+2: normalizeWords pipeline, confidence slider, applyConfidenceStyling** - `7431029` (feat)

**Plan metadata:** (docs commit — see final_commit)

## Files Created/Modified
- `templates/viewer.html` — Added clusterByHpos(), columnSort(), rejoinHyphens(), normalizeWords(), applyConfidenceStyling(); added #word-list container, #wc-settings slider HTML; updated loadFile() and renderWords(); added WC_THRESHOLD_KEY / wcThreshold module state

## Decisions Made
- Used `#word-list` inner container inside `#text-panel` to prevent `renderWords()` from wiping the persistent `#wc-settings` slider. Without this, every file load (which sets `panel.innerHTML`) would destroy the slider.
- Implemented both tasks atomically since `applyConfidenceStyling()` and `wcThreshold` (Task 2) are called by `loadFile()` wiring (Task 1). Splitting would cause a JS ReferenceError in the loaded page.
- `columnSort()` fallback: if blocks is empty or falsy, returns words unchanged. Single-column files (ALTO without TextBlock elements) are handled transparently.
- `rejoinHyphens()` guard: joins only when `w.line_end && w.content.endsWith('-')`. This prevents spurious joins on em-dashes or mid-sentence hyphens that happen to be last on a line without a true compound split.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added #word-list inner container for slider persistence**
- **Found during:** Implementation review (Task 1+2)
- **Issue:** The plan placed #wc-settings as static HTML in #text-panel, but both `loadFile()` and `renderWords()` set `panel.innerHTML` which would destroy the slider on every file load
- **Fix:** Introduced `<div id="word-list">` inside `#text-panel`; updated renderWords() to target #word-list; updated loadFile() Loading/Error messages to target #word-list; #wc-settings remains outside word-list and persists
- **Files modified:** templates/viewer.html
- **Verification:** Slider element survives file switches; applyConfidenceStyling() finds it via getElementById after renderWords() runs
- **Committed in:** 7431029

---

**Total deviations:** 1 auto-fixed (Rule 2 - Missing Critical)
**Impact on plan:** Essential correctness fix. The plan's static HTML approach required an inner container to survive renderWords()'s innerHTML replacement. No scope creep.

## Issues Encountered
- renderWords() and loadFile() both use innerHTML = ... on #text-panel, which would destroy static child elements. Resolved by using an inner #word-list container pattern (documented as deviation above).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- normalizeWords() pipeline fully wired into loadFile()
- Confidence threshold slider working with localStorage persistence
- Plan 03 (if exists) can build on normalizeWords output or add further normalization passes
- No blockers

## Self-Check: PASSED
- templates/viewer.html: FOUND
- 19-02-SUMMARY.md: FOUND
- commit 7431029: FOUND

---
*Phase: 19-text-normalization*
*Completed: 2026-03-02*
