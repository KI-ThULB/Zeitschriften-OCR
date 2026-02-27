# Phase 10: TIFF and ALTO Data Endpoints - Research

**Researched:** 2026-02-27
**Domain:** Flask image serving (Pillow JPEG rendering + disk cache) and ALTO XML parsing (lxml)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**JPEG Scaling**
- Scale to max 1600px on longest side (handles both portrait and landscape TIFFs correctly)
- Source TIFFs served from `uploads/` subfolder only — no fallback to CLI input path
- JPEG dimensions (jpeg_width, jpeg_height) returned by `/alto/<stem>` JSON — no custom response headers on the image endpoint

**JPEG Caching**
- Cache rendered JPEG as `<stem>.jpg` in a `jpegcache/` subfolder inside the output directory
- No automatic cache invalidation — TIFFs don't change after upload; operator deletes `jpegcache/` manually if needed
- On request: serve cached file if exists, otherwise render from TIFF and write cache

**ALTO Word JSON Shape**
- Flat array — all words in one list, no block/line nesting
- Top-level response: `{ page_width, page_height, jpeg_width, jpeg_height, words: [...] }`
- Per-word fields: `id`, `content`, `hpos`, `vpos`, `width`, `height`, `confidence`
- Words with no ALTO confidence attribute: include with `confidence: null` (not excluded, not coerced to 0)

**Error Handling**
- Missing stem (TIFF or ALTO XML not found): `404` with JSON body `{"error": "not found", "stem": "<stem>"}`
- Corrupt or unreadable TIFF (Pillow failure): `500` with JSON error body
- Malformed ALTO XML (parse failure): `500` with JSON error body
- Path traversal in stem (contains `/` or `..`): `400` reject immediately

**ALTO JSON Caching**
- No disk cache for ALTO JSON — parse XML on every request
- ALTO XML files are small (10–100 KB) and fast to parse; Phase 12 edits them directly, making a JSON cache a stale-data risk

### Claude's Discretion
- Exact JPEG quality setting (suggest 85)
- Pillow resampling filter (LANCZOS recommended for downscaling)
- JSON error body field names beyond `error` and `stem`
- How jpeg_width/jpeg_height are computed (from PIL image size after resize)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEW-02 | Clicking a file shows the TIFF rendered as an image in the left panel | GET /image/<stem> serves scaled JPEG from uploads/; disk-cached in jpegcache/; Pillow resize + save verified against live interpreter |
| VIEW-03 | Clicking a file shows the OCR text in the right panel, extracted word-by-word from the ALTO XML | GET /alto/<stem> parses ALTO XML with lxml; returns flat word array with page/jpeg dimensions; pattern verified against real ALTO files |
</phase_requirements>

## Summary

Phase 10 adds two read-only GET endpoints to the existing Flask 3.1 `app.py`. The `/image/<stem>` endpoint loads a TIFF from `uploads/`, scales it to max 1600px on the longest side using Pillow's LANCZOS filter, saves the JPEG to `jpegcache/` for subsequent requests, and serves the file with `send_file()`. The `/alto/<stem>` endpoint parses the corresponding `alto/<stem>.xml` using lxml, extracts the Page WIDTH/HEIGHT and all String elements, and returns a flat JSON word array with the four required dimension fields. No new dependencies are required: Pillow, lxml, and Flask are all already in `requirements.txt`.

The stack is completely verified against the live interpreter. Pillow 11.1.0 is installed; `Image.resize()` with `Image.Resampling.LANCZOS` and `Image.save(..., format='JPEG', quality=85)` work correctly. The lxml ALTO String attribute access pattern (`elem.get('WC')` returning `None` when absent, convertible to Python `None` in jsonify) is verified against real project ALTO files which use float WC values (0.0–1.0). A real production ALTO file has 2333 String elements — well within flat array performance limits for the browser.

The two critical design decisions: (1) `jpegcache/` sits alongside `uploads/` and `alto/` inside the output directory; (2) the `/alto/` response includes `jpeg_width`/`jpeg_height` so the viewer in Phase 11 can compute the overlay scale factor (`scale_x = rendered_width / page_width`) without any additional state or headers. Both endpoints must reject stems containing `/` or `..` with a 400 before any filesystem access.

