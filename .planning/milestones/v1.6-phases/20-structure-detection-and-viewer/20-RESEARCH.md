# Phase 20: Structure Detection and Viewer - Research

**Researched:** 2026-03-02
**Domain:** Client-side JavaScript paragraph detection, VLM-to-ALTO coordinate overlap, structured HTML rendering
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Role label presentation**
- Structural roles are communicated through visual styling only — no explicit badge, tag, or inline label before blocks
- Role count summary shown below the confidence badge in the right panel (e.g. "1 heading, 3 paragraphs, 1 caption")
- Summary updates on every `loadFile()` call, same lifecycle as the confidence badge
- No VLM/fallback distinction in the count — plain role counts only

**Paragraph break visual style**
- Blank line gap between paragraph blocks (CSS margin-bottom on each `.para-block`)
- Paragraph boundary threshold: gap between successive TextLine VPOS values > 1.5× the median inter-line spacing within the block
- Every TextBlock boundary is always treated as a paragraph break regardless of spacing
- Detection is entirely client-side JavaScript using existing `/alto/<stem>` data (blocks, word VPOS) — no server changes

**Heading and role styling**
- Headings: `font-weight: bold` + `font-size: 1.1em` (slightly larger)
- Captions: `font-size: 0.9em` + `font-style: italic`
- Advertisements: `font-size: 0.9em` + `font-style: italic` + subtle left border (e.g. `border-left: 3px solid #ccc; padding-left: 0.4em`)
- Paragraphs: default (no additional styling)
- Implementation: each block rendered as `<div class="para-block" data-role="heading|paragraph|caption|advertisement">`; CSS targets `[data-role=...]` selectors
- Structured display is permanent — no flat/structured toggle in this phase

**VLM role assignment and fallback**
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

### Deferred Ideas (OUT OF SCOPE)
- Flat/structured toggle button — future phase
- Heuristic heading detection (for pages without VLM) — future phase if needed
- "Segment this page" prompt in text panel — future phase
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STRUCT-07 | System groups ALTO words into paragraphs by detecting line-spacing gaps larger than the median line height, producing paragraph-separated text instead of a flat word stream | The `/alto/<stem>` endpoint already returns `blocks` array with HPOS/VPOS/WIDTH/HEIGHT per TextBlock and `word_ids`; TextLine VPOS data is embedded per-word via `vpos` attribute; paragraph detection runs fully client-side using this data |
| STRUCT-08 | System annotates detected text blocks with a structural role (heading / paragraph / caption / advertisement) derived from existing VLM article segmentation regions | VLM segment JSON is already loaded via `currentArticles` in `loadFile()`; bounding boxes are normalized 0.0–1.0 fractions; ALTO TextBlock HPOS/VPOS/WIDTH/HEIGHT is in pixel coordinates; coordinate conversion uses `pageWidth`/`pageHeight` already available |
| VIEW-07 | Viewer renders structured text — headings styled prominently (bold, larger size), paragraphs separated by whitespace — replacing the current flat word list in the text panel | `renderWords()` in viewer.html is the single injection point; replace it with a block-oriented `renderBlocks()` that emits `.para-block[data-role=...]` divs; CSS `[data-role=...]` selectors handle all styling; existing `applyConfidenceStyling()` and `wordById` remain intact |
</phase_requirements>

## Summary

Phase 20 is a pure client-side JavaScript phase with no server changes. All required data is already available: the `/alto/<stem>` endpoint returns a `blocks` array (TextBlock HPOS/VPOS/WIDTH/HEIGHT plus `word_ids`) added in Phase 19, and VLM segmentation data is already loaded into `currentArticles` by `loadSegments()`/`loadArticles()` on every `loadFile()` call. The phase builds two algorithms in `viewer.html`: (1) paragraph detection using per-word VPOS to find gaps wider than 1.5x the median inter-line spacing within each TextBlock, and (2) role assignment using bounding-box intersection between ALTO TextBlocks (pixel coords) and VLM regions (normalized 0.0–1.0 fractions converted via `pageWidth`/`pageHeight`).

The rendering replaces the flat word `<span>` dump in `#word-list` with structured `<div class="para-block" data-role="...">` containers. Each block holds word spans exactly as before so `wordById`, click-to-edit, `applyConfidenceStyling()`, and SVG highlight all continue to work without modification. The role count summary appends a single `<div id="struct-summary">` inside `#wc-settings`, updated alongside `#wc-badge` on each file load.

