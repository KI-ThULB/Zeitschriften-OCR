---
phase: 12-word-correction
plan: 02
subsystem: ui
tags: [javascript, css, fetch, alto-xml, inline-edit, flask, viewer]

# Dependency graph
requires:
  - phase: 12-word-correction/12-01
    provides: POST /save/<stem> endpoint for atomic ALTO word correction
  - phase: 10-tiff-and-alto-data-endpoints
    provides: GET /alto/<stem> ALTO JSON endpoint with word_id indexing
  - phase: 11-side-by-side-viewer-ui
    provides: templates/viewer.html with renderWords(), selectWord(), SVG overlay
provides:
  - Inline word edit UX in templates/viewer.html (editWord, cancelEdit, saveWord)
  - CSS: .word-input, .word-error, @keyframes flash-green, .word-saved
  - Complete operator correction workflow: single-click to open, Enter to save, blur/Escape to cancel
affects: [future-alto-editing, phase-13-and-beyond]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "editingSpan guard: module-level state variable prevents multiple simultaneous edits"
    - "setTimeout(0) blur deferral: lets onclick cancelEdit() fire before blur handler to avoid double-cancel"
    - "void span.offsetWidth reflow trick: forces CSS animation restart for re-edit of same word"
    - "animationend {once:true} listener: cleans up .word-saved class after green flash completes"

key-files:
  created: []
  modified:
    - templates/viewer.html

key-decisions:
  - "editingSpan module-level variable tracks the currently open input — single check prevents multiple concurrent edits"
  - "blur handler uses setTimeout(0) to defer cancel, allowing onclick on a new word to run first and cancel the previous edit cleanly"
  - "cancelEdit() called at top of loadFile() to silently close any in-progress edit when user switches files"
  - "clearHighlight() called on edit open, showHighlight() called on edit close (save or cancel) — SVG overlay hidden during text input"
  - "Existing setupKeyboard() INPUT guard (tagName==='INPUT') already prevents ArrowLeft/ArrowRight file switching during text entry"

patterns-established:
  - "Inline edit pattern: replace span content with input → listen for Enter/Escape/blur → restore or commit"
  - "Green flash pattern: remove class → force reflow via offsetWidth → re-add class → clean up on animationend"

requirements-completed: [EDIT-01, EDIT-02, EDIT-04]

# Metrics
duration: ~5min (including checkpoint)
completed: 2026-02-28
---

# Phase 12 Plan 02: Word Correction UI Summary

**Inline word-edit UX in viewer.html: single-click to edit, Enter-to-save via POST /save/<stem>, blur/Escape cancel, green flash on success, inline error display**

## Performance

- **Duration:** ~5 min (including human-verify checkpoint)
- **Started:** 2026-02-28
- **Completed:** 2026-02-28
- **Tasks:** 2 (1 auto, 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments
- editWord(), cancelEdit(), saveWord() functions added to templates/viewer.html
- Single click on any .word span opens an inline input pre-filled with current OCR text
- Enter triggers saveWord() which POSTs to /save/<stem> and on 200 updates span text in-place with green flash
- Escape or blur cancels edit silently, restoring original word text with no server call
- Only one word editable at a time via editingSpan module-level guard
- Empty/whitespace input blocked with "Word cannot be empty" inline error — no server call
- Server error (non-200) shows "Save failed — invalid content" inline; input stays open for correction
- SVG highlight hidden during edit, restored after save or cancel
- File switch while editing cancels the edit cleanly before loading the new file
- All 7 browser UX checks confirmed by operator

## Task Commits

Each task was committed atomically:

1. **Task 1: Add inline edit CSS classes and JS functions to viewer.html** - `99788e0` (feat)
2. **Task 2: Human verify Phase 12 word correction UX in browser** - checkpoint approved (no commit)

**Plan metadata:** *(docs commit follows)*

## Files Created/Modified
- `templates/viewer.html` - Added .word-input/.word-error CSS, flash-green keyframe animation, editingSpan state variable, editWord()/cancelEdit()/saveWord() functions, updated panel.onclick handler, loadFile() edit cancel guard

## Decisions Made
- `editingSpan` module-level variable: the cleanest way to enforce single-edit-at-a-time — one null check in onclick is all that's needed
- `setTimeout(0)` in blur handler: necessary to let onclick fire first on word-to-word transitions; without it blur fires before the new word's onclick, causing a double-cancel visual glitch
- `void span.offsetWidth` reflow: required to restart the CSS animation if the same word is saved twice in quick succession; otherwise the browser skips the second animation
- `loadFile()` guard: `if (editingSpan) cancelEdit()` at the top of loadFile() is the minimal change to handle file-switch-while-editing without restructuring the function

## Deviations from Plan

None - plan executed exactly as written. All CSS, JS, and handler changes matched the plan specification.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 12 (Word Correction) is complete: POST /save/<stem> backend (Plan 01) + inline edit UX (Plan 02) both shipped and verified
- The full operator correction workflow is live: click word, edit, save, see green flash, XML on disk is updated atomically
- Ready for Phase 13 (next milestone v1.5 phase)

---
*Phase: 12-word-correction*
*Completed: 2026-02-28*