**Primary recommendation:** Implement both endpoints by extending `app.py` in-place. Use Pillow `Image.open()` → `convert('RGB')` → `resize()` → `save(format='JPEG', quality=85)` for the image endpoint, and lxml `etree.parse()` → `root.find(Page)` → `root.iter(String)` for the ALTO endpoint. Both patterns are already used in `pipeline.py` — no new patterns needed.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | >=11.1.0 (11.1.0 installed) | TIFF loading, scaling, JPEG encoding | Already in requirements.txt; `Image.open()` handles all TIFF variants; `resize(LANCZOS)` optimal for downscaling |
| lxml | >=5.3.0 (installed) | ALTO XML parsing, Page/String element access | Already in requirements.txt; used throughout pipeline.py; validated against real ALTO files |
| Flask | >=3.1.0 (installed) | Route definitions, `send_file()`, `jsonify()` | Already the app server; `send_file()` handles mimetype, etag, range for image serving |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | File path construction, existence checks | Already used everywhere in app.py and pipeline.py |
| io.BytesIO | stdlib | In-memory JPEG buffer (only if serving from memory) | Not needed — cache hit serves from disk path, cache miss writes to disk then serves from disk |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `send_file(path)` | `send_file(BytesIO)` | Path gives etag + Last-Modified for free; BytesIO needed only if not writing to disk. Disk cache means always use path. |
| `lxml.etree` | `xml.etree.ElementTree` | stdlib ET works but lxml is already the project standard and handles large files faster |

**Installation:**
```bash
# No new dependencies — all already in requirements.txt
pip install -r requirements.txt
```

## Architecture Patterns

### Recommended Project Structure

No new files or directories in the source tree. Two new additions to the runtime output directory:

```
output/                         # app.config['OUTPUT_DIR']
├── uploads/                    # existing — source TIFFs from POST /upload
├── alto/                       # existing — ALTO XML files from OCR
└── jpegcache/                  # NEW — scaled JPEG files, one per TIFF stem
    └── <stem>.jpg
```

Both new routes are added directly to `app.py` (no new modules). The `jpegcache/` directory is created lazily on first image request (same pattern as `uploads/` creation in `__main__`).

### Pattern 1: JPEG Endpoint — Cache-Then-Serve

**What:** Check `jpegcache/<stem>.jpg` exists. If yes, serve it. If no, open TIFF, scale, save to cache, then serve from cache path.
**When to use:** All requests to `GET /image/<stem>`

```python
# Source: verified against Pillow 11.1.0 + Flask 3.1 live interpreter
@app.get('/image/<stem>')
def serve_image(stem):
    # 1. Reject path traversal immediately
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    output_dir = Path(app.config['OUTPUT_DIR'])
    tiff_path = output_dir / 'uploads' / (stem + '.tif')
    if not tiff_path.exists():
        # Try .tiff extension
        tiff_path = output_dir / 'uploads' / (stem + '.tiff')
    if not tiff_path.exists():
        return jsonify({'error': 'not found', 'stem': stem}), 404

    cache_dir = output_dir / 'jpegcache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / (stem + '.jpg')

    if cache_path.exists():
        return send_file(cache_path, mimetype='image/jpeg')

    # Render JPEG from TIFF
    try:
        img = Image.open(tiff_path)
        # Convert to RGB — handles CMYK, palette (P), RGBA, etc.
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Scale to max 1600px on longest side
        MAX_PX = 1600
        w, h = img.size
        longest = max(w, h)
        if longest > MAX_PX:
            scale = MAX_PX / longest
            img = img.resize(
                (round(w * scale), round(h * scale)),
                Image.Resampling.LANCZOS,
            )

        img.save(str(cache_path), format='JPEG', quality=85)
    except Exception as exc:
        return jsonify({'error': 'render failed', 'detail': str(exc)}), 500

    return send_file(cache_path, mimetype='image/jpeg')
```

### Pattern 2: ALTO JSON Endpoint — Parse-On-Every-Request

**What:** Open `alto/<stem>.xml`, parse with lxml, extract Page dimensions and all String elements, return JSON. No caching.
**When to use:** All requests to `GET /alto/<stem>`