The VLM type-to-role mapping from real segment data is: `headline` → `heading`, `article` → `paragraph`, `advertisement` → `advertisement`, `caption` → `caption`, `illustration` → `paragraph`. The ALTO coordinate space uses absolute pixels; the VLM bounding box uses 0.0–1.0 fractions of JPEG dimensions. Intersection must scale VLM boxes by `pageWidth`/`pageHeight` (not `jpeg_width`/`jpeg_height`) since ALTO coordinates are in ALTO page units.

**Primary recommendation:** Implement `detectParagraphs(block, words)` and `assignRoles(blocks, articles, pageWidth, pageHeight)` as standalone pure functions, then replace `renderWords()` with `renderBlocks(paraBlocks)`. Keep all existing word-level infrastructure (wordById, applyConfidenceStyling, editWord, selectWord) unchanged.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS (ES2020) | browser-native | Paragraph detection, role assignment, rendering | No build step; project pattern (all prior phases use inline JS in viewer.html) |
| CSS attribute selectors | browser-native | Role-based visual styling via `[data-role=...]` | Decouples style from logic; no class explosion; existing project pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None needed | — | All required functionality is browser-native | This phase adds no dependencies |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline JS in viewer.html | Separate .js module file | Project uses inline JS exclusively; separate file would require a new static route in Flask |
| CSS attribute selectors | JS classList per role | Attribute selectors require zero JS in the render path; cleaner |
| VPOS-based paragraph detection | Re-use existing line_end flags | line_end only marks TextLine ends, not paragraph gaps; VPOS gap analysis is the correct approach for STRUCT-07 |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Project Structure

No new files. All changes are in:
```
templates/
└── viewer.html    # add CSS rules, detectParagraphs(), assignRoles(), renderBlocks(), updateStructSummary()
```

### Pattern 1: Paragraph Detection via VPOS Gap Analysis

**What:** For each TextBlock, sort its words by VPOS. Compute the median gap between successive unique VPOS values (treating each VPOS value as a TextLine). A new paragraph starts when consecutive VPOS gap > 1.5 × median gap. Every TextBlock boundary is always a paragraph break regardless of spacing.

**When to use:** STRUCT-07 requires this exact algorithm.

**Example:**
```javascript
// Source: derived from CONTEXT.md locked decision + existing serve_alto() block data
function detectParagraphs(block, wordById) {
  // Gather words for this block in VPOS order
  const blockWords = (block.word_ids || [])
    .map(id => wordById[id])
    .filter(Boolean);
  blockWords.sort((a, b) => a.vpos - b.vpos);

  if (blockWords.length === 0) return [{ block, words: [] }];

  // Compute unique VPOS values and gaps between successive lines
  const vposValues = [...new Set(blockWords.map(w => w.vpos))].sort((a, b) => a - b);
  if (vposValues.length <= 1) return [{ block, words: blockWords }];

  const gaps = [];
  for (let i = 1; i < vposValues.length; i++) {
    gaps.push(vposValues[i] - vposValues[i - 1]);
  }
  const sorted = [...gaps].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];
  const threshold = median * 1.5;

  // Split into paragraphs at gap > threshold
  const paragraphs = [];
  let current = [];
  for (const w of blockWords) {
    if (current.length > 0) {
      const lastVpos = current[current.length - 1].vpos;
      if (w.vpos - lastVpos > threshold) {
        paragraphs.push(current);
        current = [];
      }
    }
    current.push(w);
  }
  if (current.length > 0) paragraphs.push(current);

  return paragraphs.map(words => ({ block, words }));
}
```

### Pattern 2: VLM-to-ALTO Bounding Box Overlap (Role Assignment)

**What:** Convert VLM normalized bounding boxes to ALTO pixel coordinates, compute intersection area with each TextBlock, assign the role of the VLM region with maximum overlap to the block. Default to "paragraph" if no overlap found.

**When to use:** STRUCT-08 requires this exact strategy.

**Data sources:**
- ALTO TextBlock: `{ hpos, vpos, width, height }` in ALTO page pixel coordinates
- VLM region bounding box: `{ x, y, width, height }` in 0.0–1.0 fractions of page dimensions
- Coordinate conversion: multiply VLM fractions by `pageWidth` and `pageHeight` (NOT jpeg dimensions)

