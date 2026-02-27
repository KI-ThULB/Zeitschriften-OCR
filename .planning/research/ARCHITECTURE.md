# Architecture Research: v1.4 Web Viewer — Flask + pipeline.py Integration

**Domain:** Local Flask web app wrapping existing batch OCR CLI (pipeline.py)
**Researched:** 2026-02-27
**Confidence:** HIGH — conclusions drawn from direct codebase inspection (pipeline.py 1,146 lines), real ALTO XML output samples, and Flask 3.1.x official documentation.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Browser (localhost)                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Upload UI   │  │ Progress UI  │  │  Side-by-Side Viewer   │ │
│  │  (drag-drop) │  │  (SSE recv)  │  │  TIFF + ALTO text/bbox │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬─────────────┘ │
│         │ POST /upload     │ GET /stream          │ GET /files   │
│         │                  │ EventSource          │ GET /image/  │
│         │                  │                      │ GET /alto/   │
└─────────┼──────────────────┼──────────────────────┼─────────────┘
          │                  │                      │
┌─────────▼──────────────────▼──────────────────────▼─────────────┐
│                        app.py (Flask 3.1.x)                      │
│                                                                  │
│  POST /upload          → queue TIFF path, return 202             │
│  POST /run             → launch background OCR thread, return 202│
│  GET  /stream          → SSE generator, reads from queue         │
│  GET  /files           → list output/alto/*.xml → JSON           │
│  GET  /image/<stem>    → TIFF→JPEG thumbnail, return bytes       │
│  GET  /alto/<stem>     → parse ALTO XML → JSON word list         │
│  POST /alto/<stem>     → receive correction, write ALTO XML      │
│                                                                  │
│  Shared state (module-level, single-process):                    │
│    _ocr_queue: queue.Queue  (thread-safe, SSE reads from here)   │
│    _ocr_running: threading.Event                                 │
└──────────────┬───────────────────────────────────────────────────┘
               │ import (direct function calls)
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      pipeline.py                                 │
│                                                                  │
│  Functions used by app.py:                                       │
│    process_tiff()     — called in background thread             │
│    run_batch()        — NOT used directly (see note below)       │
│    load_tiff()        — used for TIFF→JPEG serving               │
│    validate_tesseract() — called once at Flask startup           │
│    load_xsd()         — called once at Flask startup             │
│    validate_alto_file() — called after each OCR completes        │
│    discover_tiffs()   — used for file listing                    │
│                                                                  │
│  Functions NOT used by app.py:                                   │
│    main()             — CLI entry point, irrelevant to web       │
│    write_error_log()  — replaced by in-memory error state        │
│    write_report()     — not needed for single-file web flow      │
└─────────────────────────────────────────────────────────────────┘
               │ writes
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Filesystem                                 │
│                                                                  │
│  input_dir/          (user-configured at Flask startup)          │
│    scan_001.tif                                                  │
│    scan_002.tif                                                  │
│                                                                  │
│  output_dir/alto/    (user-configured at Flask startup)          │
│    scan_001.xml      (ALTO 2.1 CCS-GmbH namespace, pixel coords) │
│    scan_002.xml                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration: Import vs Subprocess

**Decision: Import pipeline.py directly (tight coupling). Do not use subprocess.**

**Rationale:**

Subprocess would require: serializing arguments to CLI flags, parsing stdout for progress, and managing stderr. The pipeline functions are already Python with clean signatures. Importing is simpler and faster — no process spawn overhead per file.

The one real risk with direct import is that `process_tiff()` was designed to be called inside `ProcessPoolExecutor` (subprocess spawn on macOS). In the web context, each file is processed in a **background thread** (not a subprocess), so `process_tiff()` must not crash the Flask process. It must `raise` on error (which it already does — the CLI's `sys.exit` was fixed in v1.1) and the caller thread must catch the exception.

**Concrete import surface:**

```python
# In app.py
from pipeline import (
    process_tiff,
    load_tiff,
    validate_tesseract,
    load_xsd,
    validate_alto_file,
    discover_tiffs,
    ALTO21_NS,
)
```

`run_batch()` is NOT imported. The web app calls `process_tiff()` for each file directly, with its own progress tracking via `queue.Queue`. This avoids the `ProcessPoolExecutor` complexity — parallelism is unnecessary in the UI use case (operator watches one file at a time).

**Why not ProcessPoolExecutor in the web context:**

`run_batch()` uses `ProcessPoolExecutor` with `as_completed()`. In a Flask request handler, spawning a subprocess pool blocks the request thread and progress updates can only happen via stdout (which the web can't read in real-time without subprocess pipe polling). A simple background thread calling `process_tiff()` sequentially for each queued TIFF is correct for the single-operator local use case.

---

## Progress Streaming: SSE (Server-Sent Events)

**Decision: Server-Sent Events (SSE) via Flask streaming generator. Not WebSocket, not polling.**

**Rationale:**

| Mechanism | Verdict | Reason |
|-----------|---------|--------|
| SSE (EventSource) | USE THIS | One-way server→browser, native browser API, single HTTP connection, works with Flask streaming generators, no library needed |
| WebSocket | Too heavy | Requires flask-socketio or websockets library; bidirectional not needed; adds SocketIO.js dependency |
| Polling (setInterval fetch) | Avoid | Introduces latency gaps; wastes requests; SSE is simpler to implement correctly |

**SSE wire format (text/event-stream):**

Each event the server yields must follow this format:

```
data: {"done": 1, "total": 5, "pct": 20, "eta_s": 40, "file": "scan_001.tif", "status": "ok"}\n\n
```

Named events allow the client to distinguish progress from completion:

```
event: progress\ndata: {...}\n\n
event: complete\ndata: {"processed": 5, "failed": 0}\n\n
event: error\ndata: {"file": "scan_003.tif", "message": "..."}\n\n
```

**Flask SSE endpoint pattern:**

```python
import queue
import threading

_ocr_queue: queue.Queue = queue.Queue()
_ocr_running = threading.Event()

@app.get('/stream')
def stream():
    def generate():
        while True:
            try:
                msg = _ocr_queue.get(timeout=30)
            except queue.Empty:
                yield ': keepalive\n\n'   # SSE comment = keep-alive ping
                continue
            if msg is None:              # sentinel: OCR batch done
                yield 'event: complete\ndata: {}\n\n'
                break
            yield f'event: progress\ndata: {json.dumps(msg)}\n\n'
    return app.response_class(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
```

**Background OCR thread pattern:**

```python
@app.post('/run')
def run_ocr():
    if _ocr_running.is_set():
        return {'error': 'already running'}, 409
    tiff_paths = list(_queued_tiffs)  # copy the queue
    _ocr_running.set()

    def worker():
        try:
            for i, path in enumerate(tiff_paths):
                try:
                    process_tiff(path, output_dir, lang, psm, padding,
                                 no_crop=False, adaptive_threshold=False)
                    _ocr_queue.put({'done': i+1, 'total': len(tiff_paths),
                                    'file': path.name, 'status': 'ok'})
                except Exception as e:
                    _ocr_queue.put({'done': i+1, 'total': len(tiff_paths),
                                    'file': path.name, 'status': 'error',
                                    'message': str(e)})
        finally:
            _ocr_queue.put(None)  # sentinel
            _ocr_running.clear()

    threading.Thread(target=worker, daemon=True).start()
    return {'status': 'started'}, 202
```

**Important:** `X-Accel-Buffering: no` header prevents nginx (if present) from buffering the SSE stream. `Cache-Control: no-cache` prevents browser caching. The `: keepalive` comment keeps the connection alive during long OCR operations (Tesseract on a 200MB TIFF takes 10-30 seconds per file).

**Browser client pattern:**

```javascript
const source = new EventSource('/stream');
source.addEventListener('progress', e => {
    const d = JSON.parse(e.data);
    updateProgressBar(d.done, d.total, d.pct);
});
source.addEventListener('complete', e => {
    source.close();
    refreshFileList();
});
```

---

## TIFF to JPEG Serving for Large Files

**Decision: On-demand thumbnail generation using Pillow `Image.thumbnail()` with `Image.Resampling.LANCZOS`. Serve from memory (BytesIO). Do NOT cache to disk.**

**The problem:** Input TIFFs are 117–240 MB each, at 400–600 DPI. A 5146x7548 pixel page at 400 DPI (verified from real output) must be downscaled to browser-displayable size (typically 1024–2000px wide) without loading the full raster into RAM unnecessarily.

**Memory math for a 5146x7548 TIFF:**
- Stored as RGB: 5146 × 7548 × 3 bytes = ~116 MB decompressed
- Thumbnail at 1200px wide (aspect-preserved): ~1200 × 1760 × 3 = ~6 MB
- Pillow `thumbnail()` uses lazy decoding — it does NOT load the full image before scaling on JPEG/PNG input, but TIFF format requires full decode first
- At 240 MB TIFF → ~480 MB decompressed RGB — acceptable for a single request in a local single-user app

**Serving pattern:**

```python
from io import BytesIO
from flask import send_file

@app.get('/image/<stem>')
def serve_image(stem):
    tiff_path = input_dir / f'{stem}.tif'
    if not tiff_path.exists():
        tiff_path = input_dir / f'{stem}.tiff'
    if not tiff_path.exists():
        abort(404)

    img, dpi, _ = load_tiff(tiff_path)   # reuse pipeline's load_tiff()
    img = img.convert('RGB')             # TIFF may be grayscale or RGBA
    img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)  # in-place, aspect-safe

    buf = BytesIO()
    img.save(buf, format='JPEG', quality=85)
    buf.seek(0)
    return send_file(buf, mimetype='image/jpeg')
```

**Why no disk cache:** The local web app serves a single operator. On-demand generation is 1–3 seconds per TIFF. Caching to disk would require invalidation logic and storage (100 files × 500 KB JPEG = 50 MB, acceptable but adds complexity). Start without caching; add if performance is a complaint.

**Why not serve the TIFF directly:** Browsers cannot display TIFF natively. Even if they could, loading a 200 MB file over localhost into browser memory would cause tab crashes.

**Thumbnail size choice:** 1600px on the long edge. At 400 DPI, a page 19cm wide = 7548 pixels; at 1600px the viewer renders at ~85 DPI, which is comfortable for reading and correction. The viewer panel is typically 600–900px CSS wide, so 1600px gives 2x retina-quality rendering.

**ALTO coordinate scaling:** The viewer must map ALTO pixel coordinates (in the full-resolution space) to the thumbnail's pixel space. This requires knowing the scale factor:

```javascript
const scaleX = thumbnailWidth / altoPageWidth;   // e.g. 1600/5146 = 0.311
const scaleY = thumbnailHeight / altoPageHeight; // e.g. 1170/7548 = 0.155
// Word box in thumbnail space:
const x = word.hpos * scaleX;
const y = word.vpos * scaleY;
const w = word.width * scaleX;
const h = word.height * scaleY;
```

The API endpoint must therefore return both the ALTO page dimensions (`page_width`, `page_height`) and the thumbnail dimensions (or a single `scale` factor).

---

## ALTO XML Parsing: Data Shape for Frontend

**Source of truth:** Real ALTO XML output (inspected from `output/alto/Ve_Volk_165945877_1957_Band_1-0001.xml`).

Key observed facts:
- `MeasurementUnit` = `pixel` (not `mm10` — coordinates are raw pixels in cropped image space)
- Page `WIDTH`=5146, `HEIGHT`=7548 in the sample (the cropped image dimensions)
- Each `String` element has: `ID`, `HPOS`, `VPOS`, `WIDTH`, `HEIGHT`, `WC` (confidence 0.0–1.0), `CONTENT`
- Words are organized: `Page > PrintSpace > ComposedBlock > TextBlock > TextLine > String`
- `SP` (space) elements separate words on a line; they have no `CONTENT`

**API endpoint: `GET /alto/<stem>`**

The frontend needs a flat list of words with bounding boxes, grouped by text line for display. The frontend does NOT need the full XML hierarchy.

**Recommended JSON shape:**

```json
{
  "stem": "scan_001",
  "page_width": 5146,
  "page_height": 7548,
  "words": [
    {
      "id": "string_0",
      "content": "Erfurt,",
      "hpos": 1321,
      "vpos": 1162,
      "width": 146,
      "height": 49,
      "confidence": 0.90,
      "line_id": "line_0",
      "block_id": "block_0"
    },
    ...
  ]
}
```

**Why flat array (not nested by block/line):** The viewer's word-click-to-highlight feature iterates over words and draws bounding boxes. A flat array is directly consumable by the canvas/SVG overlay layer. The `line_id` and `block_id` fields allow the frontend to group words into lines for the text panel display without requiring the full hierarchy.

**Why include `line_id`:** The text panel renders words reading-order, grouped by line. Without line grouping, words from different columns would interleave.

**ALTO parsing function (in app.py):**

```python
from lxml import etree

NS = 'http://schema.ccs-gmbh.com/ALTO'

def parse_alto_words(alto_path: Path) -> dict:
    tree = etree.parse(str(alto_path))
    root = tree.getroot()
    page = root.find(f'.//{{{NS}}}Page')
    page_w = int(page.get('WIDTH', 0))
    page_h = int(page.get('HEIGHT', 0))
    words = []
    for line in root.iter(f'{{{NS}}}TextLine'):
        line_id = line.get('ID', '')
        block = line.getparent()
        block_id = block.get('ID', '') if block is not None else ''
        for string in line.findall(f'{{{NS}}}String'):
            words.append({
                'id': string.get('ID'),
                'content': string.get('CONTENT', ''),
                'hpos': int(string.get('HPOS', 0)),
                'vpos': int(string.get('VPOS', 0)),
                'width': int(string.get('WIDTH', 0)),
                'height': int(string.get('HEIGHT', 0)),
                'confidence': float(string.get('WC', 0.0)),
                'line_id': line_id,
                'block_id': block_id,
            })
    return {'page_width': page_w, 'page_height': page_h, 'words': words}
```

---

## Word Correction: Save Back to ALTO XML

**API endpoint: `POST /alto/<stem>`**

Request body (JSON):
```json
{"id": "string_42", "content": "corrected_word"}
```

**Algorithm:**
1. Parse the ALTO XML with lxml
2. Find the `String` element with the matching `ID` attribute
3. Update `CONTENT` attribute in-place
4. Serialize back to file using `etree.tostring()` with `xml_declaration=True, encoding='UTF-8'`
5. Write to disk (overwrite in place)

**Why in-place overwrite is safe:** The constraint "originals must never be modified" applies to the input TIFFs, not the ALTO XML output. ALTO XML is the generated artifact; corrections are the intended output.

**Lxml serialization note:** lxml's `etree.tostring()` preserves attribute order for existing attributes but may reformat whitespace. The file may look slightly different from the Tesseract-generated version after correction. This is acceptable — ALTO schema validity is preserved.

---

## Recommended File Structure

```
Zeitschriften-OCR/
├── pipeline.py             # existing — no changes required for v1.4
├── app.py                  # NEW — Flask application, ~250 lines
├── requirements.txt        # add: flask>=3.1.0
├── schemas/
│   └── alto-2-1.xsd        # existing
├── static/                 # NEW — frontend assets
│   ├── index.html          # upload + progress UI
│   ├── viewer.html         # side-by-side TIFF + text viewer
│   ├── app.js              # upload, SSE client, progress rendering
│   └── viewer.js           # ALTO word rendering, bbox overlay, correction
├── tests/
│   ├── __init__.py         # existing
│   ├── test_load_config.py # existing
│   └── test_app.py         # NEW — Flask test client tests
└── output/                 # existing
    └── alto/
```

**Structure rationale:**

- `app.py` at root (same level as `pipeline.py`) — enables `from pipeline import ...` without path manipulation
- `static/` flat (not `static/js/`, `static/css/`) — only 4 files, no need for subdirectories
- Two HTML pages (not SPA) — `index.html` for upload/progress, `viewer.html` for viewing/correction. Simple, no build step, no JS framework.
- Flask serves `static/` directly with `app.static_folder='static'` — no separate HTTP server needed

---

## Component Boundaries

| Component | File | Responsibility | Does NOT Own |
|-----------|------|----------------|--------------|
| OCR Pipeline | `pipeline.py` | TIFF loading, deskew, crop, OCR, ALTO XML generation | HTTP, JSON, frontend concerns |
| Flask App | `app.py` | HTTP routing, SSE streaming, ALTO parsing, JPEG generation, correction writes | OCR algorithm logic |
| Upload/Progress UI | `static/index.html` + `app.js` | Drag-drop, file queue display, SSE-driven progress | ALTO parsing, image rendering |
| Viewer UI | `static/viewer.html` + `viewer.js` | TIFF image display, ALTO word overlay, inline correction | Upload, OCR triggering |

**Boundary enforcement:** `pipeline.py` must have zero Flask imports. `app.py` must not duplicate OCR logic — it calls pipeline functions only. If a function is needed in both CLI and web contexts, it stays in `pipeline.py`.

---

## Data Flow: End-to-End

### Flow 1: Upload and OCR

```
Operator drops TIFF on browser
    ↓ POST /upload (multipart form or JSON path reference)
app.py: add path to _queued_tiffs list → 202 response
    ↓ Operator clicks "Start OCR"
    ↓ POST /run
app.py: threading.Thread(target=worker) → 202 response
    ↓ Browser opens EventSource('/stream')
Background thread: process_tiff(path, ...) — 10-60s per file
    ↓ thread puts progress dict in _ocr_queue
SSE generator: reads _ocr_queue → yields event to browser
Browser: updates progress bar, ETA display
    ↓ sentinel None in queue
SSE generator: yields 'event: complete' → close EventSource
```

### Flow 2: View a Processed File

```
Operator selects file from list
    ↓ GET /files → JSON list of {stem, word_count, modified}
    ↓ Browser navigates to viewer.html?stem=scan_001
    ↓ GET /image/scan_001 (parallel with ALTO fetch)
app.py: load_tiff() → thumbnail() → BytesIO → JPEG response
Browser: display image in left panel
    ↓ GET /alto/scan_001
app.py: parse_alto_words() → JSON {page_width, page_height, words: [...]}
Browser: render word text in right panel, draw overlay boxes
```

### Flow 3: Correct a Word

```
Operator clicks word in text panel
    ↓ Browser highlights bounding box on image (client-side)
Operator edits word text → presses Enter or clicks Save
    ↓ POST /alto/scan_001 {"id": "string_42", "content": "korrigiert"}
app.py: parse ALTO → find String[@ID='string_42'] → set CONTENT → write
    → 200 {"ok": true}
Browser: update displayed word in text panel
```

---

## Build Order (Phase Dependencies)

```
Phase A: Flask skeleton + file listing
  app.py: GET /files, GET /files-list, serve static/
  Validates: Flask boots, imports pipeline.py without error
  No UI needed — test with curl

Phase B: TIFF→JPEG serving
  GET /image/<stem>
  Validates: Pillow thumbnail works on real TIFFs, memory is manageable
  Smoke test: open /image/Ve_Volk_165945877_1957_Band_1-0001 in browser
  MUST complete before viewer UI (UI depends on image endpoint)

Phase C: ALTO parsing endpoint
  GET /alto/<stem>
  Validates: JSON shape is correct, all words extracted
  Smoke test: curl /alto/<stem> | jq '.words | length'
  MUST complete before viewer UI (UI depends on word data)

Phase D: Viewer UI (depends on B + C)
  static/viewer.html + viewer.js
  Word list rendering, bbox overlay on canvas/SVG
  Click-to-highlight interaction

Phase E: Word correction endpoint + UI
  POST /alto/<stem> write-back
  Edit interaction in viewer.js
  MUST come after Phase D (requires working viewer)

Phase F: Upload UI + SSE progress
  POST /upload, POST /run, GET /stream
  static/index.html + app.js SSE client
  Background thread OCR integration
  Can be developed in parallel with Phase D/E

Phase G: Integration + file list UI
  File browser on index.html, link to viewer
  End-to-end: upload → OCR → view → correct
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using `run_batch()` in the web app

**What:** Importing `run_batch()` from pipeline.py and calling it from a Flask route.

**Why wrong:** `run_batch()` creates a `ProcessPoolExecutor` internally, forks subprocesses, and uses `ProgressTracker` which writes to `stderr` with `\r` overwriting — none of which integrate with Flask's SSE streaming. Progress information is trapped inside the subprocess workers with no mechanism to route it back to the web client.

**Do this instead:** Call `process_tiff()` directly in a background thread. Each call completes and posts a progress event to `_ocr_queue` before the next file starts. Sequential is correct for the UI use case — operators watch one file at a time.

### Anti-Pattern 2: Blocking the Flask request thread with OCR

**What:** Calling `process_tiff()` inside a route handler (synchronously blocking the response).

**Why wrong:** OCR on a 200 MB TIFF takes 10–60 seconds. Flask's development server is single-threaded by default. Blocking the request thread prevents the SSE `/stream` endpoint from sending progress events (it can't respond while another request is running). The browser UI freezes.

**Do this instead:** `POST /run` starts a `threading.Thread(target=worker, daemon=True)` and immediately returns `202 Accepted`. The SSE endpoint (`GET /stream`) runs concurrently. Use `threaded=True` in `app.run()` (Flask's development server default is already threaded since Flask 1.0).

### Anti-Pattern 3: Serving the raw TIFF to the browser

**What:** Reading the TIFF file and sending its bytes directly as the image response.

**Why wrong:** Browsers do not support TIFF natively. Even if a plugin were available, a 200 MB TIFF over localhost would consume the full 200 MB of browser tab memory. Loading would be slow and crash-prone.

**Do this instead:** Convert to JPEG thumbnail in the `/image/<stem>` endpoint. 1600px JPEG at quality=85 is typically 300–600 KB — fast to load and rendering in the browser.

### Anti-Pattern 4: Writing JPEG thumbnails to disk as a cache layer

**What:** Saving `output/<stem>_thumb.jpg` to disk when first requested, serving the cached file on subsequent requests.

**Why wrong:** Adds file management complexity (stale thumbnails if TIFF changes), disk usage (negligible here), and cache invalidation logic. On-demand generation for a single local operator takes 1–3 seconds, which is acceptable.

**Do this instead:** Generate in memory with `BytesIO`, return directly. If generation time becomes a complaint (multiple reloads per session), add an in-process `lru_cache(maxsize=20)` keyed on stem — no disk involvement.

### Anti-Pattern 5: One SSE connection per TIFF file

**What:** Opening a new `EventSource` for each file being processed.

**Why wrong:** Browsers limit concurrent connections per domain (6 without HTTP/2). Multiple SSE connections quickly exhaust this limit, and each requires keeping the generator alive in Flask.

**Do this instead:** One SSE stream per OCR batch run. The background thread posts progress for all files sequentially into `_ocr_queue`. One `EventSource` connection sees all progress.

### Anti-Pattern 6: Storing queued TIFF paths in Flask session or cookies

**What:** Encoding the list of files to process in the HTTP session.

**Why wrong:** Sessions have size limits (4 KB for cookie-based sessions). A list of 300 TIFF paths would overflow. Sessions are per-client, but the OCR is a single-machine global operation.

**Do this instead:** Store `_queued_tiffs` as a module-level list in `app.py`. This is a local, single-operator app — there is no multi-user concern. Module-level state is the correct scope.

---

## Scaling Considerations

This is a **local single-operator tool** — scaling is not a design goal. The architecture must be simple, not scalable.

| Concern | At 1 operator (target) | If it becomes a problem |
|---------|------------------------|-------------------------|
| Concurrent OCR | Sequential (1 file at a time via thread) | Re-introduce `run_batch()` with ProcessPoolExecutor |
| Large TIFF memory | 480 MB per request, sync, single user | Not a problem for local use |
| File list size | Hundreds of files in `output/alto/` | `os.scandir()` is fast; no pagination needed |
| Multiple browser tabs | Module-level `_ocr_queue` shared across requests | Acceptable; SSE stream goes to whichever tab opened it |

---

## Integration Points Summary

| Boundary | From | To | Method | Notes |
|----------|------|----|--------|-------|
| app.py → pipeline.py | Flask route | `process_tiff()` | Direct import + thread call | Must catch Exception — no sys.exit in workers |
| app.py → pipeline.py | Flask startup | `validate_tesseract()` | Direct import + call at init | Exits with clear error if Tesseract absent |
| app.py → pipeline.py | Flask startup | `load_xsd()` | Direct import + call at init | Returns None if schema missing (validation skipped) |
| app.py → pipeline.py | JPEG endpoint | `load_tiff()` | Direct import + call in route | Returns PIL Image; convert to JPEG in route |
| Background thread → SSE | Worker thread | `_ocr_queue` | `queue.Queue.put()` | Thread-safe; SSE generator reads with timeout |
| Browser → app.py | Upload/run | `POST /upload`, `POST /run` | HTTP JSON | 202 Accepted; non-blocking |
| Browser → app.py | Progress | `GET /stream` EventSource | SSE text/event-stream | Keep-alive comment every 30s |
| Browser → app.py | Viewing | `GET /image/<stem>` | HTTP JPEG | On-demand thumbnail generation |
| Browser → app.py | Word data | `GET /alto/<stem>` | HTTP JSON | Flat word list with bbox coords |
| Browser → app.py | Correction | `POST /alto/<stem>` | HTTP JSON | Overwrites ALTO XML in-place |

---

## Sources

- Flask 3.1.x official documentation — streaming patterns: https://flask.palletsprojects.com/en/stable/patterns/streaming/
- MDN Server-Sent Events specification and wire format: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- Direct inspection of `pipeline.py` (1,146 lines) — function signatures, process_tiff(), run_batch(), ProgressTracker
- Real ALTO XML output: `output/alto/Ve_Volk_165945877_1957_Band_1-0001.xml` — confirmed pixel coordinates, page dimensions, String element structure
- Pillow lazy-loading behavior for TIFF: established from training data (HIGH confidence for TIFF decode behavior — Pillow.Image.open() is lazy for TIFF, full decode happens on first pixel access)

---

*Architecture research for: v1.4 Web Viewer — Flask + pipeline.py integration*
*Researched: 2026-02-27*