```python
# Source: verified against lxml 5.3.0 + real project ALTO files (2333 words)
@app.get('/alto/<stem>')
def serve_alto(stem):
    # 1. Reject path traversal immediately
    if '/' in stem or '..' in stem:
        return jsonify({'error': 'invalid stem'}), 400

    output_dir = Path(app.config['OUTPUT_DIR'])
    alto_path = output_dir / 'alto' / (stem + '.xml')

    if not alto_path.exists():
        return jsonify({'error': 'not found', 'stem': stem}), 404

    try:
        from lxml import etree
        root = etree.parse(str(alto_path)).getroot()
    except Exception as exc:
        return jsonify({'error': 'parse failed', 'detail': str(exc)}), 500

    ns = 'http://schema.ccs-gmbh.com/ALTO'  # pipeline.ALTO21_NS

    # Page dimensions (from Page element WIDTH/HEIGHT attributes)
    page = root.find(f'.//{{{ns}}}Page')
    if page is None:
        return jsonify({'error': 'no Page element in ALTO XML'}), 500
    page_width = int(page.get('WIDTH', 0))
    page_height = int(page.get('HEIGHT', 0))

    # Compute jpeg dimensions from cache (must exist if we're rendering)
    cache_path = Path(app.config['OUTPUT_DIR']) / 'jpegcache' / (stem + '.jpg')
    if cache_path.exists():
        from PIL import Image as _Image
        with _Image.open(cache_path) as _img:
            jpeg_width, jpeg_height = _img.size
    else:
        # JPEG not yet rendered — return 0,0 as placeholder
        jpeg_width, jpeg_height = 0, 0

    # Flat word array — all String elements, document order
    words = []
    for i, elem in enumerate(root.iter(f'{{{ns}}}String')):
        wc_raw = elem.get('WC')
        words.append({
            'id': f'w{i}',
            'content': elem.get('CONTENT', ''),
            'hpos': int(elem.get('HPOS', 0)),
            'vpos': int(elem.get('VPOS', 0)),
            'width': int(elem.get('WIDTH', 0)),
            'height': int(elem.get('HEIGHT', 0)),
            'confidence': float(wc_raw) if wc_raw is not None else None,
        })

    return jsonify({
        'page_width': page_width,
        'page_height': page_height,
        'jpeg_width': jpeg_width,
        'jpeg_height': jpeg_height,
        'words': words,
    })
```

**Note on jpeg_width/jpeg_height in ALTO response:** The CONTEXT.md decision is that these come from `PIL image.size` after resize. The approach above reads them from the cached JPEG file. If the JPEG hasn't been rendered yet when `/alto/` is called first, return 0,0 as a fallback — the viewer will call `/image/` first in practice (Phase 11 will always load the image before the word overlay). An alternative: compute the dimensions from TIFF + scale formula without opening the cache, which avoids the dependency ordering issue. Document this as an open question for the planner.

### Pattern 3: Path Traversal Rejection

**What:** Stems containing `/` or `..` are rejected with 400 before any filesystem access.
**When to use:** First guard in both endpoints.

```python
# Verified: '../secret', 'folder/scan', 'scan..xml' all detected
if '/' in stem or '..' in stem:
    return jsonify({'error': 'invalid stem'}), 400
```

**Why this is sufficient:** Flask's `<stem>` routing captures the URL path segment between `/image/` and the end of the path. A URL like `/image/../etc/passwd` is handled by the HTTP layer before Flask routing; the stem value never contains `/` in a properly mounted Flask app. The `..` check covers edge cases in stem strings containing literal double-dots.

### Pattern 4: TIFF Image Mode Normalization

**What:** TIFF files can be RGB, L (grayscale), CMYK, P (palette), RGBA, or 1 (bilevel). JPEG format only accepts RGB and L. Must convert before save.
**When to use:** Always, before `img.save(format='JPEG')`

```python
# Verified: CMYK, P, RGBA all need convert; L can save directly as JPEG
if img.mode not in ('RGB', 'L'):
    img = img.convert('RGB')
```

### Anti-Patterns to Avoid

