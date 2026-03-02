# Phase 20: Structure Detection and Viewer - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Layer structural rendering onto the normalized word stream from Phase 19. Detect paragraph boundaries from ALTO line-spacing data, assign structural roles (heading/paragraph/caption/advertisement) from existing VLM article segmentation, and render the structure visually in the text panel — headings styled prominently, paragraphs separated by blank lines, captions and advertisements styled distinctly. All changes are display-only; ALTO XML is never modified. No new server endpoints needed.

</domain>

<decisions>
## Implementation Decisions

### Role label presentation
- Structural roles are communicated through visual styling only — no explicit badge, tag, or inline label before blocks
- Role count summary shown below the confidence badge in the right panel (e.g. "1 heading, 3 paragraphs, 1 caption")
- Summary updates on every `loadFile()` call, same lifecycle as the confidence badge
- No VLM/fallback distinction in the count — plain role counts only

### Paragraph break visual style
- Blank line gap between paragraph blocks (CSS margin-bottom on each `.para-block`)
- Paragraph boundary threshold: gap between successive TextLine VPOS values > 1.5× the median inter-line spacing within the block
- Every TextBlock boundary is always treated as a paragraph break regardless of spacing
- Detection is entirely client-side JavaScript using existing `/alto/<stem>` data (blocks, word VPOS) — no server changes

### Heading and role styling
- Headings: `font-weight: bold` + `font-size: 1.1em` (slightly larger)
- Captions: `font-size: 0.9em` + `font-style: italic`
- Advertisements: `font-size: 0.9em` + `font-style: italic` + subtle left border (e.g. `border-left: 3px solid #ccc; padding-left: 0.4em`)
- Paragraphs: default (no additional styling)
- Implementation: each block rendered as `<div class="para-block" data-role="heading|paragraph|caption|advertisement">`; CSS targets `[data-role=...]` selectors
- Structured display is permanent — no flat/structured toggle in this phase

### VLM role assignment and fallback
- Role assignment: for each TextBlock, compute overlap with each VLM article region; assign the role from the region with the greatest overlap
- Minimum overlap: max-overlap wins regardless of percentage (no minimum threshold)
- TextBlock with no overlapping VLM region: defaults to "paragraph" role
- No VLM data for page (page not yet segmented): paragraph breaks still shown from line-spacing, but all blocks get "paragraph" role — no heading styling, no heuristic detection
- No "Segment this page" prompt or special indicator when VLM data is absent

### Claude's Discretion
- Exact pixel/rem values for blank line gap between paragraphs
- Exact font-size multiplier (guide: ~1.1em for headings, ~0.9em for captions/ads)
- Exact border color and width for advertisement blocks
- How overlap area is computed (bounding box intersection logic already established in Phase 16 mets.py)

</decisions>

<specifics>
## Specific Ideas

- The role count summary lives in `#wc-settings` section or immediately below it in the right panel — adjacent to the confidence badge for a unified "page stats" area
- VLM article region data is already loaded via `loadSegments()` in `loadFile()` — role assignment can piggyback on `currentArticles` (already populated) without a new network call
- TextBlock HPOS/VPOS/WIDTH/HEIGHT is already in `data.blocks` from Phase 19's `serve_alto()` extension — no new API data needed

</specifics>

<deferred>
## Deferred Ideas

- Flat/structured toggle button — future phase
- Heuristic heading detection (for pages without VLM) — future phase if needed
- "Segment this page" prompt in text panel — future phase

</deferred>

---

*Phase: 20-structure-detection-and-viewer*
*Context gathered: 2026-03-02*
