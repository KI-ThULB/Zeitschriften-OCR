# Stack Research: v1.4 Web Viewer

**Domain:** Local Flask web viewer for OCR pipeline (drag-and-drop upload, live progress, side-by-side TIFF+text viewer, word-level ALTO XML correction)
**Researched:** 2026-02-27
**Confidence:** HIGH

> This file covers NEW additions only. Existing stack (Pillow, opencv-python-headless, deskew, pytesseract, lxml) is validated and unchanged.

---

## Recommended Stack (New Additions Only)

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Flask | 3.1.3 | Web framework: routes, file upload, SSE streaming, static serving | Current stable (Feb 2026). No extensions needed — built-in `Response`, `send_file`, `stream_with_context`, and Werkzeug's `secure_filename` cover all required features. Flask 3.x requires Python >=3.8; project runs 3.11. |
| Werkzeug | 3.1.6 | File upload security (secure_filename), bundled with Flask | Installed automatically as Flask dependency. `werkzeug.utils.secure_filename` sanitizes uploaded TIFF filenames before writing to disk. No separate install needed. |

**No Flask extensions are needed.** Every required feature (streaming, file upload, static serving, JSON responses) is built into Flask 3.x core + Werkzeug. See "What NOT to Add" below.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | >=11.1.0 (already in requirements.txt) | TIFF → JPEG conversion for browser serving | Already a dependency. `image.thumbnail((1400, 9999), Image.LANCZOS)` then `image.save(buf, "JPEG", quality=85)`. No new install needed. |
| lxml | >=5.3.0 (already in requirements.txt) | ALTO XML parsing and word-level editing | Already a dependency. `etree.findall('{ns}String')`, `element.set('CONTENT', new_text)`, `etree.tostring()` covers all word edit and save operations. |

### No Frontend Libraries Needed

| Approach | Decision | Rationale |
|----------|----------|-----------|
| Vanilla JS (ES2020+) | USE | `EventSource()` (SSE), `fetch()` (word save, file list), `DataTransfer` (drag-and-drop), `document.createElementNS()` (SVG rects) — all native browser APIs. No CDN dependency, no build step, no version drift. |
| Jinja2 templates | USE | Bundled with Flask. Server-renders initial HTML (file list, viewer layout). JS handles only dynamic updates (progress, rect highlight, word edit). |

---

## Key Design Decisions

### 1. Flask: No Extensions

Flask 3.1.3 core + Werkzeug 3.1.6 (bundled) cover everything:

- **File upload**: `request.files["file"]` + `werkzeug.utils.secure_filename()`
- **SSE streaming**: `Response(generator_fn(), mimetype="text/event-stream")`
- **Image serving**: `send_file(BytesIO(jpeg_bytes), mimetype="image/jpeg")`
- **JSON API**: `flask.jsonify()`
- **Threading**: `app.run(threaded=True)` (one thread per SSE connection)

**flask-sse rejected**: Requires Redis. Local tool; no Redis infrastructure.
**flask-socketio rejected**: WebSockets are bidirectional. SSE is sufficient for one-way progress stream.
**flask-cors rejected**: Same-origin app. Flask serves HTML + API from the same host:port. No cross-origin requests occur.
**flask-wtf rejected**: No complex forms. Simple `fetch()` POSTs with JSON body are sufficient.

### 2. SSE over Polling

**Decision: Server-Sent Events (SSE)** via native `EventSource` browser API.

**Rationale:**
- OCR files take 10–60s each. A 500ms polling interval introduces up to 500ms lag per event, visible at this timescale.
- `EventSource("/progress")` is a single JS line; no library, no configuration.
- Push model: updates arrive exactly when each file completes — matches how `ProgressTracker` already fires events in `run_batch()`.
- Flask's `stream_with_context` + `Response(generator, mimetype="text/event-stream")` is the established pattern for Flask SSE; no extension required.

**Architecture for SSE + ProcessPoolExecutor coexistence:**

```
POST /process
  → starts threading.Thread(target=run_batch_with_queue)
  → run_batch() accepts optional progress_queue= parameter
  → each worker future completion puts dict onto multiprocessing.Queue
  → relay thread moves from mp.Queue → threading.Queue (Flask-thread-safe)

GET /progress (SSE)
  → Flask thread blocks on threading.Queue.get()
  → yields "data: {...}\n\n" for each progress event
  → yields "data: {done: true}\n\n" on sentinel → stream closes
```