**Example:**
```javascript
// Source: mets.py _find_word_ids_in_region() adapted for client-side JS
// VLM types → structural roles
const VLM_TYPE_TO_ROLE = {
  headline:      'heading',
  article:       'paragraph',
  advertisement: 'advertisement',
  illustration:  'paragraph',
  caption:       'caption',
};

function intersectionArea(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2) {
  const ix1 = Math.max(ax1, bx1);
  const iy1 = Math.max(ay1, by1);
  const ix2 = Math.min(ax2, bx2);
  const iy2 = Math.min(ay2, by2);
  if (ix2 <= ix1 || iy2 <= iy1) return 0;
  return (ix2 - ix1) * (iy2 - iy1);
}

function assignRoles(blocks, articles, pageWidth, pageHeight) {
  // articles = currentArticles array from loadArticles()
  // Returns Map<blockId, role>
  const roleMap = new Map();
  for (const block of blocks) {
    let bestRole = 'paragraph';
    let bestArea = 0;
    for (const region of articles) {
      const bb = region.bounding_box;
      const rx1 = bb.x * pageWidth;
      const ry1 = bb.y * pageHeight;
      const rx2 = rx1 + bb.width * pageWidth;
      const ry2 = ry1 + bb.height * pageHeight;
      const area = intersectionArea(
        block.hpos, block.vpos,
        block.hpos + block.width, block.vpos + block.height,
        rx1, ry1, rx2, ry2
      );
      if (area > bestArea) {
        bestArea = area;
        bestRole = VLM_TYPE_TO_ROLE[region.type] || 'paragraph';
      }
    }
    roleMap.set(block.id, bestRole);
  }
  return roleMap;
}
```

### Pattern 3: Block-Oriented Rendering

**What:** Replace the current flat `renderWords()` (which injects `<span class="word">` directly into `#word-list`) with `renderBlocks()` that wraps word spans in `<div class="para-block" data-role="...">` containers. Word spans are identical to before so all downstream features (click-to-edit, highlight, `applyConfidenceStyling`) work unchanged.

**When to use:** VIEW-07 requires structured rendering.

**Example:**
```javascript
// Source: derived from existing renderWords() in viewer.html
function renderBlocks(paraBlocks) {
  // paraBlocks: [{block, role, words: [...word objects]}]
  const list = document.getElementById('word-list');
  if (paraBlocks.length === 0 || paraBlocks.every(pb => pb.words.length === 0)) {
    list.innerHTML = '<em>No words found in this file.</em>';
    return;
  }
  const html = paraBlocks.map(pb =>
    `<div class="para-block" data-role="${escapeHtml(pb.role)}">${
      pb.words.map(w =>
        `<span class="word" data-id="${escapeHtml(w.id)}" data-wc="${w.confidence ?? ''}">${escapeHtml(w.content)}</span> `
      ).join('')
    }</div>`
  ).join('');
  list.innerHTML = html;
  // Re-attach click handler (same handler as before, moved to list)
  list.onclick = wordListClickHandler;
}
```

### Pattern 4: Role Count Summary

**What:** Count role occurrences across all rendered paraBlocks; update `#struct-summary` div inside `#wc-settings`.

**Example:**
```javascript
function updateStructSummary(paraBlocks) {
  const counts = {};
  for (const pb of paraBlocks) {
    if (pb.words.length === 0) continue;
    counts[pb.role] = (counts[pb.role] || 0) + 1;
  }
  const parts = [];
  if (counts.heading)       parts.push(`${counts.heading} heading${counts.heading !== 1 ? 's' : ''}`);
  if (counts.paragraph)     parts.push(`${counts.paragraph} paragraph${counts.paragraph !== 1 ? 's' : ''}`);
  if (counts.caption)       parts.push(`${counts.caption} caption${counts.caption !== 1 ? 's' : ''}`);
  if (counts.advertisement) parts.push(`${counts.advertisement} ad${counts.advertisement !== 1 ? 's' : ''}`);
  const el = document.getElementById('struct-summary');
  if (el) el.textContent = parts.join(', ');
}
```

### Pattern 5: CSS Role Styling

```css
/* Source: CONTEXT.md locked decisions */
.para-block {
  margin-bottom: 0.8em;   /* blank line gap between blocks — Claude's discretion for exact value */
}
.para-block[data-role="heading"] {
  font-weight: bold;
  font-size: 1.1em;
}
.para-block[data-role="caption"] {
  font-size: 0.9em;
  font-style: italic;
}
.para-block[data-role="advertisement"] {
  font-size: 0.9em;
  font-style: italic;
  border-left: 3px solid #ccc;
  padding-left: 0.4em;
}
/* paragraph role has no additional styling */
```

