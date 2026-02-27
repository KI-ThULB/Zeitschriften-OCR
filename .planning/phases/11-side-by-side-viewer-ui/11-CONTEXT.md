# Phase 11: Side-by-Side Viewer UI - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

A two-panel viewer HTML page served by Flask: TIFF image (left panel) with an SVG overlay, OCR words as flowing prose (right panel), a file browser sidebar, bidirectional click cross-reference, resize-safe overlay, and previous/next navigation. No word editing — that is Phase 12.

</domain>

<decisions>
## Implementation Decisions

### File List Design
- Left sidebar positioned above the TIFF image panel — persistent, always visible
- Filename only per list item — no word count or timestamps
- Data source: new `GET /files` endpoint returning stems of all `alto/*.xml` files in the output directory
- Active file indicated by highlighted row with a distinct background color (CSS active class toggle)

### Text Panel Word Display
- Flowing prose — words rendered as inline `<span>` elements that wrap naturally
- Default word state: plain text, `cursor: pointer` on hover — no underline or background decoration
- Selected word state: bold + yellow background highlight — one word selected at a time
- Clicking a word also scrolls the image panel so the SVG bounding box is visible in the viewport

### SVG Overlay Behavior
- Highlight rectangle appears on click only — no hover preview
- Style: semi-transparent yellow fill + orange stroke
- Bidirectional: clicking the SVG rectangle on the image scrolls to and highlights the corresponding word in the text panel
- On browser resize: recompute scale factors from live rendered image dimensions (ResizeObserver or window.onresize), redraw overlay in-place — no clearing required

### Navigation UX
- Previous/Next buttons placed above the two-panel area, centered
- Keyboard: Left/Right arrow keys — guard against firing when focus is inside an input element (future Phase 12 correction field)
- At first file: Previous button disabled (grayed out); at last file: Next button disabled
- On file change: both panels scroll to top, SVG overlay cleared

### Claude's Discretion
- CSS layout (flexbox vs grid for the three-column layout: sidebar + image + text)
- Exact colors for active file highlight, selected-word background, and SVG fill/stroke
- HTML structure for the SVG overlay (absolute-positioned `<svg>` layered over the `<img>`)
- How `GET /files` sorts the returned stem list (alphabetical recommended)
- Whether to use vanilla JS or a micro-library

</decisions>

<specifics>
## Specific Ideas

- The SVG overlay must use scale factors computed as `scale_x = img.naturalWidth ? img.clientWidth / page_width : 1` so bounding boxes land correctly at any rendered size
- Left/Right arrow guard: `if (document.activeElement.tagName === 'INPUT') return` before handling navigation

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-side-by-side-viewer-ui*
*Context gathered: 2026-02-27*
