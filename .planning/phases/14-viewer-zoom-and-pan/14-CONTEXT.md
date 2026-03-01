# Phase 14: Viewer Zoom and Pan - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Mouse-wheel zoom centered on cursor position and click-drag pan on the TIFF image panel in the side-by-side viewer — with the SVG word bounding-box overlay staying pixel-accurate at all zoom levels and surviving window resizes. The text panel and word-correction flow are unchanged; this phase only affects the image panel interaction model.

</domain>

<decisions>
## Implementation Decisions

### Zoom limits and feel
- **Initial view:** Fit-to-panel-width on every file load (same as current behaviour)
- **Zoom range:** 25% – 400%; clamp at both ends
- **Zoom steps:** Continuous — each wheel tick scales by a small factor (e.g. ×1.1); trackpad pinch-zoom should feel natural
- **Double-click:** Not used for zoom; keeps interaction surface clean and avoids conflict with word single-click

### Pan vs click disambiguation
- **Disambiguation method:** Movement threshold — mousedown + move >5px = pan; mousedown + release without moving = click (word interaction). No modifier key required.
- **Cursor feedback:** `cursor: grab` on image hover; `cursor: grabbing` while actively dragging
- **Edit + pan:** If a word edit is open when pan starts, `cancelEdit()` fires first — consistent with the file-switch behaviour already in place
- **Pan bounds:** Soft clamp — at least ~20% of the image must remain visible in the panel at all times; can't drag the image completely off-screen

### Reset and navigation controls
- **Reset button:** Small overlay button on the image panel, visible only when zoomed away from fit-to-width; shows zoom percentage label alongside it (e.g. "150% ⊡")
- **Keyboard shortcuts:** `+` / `-` to zoom in/out; `0` to reset to fit-to-width
- **File switch:** Reset zoom and pan to fit-to-width on every file switch; each file starts fresh
- **Zoom indicator:** Percentage label displayed next to the reset button (only shown when not at default fit-to-width zoom)

### Overlay alignment strategy
- **Approach:** Wrap the `<img>` and `<svg>` overlay together inside a shared container div; apply `transform: scale() translate()` to the container — both move as one unit with no per-rect coordinate math
- **Highlight on zoom/pan:** Highlight rect moves with the image naturally (shared-container transform handles it); no auto-pan-to-highlight on word selection
- **Edit + zoom:** If a word edit input is open when the user scrolls (zooms), `cancelEdit()` fires — same rule as pan: any viewport transform clears the active edit

### Claude's Discretion
- Exact CSS transform origin and scale factor per wheel tick
- Momentum / inertia on drag release (or not)
- Exact reset button icon and positioning within the panel
- How zoom percentage rounds for display (nearest integer vs 5% steps)
- ResizeObserver hook placement to recompute fit-to-width on window resize

</decisions>

<specifics>
## Specific Ideas

- The shared-container transform approach means the SVG never needs coordinate recalculation — the overlay is always "inside" the transformed space alongside the image
- `cancelEdit()` on any viewport change (pan start or zoom) is the clean invariant: one rule covers both cases
- The fit button fading in only when zoomed keeps the default view uncluttered

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-viewer-zoom-and-pan*
*Context gathered: 2026-03-01*