- **Serving from BytesIO instead of disk path:** Cache the JPEG to disk and serve via `send_file(path)`. Path-based serving gives etag, Last-Modified, and conditional GETs for free. BytesIO serving loses all HTTP caching benefits.
- **Returning jpeg dimensions in image response headers:** The CONTEXT.md decision is to include them in the `/alto/` JSON, not as custom image endpoint headers. Do not add `X-JPEG-Width` etc.
- **TIFF served from anywhere except uploads/:** The decision is `uploads/` only. Do not fall back to searching the full output directory or the CLI input path.
- **Caching the ALTO JSON:** Phase 12 writes directly to `alto/<stem>.xml`; a JSON cache would immediately go stale. Parse on every request.
- **Using `thumbnail()` instead of `resize()`:** `thumbnail()` modifies in-place and uses BICUBIC. `resize()` with explicit computed dimensions and LANCZOS gives better downscale quality and returns a new image (safe for chaining).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JPEG encoding from TIFF | Custom TIFF decoder | `Pillow Image.open() + Image.save(format='JPEG')` | Pillow handles all TIFF variants (BigTIFF, multi-page, CMYK, palette); hand-rolled decoders miss edge cases |
| HTTP caching headers | Manual ETag/Last-Modified logic | `Flask send_file(path)` | Flask + Werkzeug compute ETag from file mtime/size and handle If-None-Match automatically |
| XML namespace handling | String replace for namespace queries | `lxml etree` with `{ns}TagName` syntax | Already the project standard; etree handles namespaced attributes correctly |
| Path safety | os.path.abspath comparison | Simple `'/' in stem or '..' in stem` check | Stem is a single path component from URL routing, not a full path; simple string checks are sufficient and don't introduce false negatives |

**Key insight:** All required capabilities are already in the installed library set. This phase is about adding routes to `app.py`, not adding new dependencies.

## Common Pitfalls

### Pitfall 1: TIFF Mode Not RGB — JPEG Save Fails
**What goes wrong:** `img.save(format='JPEG')` raises `OSError: cannot write mode RGBA as JPEG` (or CMYK, P, 1).
**Why it happens:** Archival TIFFs are commonly CMYK (print-optimized scans) or palette-mode. JPEG only accepts RGB and L.
**How to avoid:** Always `img.convert('RGB')` unless `img.mode in ('RGB', 'L')` before saving to JPEG.
**Warning signs:** Unhandled exception in JPEG render path; 500 response on first request for a non-RGB TIFF.

### Pitfall 2: Multi-Page TIFF — Only Frame 0 Rendered
**What goes wrong:** `Image.open()` on a multi-page TIFF returns a lazy object. `img.size` gives the first frame's size, which is correct. But if the pipeline used a specific frame, the rendered JPEG should match.
**Why it happens:** Archival scans are almost always single-page TIFFs; this is consistent with `pipeline.py load_tiff()` which also uses frame 0.
**How to avoid:** Call `img.load()` or rely on implicit load via `img.size`/`img.mode`. The first frame approach matches existing pipeline behavior.
**Warning signs:** Wrong content in JPEG (showing wrong frame) — unlikely in practice for this corpus.

### Pitfall 3: Stem Case Mismatch Between TIFF Upload Filename and ALTO XML
**What goes wrong:** `/image/Scan_001` tries to open `uploads/Scan_001.tif` but the file was uploaded as `scan_001.tif` (lowercased by `secure_filename` + the `.lower()` stem normalization in `upload()`).
**Why it happens:** `app.py upload()` normalizes stems to lowercase: `stem = Path(filename).stem.lower()`. The ALTO XML is written with the lowercase stem. But the uploaded TIFF filename is saved with `secure_filename(f.filename)` (not lowercased). The TIFF file on disk retains the original casing.
**How to avoid:** In the image endpoint, after stem is received, try `uploads/<stem>.tif` first, then `uploads/<stem>.tiff`. If not found, also try the lower-cased stem. Check what `upload()` actually saves — it calls `f.save(upload_dir / filename)` where `filename = secure_filename(f.filename)` (not lowercased). The stem is lowercased for the `_jobs` dict key, but the file is saved with the original (secure) filename. This creates a mismatch: `_jobs` key is lowercase stem, but TIFF file is at `uploads/<original_filename>`.
**Warning signs:** 404 on `/image/<lowercase_stem>` even though TIFF was uploaded. Must read `_jobs[stem]['filename']` to get the actual filename, or scan `uploads/` for a case-insensitive match.

**IMPORTANT IMPLICATION:** The `/image/<stem>` endpoint cannot simply construct `uploads/<stem>.tif` — it must look up the actual filename via `_jobs[stem]['filename']` or scan the uploads directory. This is a design constraint the planner must address.