**Required pipeline.py change:** `run_batch()` needs an optional `progress_queue=None` parameter. When `None`, behavior is unchanged (CLI mode). When set, each `future.result()` call additionally puts a progress dict on the queue. This is a non-breaking additive change.

**Flask threading:** `app.run(debug=False, threaded=True)` — one thread per SSE connection. For a single-operator local tool, this is always safe. `threaded=True` is the Flask default since Flask 1.0, so no explicit flag may be needed, but setting it explicitly documents the intent.

### 3. TIFF Serving: Write-Once Preview Cache

**Decision: Convert on first request; cache JPEG to disk.**

| Approach | First Load | Subsequent Loads | Decision |
|----------|-----------|-----------------|----------|
| Pure on-the-fly (no cache) | 2–5s (Pillow loads 240MB TIFF) | 2–5s every time | REJECTED |
| Write-once cache | 2–5s once per file | <100ms (send_file) | CHOSEN |
| Pre-convert all on startup | Blocks startup for minutes | Fast | REJECTED |

**Cache path:** `<output_dir>/preview/<stem>.jpg` — parallel to existing `<output_dir>/alto/<stem>.xml` layout.

**Conversion parameters:**
- `image.thumbnail((1400, 9999), Image.LANCZOS)` — max 1400px wide; proportional height. Sufficient for a two-panel browser layout at 1920px screen width.
- `image.save(path, "JPEG", quality=85, optimize=True)` — readable text, ~300–600KB per file (vs 117–240MB TIFF).

**Cache invalidation:** Preview JPEGs are not invalidated by `--force` (TIFFs never change). If a TIFF is replaced by the operator, deleting `output/preview/` manually regenerates on next view.

**Browser does not support TIFF natively** (Firefox/Chrome since ~2018 dropped TIFF; no path to serve TIFFs directly).

### 4. SVG over Canvas for Bounding Box Overlay

**Decision: SVG overlay, `position: absolute` over `<img>`.**

**Architecture:**
```html
<div style="position: relative; display: inline-block;">
  <img id="scan" src="/image/scan_001" style="max-width: 100%;">
  <svg id="overlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
       viewBox="0 0 {page_width} {page_height}">
    <!-- one <rect> per ALTO String element -->
    <rect data-word-id="w42" x="100" y="200" width="80" height="30"
          fill="none" stroke="blue" stroke-width="1" opacity="0.5"/>
  </svg>
</div>
```

**Why SVG, not Canvas:**
- Each `<rect>` is a DOM element: native `click` events, no custom hit-testing code.
- Highlight on click: `rect.classList.add("selected")` (CSS `.selected { stroke: red; fill: rgba(255,0,0,0.1); }`).
- Dynamic update on word edit: remove/replace one `<rect>` without redrawing the entire image.
- `viewBox` handles coordinate scaling automatically — ALTO coordinates map directly without JS math.
- Natural for ALTO's data model: one `<rect>` per `<String>` element, `data-word-id` matches ALTO `@ID`.

**Canvas rejected:** Requires custom hit-testing (point-in-rect loop), full overlay redraw on any change, more JS complexity for no gain in this use case.

### 5. Vanilla JS + Jinja2 (No Frontend Framework)

**Decision: Vanilla JS (ES2020+) with Jinja2 server-rendered templates.**

**Rationale:** The web app has approximately 4 views and 3 interactive behaviors:
1. Upload page (drag-and-drop + queue list)
2. Progress page (SSE updates)
3. File browser (static list)
4. Viewer page (SVG overlay + text panel + word edit)

All required browser APIs are native:
- **Drag-and-drop:** `dragover`, `drop`, `DataTransfer.files`
- **File upload:** `FormData` + `fetch()`
- **SSE:** `new EventSource("/progress")`
- **Word save:** `fetch("/api/words/save", {method: "POST", body: JSON.stringify(...)})`
- **SVG manipulation:** `document.createElementNS("http://www.w3.org/2000/svg", "rect")`
- **ALTO parsing on client:** Not needed — server parses ALTO and returns JSON word list

**Alpine.js rejected:** 45KB, CDN dependency, reactive system is overkill for 4 views with modest state.
**HTMX rejected:** Server would need to return HTML fragments for every state change; SSE extension adds complexity vs native `EventSource`.
**React/Vue rejected:** Build pipeline required; massive overkill for a local operator tool.

---

## Full Requirements Delta (New Lines Only)

Add to `requirements.txt`:

```
flask>=3.1.3
```

Werkzeug is installed automatically as a Flask dependency. No other new packages.

**Total new Python dependencies: 1** (`flask`)

---

## Integration Points with pipeline.py

