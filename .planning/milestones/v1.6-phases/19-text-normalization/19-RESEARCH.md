# Phase 19: Text Normalization - Research

**Researched:** 2026-03-02
**Domain:** Client-side JavaScript text processing on ALTO word data — column sorting, hyphen rejoining, confidence fading
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Confidence marking style**
- Low-confidence words displayed at reduced opacity (≈40%) — faded, not colored, not underlined
- Hovering a faded word shows a tooltip with the ALTO @WC score, e.g. "Confidence: 0.42"
- Low-confidence word count shown as a badge in the sidebar (e.g. "23 low-confidence words")
- No hide toggle — fading only; hidden words break text flow

**Threshold control UX**
- Confidence threshold slider lives in the right-side settings panel (existing panel, below article browser)
- Default threshold: 0.5 (WC < 0.5 → faded)
- Real-time display update as slider is dragged — no mouseup delay
- Threshold value persisted in localStorage so it survives page reloads and sessions
- No hide-words toggle — slider controls fade opacity threshold only

**Column detection**
- Automatic HPOS clustering: group TextBlocks by horizontal position gaps to identify column bands, sort columns left-to-right, sort TextBlocks within each column by VPOS (top-to-bottom)
- Full-width TextBlocks (HPOS ≈ 0 and WIDTH > ~60% of page width) are placed first in output, before column content — treats them as headlines/headers matching natural newspaper reading order
- Single-column fallback: if clustering finds only one group, fall back to plain VPOS order with no change to current behavior
- No manual override in this phase — algorithm only; operator can consult TIFF image if order looks wrong

**Hyphenation rejoining**
- Detect end-of-line hyphens only: a word is a rejoining candidate if the CONTENT of the last String element in a TextLine ends with "-" and a following TextLine exists
- Join unconditionally — operator verifies via TIFF image if a join looks wrong
- Mid-word compound hyphens (e.g. "Sozial-Demokrat") are preserved — only line-terminal hyphens are removed
- Display: show the clean rejoined form only; no tooltip, no marker, no original form on hover