### Anti-Patterns to Avoid
- **Modifying `wordById`:** `wordById` maps original `data.words` (not normalized/display words). Do not change it — it is used by the edit/save pipeline.
- **Re-fetching segment data:** `currentArticles` is already populated by `loadArticles()` in `loadFile()`. Do not add a new fetch call for role assignment.
- **Using jpeg dimensions for coordinate conversion:** VLM bounding boxes must be multiplied by `pageWidth`/`pageHeight` (ALTO pixel space), not `jpeg_width`/`jpeg_height`. ALTO coordinates are in ALTO page units.
- **Mutating `displayWords`:** `displayWords` is the normalized flat word list from Phase 19. The block-rendering pipeline works off `data.blocks` and `wordById`, not `displayWords`.
- **Destroying `#wc-settings` on re-render:** `renderBlocks()` only writes into `#word-list`; `#wc-settings` is a sibling div and must not be touched. This is the same invariant established in Phase 19-02.
- **Forgetting empty-block guard:** Some TextBlocks may have no `word_ids` (e.g. illustration-only blocks). Guard against empty word lists before rendering.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coordinate space conversion | Custom projection math | Direct `bb.x * pageWidth` multiplication | VLM bounding boxes are already normalized; one multiply per axis suffices |
| VLM data loading | New `/structure/<stem>` endpoint | Reuse `currentArticles` already in memory | Zero server changes needed; data is already loaded |
| Per-TextLine VPOS data | New server field | Use per-word `vpos` already in `data.words` | Words carry VPOS; unique VPOS values within a block proxy for TextLines |
| CSS-in-JS role styling | Dynamic style injection | Static CSS `[data-role=...]` rules | Attribute selectors are predictable, testable, and need no JS |

**Key insight:** Every data dependency for this phase was deliberately added by Phase 19. No new server endpoints, no new API fields, no new dependencies.

## Common Pitfalls

### Pitfall 1: Coordinate Space Mismatch
**What goes wrong:** VLM bounding boxes (`x`, `y`, `width`, `height`) are 0.0–1.0 fractions of the JPEG image dimensions. ALTO TextBlock coordinates are pixel values in ALTO page space. If the JPEG was downscaled (MAX_PX=1600 in serve_image()), JPEG dimensions differ from ALTO page dimensions.
**Why it happens:** `jpeg_width` ≠ `pageWidth` when the source TIFF was larger than 1600px on its longest side.
**How to avoid:** Always convert VLM bounding boxes using `bb.x * pageWidth` and `bb.y * pageHeight`, where `pageWidth` and `pageHeight` come from the `/alto/<stem>` response (ALTO page dimensions). Never use `jpeg_width`/`jpeg_height` for VLM-to-ALTO conversion.
**Warning signs:** Role assignment seems random or all blocks get "paragraph" even when VLM regions exist.

### Pitfall 2: Load Sequencing — `currentArticles` May Be Empty
**What goes wrong:** `loadArticles()` is async. If `assignRoles()` is called before the `loadArticles()` fetch resolves, `currentArticles` will be empty and all blocks default to "paragraph".
**Why it happens:** `loadFile()` calls `loadSegments()` and `loadArticles()` without `await`, then immediately calls `renderWords()` (which becomes `renderBlocks()`). In Phase 19 this was fine for word rendering, but role assignment needs the articles.
**How to avoid:** Move block rendering into a coordinated function that waits for both ALTO data AND articles data. Or (simpler): call `renderBlocks()` twice — once immediately with `currentArticles = []` (all paragraph roles as fallback) and again inside `loadArticles()` after the fetch resolves. The second render replaces the first with proper roles.
**Warning signs:** Roles always show as "paragraph" even on segmented pages.

### Pitfall 3: Paragraph Detection on Single-Word Blocks
**What goes wrong:** A TextBlock with only one word has no gaps to compute a median from. The gap array is empty, and the median calculation throws or returns `undefined`.
**Why it happens:** Some ALTO files have TextBlocks wrapping a single word (e.g. page numbers, running heads).
**How to avoid:** Guard: if `vposValues.length <= 1`, return the block as a single paragraph with all its words.
**Warning signs:** JavaScript errors on some pages but not others.