| Feature | Integration | pipeline.py Change? |
|---------|-------------|-------------------|
| Run OCR from UI | `from pipeline import run_batch` — call in background thread | YES: add `progress_queue=None` parameter to `run_batch()` |
| Browse processed files | `from pipeline import discover_tiffs` — scan output/alto/ | NO |
| TIFF → JPEG preview | Pillow (already imported in pipeline.py) — replicate `load_tiff()` read | NO |
| ALTO word data | lxml (already in requirements.txt) — parse in app.py | NO |
| Word edit + save | lxml in app.py — find String by ID, set CONTENT, write XML | NO |

**app.py architecture:** A separate file alongside `pipeline.py`. Imports from `pipeline` directly (not subprocess). This avoids parsing fragility and shares the same lxml/Pillow imports already present.

---

## What NOT to Add

| Do Not Add | Why | What to Use Instead |
|------------|-----|---------------------|
| `flask-sse` | Requires Redis; overkill for local tool | `flask.Response(generator, mimetype="text/event-stream")` |
| `flask-socketio` | WebSocket bidirectionality not needed; more complex than SSE | `EventSource` (SSE) for one-way progress stream |
| `flask-cors` | Same-origin app; Flask serves all HTML + API | Nothing — no CORS needed |
| `flask-wtf` | No complex forms; CSRF protection unnecessary for localhost-only tool | `werkzeug.utils.secure_filename` + `request.files` |
| `celery` | Task queue for distributed workers; this is a local single-operator tool | `threading.Thread` + `multiprocessing.Queue` |
| `redis` | Required by celery/flask-sse; no network infrastructure wanted | `queue.Queue` (stdlib) |
| Alpine.js / HTMX | Frontend reactivity library; 4 views don't justify the dependency | Vanilla JS ES2020+ |
| React / Vue | Full SPA framework; requires build pipeline | Vanilla JS + Jinja2 |
| `tifffile` | Already have Pillow; no BigTIFF or scientific scan requirements | Pillow (already installed) |

---

## Alternatives Considered

| Recommended | Alternative | When Alternative is Better |
|-------------|-------------|----------------------------|
| Flask 3.1.3 | FastAPI | When async I/O matters; for this CPU-bound pipeline, threading+Flask is simpler |
| SSE (EventSource) | Polling (setInterval + fetch) | Polling is simpler to debug; acceptable if SSE proves difficult with process pool relay |
| SVG overlay | Canvas overlay | Canvas preferred if bounding boxes number in the thousands (>5000/page) and redraw performance matters; ALTO archival pages typically have 200–800 words |
| Write-once preview cache | Pure on-the-fly | Acceptable for fast SSDs + small TIFFs; 240MB files make repeated conversion too slow |
| Vanilla JS | Alpine.js | If interactive state grows beyond ~5 reactive variables; Alpine adds little cost |

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| Flask | 3.1.3 | Python 3.8–3.13, Werkzeug 3.1.x | Flask 3.x drops Python 3.7 |
| Werkzeug | 3.1.6 | Flask 3.1.x | Installed automatically; do not pin separately |
| Pillow | >=11.1.0 | Flask (no conflict) | Already pinned in requirements.txt |
| lxml | >=5.3.0 | Flask (no conflict) | Already pinned in requirements.txt |

---

## Sources

- `pip index versions flask` — confirmed Flask 3.1.3 is current latest (Feb 2026) — HIGH confidence
- `pip index versions werkzeug` — confirmed Werkzeug 3.1.6 is current latest (Feb 2026) — HIGH confidence
- `pip index versions pillow` — confirmed Pillow 12.1.1 available; project uses 11.1.0 (pinned, compatible) — HIGH confidence
- Flask documentation (training knowledge, Flask 3.x): `stream_with_context`, `Response`, `send_file`, `threaded=True` — MEDIUM confidence (verified against pip version availability)
- Python stdlib verification: `multiprocessing.Queue`, `threading.Thread`, `queue.Queue` — HIGH confidence (tested locally)
- Pillow JPEG conversion performance test: 4000×5500 → 1200×1650 JPEG in 0.163s locally — HIGH confidence
- lxml ALTO XML round-trip test: `findall`, `set`, `tostring` verified locally — HIGH confidence
- Browser API support (EventSource, DataTransfer, createElementNS): ES2020+ baseline, universally available in 2026 Chrome/Firefox/Safari — HIGH confidence (MDN baseline, training knowledge)

---

*Stack research for: Zeitschriften-OCR v1.4 Web Viewer (new additions only)*
*Researched: 2026-02-27*
