# Phase 13: Upload UI and Live Progress - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

A new root page (GET /) with a drag-and-drop TIFF upload zone, a visible file queue, a Start button that triggers OCR via the existing Flask background worker, and a live per-file progress display fed by the SSE stream — unified into one page that transitions from queue → processing → results without a page reload. The viewer (/viewer/<stem>) and all existing endpoints are unchanged.

</domain>

<decisions>
## Implementation Decisions

### Page layout and upload zone
- **New dedicated page at GET /** — root URL becomes the upload/progress dashboard; the viewer stays at /viewer/<stem>; clean separation of concerns
- **Large dashed-border rectangle** with a folder/file icon and text "Drag TIFF files here or click to browse" — classic, immediately recognizable drop zone
- **Click anywhere in the zone opens a file picker** — supports both drag-and-drop and click-to-browse workflows
- **Drop zone always visible above the queue** — operator can keep adding files before hitting Start; never collapses

### Queue display and file removal
- **Simple list rows** — filename on the left, × remove button on the right; no extra columns
- **× button removes instantly** with no confirmation dialog — files haven't been processed, nothing to lose
- **Silent de-duplication** — if a filename already in the queue is dropped again, the second drop is ignored
- **Invalid (non-TIFF) files** appear briefly as a red error row with "Not a TIFF file", then auto-remove after 3 seconds — operator gets feedback without a dialog

### Progress display during OCR
- **Per-file rows** — each queued file transitions through three states: pending (grey), processing (spinner), done or error (icon)
- **Overall status line above the rows** — "3/10 files done — ETA 45s" — gives the big-picture view without scanning all rows
- **Start button disables and relabels to "Processing…"** while the batch is running; re-enables when the batch finishes
- **Failed files appear as error rows** — "✗ scan_001.tif — failed"; batch continues for other files (matches existing pipeline error isolation)
- **Status line hides after batch finishes**; results expand to fill the space

### Results list and viewer linking
- **Per-file rows become results in-place** — done rows transform into: "✓ scan_001.tif (1,234 words)" where the filename is a clickable link to /viewer/<stem>
- **Result row shows filename + word count** — word count confirms OCR ran and gives a quality signal; no processing time displayed
- **Back navigation: browser back button** — /viewer/<stem> is a separate page; no explicit "Back" link needed in the viewer
- **After batch: new batch without page reload** — drop zone stays active; dragging new files clears the old queue and builds a new one; Start re-enables; previous results remain visible until a new batch starts

### Claude's Discretion
- Exact CSS layout (flexbox vs. grid, spacing, colours for state indicators)
- Whether the new GET / route renders a new template (upload.html) or reuses viewer.html with conditional sections
- How the SSE stream events are structured (already exists in app.py from Phase 9 — planner reads the existing implementation)
- Spinner implementation (CSS animation vs. Unicode character)

</decisions>

<specifics>
## Specific Ideas

- The per-file row approach means the queue and results live in the same list — no separate "Results" section; the list is the single source of truth throughout the workflow
- The "3/10 files done — ETA 45s" status line mirrors what the CLI ProgressTracker already emits — SSE events likely carry this data

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-upload-ui-and-live-progress*
*Context gathered: 2026-03-01*