### Pitfall 4: `#word-list` innerHTML Destroying `#wc-settings`
**What goes wrong:** If `renderBlocks()` writes to `document.getElementById('text-panel').innerHTML` instead of `document.getElementById('word-list').innerHTML`, it destroys the confidence slider (`#wc-settings`).
**Why it happens:** Established footgun, documented in Phase 19-02 decision log.
**How to avoid:** Write only to `#word-list`. The HTML structure is: `#text-panel > #word-list` + `#wc-settings`. Keep it that way.
**Warning signs:** Slider disappears after navigating to a new file.

### Pitfall 5: `applyConfidenceStyling` Called Before `renderBlocks`
**What goes wrong:** `applyConfidenceStyling()` queries `document.querySelectorAll('.word[data-wc]')`. If called before `renderBlocks()` has injected the spans, it finds nothing.
**Why it happens:** Timing — the function is called at the end of `loadFile()`.
**How to avoid:** Call `applyConfidenceStyling(wcThreshold)` after `renderBlocks()` completes, same as the current pattern after `renderWords()`.
**Warning signs:** Words appear un-faded even though threshold is set low.

### Pitfall 6: VLM Type `headline` vs Structural Role `heading`
**What goes wrong:** VLM regions use type `headline`; the structural roles used in the CONTEXT.md decisions are `heading`, `paragraph`, `caption`, `advertisement`. Direct comparison fails.
**Why it happens:** Naming mismatch between the VLM output vocabulary and the UI role vocabulary.
**How to avoid:** Use the `VLM_TYPE_TO_ROLE` mapping explicitly: `{ headline: 'heading', article: 'paragraph', advertisement: 'advertisement', illustration: 'paragraph', caption: 'caption' }`. Apply this mapping when converting region type to role in `assignRoles()`.
**Warning signs:** TextBlocks in headline regions render without bold styling.

## Code Examples

### Full Integration in `loadFile()`

```javascript
// Source: existing loadFile() pattern in viewer.html — shows where to insert block rendering
async function loadFile(index) {
  // ... (existing setup: gen, currentStem, sidebar, nav buttons, clear state) ...

  try {
    const data = await fetch(`/alto/${stem}`).then(r => r.json());
    if (gen !== loadGen) return;
    pageWidth = data.page_width;
    pageHeight = data.page_height;
    jpeg_width = data.jpeg_width || 0;
    jpeg_height = data.jpeg_height || 0;
    recomputeFitScale();
    wordById = Object.fromEntries(data.words.map(w => [w.id, w]));
    displayWords = normalizeWords(data.words, data.blocks || [], data.page_width);

    // Phase 20: render with paragraph structure
    // currentArticles may be [] here (loadArticles is still in-flight)
    const paraBlocks = buildParaBlocks(data.blocks || [], wordById, currentArticles, pageWidth, pageHeight);
    renderBlocks(paraBlocks);
    updateStructSummary(paraBlocks);
    applyConfidenceStyling(wcThreshold);

    loadSegments(stem);
    loadArticles(stem);  // on completion: re-render blocks with proper roles
  } catch (err) {
    // ...
  }
}
```

### `buildParaBlocks()` — Top-Level Coordinator

```javascript
// Source: based on CONTEXT.md algorithm decisions
function buildParaBlocks(blocks, wordById, articles, pageWidth, pageHeight) {
  const roleMap = assignRoles(blocks, articles, pageWidth, pageHeight);
  const result = [];
  for (const block of blocks) {
    const role = roleMap.get(block.id) || 'paragraph';
    const subParas = detectParagraphs(block, wordById);
    for (const { words } of subParas) {
      result.push({ block, role, words });
    }
  }
  // Append words not in any block (ALTO files without TextBlock structure)
  const coveredIds = new Set(result.flatMap(pb => pb.words.map(w => w.id)));
  const orphans = Object.values(wordById).filter(w => !coveredIds.has(w.id));
  if (orphans.length > 0) {
    result.push({ block: null, role: 'paragraph', words: orphans });
  }
  return result;
}
```

### Re-render After `loadArticles()` Resolves