### Claude's Discretion
- Exact opacity value for faded words (≈40% is the guide; exact CSS value Claude's choice)
- HPOS clustering algorithm specifics (gap threshold, minimum gap width as % of page width)
- Tooltip styling and positioning for the WC confidence value
- Badge styling and placement within the sidebar for the low-confidence word count

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEXT-01 | User sees ALTO words delivered in correct multi-column reading order — left-to-right across columns (detected from TextBlock HPOS), then top-to-bottom within each column | TextBlock elements confirmed present in real ALTO files with HPOS/VPOS/WIDTH. Column sorting is pure JS on existing `/alto/<stem>` response data. |
| TEXT-02 | System detects and rejoins German end-of-line hyphenated words (e.g. "Ver-" + "bindung" → "Verbindung") for display in the text panel and TEI export, preserving the original split form in ALTO | Real ALTO files confirm hyphenated line-ends ("so-"+"wohl", "entgegen-"+"steht,"). Detection pattern: last String in a TextLine whose CONTENT ends with "-". Join is display-only — ALTO XML not modified. |
| TEXT-03 | User can configure a minimum word-confidence threshold; words below it are visually marked (e.g. faded) in the text panel so low-quality OCR regions are obvious at a glance | WC attribute already present per-word in `/alto/<stem>` JSON response as `confidence` float. CSS opacity + title attribute tooltip. Slider in existing `#text-panel` below article browser. |
</phase_requirements>

---

## Summary

Phase 19 is a **pure client-side JavaScript** phase. All three requirements (TEXT-01, TEXT-02, TEXT-03) operate entirely within the browser on data already delivered by the existing `/alto/<stem>` endpoint. No server changes are required and no new Python modules are needed. The ALTO XML is never modified.

The `/alto/<stem>` endpoint currently returns a flat word array in document order (XML iteration order). This phase adds a `normalizeWords()` pipeline function in the viewer JS that transforms the flat word list into a display-ready ordered-and-rejoined word list, and adds a confidence threshold slider to the text panel.

The real ALTO files on disk were inspected and confirm: (1) `TextBlock` elements are present with `HPOS`/`VPOS`/`WIDTH` attributes, enabling column clustering; (2) end-of-line hyphenated words occur in real data (e.g. "so-"/"wohl", "entgegen-"/"steht,"); (3) every `String` element carries a `WC` attribute that is already passed through as `confidence` in the API response. All prerequisites are satisfied.

The viewer currently renders words via `renderWords(data.words)` where `data.words` is the flat array from the API. This phase inserts a normalization step before rendering: `renderWords(normalizeWords(data.words, data.page_width))`. The normalization step is display-only — it does not write back to `wordById` (which is used for edit/highlight operations and must stay keyed on original word IDs). The confidence slider is added to the `#text-panel` section (below the article browser), with its threshold persisted in `localStorage`.

**Primary recommendation:** Add a single `normalizeWords(words, pageWidth)` function to viewer.html that handles column sort, hyphen rejoin, and confidence metadata in one pass, then add a confidence slider below the article list that triggers a re-render using the cached normalized word list.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS (ES2020+) | Browser native | Column sort, hyphen detection, DOM rendering | Already the project's entire frontend stack — no build tool, no framework |
| CSS opacity | Browser native | Confidence fading | Zero-dependency; real-time performance without DOM replacement |
| localStorage | Browser native | Threshold persistence | Already used in the project for similar viewer state |
| HTML `title` attribute | Browser native | WC tooltip on faded words | Works without a tooltip library; consistent with existing viewer patterns |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lxml (Python) | Already in requirements.txt | ALTO XML parsing in `/alto/<stem>` route | Already powers the endpoint — no change needed |
| Flask | 3.1 (already installed) | Serves existing `/alto/<stem>` | No changes required for this phase |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `title` attribute tooltip | Custom CSS/JS tooltip div | Custom tooltip gives finer styling control but adds JS complexity; `title` is sufficient for a confidence score readout |
| CSS `opacity` | CSS `color: rgba(...)` | Opacity fades the whole span including any background; color approach only desaturates text — both are valid, opacity chosen per decision |
| In-place word span style | Separate `<span class="faded">` wrapper | Setting `style.opacity` on the existing `.word` span is simpler and consistent with existing rendering |

**Installation:** No new packages required. All work is in `templates/viewer.html` and potentially a minimal addition to `app.py` for block-level data exposure.

---

## Architecture Patterns

### How the Existing Pipeline Works

The `/alto/<stem>` route in `app.py` currently iterates `root.iter(f'{{{ns}}}String')` — this is a flat document-order traversal that does NOT group by TextBlock. The response contains:

```json
{
  "page_width": 10114,
  "page_height": 7529,
  "jpeg_width": ...,
  "jpeg_height": ...,
  "words": [
    {"id": "w0", "content": "am", "hpos": 857, "vpos": 485, "width": 56, "height": 26, "confidence": 0.89},
    ...
  ]
}
```

The words do NOT include which TextBlock or TextLine they belong to. Column detection via HPOS clustering requires TextBlock-level data, which the current endpoint does not expose.

### Critical Finding: Block-Level Data Gap

**The `/alto/<stem>` response only has flat String-level words — it does not include TextBlock boundaries or HPOS/VPOS of the block.** Column detection needs TextBlock HPOS/WIDTH per word (or a separate block list). There are two implementation options:

**Option A: Add blocks array to `/alto/<stem>` response (recommended)**
Extend the existing endpoint to also return a `blocks` array alongside `words`:
```json
{
  "blocks": [
    {"id": "block_0", "hpos": 493, "vpos": 485, "width": 1677, "height": 437, "word_ids": ["w0","w1",...]}
  ],
  "words": [...],
  ...
}
```
The client-side `normalizeWords()` can then sort blocks by column band then VPOS, then flatten words in that order. This keeps all normalization client-side.

**Option B: Client-side re-parse via separate endpoint**
Serve raw ALTO XML to the client and parse it in JavaScript. This is heavier and inconsistent with the project pattern of JSON APIs.

**Recommendation: Option A** — extend `serve_alto()` in `app.py` to also return a `blocks` array. The change is minimal (add one `findall` call) and keeps all normalization client-side.

### Recommended Project Structure

No new files. All changes are confined to:
```
app.py                         # serve_alto(): add blocks array to response
templates/viewer.html          # normalizeWords(), renderWords(), confidence slider
```

### Pattern 1: Block Array Extension in serve_alto()

**What:** Add a `blocks` array to the `/alto/<stem>` JSON response, each block carrying its HPOS/VPOS/WIDTH/HEIGHT and the list of word IDs it contains.
**When to use:** Required for column detection — words need to be associated with their parent TextBlock geometry.

```python
# In serve_alto() in app.py — after the existing words loop:
blocks = []
for block_elem in root.findall(f'.//{{{ns}}}TextBlock'):
    block_word_ids = []
    for i, str_elem in enumerate(block_elem.iter(f'{{{ns}}}String')):
        # Need the global index — build a lookup from element identity to word id
        pass  # see implementation note below
```

Implementation note: the safest approach is a two-pass strategy:
1. First pass: iterate all String elements globally, build `elem_to_idx` dict keyed on element `id()`.
2. Second pass: iterate TextBlock elements, look up each child String's index in `elem_to_idx`.

This avoids re-parsing and is O(n) total.

### Pattern 2: normalizeWords() Client-Side Pipeline

**What:** A pure function `normalizeWords(words, blocks, pageWidth)` that returns a new ordered-and-rejoined display list.
**When to use:** Called once per file load, result stored in a module-level `displayWords` variable used by `renderWords()`.

```javascript
// Source: project-derived pattern, no external library

function normalizeWords(words, blocks, pageWidth) {
  // Step 1: Column sort
  const ordered = columnSort(words, blocks, pageWidth);

  // Step 2: Hyphen rejoin
  return rejoinHyphens(ordered);
}

function columnSort(words, blocks, pageWidth) {
  if (!blocks || blocks.length === 0) return words;  // fallback

  const FULL_WIDTH_THRESHOLD = 0.6;  // blocks wider than 60% of page = full-width

  // Separate full-width blocks (headlines) from column blocks
  const fullWidthBlocks = blocks.filter(b => b.width / pageWidth > FULL_WIDTH_THRESHOLD);
  const columnBlocks    = blocks.filter(b => b.width / pageWidth <= FULL_WIDTH_THRESHOLD);

  // Cluster column blocks by HPOS band
  const columns = clusterByHpos(columnBlocks);

  // Sort columns left-to-right, blocks within column top-to-bottom
  columns.sort((a, b) => a.centerHpos - b.centerHpos);
  columns.forEach(col => col.blocks.sort((a, b) => a.vpos - b.vpos));

  // Sort full-width blocks top-to-bottom
  fullWidthBlocks.sort((a, b) => a.vpos - b.vpos);

  // Build ordered word ID list
  const wordMap = Object.fromEntries(words.map(w => [w.id, w]));
  const orderedIds = [
    ...fullWidthBlocks.flatMap(b => b.word_ids),
    ...columns.flatMap(col => col.blocks.flatMap(b => b.word_ids)),
  ];

  // Deduplicate (words not in any block fall through; append at end)
  const seen = new Set(orderedIds);
  const remainder = words.filter(w => !seen.has(w.id)).map(w => w.id);
  return [...orderedIds, ...remainder]
    .map(id => wordMap[id])
    .filter(Boolean);
}

function clusterByHpos(blocks) {
  if (blocks.length === 0) return [];
  const sorted = [...blocks].sort((a, b) => a.hpos - b.hpos);
  const GAP_FRACTION = 0.05;  // gap > 5% of page width = column boundary
  // clusters is built dynamically — see implementation note
  // Returns [{centerHpos, blocks: [...]}, ...]
}
```

### Pattern 3: Hyphen Rejoin

**What:** Merge a word ending in "-" at the end of a TextLine with the first word of the following TextLine.
**Key constraint:** The detection must operate on the display-ordered word list (post column sort), grouping by TextLine.

The `/alto/<stem>` response does not include TextLine groupings — words are flat. Hyphen detection needs to know which word ends a TextLine.

**Detection approach using existing word data:** A word ends a TextLine when the next word has a substantially higher VPOS (vertical drop). For archival newspaper scans with consistent line spacing, a VPOS delta > ~50% of the word's own HEIGHT reliably separates lines. However, this heuristic can fail for large font sizes or footnotes.

**Cleaner approach: add line boundary metadata to the response.** Two sub-options:
- Add `line_end: true` flag to each word in the words array (server-side, one extra boolean per word)
- Add a `lines` array parallel to `blocks` (more data but more flexible)

**Recommendation:** Add `line_end: true` to each word in `serve_alto()`. This is a one-attribute addition and makes hyphen detection O(n) and unambiguous.

```python
# In serve_alto(), in the words loop:
# Track whether this String is the last String in its TextLine
all_strings = list(root.iter(f'{{{ns}}}String'))
last_in_line = set()
for tl in root.findall(f'.//{{{ns}}}TextLine'):
    tl_strings = list(tl.iter(f'{{{ns}}}String'))
    if tl_strings:
        last_in_line.add(id(tl_strings[-1]))

for i, elem in enumerate(all_strings):
    wc_raw = elem.get('WC')
    words.append({
        'id': f'w{i}',
        'content': elem.get('CONTENT', ''),
        'hpos': int(elem.get('HPOS', 0)),
        'vpos': int(elem.get('VPOS', 0)),
        'width': int(elem.get('WIDTH', 0)),
        'height': int(elem.get('HEIGHT', 0)),
        'confidence': float(wc_raw) if wc_raw is not None else None,
        'line_end': id(elem) in last_in_line,
    })
```

Then client-side rejoin:

```javascript
function rejoinHyphens(words) {
  const result = [];
  let i = 0;
  while (i < words.length) {
    const w = words[i];
    if (w.line_end && w.content.endsWith('-') && i + 1 < words.length) {
      const next = words[i + 1];
      // Remove trailing hyphen, concatenate with first word of next line
      const joined = { ...w, content: w.content.slice(0, -1) + next.content };
      result.push(joined);
      i += 2;  // consume both words
    } else {
      result.push(w);
      i += 1;
    }
  }
  return result;
}
```

Note: the joined word inherits the ID and coordinates of the first fragment. This is correct for click-to-highlight (the edit/highlight system uses `wordById` which is populated from `data.words`, not from the normalized display list).

### Pattern 4: Confidence Fading

**What:** Apply inline `style.opacity` to `.word` spans based on the word's `confidence` vs. the current threshold.
**Threshold:** Stored in `localStorage['wc_threshold']`, defaulting to `0.5`.

```javascript
const WC_THRESHOLD_KEY = 'wc_threshold';
let wcThreshold = parseFloat(localStorage.getItem(WC_THRESHOLD_KEY) ?? '0.5');

function applyConfidenceStyling(threshold) {
  document.querySelectorAll('.word[data-wc]').forEach(span => {
    const wc = parseFloat(span.dataset.wc);
    if (!isNaN(wc) && wc < threshold) {
      span.style.opacity = '0.4';
      span.title = `Confidence: ${wc.toFixed(2)}`;
    } else {
      span.style.opacity = '';
      span.title = '';
    }
  });
  updateLowConfidenceBadge(threshold);
}
```

Words are rendered with `data-wc` attribute so re-styling can be applied without re-rendering the entire word list:

```javascript
// In renderWords():
`<span class="word" data-id="${escapeHtml(w.id)}" data-wc="${w.confidence ?? ''}">${escapeHtml(w.content)}</span> `
```

### Pattern 5: Confidence Threshold Slider

**What:** An `<input type="range">` in the `#text-panel` below the article section.
**Where:** Appended to `#text-panel` after the article browser section (consistent with decision: right-side settings panel below article browser).

```html
<!-- Added inside #text-panel (via JS injection or static HTML) -->
<div id="wc-settings">
  <label style="font-size:0.78rem;color:#666;">
    Confidence threshold:
    <input type="range" id="wc-slider" min="0" max="1" step="0.05" value="0.5">
    <span id="wc-threshold-label">0.50</span>
  </label>
  <div id="wc-badge" style="font-size:0.78rem;color:#888;margin-top:2px;"></div>
</div>
```

The slider uses the `input` event (not `change`) for real-time updates as dragged:

```javascript
document.getElementById('wc-slider').addEventListener('input', (e) => {
  wcThreshold = parseFloat(e.target.value);
  localStorage.setItem(WC_THRESHOLD_KEY, wcThreshold);
  document.getElementById('wc-threshold-label').textContent = wcThreshold.toFixed(2);
  applyConfidenceStyling(wcThreshold);
});
```

### Anti-Patterns to Avoid

- **Re-rendering all word spans on slider drag:** Do NOT call `renderWords()` on every slider event — it destroys the DOM and loses edit state. Instead, apply `style.opacity` to existing spans via `applyConfidenceStyling()`.
- **Modifying `wordById` with normalized/joined words:** `wordById` is used by the edit and highlight system and must remain keyed on original ALTO word IDs and original content. The normalized `displayWords` list is separate.
- **Operating on the flat word stream for column sort:** The flat `data.words` array is in document XML order, which is NOT necessarily left-column-first for multi-column pages. Never assume document order = reading order.
- **Detecting line-end hyphens by VPOS delta heuristic alone:** A word's own HEIGHT varies by font size; a fixed pixel threshold will fail on archival scans with mixed body/headline text. Use the `line_end` flag added server-side for reliable detection.
- **Rejoining compound hyphens:** "Sozial-Demokrat" has a hyphen in the middle of the word, not at the end of a line. The `line_end && content.endsWith('-')` guard handles this correctly — a mid-word hyphen never has `line_end: true`.
- **Assuming all ALTO files have TextBlock elements:** Some Tesseract ALTO outputs may have flat PrintSpace → TextLine structure without intermediate TextBlock. The column-sort must gracefully fall back to VPOS order when `blocks.length === 0`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tooltip on confidence score | Custom positioned tooltip div with JS show/hide | HTML `title` attribute on the `.word` span | `title` is instant, accessible, and zero JS; custom tooltips require event handling, z-index management, and scroll awareness |
| Threshold persistence | Server-side session or cookie | `localStorage` | Already used by the project (no existing evidence, but standard for this class of viewer state); no server round-trip needed |
| Re-parse ALTO XML client-side | Fetch raw XML, parse with DOMParser | Use existing `/alto/<stem>` JSON response with blocks array extension | JSON is already structured; XML re-parse in the browser is slower and duplicates server-side logic |
| NLP-based hyphenation detection | Dictionary lookup, language model | Simple trailing-hyphen + `line_end` flag rule | German newspaper ALTO from Tesseract has reliable line-terminal hyphens; NLP adds latency and complexity for zero accuracy gain in this case |

**Key insight:** All three requirements (TEXT-01, TEXT-02, TEXT-03) are achievable with plain JavaScript array manipulation on structured data. The only server change is adding two metadata fields (`blocks` array and `line_end` flag) to the existing `/alto/<stem>` endpoint.

---

## Common Pitfalls

### Pitfall 1: Block-Level Data Not in Current API Response
**What goes wrong:** `serve_alto()` currently iterates `root.iter(f'{{{ns}}}String')` — a flat traversal with no TextBlock context. Implementing column sort purely from word HPOS values (without block boundaries) is fragile because words within a single line span both columns and cannot be separated by HPOS alone.
**Why it happens:** The Phase 9 API was designed for word-level editing, not layout analysis.
**How to avoid:** Extend `serve_alto()` to also return a `blocks` array (TextBlock HPOS/VPOS/WIDTH/HEIGHT + word_ids list). This is a non-breaking additive change to the JSON response.
**Warning signs:** If column detection is attempted purely from word HPOS, words from multi-column lines will be incorrectly split and column boundaries will fluctuate line by line.

### Pitfall 2: TextLine Membership Not Exposed
**What goes wrong:** Hyphen rejoin requires knowing which word is the last in its TextLine. This is not in the current API response.
**Why it happens:** Same reason as Pitfall 1 — the API was designed for word-level editing.
**How to avoid:** Add `line_end: true/false` boolean to each word in `serve_alto()`. Computing this server-side in one pass over TextLine elements is O(n) and adds negligible response size.
**Warning signs:** Attempting to infer line-end from VPOS delta is error-prone for pages with irregular line spacing (footnotes, captions, headlines).

### Pitfall 3: Confidence Slider Triggers Full Re-render
**What goes wrong:** If `renderWords()` is called on every slider `input` event, the entire text panel DOM is rebuilt 10-20 times per second during a drag. This loses the edit state, is slow, and causes visible flicker.
**Why it happens:** Using the same render path for initial load and threshold updates.
**How to avoid:** Separate concerns: `renderWords()` builds the DOM once per file load; `applyConfidenceStyling(threshold)` only touches `style.opacity` and `title` attributes on existing spans.
**Warning signs:** If you call `renderWords(displayWords)` inside the slider event handler, you will hit this pitfall.

### Pitfall 4: Normalized Word IDs Break Edit/Highlight
**What goes wrong:** After hyphen rejoining, a "joined word" is a synthetic object that does not exist in `wordById`. If clicked for editing, `wordById[span.dataset.id]` returns the correct original word — but the displayed content is the joined form. Saving the joined form back to the ALTO would write the joined word (without hyphen) as the content, which could break ALTO schema validity or surprise the operator.
**Why it happens:** The display list and the ALTO-backed edit list are conflated.
**How to avoid:** Joined words use the ID of the first fragment. Clicking a joined word for editing reveals the original un-rejoined content (the actual ALTO String content). This is correct behavior — the operator edits the ALTO word as stored, not the display form. Document this clearly in code comments.
**Warning signs:** If `renderWords()` uses a word object whose `content` is the joined form AND that same object is written back via `/save/<stem>`, data corruption occurs.

### Pitfall 5: Full-Width Block Detection Threshold Too Tight
**What goes wrong:** A TextBlock that is 58% of page width gets treated as a column block when it should be a full-width headline block. This puts the headline in the column flow, out of order.
**Why it happens:** Fixed percentage threshold does not account for page margins. Real archival pages have HPOS ≠ 0 for all blocks due to crop offsets.
**How to avoid:** The full-width test should check both `hpos` proximity to page margin AND relative width. Suggested rule: `hpos < pageWidth * 0.05 AND width > pageWidth * 0.60`. Adjust in code based on real file inspection.
**Warning signs:** Headers appearing in the middle of column text in the display panel.

### Pitfall 6: ALTO Files Without ComposedBlock/TextBlock
**What goes wrong:** Some TIFF pages may produce ALTO with only `PrintSpace → TextLine → String` (no TextBlock), especially for single-column pages or pages where Tesseract failed layout analysis.
**Why it happens:** Tesseract PSM mode and content type affect structural output.
**How to avoid:** The `blocks` array will be empty for such files. `columnSort()` must detect `blocks.length === 0` and return words in their original order (VPOS sort is already document order for single-column files).
**Warning signs:** Error in column sort when `blocks` is undefined or empty.

---

## Code Examples

Verified patterns from codebase inspection:

### Existing renderWords() — Current Baseline
```javascript
// Source: templates/viewer.html, line 323
function renderWords(words) {
  const panel = document.getElementById('text-panel');
  if (words.length === 0) {
    panel.innerHTML = '<em>No words found in this file.</em>';
    return;
  }
  panel.innerHTML = words.map(w =>
    `<span class="word" data-id="${escapeHtml(w.id)}">${escapeHtml(w.content)}</span> `
  ).join('');
  // ... click handler
}
```

Phase 19 extends this to include `data-wc` attribute:
```javascript
// Phase 19 version — adds data-wc for confidence styling
panel.innerHTML = words.map(w =>
  `<span class="word" data-id="${escapeHtml(w.id)}" data-wc="${w.confidence ?? ''}">${escapeHtml(w.content)}</span> `
).join('');
```

### Existing loadFile() — Where normalizeWords() Is Called
```javascript
// Source: templates/viewer.html, line 265
async function loadFile(index) {
  // ...
  const data = await fetch(`/alto/${stem}`).then(r => r.json());
  // ...
  wordById = Object.fromEntries(data.words.map(w => [w.id, w]));
  renderWords(data.words);  // ← Phase 19: replace with renderWords(normalizeWords(data.words, data.blocks, data.page_width))
  // ...
}
```

### Real ALTO TextBlock Structure (confirmed from output/alto/ inspection)
```xml
<!-- Source: output/alto/Ve_Volk_165945877_1957_Band_2-0403.xml -->
<ComposedBlock ID="cblock_1" HPOS="493" VPOS="485" WIDTH="1677" HEIGHT="437">
  <TextBlock ID="block_0" HPOS="493" VPOS="485" WIDTH="1677" HEIGHT="437">
    <TextLine ID="line_0" HPOS="857" VPOS="485" WIDTH="288" HEIGHT="26">
      <String ID="string_0" HPOS="857" VPOS="485" WIDTH="56" HEIGHT="26" WC="0.89" CONTENT="am"/>
    </TextLine>
    <!-- ... -->
    <TextLine ID="line_7" ...>
      <String ... CONTENT="so-"/>  <!-- last String in line → line_end: true, ends with "-" → rejoin candidate -->
    </TextLine>
    <TextLine ID="line_8" ...>
      <String ... CONTENT="wohl"/>  <!-- first String of next line → rejoined result: "sowohl" -->
    </TextLine>
  </TextBlock>
</ComposedBlock>
```

### Page Dimensions (confirmed from real file)
```xml
<!-- Page width for Ve_Volk_165945877_1957_Band_2-0403.xml -->
<Page WIDTH="10114" HEIGHT="7529" ...>
```
Block at HPOS=493, WIDTH=1677 → `1677/10114 = 16.6%` — clearly a column block.

### serve_alto() Extension — blocks array
```python
# Source: app.py serve_alto() — to be extended in Phase 19
# Add BEFORE the return statement, AFTER the words loop:

# Build elem → global index map for TextBlock word_ids assembly
elem_to_idx = {}
for i, elem in enumerate(root.iter(f'{{{ns}}}String')):
    elem_to_idx[id(elem)] = i

# Build blocks array
blocks_out = []
for block_elem in root.findall(f'.//{{{ns}}}TextBlock'):
    word_ids = [
        f'w{elem_to_idx[id(s)]}'
        for s in block_elem.iter(f'{{{ns}}}String')
        if id(s) in elem_to_idx
    ]
    blocks_out.append({
        'id': block_elem.get('ID', ''),
        'hpos': int(block_elem.get('HPOS', 0)),
        'vpos': int(block_elem.get('VPOS', 0)),
        'width': int(block_elem.get('WIDTH', 0)),
        'height': int(block_elem.get('HEIGHT', 0)),
        'word_ids': word_ids,
    })

return jsonify({
    'page_width': page_width,
    'page_height': page_height,
    'jpeg_width': jpeg_width,
    'jpeg_height': jpeg_height,
    'words': words,
    'blocks': blocks_out,  # NEW
})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat word stream in document XML order | Normalized display list (column-sorted, hyphen-rejoined) | Phase 19 | Reading order matches natural newspaper layout |
| No confidence feedback | WC-faded words with threshold slider | Phase 19 | Operators can instantly identify low-quality OCR regions |
| No TextBlock data in API | blocks array + line_end flag in /alto/<stem> | Phase 19 | Enables client-side layout analysis without ALTO re-parse |

**Deprecated/outdated:**
- Direct `renderWords(data.words)` call: replaced by `renderWords(normalizeWords(data.words, data.blocks, data.page_width))` — the raw `data.words` list must not be passed directly to `renderWords` after this phase.

---

## Open Questions

1. **HPOS clustering gap threshold**
   - What we know: Page width is 10114 px in the one real file inspected; blocks are clearly separated (block at HPOS=493 vs. blocks starting at ~2200+). A 5% page-width gap (~500 px) would cleanly separate these columns.
   - What's unclear: Whether all real files have equally clear column gaps. Pages with narrow gutters (adjacent column HPOS values within 200 px) might be mis-clustered.
   - Recommendation: Start with `gap > pageWidth * 0.05` and log cluster assignments during development. A conservative threshold is better than aggressive splitting; single-column fallback catches degenerate cases.

2. **Hyphen rejoin and word IDs in edit flow**
   - What we know: The edit system (`editWord`, `saveWord`) uses `wordById[span.dataset.id]` and writes to the ALTO using the word's positional index. A joined word span has the ID of the first fragment.
   - What's unclear: Should clicking a joined word for editing show the un-joined content (correct ALTO state) or the joined form?
   - Recommendation: Show the un-joined ALTO content in the edit input — this is what will be saved. Add a comment in the code explaining the design. The joined form is display-only.

3. **Confidence badge placement**
   - What we know: The decision says "badge in the sidebar." The sidebar currently holds only file-item divs. The text panel holds word spans and the article browser.
   - What's unclear: The CONTEXT.md says "right-side settings panel (existing panel, below article browser)" for the slider — and "sidebar badge" for the count. The sidebar is the left-side file list panel; the text panel is the right side. These appear to be two different elements.
   - Recommendation: Place the count badge inside the `#text-panel` (right side) as part of the confidence settings section, below the slider — not in the left file-list sidebar. The CONTEXT.md "sidebar" likely refers to the settings/text panel, not the left nav. If uncertain, the badge can be placed immediately above or below the slider label.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `app.py` `serve_alto()` route (lines 438–530) — confirmed current API response shape
- Direct codebase inspection — `templates/viewer.html` `renderWords()` (line 317–338) — confirmed current render pattern
- Direct codebase inspection — `output/alto/Ve_Volk_165945877_1957_Band_2-0403.xml` — confirmed TextBlock structure, WC attributes, real hyphenated words ("so-"/"wohl", "entgegen-"/"steht,")
- `.planning/phases/19-text-normalization/19-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- MDN Web Docs pattern: `localStorage.getItem/setItem` for browser-persistent UI state — well-established standard
- HTML `title` attribute for tooltip: well-established browser-native behavior, no library needed

### Tertiary (LOW confidence)
- HPOS clustering gap threshold of 5% — derived from single real file inspection; should be validated against more files

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all vanilla JS + existing Flask/Python
- Architecture: HIGH — confirmed from direct code and real ALTO file inspection; only open question is clustering threshold
- Pitfalls: HIGH — identified from direct code analysis (serve_alto flat iteration, renderWords pattern, wordById edit flow)

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain — no third-party libraries involved)
