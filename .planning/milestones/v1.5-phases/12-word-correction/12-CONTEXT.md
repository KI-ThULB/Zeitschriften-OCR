# Phase 12: Word Correction - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Inline word editing in the viewer's text panel: single-click a word → input field appears → type correction → Enter saves to ALTO XML (atomic write, XSD validation gate) → confirmation shown. Cancel, validation errors, and success feedback are all in-panel. No new server endpoints beyond the save action; no batch editing; no structural ALTO changes (word merge/split out of scope).

</domain>

<decisions>
## Implementation Decisions

### Edit trigger and cancel
- **Single click** on any word span in the text panel opens edit mode (not double-click)
- **Blur (click outside)** silently cancels: input closes, original OCR text is restored, no disk write
- **Escape key** always cancels: input closes, original text restored — standard keyboard UX
- **Clicking another word** while one is already in edit mode: cancel the in-progress edit silently, then open the newly clicked word — only one word editable at a time

### Save interaction model
- **Enter key** triggers save — no visible Save button needed
- **Input field width**: grows to match the word's natural width with a minimum of 60px (to ensure usability on single-character words)
- **Empty input blocks save**: if the user clears the field, show an inline error "Word cannot be empty" and keep the input open — do not attempt a write
- **Post-save focus**: return focus to the text panel (no specific element) — neutral reset, user chooses what to do next

### Validation error display
- **Location**: inline, directly below the input field — spatially connected to the action
- **Error persists**: as long as the input is open (until user saves successfully or cancels)
- **Input stays open and editable** after validation failure — user can fix the value and retry without re-clicking the word
- **Error message**: generic operator-friendly text — "Save failed — invalid content" — no raw XSD/lxml output

### Success confirmation
- **Style**: the word span briefly flashes a green background (~1 second CSS transition), then returns to normal — input is already closed at this point
- **No persistent edit marker**: corrected words are visually identical to uncorrected words after the flash fades
- **SVG bounding-box overlay**: hidden while the input is open for that word; restored (on the now-corrected word span) after save or cancel
- **Text panel update**: in-place DOM update only — the word span's text content updates to the corrected value; no page reload

### Claude's Discretion
- Exact CSS animation for the green flash (transition, keyframe, or class toggle)
- How the input integrates into the flowing text layout (inline-block, positioned replacement, etc.)
- Flask endpoint design for the save action (path, request format, response structure)
- lxml atomic write implementation (temp file + rename, or in-memory + overwrite with rollback)

</decisions>

<specifics>
## Specific Ideas

- The edit UX should feel natural within the flowing text panel — the input should not visually displace surrounding words dramatically
- Validation failure should never corrupt the ALTO XML on disk — the file must remain untouched if validation does not pass

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-word-correction*
*Context gathered: 2026-02-28*