```javascript
// Source: existing loadArticles() in viewer.html — shows where to add re-render
async function loadArticles(stem) {
  currentArticles = [];
  activeArticleId = null;
  renderArticleList([]);
  try {
    const resp = await fetch(`/articles/${encodeURIComponent(stem)}`);
    if (!resp.ok) return;
    const data = await resp.json();
    currentArticles = data.regions || [];
    renderArticleList(currentArticles);

    // Phase 20: re-render blocks now that VLM data is loaded
    const altoData = /* need access to last-loaded blocks */;
    // Pattern: store data.blocks in a module-level variable `currentBlocks`
    if (currentBlocks && currentBlocks.length > 0) {
      const paraBlocks = buildParaBlocks(currentBlocks, wordById, currentArticles, pageWidth, pageHeight);
      renderBlocks(paraBlocks);
      updateStructSummary(paraBlocks);
      applyConfidenceStyling(wcThreshold);
    }
  } catch (e) { /* silently skip */ }
}
```

### HTML Structure for Role Count Summary

```html
<!-- Inside #wc-settings, after #wc-badge -->
<div id="struct-summary" style="font-size:0.78rem;color:#888;margin-top:2px;min-height:1em;"></div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat `<span>` word list | Block-oriented `<div class="para-block">` rendering | Phase 20 | Enables CSS role styling and whitespace separation |
| `renderWords(displayWords)` call | `renderBlocks(paraBlocks)` call | Phase 20 | Replaces Phase 19 entry point; preserves all word-level behavior |

**Note:** Phase 19 `displayWords` and `normalizeWords()` are NOT replaced — they remain for the word-level edit pipeline. `renderBlocks()` uses the `data.blocks` structural data alongside `wordById` as a lookup; it does not reuse `displayWords` directly. This is intentional: column sort order is embedded in `data.blocks` ordering; paragraph detection works per-block.

## Open Questions

1. **Column ordering of blocks in `data.blocks`**
   - What we know: `serve_alto()` returns `blocks` in ALTO document order (TextBlock element order). Phase 19's `columnSort()` reorders `displayWords` but does NOT reorder `data.blocks`.
   - What's unclear: Whether `data.blocks` should be passed through `columnSort`-equivalent ordering before paragraph detection, or whether ALTO document order is already correct for reading.
   - Recommendation: Use ALTO document order for `data.blocks` in Phase 20. The column sort was designed for the flat word stream. Block rendering already preserves TextBlock boundaries, and visual order follows the TIFF image structure. If the ordering proves wrong in practice, a follow-up sort by the same cluster algorithm used in `columnSort()` can be applied to `blocks` in Phase 21.

2. **`currentBlocks` module-level variable**
   - What we know: `loadArticles()` needs access to `data.blocks` to re-render after VLM data arrives. Currently `data.blocks` is local to the `loadFile()` try block.
   - What's unclear: Whether to promote `data.blocks` to module-level state or use a closure.
   - Recommendation: Add `let currentBlocks = [];` alongside existing module-level state (`stems`, `wordById`, etc.) and assign `currentBlocks = data.blocks || []` in `loadFile()`. This follows the existing pattern.

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `/Users/zu54tav/Zeitschriften-OCR/templates/viewer.html` — complete `loadFile()`, `renderWords()`, `loadArticles()`, `currentArticles`, `wordById`, `displayWords`, `normalizeWords()`, `applyConfidenceStyling()`, module-level state variables
- Direct code inspection of `/Users/zu54tav/Zeitschriften-OCR/app.py` `serve_alto()` — `blocks` array shape: `{id, hpos, vpos, width, height, word_ids[]}`, `pageWidth`, `pageHeight`, `jpeg_width`, `jpeg_height`
- Direct inspection of `/Users/zu54tav/Zeitschriften-OCR/output/segments/Ve_Volk_165945877_1957_Band_2-0403.json` — real VLM region structure: `{id, type, title, bounding_box:{x,y,width,height}}` with types `headline`, `article`, `advertisement`, `illustration`, `caption`
- Direct code inspection of `/Users/zu54tav/Zeitschriften-OCR/mets.py` `_find_word_ids_in_region()` — established coordinate conversion pattern: `bb.x * page_width`, `bb.y * page_height`
- CONTEXT.md locked decisions — all algorithmic and styling choices

### Secondary (MEDIUM confidence)
- CSS `[data-role=...]` attribute selector syntax — standard CSS2, universally supported
- Median computation pattern for gap threshold — standard statistical approach for robust line-spacing detection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all tools are browser-native or already present
- Architecture: HIGH — all data structures verified in running code; no inferences needed
- Pitfalls: HIGH — coordinate mismatch, load sequencing, and innerHTML invariant all verified from existing code

**Research date:** 2026-03-02
**Valid until:** 2026-04-01 (stable codebase; no external dependencies)