### Pitfall 4: jpegcache/ Not Created Before First Request
**What goes wrong:** `cache_path.write_bytes(...)` or `img.save(cache_path)` raises `FileNotFoundError` if `jpegcache/` doesn't exist.
**Why it happens:** The `__main__` block in `app.py` creates `uploads/` and `alto/` but not `jpegcache/`. Tests with fresh tmp_path won't have it.
**How to avoid:** Call `cache_dir.mkdir(parents=True, exist_ok=True)` at the start of every cache-miss path in the image endpoint.
**Warning signs:** `FileNotFoundError` on first image request after server restart.

### Pitfall 5: WC Attribute Float Precision
**What goes wrong:** ALTO `WC="0.90"` → Python `float('0.90')` → JSON `0.9` (trailing zero dropped). This is correct JSON and not a bug, but the viewer must handle any float 0.0–1.0.
**Why it happens:** Python `float` and JSON number serialization drops trailing zeros.
**How to avoid:** Do nothing — `float(wc_raw)` is correct. Document in tests that `WC="0.95"` → `confidence: 0.95` (not `"0.95"` as string).
**Warning signs:** None — this is expected behavior.

### Pitfall 6: ALTO XML Without Page WIDTH/HEIGHT
**What goes wrong:** `int(page.get('WIDTH', 0))` returns 0 if the attribute is missing or malformed.
**Why it happens:** Corrupt or hand-edited ALTO files may lack Page dimensions.
**How to avoid:** Return 500 with informative error if `page_width == 0 or page_height == 0`. Do not return a response with 0 dimensions — the viewer would compute scale_x = infinity.
**Warning signs:** Scale factor computation fails in viewer (Phase 11) producing out-of-bounds overlays.

### Pitfall 7: Filename Lookup for Image Endpoint
**What goes wrong:** `_jobs` dict is module-level state and persists across server restarts only in memory. If the server restarts, `_jobs` is empty even if `uploads/` contains TIFFs.
**Why it happens:** Phase 9 design: `_jobs` is populated by `POST /upload`, not pre-loaded from disk.
**How to avoid:** The image endpoint must handle the case where `_jobs[stem]` doesn't exist. Fall back to scanning `uploads/` for a file whose stem (lowercased) matches the requested stem. This handles the server-restart case.
**Warning signs:** 404 on valid stems after server restart.

## Code Examples

Verified patterns from live interpreter (Pillow 11.1.0, Flask 3.1, lxml 5.3.0):

### Scale Computation (max 1600px on longest side)
```python
# Source: verified in live Python interpreter 2026-02-27
MAX_PX = 1600
w, h = img.size  # e.g., (5146, 7548) for a real ALTO page
longest = max(w, h)
if longest > MAX_PX:
    scale = MAX_PX / longest
    new_w = round(w * scale)
    new_h = round(h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
jpeg_width, jpeg_height = img.size
# Portrait 1200x2000 → 960x1600; landscape 4000x2500 → 1600x1000
```

### JPEG Save to Disk
```python
# Source: verified against Pillow 11.1.0
img.save(str(cache_path), format='JPEG', quality=85)
```

### Send File from Disk
```python
# Source: verified against Flask 3.1 — path gives etag/Last-Modified
from flask import send_file
return send_file(cache_path, mimetype='image/jpeg')
```

### ALTO XML Parse — Page Dimensions
```python
# Source: verified against real project ALTO files (page_width=5146, page_height=7548)
from lxml import etree
root = etree.parse(str(alto_path)).getroot()
ns = 'http://schema.ccs-gmbh.com/ALTO'
page = root.find(f'.//{{{ns}}}Page')
page_width = int(page.get('WIDTH', 0))
page_height = int(page.get('HEIGHT', 0))
```

### ALTO XML Parse — Word Array
```python
# Source: verified against real project ALTO files (2333 String elements)
words = []
for i, elem in enumerate(root.iter(f'{{{ns}}}String')):
    wc_raw = elem.get('WC')  # None if attribute absent
    words.append({
        'id': f'w{i}',
        'content': elem.get('CONTENT', ''),
        'hpos': int(elem.get('HPOS', 0)),
        'vpos': int(elem.get('VPOS', 0)),
        'width': int(elem.get('WIDTH', 0)),
        'height': int(elem.get('HEIGHT', 0)),
        'confidence': float(wc_raw) if wc_raw is not None else None,
    })
```

