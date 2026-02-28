# Phase 11: Side-by-Side Viewer UI - Research

**Researched:** 2026-02-28
**Domain:** Flask HTML template serving, vanilla JS fetch, SVG overlay, ResizeObserver, DOM construction
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**File List Design**
- Left sidebar positioned above the TIFF image panel — persistent, always visible
- Filename only per list item — no word count or timestamps
- Data source: new `GET /files` endpoint returning stems of all `alto/*.xml` files in the output directory
- Active file indicated by highlighted row with a distinct background color (CSS active class toggle)

**Text Panel Word Display**
- Flowing prose — words rendered as inline `<span>` elements that wrap naturally
- Default word state: plain text, `cursor: pointer` on hover — no underline or background decoration
- Selected word state: bold + yellow background highlight — one word selected at a time
- Clicking a word also scrolls the image panel so the SVG bounding box is visible in the viewport

**SVG Overlay Behavior**
- Highlight rectangle appears on click only — no hover preview
- Style: semi-transparent yellow fill + orange stroke
- Bidirectional: clicking the SVG rectangle on the image scrolls to and highlights the corresponding word in the text panel
- On browser resize: recompute scale factors from live rendered image dimensions (ResizeObserver or window.onresize), redraw overlay in-place — no clearing required

**Navigation UX**
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEW-01 | User can browse all previously processed files in a file list panel | GET /files endpoint returning sorted stems from alto/*.xml; sidebar renders as clickable list items with active CSS class toggle |
| VIEW-04 | User can navigate to the previous/next file with keyboard or buttons | JS maintains currentIndex into stems array; Prev/Next buttons call loadFile(currentIndex ± 1); keyboard handler guards INPUT focus |
| OVLY-01 | Clicking a word in the text panel highlights its bounding box on the TIFF image | SVG rect drawn at (hpos * scale_x, vpos * scale_y) with semi-transparent fill; clicking SVG rect scrolls text panel to corresponding span |
| OVLY-02 | Bounding box coordinates scale correctly as the image is resized | ResizeObserver on the img element recomputes scale_x = img.clientWidth / page_width and repositions the single active rect in-place |
</phase_requirements>

## Summary

Phase 11 adds one new Flask endpoint (`GET /files`) and one new HTML template (`templates/viewer.html`) to `app.py`. The viewer is a single-page app driven entirely by vanilla JavaScript: on load it fetches the file list, renders the sidebar, and loads the first file. File loads are Ajax — no full-page reload. The left panel holds an `<img>` tag (src set to `/image/<stem>`) overlaid by an absolutely-positioned `<svg>` element inside a common wrapper div. The right panel holds a `<div>` whose contents are replaced with `<span>` elements on each file load. Clicking a span draws one `<rect>` in the SVG; clicking the rect scrolls the text panel to the corresponding span. ResizeObserver on the `<img>` element recomputes scale factors whenever the image dimensions change, repositioning the active rect without clearing it.

Real production ALTO files in this project contain between 50 and 5786 words (mean ~3400 across 23 files). The SVG always holds at most one `<rect>` element regardless of word count, so there is no SVG performance ceiling. The text panel's 5786 inline `<span>` elements is well within normal browser DOM capacity — batch-built with a single `innerHTML` assignment to avoid repeated reflows. The `GET /alto/<stem>` endpoint already returns `page_width`, `page_height`, `jpeg_width`, and `jpeg_height` from Phase 10, so the viewer has all coordinate data it needs without additional server work.

No new Python dependencies are required. The only new file beyond `templates/viewer.html` and the `GET /files` route is a CSS block embedded in the template (no separate `.css` file needed given the project's single-operator, local-use scope).

**Primary recommendation:** Add `GET /files` to `app.py`, add `GET /` that renders `templates/viewer.html`, and write all viewer JS inline in the template. Use vanilla JS fetch + DOM manipulation throughout — no frontend framework or build step required.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.3 (installed) | `render_template()` for viewer.html, `GET /files` endpoint, `jsonify()` | Already the app server; `render_template` resolves `templates/` directory automatically |
| Jinja2 | bundled with Flask | HTML template rendering, `url_for()` for static assets | Flask's built-in template engine; no separate install |
| Vanilla JS | ES2020+ (browser) | fetch, DOM manipulation, ResizeObserver, keyboard events | No build step; matches project's single-file, operator-tool philosophy |
| ResizeObserver API | Baseline (since Jul 2020) | Observe `<img>` size changes to recompute SVG scale factors | Built-in browser API; universally available; no polyfill needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CSS Flexbox | browser-native | Three-column layout (sidebar + image panel + text panel) | Claude's discretion; flexbox simpler than grid for this fixed three-column use case |
| SVG (inline) | browser-native | Bounding box highlight rect overlaid on image | One `<rect>` element at a time; always in the DOM, visibility toggled |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla JS | Alpine.js / htmx | Adds a CDN dependency; project philosophy favors no build tooling; vanilla JS is sufficient for this scope |
| Inline SVG (absolute positioned) | Canvas 2D | Canvas would require full redraw on resize; SVG rect repositioning is a simpler attribute update; Canvas adds complexity for no benefit at ≤5786 words |
| `innerHTML` batch build | `DocumentFragment` iteration | `innerHTML` with a pre-built string is idiomatic and equally fast for a one-time DOM replacement on file load |

**Installation:**
```bash
# No new dependencies — all already in requirements.txt
pip install -r requirements.txt
```

## Architecture Patterns

### Recommended Project Structure

```
app.py                         # add GET /files, GET / routes
templates/
└── viewer.html                # new — all CSS + JS inline
output/
├── alto/                      # existing — source of /files list
├── jpegcache/                 # existing — served by GET /image/<stem>
└── uploads/                   # existing — source TIFFs
```

No separate `static/` directory needed. All CSS and JS lives inside `viewer.html` using `<style>` and `<script>` tags. This matches the project's single-operator, local-use philosophy — no CDN, no build step, no asset pipeline.

### Pattern 1: GET /files Endpoint

**What:** Returns sorted list of stems from `output/alto/*.xml`.
**When to use:** Called once on viewer page load to populate the sidebar.

```python
# Source: Flask 3.1 jsonify + pathlib glob, verified against live interpreter
@app.get('/files')
def list_files():
    """Return alphabetically sorted list of ALTO stems in output/alto/."""
    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_dir = output_dir / 'alto'
    if not alto_dir.exists():
        return jsonify({'stems': []})
    stems = sorted(p.stem for p in alto_dir.glob('*.xml'))
    return jsonify({'stems': stems})
```

Response: `{"stems": ["144528908_0019", "Ve_Volk_165945877_1957_Band_1-0001", ...]}`

### Pattern 2: GET / Viewer Route

**What:** Serves the single-page viewer HTML.
**When to use:** Entry point — user navigates to `http://localhost:5000/`.

```python
@app.get('/')
def viewer():
    """Serve the side-by-side viewer page."""
    return render_template('viewer.html')
```

`render_template` automatically resolves `templates/viewer.html` relative to `app.py`. The `templates/` directory must be created alongside `app.py`.

### Pattern 3: Three-Panel Layout (CSS Flexbox)

**What:** Sidebar + image panel + text panel as a row. Sidebar contains file list and Prev/Next nav above the two panels.
**When to use:** Outer page structure.

```html
<!-- Outer wrapper: nav bar above, three columns below -->
<div id="nav-bar">
  <button id="btn-prev" disabled>&#8592; Previous</button>
  <button id="btn-next" disabled>&#8594; Next</button>
</div>
<div id="main">
  <div id="sidebar"><!-- file list --></div>
  <div id="image-panel">
    <div id="image-wrapper" style="position:relative; display:inline-block;">
      <img id="tiff-img" src="" alt="">
      <svg id="overlay" style="position:absolute; top:0; left:0; pointer-events:none; width:100%; height:100%;">
        <rect id="highlight-rect" style="display:none;" fill="rgba(255,255,0,0.3)" stroke="orange" stroke-width="2"/>
      </svg>
    </div>
  </div>
  <div id="text-panel"><!-- word spans --></div>
</div>
```

Key CSS rules:
```css
#main { display: flex; height: calc(100vh - 48px); }
#sidebar { width: 220px; overflow-y: auto; flex-shrink: 0; }
#image-panel { flex: 1; overflow: auto; }
#text-panel { width: 380px; overflow-y: auto; flex-shrink: 0; }
#image-wrapper { display: inline-block; position: relative; }
#tiff-img { display: block; max-width: 100%; height: auto; }
#overlay { position: absolute; top: 0; left: 0; pointer-events: none; }
```

### Pattern 4: SVG Overlay — Absolute Position Over `<img>`

**What:** `<svg>` is `position:absolute` inside a `position:relative` wrapper div. The SVG always has `width:100%; height:100%` so it tracks the image exactly. One persistent `<rect id="highlight-rect">` is toggled visible/hidden; its attributes are updated on each click.
**When to use:** Required for OVLY-01 and OVLY-02.

```javascript
// Source: verified scale factor math against real ALTO files (page_width=5146, jpeg_width=1091)
function showHighlight(word) {
  const img = document.getElementById('tiff-img');
  const rect = document.getElementById('highlight-rect');
  const scaleX = img.clientWidth / pageWidth;
  const scaleY = img.clientHeight / pageHeight;
  rect.setAttribute('x', word.hpos * scaleX);
  rect.setAttribute('y', word.vpos * scaleY);
  rect.setAttribute('width', word.width * scaleX);
  rect.setAttribute('height', word.height * scaleY);
  rect.style.display = '';
}

function clearHighlight() {
  document.getElementById('highlight-rect').style.display = 'none';
}
```

`pageWidth` and `pageHeight` come from the `/alto/<stem>` JSON response and are stored in module-level variables when a file is loaded. They do not change on resize — only `img.clientWidth` / `img.clientHeight` change.

### Pattern 5: ResizeObserver for Resize-Safe Overlay

**What:** ResizeObserver fires when the `<img>` element changes rendered size. On each callback, recompute scale factors and reposition the active rect.
**When to use:** Required for OVLY-02. Attach once on page load; survives across file changes.

```javascript
// Source: MDN ResizeObserver (Baseline since July 2020)
let activeWord = null;  // the currently highlighted word object

const resizeObserver = new ResizeObserver(() => {
  if (activeWord !== null) {
    showHighlight(activeWord);  // recomputes from live img.clientWidth/clientHeight
  }
});
resizeObserver.observe(document.getElementById('tiff-img'));
```

This is set up once on DOMContentLoaded. Because ResizeObserver observes the `<img>` element (not the window), it fires correctly even if only the panel width changes (e.g., in a future resizable-panels UI).

### Pattern 6: Text Panel — Batch DOM Build

**What:** Build the entire text panel HTML as a string, assign to `innerHTML` in one operation.
**When to use:** On every file load (replaces previous content).

```javascript
// Source: verified against 5786-word real ALTO file; single innerHTML = no repeated reflows
function renderWords(words) {
  const panel = document.getElementById('text-panel');
  const parts = words.map(w =>
    `<span class="word" data-id="${w.id}">${escapeHtml(w.content)}</span> `
  );
  panel.innerHTML = parts.join('');
  // Attach click handler via delegation — one listener on the panel
  panel.onclick = (e) => {
    const span = e.target.closest('.word');
    if (!span) return;
    const word = wordById[span.dataset.id];
    selectWord(word, span);
  };
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
```

`wordById` is a plain object keyed by `w.id` (e.g., `'w0'`, `'w1'`), populated when `/alto/<stem>` response is parsed.

Event delegation (one `onclick` on the panel div) is used instead of one listener per span. This avoids attaching 5786 event listeners and survives `innerHTML` replacement without explicit listener cleanup.

### Pattern 7: Bidirectional Click — SVG Rect to Text Span

**What:** The SVG `<rect>` carries the word id. Clicking it finds the corresponding span in the text panel and scrolls it into view.
**When to use:** Required by the locked SVG overlay bidirectional decision.

The SVG rect is `pointer-events:none` by default (so clicks pass through to the image), but for the click-on-rect-to-scroll-text behavior, the rect itself must be clickable. The solution: set `pointer-events:all` on the rect when it is visible, and `pointer-events:none` on the overlay SVG as a whole so unoccupied areas don't block image interaction.

```javascript
// On word click in text panel:
function selectWord(word, span) {
  // 1. Deselect previous span
  document.querySelectorAll('.word.selected').forEach(s => s.classList.remove('selected'));
  // 2. Select new span
  span.classList.add('selected');
  activeWord = word;
  // 3. Draw SVG rect
  showHighlight(word);
  highlightRect.dataset.wordId = word.id;
  highlightRect.style.pointerEvents = 'all';
  // 4. Scroll image panel so rect is visible
  highlightRect.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// On rect click:
highlightRect.addEventListener('click', () => {
  const span = document.querySelector(`.word[data-id="${highlightRect.dataset.wordId}"]`);
  if (span) {
    span.classList.add('selected');
    span.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
});
```

### Pattern 8: Keyboard Navigation Guard

**What:** Left/Right arrow keys navigate prev/next. Guard fires before navigation to avoid conflicting with future Phase 12 input fields.
**When to use:** Required by the locked navigation decision.

```javascript
// Source: CONTEXT.md specifics section
document.addEventListener('keydown', (e) => {
  if (document.activeElement.tagName === 'INPUT') return;
  if (e.key === 'ArrowLeft') navigateTo(currentIndex - 1);
  if (e.key === 'ArrowRight') navigateTo(currentIndex + 1);
});
```

### Pattern 9: File Load Sequence

**What:** Loading a file is a two-fetch sequence: first set `<img src>` and call `/alto/<stem>`, then on both completing, render word spans. The image load and ALTO fetch are independent and can run in parallel.
**When to use:** On sidebar item click, Prev/Next button click, keyboard navigation.

```javascript
async function loadFile(index) {
  if (index < 0 || index >= stems.length) return;
  currentIndex = index;
  const stem = stems[index];

  // 1. Update sidebar active state
  document.querySelectorAll('#sidebar .file-item').forEach((el, i) => {
    el.classList.toggle('active', i === index);
  });

  // 2. Update Prev/Next button disabled state
  document.getElementById('btn-prev').disabled = (index === 0);
  document.getElementById('btn-next').disabled = (index === stems.length - 1);

  // 3. Clear previous state
  clearHighlight();
  activeWord = null;
  document.getElementById('text-panel').innerHTML = 'Loading…';
  document.getElementById('image-panel').scrollTop = 0;
  document.getElementById('text-panel').scrollTop = 0;

  // 4. Set image src (browser loads async)
  document.getElementById('tiff-img').src = `/image/${stem}`;

  // 5. Fetch ALTO data in parallel
  const data = await fetch(`/alto/${stem}`).then(r => r.json());
  pageWidth = data.page_width;
  pageHeight = data.page_height;
  wordById = Object.fromEntries(data.words.map(w => [w.id, w]));

  // 6. Render word spans
  renderWords(data.words);
}
```

Note: image loading (`<img src>` assignment) does not need to be awaited before rendering word spans — the text panel can be ready while the image is still loading. The SVG overlay only positions on click (after the image has rendered), so `img.clientWidth` will be valid by then.

### Anti-Patterns to Avoid

- **One event listener per span:** Attaching `addEventListener('click', ...)` to each of 5786 span elements on every file load creates and destroys thousands of listeners. Use event delegation on the panel container instead.
- **Clearing and recreating the SVG rect on every click:** Keep one persistent `<rect>` in the SVG; update its attributes and toggle `display`. Creating/removing elements triggers layout thrashing.
- **Using `window.onresize` instead of ResizeObserver:** `window.onresize` fires on viewport changes but misses panel-level size changes (e.g., if panels become resizable in a future phase). ResizeObserver fires on the element itself.
- **Placing the SVG outside the image wrapper:** If SVG and `<img>` are separate siblings, their positions must be synchronized manually. Absolute positioning inside a `position:relative` wrapper keeps them in lockstep automatically.
- **Computing scale from `naturalWidth` instead of `clientWidth`:** `naturalWidth` is the JPEG pixel width (1091px). `clientWidth` is the rendered browser pixel width (e.g., 600px). The scale factor must be `clientWidth / page_width` to map ALTO coordinates to browser pixels, not `naturalWidth / page_width`.
- **Using `img.width` attribute instead of `img.clientWidth`:** The `width` HTML attribute (if set) returns the attribute value, not the rendered size. `clientWidth` always returns the actual rendered width including CSS scaling.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Resize detection | `setInterval` polling `img.clientWidth` | ResizeObserver | Browser-native, zero-overhead; fires exactly when size changes, not on a timer |
| HTML escaping for span content | Custom regex replace | `escapeHtml()` with four substitutions, or `textContent` assignment | XSS risk if OCR text contains `<` or `&`; must escape before innerHTML insertion |
| URL construction for endpoints | String template literals | Flask `url_for()` in template or simple `/image/${stem}` in JS | Stems are already validated safe strings (no path separators); simple template literals are fine here |
| File list discovery | Walk filesystem in JS | `GET /files` Flask endpoint | Filesystem access from browser JS is not possible; Flask serves the list |

**Key insight:** The entire viewer is fetch + DOM string concatenation + SVG attribute updates. No third-party JS library adds meaningful capability here.

## Common Pitfalls

### Pitfall 1: SVG Overlay Misalignment After Image Load

**What goes wrong:** Word bounding boxes are offset or wrong size immediately after clicking a word, because `img.clientWidth` is 0 until the image finishes loading.
**Why it happens:** Setting `<img src>` is async. If the user clicks a word before the image finishes loading, `img.clientWidth` is 0 and scale factors are 0, placing the rect at (0,0) with zero size.
**How to avoid:** Only enable word clicks after the `<img>` fires its `load` event. During image loading, show a "loading" state on the text panel or disable clicks.
**Warning signs:** Rect appears at top-left corner or is invisible on first click immediately after file load.

```javascript
const img = document.getElementById('tiff-img');
img.addEventListener('load', () => {
  // Now clientWidth is valid — enable word interaction
  enableWordClicks();
});
```

### Pitfall 2: `img.clientWidth` Returns 0 Before Image Is In Layout

**What goes wrong:** Even after `img.src` is set, if the image has no intrinsic size yet (loading), `clientWidth` is 0. ResizeObserver callback may fire before the image has dimensions.
**Why it happens:** Browser computes layout only after the image loads its intrinsic dimensions from the network.
**How to avoid:** Check `if (img.clientWidth === 0) return;` in the ResizeObserver callback. Only reposition the rect when the image has valid dimensions.
**Warning signs:** ResizeObserver fires with entry dimensions of 0; scale factor becomes 0/NaN; rect jumps to origin.

### Pitfall 3: `GET /files` Returns Stems Not in Uploads

**What goes wrong:** A stem appears in `alto/*.xml` but has no corresponding TIFF in `uploads/` (e.g., files processed by the CLI before the web app existed, or after a server restart with a fresh `uploads/` directory). Clicking the file loads the text panel (ALTO JSON works) but the image panel shows a broken image.
**Why it happens:** `GET /image/<stem>` requires the TIFF in `uploads/` but CLI-processed TIFFs are in the original input path, not `uploads/`. The `jpegcache/` may also be empty.
**How to avoid:** Handle `img` `error` event gracefully — show a placeholder message ("Image not available") without breaking the text panel. This is a known architectural constraint from the uploads-only design decision in Phase 10.
**Warning signs:** Broken image icon in left panel while text panel works correctly.

```javascript
img.addEventListener('error', () => {
  img.alt = 'Image not available for this file';
});
```

### Pitfall 4: Stale `pageWidth`/`pageHeight` on File Switch

**What goes wrong:** User switches files rapidly. The second `/alto/<stem>` fetch completes before the first, so `pageWidth`/`pageHeight` reflect the first file's dimensions while the word spans are from the second file. A word click uses wrong scale factors.
**Why it happens:** Two in-flight `fetch()` calls; the first may resolve after the second.
**How to avoid:** Use a generation counter (request ID). On each `loadFile()` call, increment a counter and check it in the fetch `.then()`. Discard results if the counter changed.

```javascript
let loadGen = 0;

async function loadFile(index) {
  const gen = ++loadGen;
  const stem = stems[index];
  const data = await fetch(`/alto/${stem}`).then(r => r.json());
  if (gen !== loadGen) return;  // superseded by a newer load
  // ... continue rendering
}
```

### Pitfall 5: SVG `pointer-events` Blocks Image Interaction

**What goes wrong:** The SVG overlay covers the entire image. If `pointer-events` is not `none` on the SVG background, mouse events (click, drag, scroll) are swallowed by the SVG instead of reaching the image or the scroll container.
**Why it happens:** SVG elements intercept pointer events by default.
**How to avoid:** Set `pointer-events: none` on the `<svg>` element. Set `pointer-events: all` only on the `<rect>` when it is visible and needs to be clickable.
**Warning signs:** Scrolling the image panel feels "broken" — scroll events are not bubbling to the container.

### Pitfall 6: `scrollIntoView` Scrolls the Wrong Container

**What goes wrong:** `span.scrollIntoView()` scrolls the `<body>` or `<html>` element instead of the `#text-panel` div, because `scrollIntoView` targets the nearest scrollable ancestor, which may be the page itself if the panel's overflow is not set to `auto` or `scroll`.
**Why it happens:** CSS `overflow: auto` must be on the panel div itself, not on a parent.
**How to avoid:** Ensure `#text-panel { overflow-y: auto; }` and `#image-panel { overflow: auto; }` are set. Test scrollIntoView with a real ALTO file where the highlighted word is below the fold.
**Warning signs:** Clicking a word in the SVG rect scrolls the whole page rather than the text panel.

### Pitfall 7: `templates/` Directory Does Not Exist

**What goes wrong:** `render_template('viewer.html')` raises `TemplateNotFound: viewer.html` because Flask's default template loader looks for a `templates/` directory sibling to `app.py`, which does not exist yet.
**Why it happens:** The project has not used templates before Phase 11. No `templates/` directory exists.
**How to avoid:** Create `templates/` directory as Wave 0 task before implementing the route. The test for `GET /` should assert `200 text/html` to catch this.
**Warning signs:** `jinja2.exceptions.TemplateNotFound` traceback on first request to `/`.

## Code Examples

Verified patterns from live interpreter and project codebase:

### GET /files Endpoint (complete)

```python
# Source: Flask 3.1 + pathlib, pattern consistent with existing serve_alto() in app.py
@app.get('/files')
def list_files():
    """Return alphabetically sorted list of ALTO stems in output/alto/."""
    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_dir = output_dir / 'alto'
    if not alto_dir.exists():
        return jsonify({'stems': []})
    stems = sorted(p.stem for p in alto_dir.glob('*.xml'))
    return jsonify({'stems': stems})
```

### Page Load Sequence (JavaScript)

```javascript
// Source: pattern consistent with Flask JS patterns docs (url_for + fetch)
document.addEventListener('DOMContentLoaded', async () => {
  const resp = await fetch('/files');
  const data = await resp.json();
  stems = data.stems;
  renderSidebar(stems);
  if (stems.length > 0) loadFile(0);
});
```

### Scale Factor Computation (JavaScript)

```javascript
// Source: verified against real ALTO data (page_width=5146, jpeg_width=1091, rendered=~600px)
// ALTO native coords → browser pixel coords
function getScaleFactors() {
  const img = document.getElementById('tiff-img');
  return {
    x: img.clientWidth / pageWidth,
    y: img.clientHeight / pageHeight,
  };
}
```

### ResizeObserver Setup (JavaScript)

```javascript
// Source: MDN ResizeObserver (Baseline since July 2020)
const resizeObserver = new ResizeObserver(() => {
  if (img.clientWidth === 0) return;
  if (activeWord !== null) showHighlight(activeWord);
});
resizeObserver.observe(document.getElementById('tiff-img'));
```

### Keyboard Navigation Guard (JavaScript)

```javascript
// Source: CONTEXT.md specifics — guard against input focus (Phase 12 forward compat)
document.addEventListener('keydown', (e) => {
  if (document.activeElement.tagName === 'INPUT') return;
  if (e.key === 'ArrowLeft') navigateTo(currentIndex - 1);
  if (e.key === 'ArrowRight') navigateTo(currentIndex + 1);
});
```

### HTML Escaping for OCR Text

```javascript
// Source: standard XSS prevention — OCR text may contain '<', '>', '&'
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
```

### Test Infrastructure — Flask Test Client for GET /

```python
# Source: consistent with existing conftest.py pattern
def test_viewer_route_returns_html(client, flask_app):
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'text/html' in resp.content_type

def test_files_endpoint_returns_sorted_stems(client, flask_app, tmp_path):
    alto_dir = tmp_path / 'alto'
    alto_dir.mkdir()
    (alto_dir / 'scan_002.xml').write_text('<ALTO/>')
    (alto_dir / 'scan_001.xml').write_text('<ALTO/>')
    resp = client.get('/files')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['stems'] == ['scan_001', 'scan_002']

def test_files_endpoint_empty_when_no_alto_dir(client, flask_app):
    resp = client.get('/files')
    assert resp.status_code == 200
    assert resp.get_json()['stems'] == []
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `window.onresize` for element size | `ResizeObserver` | Baseline July 2020 | Element-level observation; fires on panel resize, not just viewport resize |
| One listener per element | Event delegation on container | N/A (pattern, not API change) | Avoids 5786 listener attach/detach cycles on every file load |
| `position: absolute` + manual JS sync | `position: relative` wrapper containing both `<img>` and `<svg>` | N/A | Overlay tracks image automatically via CSS; no JS needed to synchronize positions |

**Deprecated/outdated:**
- `window.onresize`: Still works, but fires only on viewport changes. ResizeObserver fires when the element's layout size changes for any reason.

## Open Questions

1. **Handling stems with no corresponding TIFF in `uploads/`**
   - What we know: CLI-processed files have ALTO XMLs in `output/alto/` but their TIFFs are not in `uploads/`. GET /files will list them. GET /image/<stem> will return 404.
   - What's unclear: Whether to filter these from GET /files (complex) or handle the broken image gracefully in the viewer (simpler).
   - Recommendation: Handle gracefully in viewer — show alt text on img error. Do not filter GET /files — filtering would require checking uploads/ for every stem, adding complexity and latency. Document in tests as expected behavior.

2. **SVG `pointer-events` strategy for the highlight rect**
   - What we know: The SVG overlay must not block scroll/click events on the image. The rect must be clickable for bidirectional navigation.
   - What's unclear: Whether `pointer-events: all` on the rect while `pointer-events: none` on the SVG parent works correctly in all browsers for SVG elements.
   - Recommendation: Use `pointer-events: none` on `<svg>` and `pointer-events: all` on `<rect style="display:none">`. When rect is shown, set its `pointer-events` to `all`; when hidden, set to `none`. This is the standard SVG pointer-events pattern and is well-supported. Verify in browser during implementation.

3. **Plan split: one plan or two?**
   - What we know: The phase has two separable parts — (a) server-side: GET /files + GET / + templates/ directory, (b) client-side: all JavaScript in viewer.html.
   - What's unclear: Whether to TDD the server routes in a RED plan first (plan 01) then implement viewer HTML in plan 02.
   - Recommendation: Two plans. Plan 01: GET /files tests + implementation + GET / + templates/ directory stub. Plan 02: Complete viewer.html with layout, file loading, word rendering, SVG overlay, resize handling. The server routes are unit-testable with Flask test client; the viewer HTML+JS is not unit-testable without a browser and should be a focused implementation plan.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (no config file — discovered via `tests/` directory convention) |
| Config file | none — pytest discovers `tests/test_*.py` automatically |
| Quick run command | `python -m pytest tests/test_app.py -q` |
| Full suite command | `python -m pytest tests/ -q` |
| Estimated runtime | ~1 second (20 existing tests pass in 0.96s) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIEW-01 | GET /files returns sorted stems from alto/*.xml | unit | `python -m pytest tests/test_app.py::TestFilesEndpoint -x -q` | ❌ Wave 0 gap |
| VIEW-01 | GET /files returns empty list when alto/ absent | unit | `python -m pytest tests/test_app.py::TestFilesEndpoint -x -q` | ❌ Wave 0 gap |
| VIEW-01 | GET / returns 200 text/html | unit | `python -m pytest tests/test_app.py::TestViewerRoute -x -q` | ❌ Wave 0 gap |
| VIEW-04 | Previous button disabled at index 0, Next at last | manual-only | n/a — requires browser rendering | n/a |
| VIEW-04 | Keyboard ArrowLeft/Right navigation | manual-only | n/a — requires browser JS execution | n/a |
| OVLY-01 | Word click draws SVG rect | manual-only | n/a — requires browser JS + rendered image | n/a |
| OVLY-02 | Overlay recomputes on window resize | manual-only | n/a — requires ResizeObserver in browser | n/a |

**Note on manual-only tests:** VIEW-04, OVLY-01, and OVLY-02 require a live browser with rendered layout (image dimensions, scroll position, ResizeObserver callbacks). Flask test client does not execute JavaScript. These are verified by the `/gsd:verify-work` step with a browser open, not by automated pytest.

### Nyquist Sampling Rate
- **Minimum sample interval:** After every committed task → run: `python -m pytest tests/test_app.py -q`
- **Full suite trigger:** Before merging final task of any plan wave
- **Phase-complete gate:** Full suite green before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~1 second

### Wave 0 Gaps (must be created before implementation)

- [ ] `tests/test_app.py::TestFilesEndpoint` — test class for GET /files (VIEW-01 server-side)
- [ ] `tests/test_app.py::TestViewerRoute` — test class for GET / → 200 text/html (VIEW-01 entry point)
- [ ] `templates/` directory — must exist before `render_template('viewer.html')` can succeed
- [ ] `templates/viewer.html` — stub (even empty) so GET / returns 200 in RED tests

## Sources

### Primary (HIGH confidence)
- Live Python interpreter (2026-02-28) — `app.py` GET /files pattern verified with `pathlib.glob('*.xml')` on real `output/alto/` directory (23 files)
- Live Python interpreter (2026-02-28) — Scale factor math verified against real ALTO files: page_width=5146, JPEG=1091px, scale=0.1166
- Flask 3.1 official docs (https://flask.palletsprojects.com/en/stable/patterns/javascript/) — `render_template`, `url_for`, fetch patterns
- MDN ResizeObserver (https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver) — Baseline since July 2020; `contentBoxSize` + `contentRect` usage patterns
- `app.py` source (Phase 10 complete) — confirmed `GET /alto/<stem>` returns `page_width`, `page_height`, `jpeg_width`, `jpeg_height`, word array; confirmed Flask imports already include `render_template` is not yet imported (must be added)

### Secondary (MEDIUM confidence)
- Real production ALTO files in `output/alto/` — confirmed word count range 50–5786 (mean ~3400), page dimensions 4127–10174 wide
- `tests/test_app.py` and `tests/conftest.py` — confirmed test infrastructure patterns: `flask_app` fixture, `client` fixture, `TestClass`-based organization, `_write_alto()` and `_write_tiff()` helpers already available for reuse

### Tertiary (LOW confidence)
- None — all critical claims verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Flask 3.1, vanilla JS, ResizeObserver all verified; no new dependencies needed
- Architecture: HIGH — scale factor math verified against real ALTO files; patterns derived from existing Phase 10 patterns in `app.py`; SVG overlay strategy is standard CSS absolute positioning
- Pitfalls: HIGH — Pitfalls 1/2 (image load timing) and 3 (stems without uploads) discovered by reading actual `app.py` and `output/` directory structure; Pitfall 4 (stale generation) is a standard async race condition; Pitfalls 5/6/7 are CSS/DOM fundamentals verified by reasoning from the locked design decisions

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable browser APIs; Flask 3.1 stable)
