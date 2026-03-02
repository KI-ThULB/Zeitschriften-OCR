# Phase 19: Text Normalization - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the raw ALTO word stream into a clean, correctly-ordered text display in the viewer — multi-column pages sorted left-column-first, end-of-line hyphens rejoined, low-confidence words faded with a configurable threshold slider. All changes are display-only; the ALTO XML is never modified.

</domain>

<decisions>
## Implementation Decisions

### Confidence marking style
- Low-confidence words displayed at reduced opacity (≈40%) — faded, not colored, not underlined
- Hovering a faded word shows a tooltip with the ALTO @WC score, e.g. "Confidence: 0.42"
- Low-confidence word count shown as a badge in the sidebar (e.g. "23 low-confidence words")
- No hide toggle — fading only; hidden words break text flow

### Threshold control UX
- Confidence threshold slider lives in the right-side settings panel (existing panel, below article browser)
- Default threshold: 0.5 (WC < 0.5 → faded)
- Real-time display update as slider is dragged — no mouseup delay
- Threshold value persisted in localStorage so it survives page reloads and sessions
- No hide-words toggle — slider controls fade opacity threshold only

### Column detection
- Automatic HPOS clustering: group TextBlocks by horizontal position gaps to identify column bands, sort columns left-to-right, sort TextBlocks within each column by VPOS (top-to-bottom)
- Full-width TextBlocks (HPOS ≈ 0 and WIDTH > ~60% of page width) are placed first in output, before column content — treats them as headlines/headers matching natural newspaper reading order
- Single-column fallback: if clustering finds only one group, fall back to plain VPOS order with no change to current behavior
- No manual override in this phase — algorithm only; operator can consult TIFF image if order looks wrong

### Hyphenation rejoining
- Detect end-of-line hyphens only: a word is a rejoining candidate if the CONTENT of the last String element in a TextLine ends with "-" and a following TextLine exists
- Join unconditionally — operator verifies via TIFF image if a join looks wrong
- Mid-word compound hyphens (e.g. "Sozial-Demokrat") are preserved — only line-terminal hyphens are removed
- Display: show the clean rejoined form only; no tooltip, no marker, no original form on hover

### Claude's Discretion
- Exact opacity value for faded words (≈40% is the guide; exact CSS value Claude's choice)
- HPOS clustering algorithm specifics (gap threshold, minimum gap width as % of page width)
- Tooltip styling and positioning for the WC confidence value
- Badge styling and placement within the sidebar for the low-confidence word count

</decisions>

<specifics>
## Specific Ideas

- The confidence slider is in the existing right-panel (same panel as article browser) — no new UI surfaces needed
- The sidebar badge "23 low-confidence words" is per-file, updates when the file changes or when the threshold slider moves
- Column detection is purely JavaScript/Python on the ALTO word data — no VLM call, no server-side changes required (can be done entirely client-side using the existing `/alto/<stem>` response which already includes HPOS/VPOS/WIDTH/HEIGHT per word and per-block grouping)

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-text-normalization*
*Context gathered: 2026-03-02*