### Path Traversal Check
```python
# Source: verified against test cases '../secret', 'folder/scan', 'scan..xml'
if '/' in stem or '..' in stem:
    return jsonify({'error': 'invalid stem'}), 400
```

### TIFF Mode Normalization
```python
# Source: verified CMYK, P, RGBA all fail JPEG save without convert
if img.mode not in ('RGB', 'L'):
    img = img.convert('RGB')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Image.ANTIALIAS` | `Image.Resampling.LANCZOS` | Pillow 9.1.0 (2022) | Old constant removed; must use `Image.Resampling.LANCZOS` |
| `thumbnail()` for scaling | `resize()` with explicit dimensions | N/A | `thumbnail()` modifies in-place and uses BICUBIC; `resize()` with LANCZOS is explicit and returns a new image |

**Deprecated/outdated:**
- `Image.ANTIALIAS`: Removed in Pillow 10.0.0; use `Image.Resampling.LANCZOS`. The project has Pillow >=11.1.0 — ANTIALIAS will cause `AttributeError`.

## Open Questions

1. **How to resolve TIFF filename from stem in /image/ endpoint**
   - What we know: `upload()` saves TIFFs with `secure_filename(f.filename)` (original case) but the `_jobs` dict key is `stem.lower()`. The actual filename is stored in `_jobs[stem]['filename']`.
   - What's unclear: After server restart, `_jobs` is empty. Should the endpoint scan `uploads/` for files whose lowercased stem matches? Or should Phase 10 pre-populate `_jobs` from disk on startup?
   - Recommendation: In the endpoint, first try `_jobs[stem]['filename']` if it exists. If not (server restart), scan `uploads/` for `<stem>.tif` or `<stem>.tiff` (case-insensitive). This is the most robust approach without adding startup complexity.

2. **jpeg_width/jpeg_height when JPEG not yet rendered**
   - What we know: The `/alto/` response must include `jpeg_width` and `jpeg_height`. These come from the JPEG after resize, not from the TIFF directly (they differ due to scaling).
   - What's unclear: If a client calls `/alto/<stem>` before `/image/<stem>`, the JPEG cache doesn't exist yet.
   - Recommendation: Compute the JPEG dimensions from the TIFF size + scale formula without opening the cache file. This eliminates the ordering dependency: `jpeg_width = round(tiff_w * (1600 / max(tiff_w, tiff_h)))` if `max > 1600`, else `jpeg_width = tiff_w`. The planner should task this as a helper function shared between endpoints.

3. **`jpegcache/` directory creation at startup**
   - What we know: The `__main__` block in `app.py` currently creates `uploads/` and `alto/` but not `jpegcache/`.
   - What's unclear: Whether to create it at startup or lazily per-request.
   - Recommendation: Create lazily in the endpoint with `mkdir(parents=True, exist_ok=True)` — consistent with the pattern in `upload()` which does the same for `upload_dir`. Also add to the `__main__` block for completeness.

## Sources

### Primary (HIGH confidence)
- Live Python interpreter, Pillow 11.1.0 — `Image.resize()`, `Image.save(format='JPEG', quality=85)`, `Image.Resampling.LANCZOS`, mode conversion verified
- Live Python interpreter, Flask 3.1 — `send_file(path, mimetype='image/jpeg')`, `jsonify()` with `None` values verified
- Live Python interpreter, lxml — `etree.parse()`, `root.find()`, `root.iter()`, `elem.get('WC')` returning None verified against real project ALTO files
- Real project ALTO XML (`output/alto/Ve_Volk_165945877_1957_Band_1-0001.xml`) — confirmed WC float format, Page WIDTH/HEIGHT attributes, 2333 String elements

### Secondary (MEDIUM confidence)
- `app.py` source code — confirmed existing stem lowercasing, `_jobs` dict structure, `send_file` import already present in Flask imports
- `pipeline.py` source code — confirmed `ALTO21_NS = 'http://schema.ccs-gmbh.com/ALTO'`, `count_words()` iteration pattern matches word array extraction pattern

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and verified against live interpreter
- Architecture: HIGH — patterns verified against real ALTO files and live Flask/Pillow APIs
- Pitfalls: HIGH — stem/filename mismatch (Pitfall 3 and 7) discovered by reading actual `app.py upload()` code; TIFF mode issue verified with CMYK/RGBA tests

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (stable libraries: Pillow, lxml, Flask)
