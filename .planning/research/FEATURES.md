# Feature Research: ALTO XML Web Viewer with Post-Correction

**Domain:** Local OCR post-correction tool — side-by-side TIFF viewer + ALTO XML word editor
**Researched:** 2026-02-27
**Confidence:** MEDIUM (web/network research unavailable; based on training-data knowledge of reference tools + direct analysis of this codebase's ALTO structure)

---

## Reference Tool Analysis

### KBNL alto-editor (Koninklijke Bibliotheek, Netherlands)
ALTO XML browser-based editor. Key observed patterns (MEDIUM confidence — training data):
- Renders ALTO Word elements as clickable overlays on top of a scan image
- Text panel lists words in reading order; clicking a word scrolls and highlights the corresponding bounding box
- Editing is word-by-word: click to focus, type replacement, save
- Does NOT attempt to reflow or re-layout; only CONTENT attribute is edited
- Single-file focus: one XML + one image at a time

### eScriptorium (EPHE/INRIA)
Full HTR/OCR training and correction platform. Key observed patterns (MEDIUM confidence — training data):
- Line-level correction is the primary interaction; word-level is secondary
- Image and text panels are synchronized via line ID cross-reference
- Clicking a line in text panel scrolls the image to that line and draws a polygon
- Text is edited inline; changes are written back to transcription model, not raw XML
- Multi-user, server-based — very different deployment model from local Flask

### Transkribus (READ-COOP)
HTR training + correction platform. Key observed patterns (MEDIUM confidence — training data):
- Word-level bounding boxes are supported; click word → bounding box highlights in image
- Text panel shows plain text with word tokens; bounding boxes are drawn as colored rectangles
- Editing: double-click word token → inline editor appears → save pushes back to server
- Navigation: previous/next page buttons; thumbnail sidebar for file selection
- Export formats include ALTO, PAGE XML; correction edits only the CONTENT attribute (not coordinates)

### PRImA ALTOVIEWER
Desktop Java tool for ALTO XML inspection. Key observed patterns (MEDIUM confidence — training data):
- Two-panel view: scan image on left, ALTO structure tree on right
- Clicking a node in tree highlights corresponding region on image
- Read-only viewer — does not support editing

### Observation Across All Tools

**What works universally:**
- Synchronized scroll: text panel and image panel stay coupled so the user always sees the same region in both
- Word box overlays drawn on the image at reduced opacity (e.g., 30% fill, visible border)
- Click-to-select: clicking either the word in text or the box on image selects the same word in both panels
- Inline text editing: typing directly over the word token (not in a separate dialog)
- Non-destructive save: XML file is modified in place; coordinates and structure are preserved; only CONTENT attribute changes

**What frustrates users:**
- Coordinate-only views (no readable text panel) — operators must mentally map boxes to words
- Modal edit dialogs that break reading flow — clicking a word should immediately enable editing, not open a popup
- Auto-save without confirmation — lost edits if operator mis-types and navigates away
- Slow image load — archival TIFFs are large; rendering must be deferred to a JPEG/PNG proxy at viewport resolution
- No visual distinction between high-confidence and low-confidence words — everything looks the same, forcing operators to read every word
- Locked layout — split cannot be resized; operators with wide monitors want more image space, operators correcting text want more text space
- No keyboard navigation — mouse-only correction is slow; operators expect Tab to advance to next word

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a local ALTO post-correction viewer must have to be usable. Missing any of these makes the tool feel broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Side-by-side TIFF + text layout | All reference tools use this layout; operators expect the image and text to be visible simultaneously | LOW | Fixed 50/50 split is acceptable for MVP; resizable is a differentiator |
| TIFF rendered as JPEG/PNG proxy | Raw TIFF cannot be sent to a browser; 117–240 MB files must be converted on-the-fly | MEDIUM | Flask endpoint: convert TIFF → JPEG at 1500–2000px max width using Pillow; do NOT cache the full decompressed TIFF in memory between requests |
| Word bounding boxes drawn on image | If you can see text but not boxes, you can't verify OCR placement | MEDIUM | SVG overlay or `<canvas>` on top of `<img>`; coordinates from ALTO HPOS/VPOS/WIDTH/HEIGHT |
| Coordinates in pixel units for rendering | ALTO stores coordinates in the same pixel space used by the original TIFF; web viewer renders a scaled JPEG, so coordinates must be scaled by `(rendered_width / original_width)` | MEDIUM | This is a correctness requirement, not a feature; wrong scaling makes all boxes wrong |
| Click word in text → highlight box on image | Core interaction; without it the tool is just a PDF reader next to XML | MEDIUM | Requires word ID cross-reference; ALTO `String` elements have `ID` attribute (e.g., `w_1_1_1`) — use these as DOM data attributes |
| Click box on image → highlight word in text | Inverse selection; operators scan the image and want to jump to the corresponding text | MEDIUM | Same cross-reference; requires hit-testing on `<canvas>` or SVG click events |
| Inline word editing | Click a word in text panel → it becomes an `<input>` → operator types correction → saves | MEDIUM | Single-field inline editor; do NOT use a modal dialog |
| Save correction to ALTO XML | Edits must persist back to the XML file on disk; CONTENT attribute of the `String` element updated | MEDIUM | Flask POST endpoint: parse XML, find element by ID, update CONTENT, write back; validate no structural corruption |
| File browser / processed file list | Operators need to navigate between processed TIFFs; without a list the tool is one-shot only | LOW | Simple `<ul>` of filenames from `output/alto/`; clicking loads TIFF + XML pair |
| Drag-and-drop TIFF upload | Core v1.4 requirement; operators expect this as the entry point | MEDIUM | HTML5 `dragover` + `drop` events; POST to Flask; store in upload queue |
| OCR trigger from UI | Operator uploads TIFF, then clicks "Process" — triggers `pipeline.py` subprocess | MEDIUM | Flask endpoint spawns subprocess; returns job ID; client polls for completion |
| Live progress during OCR | File count, percentage, ETA — same data the CLI ProgressTracker produces | MEDIUM | Server-Sent Events (SSE) or polling endpoint; existing `ProgressTracker` class emits to stderr, web layer needs to capture stdout/stderr and relay |
| Error display | If OCR fails, the operator must see a clear error message, not a silent failure | LOW | Display stderr from subprocess; do not hide failures |

### Differentiators (Valued But Not Expected)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Resizable split panel | Operators with large monitors want more image space; correctors want more text space | LOW | CSS `flex` with a draggable divider; JS resize handler |
| Zoom/pan on image | Archival TIFFs are dense; operators need to zoom in on a word region | MEDIUM | CSS `transform: scale()` with mouse-wheel or pinch; pan via drag; alternative: Leaflet.js which handles tiles natively |
| Keyboard navigation (Tab to next word) | Tab advances to next uncorrected word; Shift+Tab goes back; Enter saves current edit | MEDIUM | Substantially speeds up correction workflow; reference tools that have this are noticeably faster to use |
| Word confidence coloring | If Tesseract provides WC (word confidence) attribute in ALTO, shade words by confidence — red for low, green for high | MEDIUM | Tesseract `image_to_alto_xml` does include WC attribute; parsing it is LOW complexity; rendering as CSS color is LOW; displaying it usefully is the MEDIUM part |
| "Jump to next unreviewed word" | A workflow button that advances to the next word that has not been confirmed — enables systematic correction | MEDIUM | Requires client-side state tracking of confirmed/unconfirmed words; no persistence needed (resets on page reload) |
| Undo last correction | Ctrl+Z reverts the most recent CONTENT edit before the next save | LOW | Client-side state only; keep a one-level edit history per session; do NOT implement full multi-level undo (server-side complexity) |
| Thumbnail sidebar | Miniature previews of all processed files for quick visual navigation | HIGH | Requires generating thumbnails at startup or on demand; adds significant UI complexity; not worth it for MVP |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-save on every keystroke | Feels responsive; no "save" step | Network round-trip per keystroke; concurrent saves corrupt XML if two requests arrive out of order; operators making typos trigger saves of garbage text | Save on blur (when operator clicks away from the word field) or on explicit Enter/Tab key; single POST per word |
| Real-time multi-user collaboration | Multiple operators correcting simultaneously | Requires server-side locking or operational transform; far beyond scope of a local single-operator tool; out of scope per PROJECT.md | This is a single-user local tool; document this clearly; do not build locking infrastructure |
| Batch text export (plain text dump) | Operators want to copy all OCR text for reuse | Encourages treating ALTO as a text container rather than a layout document; the downstream use is Goobi/Kitodo fulltext, not raw text files | Export is handled at the Goobi ingest level; out of scope for this tool |
| Re-run OCR on selected word region | Operator draws a box, re-OCRs just that region, gets a better word hypothesis | Requires Tesseract region-mode call, coordinate remapping back to full ALTO, and merging partial output — very high complexity for uncertain quality gain | Inline manual correction is the right UX for word-level errors; re-OCR is overkill |
| Coordinate editing | Operators adjust bounding box positions by dragging | Extremely complex (drag handles, coordinate remapping, ALTO rewrite); coordinates are rarely wrong in isolation — when a box is wrong, the word content is also wrong | Correct the CONTENT; coordinate errors are a pipeline bug, not an operator correction task |
| Authentication / user accounts | Seems like good practice | This is a local tool (`localhost`); adding auth adds complexity with zero security benefit in a single-user local context; PROJECT.md explicitly calls it local-only | Document "run `python app.py` and open localhost"; do not add auth |
| ALTO structural editing (merge/split words) | Operators want to merge two incorrectly split words | Requires rewriting TextLine structure, renumbering IDs, recalculating coordinates — ALTO structural edits are fundamentally different from CONTENT edits | Out of scope; CONTENT correction covers 95% of operator needs; structural issues are pipeline-level problems |
| WebSocket-based live sync | Feels modern | Adds `flask-socketio` dependency and async complexity; SSE or polling is sufficient for the progress use case | Use SSE or simple polling for progress; no WebSocket needed |

---

## Feature Dependencies

```
[TIFF file upload]
    └──requires──> [Flask file receive endpoint]
                       └──requires──> [Upload storage location (temp dir)]

[OCR trigger from UI]
    └──requires──> [TIFF file in upload queue]
    └──requires──> [pipeline.py subprocess invocation]
                       └──requires──> [Progress capture from subprocess stdout/stderr]
                                          └──required by──> [Live progress display (SSE or poll)]

[File browser]
    └──requires──> [output/alto/ directory exists and contains XML files]

[TIFF image viewer]
    └──requires──> [TIFF → JPEG conversion endpoint]
    └──requires──> [ALTO XML parsed for Page WIDTH/HEIGHT]

[Word bounding boxes on image]
    └──requires──> [ALTO XML parsed for String HPOS/VPOS/WIDTH/HEIGHT]
    └──requires──> [Coordinate scaling: pixel → rendered-image space]
    └──requires──> [TIFF original dimensions known to Flask]

[Click word → highlight box]
    └──requires──> [Word bounding boxes on image]
    └──requires──> [Word ID cross-reference: String @ID attribute in ALTO]

[Click box → highlight word in text]
    └──requires──> [Word bounding boxes on image]
    └──requires──> [Same Word ID cross-reference]

[Inline word editing]
    └──requires──> [Click word → highlight box] (for context)
    └──requires──> [Word ID cross-reference] (to know which ALTO element to update)

[Save correction to ALTO XML]
    └──requires──> [Inline word editing]
    └──requires──> [Flask POST endpoint: parse XML, find String by ID, update CONTENT, write]

[Word confidence coloring]
    └──requires──> [ALTO XML parsed for String @WC attribute]
    └──enhances──> [Click word → highlight box] (visual priority guidance)

[Keyboard navigation (Tab)]
    └──enhances──> [Inline word editing]
    └──requires──> [Word ordering known to client (reading order list)]
```

### Dependency Notes

- **Coordinate scaling is a correctness gate:** All visual features (bounding boxes, click-to-select, highlight) break if coordinate scaling is wrong. This must be implemented and verified before any word interaction feature is built.

- **Word ID (String @ID) is the cross-reference key:** ALTO `String` elements have an `ID` attribute (e.g., `w_1_1_1`) generated by Tesseract. This ID is the DOM `data-word-id` on both the text token and the SVG/canvas overlay rect. Without it, click-to-select requires expensive coordinate hit-testing on every click.

- **TIFF → JPEG proxy is a blocker for everything:** The browser cannot display a 200 MB TIFF. The Flask image-serving endpoint must exist before any visual feature can be built or tested.

- **OCR trigger depends on existing pipeline, not new code:** `pipeline.py` already handles all OCR logic. The web layer only needs to spawn it as a subprocess and capture its output. Do NOT rewrite the OCR logic in the web layer.

- **Save must be atomic:** Same pattern as `pipeline.py`'s existing output write: write to `.xml.tmp`, rename to `.xml`. A crash mid-save must not corrupt the XML file on disk.

---

## ALTO 2.1 Structure Reference (This Codebase)

The ALTO XML produced by `pipeline.py` uses these elements relevant to the viewer:

```xml
<alto xmlns="http://schema.ccs-gmbh.com/ALTO">
  <Layout>
    <Page WIDTH="4961" HEIGHT="7016" ...>
      <PrintSpace>
        <TextBlock>
          <TextLine>
            <String ID="w_1_1_1"
                    HPOS="142" VPOS="89"
                    WIDTH="312" HEIGHT="48"
                    CONTENT="Zeitschrift"
                    WC="0.96" />
            <SP />
            <String ID="w_1_1_2" ... CONTENT="für" WC="0.91" />
          </TextLine>
        </TextBlock>
      </PrintSpace>
    </Page>
  </Layout>
</alto>
```

**Key attributes for the viewer:**
- `Page/@WIDTH`, `Page/@HEIGHT` — original TIFF pixel dimensions (needed for coordinate scaling)
- `String/@ID` — unique word identifier; use as the cross-reference key between text panel and image overlay
- `String/@HPOS`, `@VPOS` — top-left corner of word bounding box in original TIFF pixel coordinates
- `String/@WIDTH`, `@HEIGHT` — bounding box dimensions in pixels
- `String/@CONTENT` — the OCR-recognized text; the only attribute that should be edited
- `String/@WC` — word confidence score (0.0–1.0); available for confidence coloring

**Coordinate system note:** The coordinates in this project's ALTO output are already offset by the crop box (see `build_alto21()` — crop_x added to HPOS, crop_y added to VPOS). This means coordinates are relative to the **original uncropped TIFF**, not the intermediate cropped image. The web viewer must render the original TIFF (not a cropped version) and use these coordinates directly.

---

## MVP Definition

### Launch With (v1.4 as specified in PROJECT.md)

These are the exact v1.4 requirements from PROJECT.md, mapped to implementation:

- [x] **Drag-and-drop TIFF upload** — HTML5 drop zone → Flask file receive endpoint → store in upload queue folder
- [x] **OCR trigger from UI with live progress** — "Process" button → Flask spawns `pipeline.py` subprocess → SSE endpoint streams stdout lines → client updates progress bar
- [x] **File browser** — list of ALTO XML stems from `output/alto/`; clicking loads that file pair
- [x] **Side-by-side TIFF + text viewer** — TIFF served as JPEG proxy; text extracted from ALTO `String/@CONTENT` in reading order
- [x] **Click word → highlight box** — word ID cross-reference; SVG/canvas overlay; coordinate scaling
- [x] **Inline word editing + save to ALTO XML** — contenteditable or `<input>`; Flask POST endpoint updates `String/@CONTENT` by ID; atomic file write

### Add After Validation (v1.4.x)

- [ ] **Resizable split panel** — trivial CSS addition once layout is stable
- [ ] **Word confidence coloring** — parse `@WC`, apply CSS color gradient; adds useful visual priority
- [ ] **Keyboard navigation (Tab to next word)** — significantly speeds up systematic correction; add when operators report correction is too slow
- [ ] **Zoom/pan on image** — needed when words are small relative to viewport; add if operators report difficulty clicking small words
- [ ] **Undo last correction (Ctrl+Z)** — client-side one-level undo; add when operators report accidental edits

### Future Consideration (v2+)

- [ ] **Thumbnail sidebar** — visual file navigation; HIGH implementation cost for LOW workflow gain at the scale of this tool (hundreds of files)
- [ ] **"Jump to next unreviewed word"** — useful for systematic correction passes; requires client-side state; defer until correction workflow is validated
- [ ] **Batch correction mode** — correct the same word across all files (e.g., a systematic OCR error on "ü" → "u") — very useful for archival German but requires full-corpus search, not single-file scope

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| TIFF → JPEG proxy endpoint | HIGH | MEDIUM | P1 — everything blocks on this |
| Coordinate scaling (pixel → rendered) | HIGH | LOW | P1 — correctness gate |
| Word bounding box overlay (SVG/canvas) | HIGH | MEDIUM | P1 |
| Click word ↔ highlight box (cross-reference) | HIGH | MEDIUM | P1 |
| Inline editing + save to ALTO XML | HIGH | MEDIUM | P1 |
| File browser | HIGH | LOW | P1 |
| Drag-and-drop upload | HIGH | MEDIUM | P1 |
| OCR trigger + live progress | HIGH | MEDIUM | P1 |
| Resizable split panel | MEDIUM | LOW | P2 |
| Word confidence coloring (WC attribute) | MEDIUM | LOW | P2 |
| Keyboard navigation (Tab) | HIGH | MEDIUM | P2 |
| Zoom/pan on image | MEDIUM | MEDIUM | P2 |
| Undo (Ctrl+Z, one level) | MEDIUM | LOW | P2 |
| Thumbnail sidebar | LOW | HIGH | P3 |
| Re-run OCR on word region | LOW | HIGH | P3 |
| ALTO structural editing | LOW | VERY HIGH | Never |

---

## Competitor Feature Analysis

| Feature | KBNL alto-editor | eScriptorium | Transkribus | This Tool (v1.4) |
|---------|-----------------|--------------|-------------|-----------------|
| Deployment model | Browser, server | Browser, server | Browser, SaaS | Local Flask, localhost |
| Image rendering | Scaled image | Tiled (OpenLayers) | Scaled image | JPEG proxy (Pillow) |
| Word-level box overlay | Yes | Line-level primary | Yes | Yes (SVG/canvas) |
| Click-to-select | Yes | Yes | Yes | Yes |
| Inline editing | Yes | Yes | Yes | Yes |
| Save to ALTO | Yes | Export only | Export only | Yes (direct file write) |
| Confidence visualization | No | No | Yes | Yes (WC attribute available) |
| Keyboard navigation | Limited | No | No | P2 (add after MVP) |
| Coordinate editing | No | No | No | No (anti-feature) |
| Multi-file workflow | Limited | Yes | Yes | File browser (simple) |
| Authentication | None (local) | Yes | Yes | None (local-only) |

---

## UX Patterns That Work vs. Frustrate

### Patterns That Work (implement these)

**Synchronized highlighting without lag.** When the operator clicks a word token in the text panel, the bounding box on the image highlights immediately (client-side JS; no server round-trip). The image scrolls to make the box visible if it is off-screen. The scroll must use `scrollIntoView({behavior: 'smooth', block: 'center'})` — instant scroll is disorienting on large images.

**Immediate editability.** Clicking a word in the text panel makes it editable immediately (no double-click, no toolbar button). The word token becomes an `<input>` pre-filled with the current CONTENT value. Tab moves to the next word and saves the current one. Enter saves the current one without advancing. Escape reverts to the original value. This is the standard contenteditable pattern from browser-based editors.

**Non-destructive save.** The ALTO file is written atomically (`.xml.tmp` then rename). Operators must be able to re-run OCR (`--force`) on a corrected file without losing their corrections — but for v1.4, the scope is one-direction (OCR → correct; correct → export). Clarify in UI: "Re-running OCR will overwrite your corrections."

**Low-opacity word box fill.** The bounding boxes should be drawn with 20–30% opacity fill and a 1px colored border. Full-opacity fill obscures the scan image. No fill (border only) is hard to see on complex scan backgrounds. 20–30% is the consensus across reference tools.

**Image-first layout.** The image panel takes ~60% of the viewport width; the text panel takes ~40%. Operators are primarily verifying the image; the text panel is the correction surface. Most reference tools use this ratio. Resizable split (P2) lets operators adjust.

### Patterns That Frustrate (avoid these)

**Modal edit dialogs.** Every reference tool that used a "click word → dialog appears → type → click Save" workflow has been revised or abandoned. The round-trip interrupts reading flow. Inline editing is the correct pattern.

**No visual feedback during save.** After clicking Save or pressing Tab, the operator needs confirmation that the edit was persisted. A brief flash (green background on the word token for 300ms) is sufficient. A toast notification is too heavyweight.

**Image loading blocking text display.** The text panel should render immediately from the ALTO XML (which is small). The image loads separately. If the image takes 2 seconds to convert and serve, the operator should see the text panel immediately and the image appearing afterward. Do not block text rendering on image loading.

**Coordinates wrong after image zoom.** If the operator zooms the image, bounding box coordinates must scale accordingly. This requires computing the current rendered image dimensions (not just the CSS zoom) and recalculating box positions. This is a common implementation mistake — overlays drawn at static coordinates become misaligned on zoom.

---

## Dependencies on Existing Pipeline Features

| Existing Feature | How Web Viewer Depends On It |
|-----------------|------------------------------|
| `pipeline.py` subprocess | Web viewer spawns it directly; does not reimplement OCR |
| `ProgressTracker` (stderr output) | Web layer must capture stderr lines and relay via SSE; existing format is `\r` overwrite-style — convert to discrete SSE events per file completion |
| `output/alto/<stem>.xml` file layout | File browser lists `output/alto/`; TIFF path inferred as `<input_dir>/<stem>.tif` — requires input dir to be known to the web app |
| ALTO `String/@ID` attribute | Critical for word cross-reference; Tesseract generates these; verify they are stable across runs (they are: based on block/line/word numbering) |
| ALTO `Page/@WIDTH`, `@HEIGHT` in pixels | Used for coordinate scaling; already present in output from this pipeline |
| ALTO `String/@WC` (word confidence) | Available in Tesseract ALTO output; used for confidence coloring (P2) |
| Atomic output write (`.xml.tmp` → `.xml`) | Web viewer save must use same pattern to prevent corruption |

---

## Sources

- **KBNL alto-editor** (training data, MEDIUM confidence): Open-source browser ALTO editor by Koninklijke Bibliotheek. Word-level editing, SVG overlay pattern, ID cross-reference.
- **eScriptorium** (training data, MEDIUM confidence): HTR platform; line-level correction model, synchronized panels, inline editing.
- **Transkribus** (training data, MEDIUM confidence): HTR/OCR correction platform; word confidence visualization, keyboard navigation patterns.
- **PRImA ALTOVIEWER** (training data, MEDIUM confidence): Reference ALTO inspection tool; two-panel read-only viewer.
- **ALTO 2.1 specification** (HIGH confidence — this codebase's output): `String/@ID`, `@HPOS`, `@VPOS`, `@WIDTH`, `@HEIGHT`, `@CONTENT`, `@WC` attributes confirmed present in `pipeline.py` output.
- **PROJECT.md** (HIGH confidence): v1.4 feature requirements, out-of-scope constraints, platform decisions (Flask, local-only, no auth).
- **CLAUDE.md** (HIGH confidence): Pipeline architecture, ALTO coordinate system, namespace constants.

---
*Feature research for: ALTO XML Web Viewer with Post-Correction (v1.4)*
*Researched: 2026-02-27*
