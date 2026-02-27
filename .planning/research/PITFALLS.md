# Pitfalls Research: Flask Web Viewer for TIFF OCR Pipeline

**Domain:** Flask web app wrapping a Python batch OCR pipeline (large TIFF uploads, background jobs, ALTO XML editing)
**Researched:** 2026-02-27
**Confidence:** HIGH

This document covers pitfalls specific to adding a Flask web viewer to the existing `pipeline.py` CLI. The prior pipeline pitfalls (DPI, namespace, crop offset) remain valid and are referenced where they interact with the new web layer. This document focuses on web-integration-specific failure modes.

---

## Critical Pitfalls

### Pitfall 1: Flask Dev Server Blocks During OCR (Concurrency Model Mismatch)

**What goes wrong:**
The operator uploads a TIFF and triggers OCR. The Flask route handler calls into `pipeline.py`'s processing logic synchronously. The Werkzeug dev server, even with `threaded=True` (its default since Flask 0.10), handles requests one thread at a time per connection — but the OCR worker runs for 30–120 seconds on a 240 MB TIFF. During that time, the browser's SSE progress stream and any other HTTP requests (e.g., the file browser, image serving) are either queued or compete for thread slots. Progress streaming breaks because the SSE response handler is blocked waiting for the blocking OCR call to yield.

The root confusion: `threaded=True` on the Werkzeug dev server means it spawns a new thread per request (not a single-threaded event loop), but if the OCR runs inline in a Flask request handler thread, that thread is tied up and cannot yield SSE events. SSE requires a long-lived response that sends `data:` frames periodically — a blocking `subprocess.run()` inside the same thread produces no frames until Tesseract exits.

**Why it happens:**
Developers test upload + OCR on a single small file, it "works," and only discover the blocking issue when the operator tries to check progress during a real 90-second OCR run. The SSE endpoint appears to connect but never sends events.

**How to avoid:**
Run OCR in a `threading.Thread` (not a new process) launched from the route handler. Keep a simple job registry (an in-memory dict keyed by `job_id`) that stores job state: `{status: "running", progress: {...}, result: None, error: None}`. The SSE endpoint polls this dict and yields frames. Since this is a local single-operator tool, an in-memory dict is sufficient — no Redis, no Celery.

Do NOT use `ProcessPoolExecutor.submit()` from within a Flask request handler and then try to stream back via SSE. The future result is not available until `.result()` blocks. Use a thread that writes progress updates to the job registry dict, and have the SSE endpoint read from that dict.

**Warning signs:**
- SSE endpoint connects (HTTP 200) but the browser's `EventSource` never fires `message` events until OCR completes
- Browser shows progress bar stuck at 0% then jumps to 100%
- Flask log shows a request taking 90+ seconds while other requests queue up

**Phase to address:** Phase 1 (Flask foundation + job management) — get the threading model right before building any UI features on top of it.

---

### Pitfall 2: Large File Upload Buffered into RAM by Werkzeug

**What goes wrong:**
By default, Werkzeug buffers uploaded files entirely into memory when they are below a threshold (`max_form_memory_size`, default 500 KB), and into a temp file when larger. For 200 MB TIFFs, Werkzeug will write to a temp file — but the Flask route handler still calls `request.files['tiff'].save(destination)` which reads the entire temp file and writes it to the upload directory, holding the full 200 MB in the I/O path. If the operator uploads multiple TIFFs in quick succession (drag-and-drop multiple files), the temp directory fills rapidly.

A separate but related issue: if `MAX_CONTENT_LENGTH` is not set, Flask accepts files of unlimited size, and the dev server may appear to hang with no feedback while receiving a 200 MB multipart upload. If `MAX_CONTENT_LENGTH` is set too low (e.g., the Flask docs example uses 16 MB), the upload is rejected with a 413 `RequestEntityTooLarge` — but on the dev server this sometimes manifests as a connection reset rather than a clean 413 response, confusing the client-side drag-and-drop handler.

**Why it happens:**
Developers set `MAX_CONTENT_LENGTH` to the Flask docs example value (16 MB) without reading why, or forget to set it at all and wonder why uploads of 200 MB files appear to hang with no progress indication on the server side.

**How to avoid:**
- Set `MAX_CONTENT_LENGTH = 300 * 1024 * 1024` (300 MB) explicitly — above the largest expected TIFF but with a hard cap.
- Do not stream-read the upload into the OCR pipeline directly — save to an uploads staging directory first, then enqueue the path. Keeps the upload and OCR phases decoupled.
- Use `werkzeug.utils.secure_filename()` on every uploaded filename before saving — `../../../etc/passwd` is a realistic attack even on localhost tools that later get exposed.
- On the client side, track upload progress via the `XMLHttpRequest.upload.onprogress` event (not SSE) — this gives byte-level upload progress before the server even receives the complete file.

**Warning signs:**
- Drag-and-drop upload of a 200 MB TIFF shows no browser progress and then fails with a connection reset
- Multiple sequential uploads fill `/tmp` unexpectedly
- Server log shows a single POST request lasting minutes for a large upload

**Phase to address:** Phase 1 (Flask foundation) — upload endpoint must be sized and validated before any other feature is built on top.

---

### Pitfall 3: TIFF-to-JPEG Coordinate System Mismatch (The Core Viewer Bug)

**What goes wrong:**
The TIFF (e.g., 4000 × 5600 pixels at 400 DPI) is converted to a JPEG for browser display. The browser renders this JPEG at whatever size the CSS dictates — say 800 × 1120 px (a 5x downscale). ALTO coordinates (HPOS/VPOS/WIDTH/HEIGHT) are in original pixel space. The word bounding box overlay is drawn using the ALTO coordinates directly as pixel values on the scaled-down image. Every bounding box appears 5x smaller than it should be, or offset in the wrong place.

The specific failure: the developer tests with a small TIFF that happens to render at near-original size in the browser, bounding boxes look correct, then the first real 4000 px wide scan breaks all overlays.

A second mismatch: Pillow's `Image.thumbnail()` or `Image.resize()` uses (width, height) convention. CSS uses `width` then `height`. JavaScript's `canvas.drawImage()` also uses (x, y, width, height). But ALTO uses HPOS (= x, horizontal offset from left) and VPOS (= y, vertical offset from top). These are consistent, but `WIDTH` and `HEIGHT` in ALTO are the bounding box dimensions, not the endpoint coordinates. A common mistake is treating HPOS+WIDTH as the right edge coordinate directly in a CSS `left` property without scaling — the `left` value must be multiplied by `(rendered_width / original_width)`.

**Why it happens:**
The developer draws boxes using ALTO coordinates with no scaling factor. Works in testing because test TIFFs are small or happen to render at similar size. Breaks silently on real scans: boxes are visible but consistently wrong.

**How to avoid:**
The server must return the original TIFF dimensions alongside the JPEG to the browser. The viewer JavaScript must compute a scale factor: `scaleX = renderedImageWidth / originalTiffWidth` and `scaleY = renderedImageHeight / originalTiffHeight`. Every ALTO coordinate is multiplied by the scale factor before being used to position an overlay element.

Embed original dimensions in the API response:
```json
{
  "image_url": "/view/scan_001/jpeg",
  "original_width": 4000,
  "original_height": 5600,
  "words": [{"id": "...", "hpos": 120, "vpos": 340, "width": 200, "height": 40, "content": "Zeitschrift"}]
}
```

The JavaScript overlay layer recomputes positions whenever the image is resized (use a `ResizeObserver` on the `<img>` element, not a one-time calculation at page load).

**Warning signs:**
- Word boxes are visible but consistently offset or wrong size on large TIFFs
- Works on small test TIFFs, breaks on real 4000+ px scans
- Boxes track correctly at one browser window size, wrong at another

**Phase to address:** Phase 2 (TIFF viewer) — this is the foundational correctness constraint for the viewer. Build coordinate scaling into the API response design from day one, not as a retrofit.

---

### Pitfall 4: ALTO XML Namespace Lost or Doubled on Round-Trip Edit

**What goes wrong:**
The web app reads an existing ALTO XML file with lxml, extracts word elements, lets the operator edit a word's CONTENT attribute, then serializes the modified tree back to disk. After saving, the ALTO namespace declaration has been mangled: either it is repeated multiple times on child elements (`xmlns="http://schema.ccs-gmbh.com/ALTO"` appearing on every `String` element), or it has been dropped from the root element entirely and the file fails schema validation.

The specific lxml behavior: when you parse an ALTO XML file and serialize it back with `etree.tostring()`, lxml may move namespace declarations to child elements if the namespace is not explicitly referenced on the root. The CCS-GmbH namespace (`http://schema.ccs-gmbh.com/ALTO`) must be declared on the root `<alto>` element — not inlined on every child.

A second issue: `etree.tostring()` without `xml_declaration=True` drops the `<?xml version="1.0" encoding="UTF-8"?>` declaration. Goobi's ingest parser may be strict about this declaration being present.

**Why it happens:**
The developer does a quick `etree.parse()` → modify attribute → `etree.tostring()` → `write_bytes()` cycle that works locally but produces malformed namespace declarations. The file still opens in a browser XML viewer and even in lxml, but fails the XSD validation the pipeline already runs.

**How to avoid:**
Use the same serialization path as `build_alto21()` in `pipeline.py`:
```python
etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
```
After any modification, run `validate_alto_file()` from `pipeline.py` before writing the file to disk. If validation fails, do not overwrite — return an error to the browser. This keeps the existing validation logic as the gatekeeper for all writes, whether from the CLI pipeline or the web editor.

Run the XSD validation check after every save, exactly as the pipeline does, using the bundled `schemas/alto-2-1.xsd`.

**Warning signs:**
- Saved ALTO files gain extra `xmlns=` attributes on every `String` element
- XSD validation passes before editing but fails after a save-cycle
- The pipeline's `--validate-only` flag reports new errors on files that were previously clean

**Phase to address:** Phase 3 (word editing) — establish a tested save + validate cycle in the first edit implementation. Never skip validation before overwrite.

---

### Pitfall 5: Concurrent Read/Write Race on ALTO XML Files

**What goes wrong:**
Two things can modify an ALTO XML file simultaneously:
1. The operator triggers a re-OCR of a file (which calls `process_tiff()` and writes a new `.xml` to disk).
2. The operator saves a word correction in the viewer (which reads, modifies, and writes the same `.xml`).

If these happen concurrently — even accidentally, e.g., the operator clicks "re-run OCR" while a slow word correction save is in flight — the file on disk may be corrupted: the re-OCR write truncates the file while the edit read is mid-parse, or vice versa.

A simpler version: the SSE progress stream is reading the job registry dict from one thread while the OCR worker thread is writing to it. If the dict values are complex mutable objects (lists, nested dicts), concurrent read/write without a lock can produce torn reads.

**Why it happens:**
Flask with `threaded=True` handles each request in a separate thread. Without explicit locking, two threads can operate on the same file simultaneously.

**How to avoid:**
Use a `threading.Lock` per file path (a `collections.defaultdict(threading.Lock)` keyed by the file stem is sufficient for a single-operator local tool). The edit-save endpoint acquires the lock before reading and holds it through the write. The OCR trigger endpoint acquires the same lock before writing the new ALTO file.

For the in-memory job registry, use a `threading.Lock` to protect all reads and writes to the job dict. Alternatively, use Python's `queue.Queue` for one-way progress updates from the OCR thread to the SSE stream — `Queue` is thread-safe by design and eliminates the need for a lock on the progress data.

**Warning signs:**
- Edited words occasionally revert to OCR text after a save
- ALTO file occasionally becomes unreadable (parse error) after concurrent operations
- SSE progress stream occasionally shows stale or contradictory state

**Phase to address:** Phase 1 (job management) for the job registry lock; Phase 3 (word editing) for the file-level lock.

---

### Pitfall 6: ProcessPoolExecutor Cannot Be Reused or Shared Across Flask Requests

**What goes wrong:**
`pipeline.py`'s `run_batch()` creates a `ProcessPoolExecutor` as a context manager (`with ProcessPoolExecutor(...) as executor:`). If the web app tries to create a long-lived module-level `ProcessPoolExecutor` to submit OCR jobs to from multiple Flask request threads, it hits two problems:

1. The executor is created at import time, before the Flask app's fork-safe `if __name__ == '__main__'` guard runs, causing multiprocessing spawn failures on macOS (which uses `spawn` not `fork`).
2. `ProcessPoolExecutor` workers cannot be easily monitored for per-file progress — futures only resolve when the entire `process_tiff()` call completes. There is no partial-progress yield from inside a subprocess.

The alternative of calling `run_batch()` directly from a Flask route handler inherits both problems: it blocks the request thread for the entire batch duration and produces no streaming progress.

**Why it happens:**
The developer tries to reuse the existing `run_batch()` function unchanged from within a Flask handler, assuming "just run it in a thread" is sufficient. The ProcessPoolExecutor spawns fine in the thread but provides no per-file progress until the batch completes.

**How to avoid:**
Run the OCR for a single queued file in a `threading.Thread` (not a subprocess pool). The thread calls `process_tiff()` directly (it internally spawns Tesseract as a subprocess — that subprocess is safe to spawn from a thread). The thread writes per-file progress to the job registry after each stage. The SSE endpoint reads from the job registry.

For multi-file queues (operator drags 5 TIFFs), process them sequentially in the same worker thread (one file at a time, updating progress between files) rather than launching a ProcessPoolExecutor. The web UI is single-operator; parallelism buys less than it costs in complexity for the progress tracking requirement.

The existing `pipeline.py` `ProcessPoolExecutor` path remains for the CLI batch mode — do not modify it to accommodate the web app. Keep CLI and web paths separate.

**Warning signs:**
- `OSError: [Errno 9] Bad file descriptor` on macOS when spawning workers from Flask
- Progress stream shows 0% for the entire batch, then 100% at the end
- OCR starts correctly for the first job but hangs on subsequent jobs

**Phase to address:** Phase 1 (job management) — the single-threaded-per-job model must be the design from the start, not a retrofit after discovering ProcessPoolExecutor doesn't compose with SSE.

---

### Pitfall 7: TIFF Rendered as JPEG Loses the Coordinate Reference Frame

**What goes wrong:**
The server converts the TIFF to JPEG using Pillow's `image.save()` with a JPEG quality setting. Pillow's default JPEG quality (75) significantly compresses archival scans — the 200 MB TIFF may yield a 15 MB JPEG that looks degraded at zoom levels operators need for proofreading. More importantly, if `image.thumbnail()` is used (which modifies the image in place and changes aspect ratio if the constraint is not applied correctly), the JPEG dimensions may not be proportional to the original TIFF dimensions, invalidating the coordinate scale factor computed by the JavaScript overlay.

A separate issue: for very large TIFFs (4000+ px wide), serving the full-resolution JPEG to the browser is slow (15–30 MB transfer) and the browser struggles to render it. But serving a downscaled JPEG requires the scale factor to be computed server-side and sent to the browser — the scale factor must be the ratio of the *served JPEG dimensions* to the *original TIFF dimensions*, not the ratio of the *CSS rendered size* to the *original TIFF dimensions*.

**Why it happens:**
The developer uses `image.thumbnail((800, 800))` without preserving the exact output dimensions, then hardcodes a scale factor. When the operator resizes the browser window or views a landscape-vs-portrait TIFF, the hardcoded factor is wrong.

**How to avoid:**
Use `image.resize()` with `Image.Resampling.LANCZOS` (not `thumbnail()`) and always record the exact output dimensions:
```python
original_w, original_h = image.size
scale = min(max_dimension / original_w, max_dimension / original_h)
new_w = int(original_w * scale)
new_h = int(original_h * scale)
jpeg_image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
```

Return `original_width`, `original_height`, `jpeg_width`, `jpeg_height` in the API response. The JavaScript computes `scaleX = rendered_img_width / original_width` using the image's actual rendered size at the time of overlay positioning, not the JPEG dimensions.

Serve the JPEG with `max_dimension = 2000` — large enough for proofreading, small enough for fast browser rendering.

**Warning signs:**
- Word bounding boxes are correct on portrait TIFFs but wrong on landscape TIFFs
- Boxes are correct immediately after page load but shift when the user resizes the browser window

**Phase to address:** Phase 2 (TIFF viewer) — JPEG generation and the coordinate API response must be designed together.

---

### Pitfall 8: Word-Level ALTO Edit Corrupts Sibling Elements

**What goes wrong:**
The operator edits the `CONTENT` attribute of a `String` element in the ALTO XML. The web app's edit endpoint receives `{word_id: "string_1234", new_content: "Zeitschrift"}`, finds the matching `String` element in the parsed tree, sets `elem.attrib['CONTENT'] = new_content`, and serializes back to disk.

The failure: the developer accidentally iterates `root.iter()` and modifies the tree while iterating, which corrupts the element order in lxml. Or the word ID lookup uses `xpath()` with an unconstrained `//String` search that finds elements in the wrong `TextBlock` when two blocks have identically numbered `String` elements (a real occurrence in Tesseract ALTO output with multi-column layouts).

A second corruption: the edit endpoint does a `str.replace()` on the raw XML bytes (e.g., `xml.replace(old_content, new_content)`) which is fragile — it replaces all occurrences, not just the target word, and breaks if the old content contains XML-special characters (`<`, `>`, `&`).

**Why it happens:**
String replacement seems simpler than lxml round-trips. The corruption only manifests on pages with repeated words or XML-special characters in OCR text.

**How to avoid:**
Use lxml for all edits — never string-replace XML. Use stable element IDs (`ID` attribute on `String` elements in Tesseract ALTO output) for lookup:
```python
target = root.find(f'.//{{{ALTO21_NS}}}String[@ID="{word_id}"]')
if target is None:
    return error("word not found")
target.attrib['CONTENT'] = new_content
```
Validate that `word_id` contains only alphanumeric/underscore characters before using it in an XPath expression — user-controlled XPath injection is a real risk even on a local tool.

Never modify the tree while iterating over it. Collect targets first, then modify.

**Warning signs:**
- Editing a word occasionally changes a different word on the same page
- Ampersands or angle brackets in OCR text cause the save to fail silently (the XML write succeeds but the file is malformed)
- Multi-column pages have edit-correctness issues that single-column pages do not

**Phase to address:** Phase 3 (word editing) — test explicitly with: repeated words, XML-special characters in OCR text, multi-column layouts.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| In-memory job registry (dict) | No Redis/DB dependency for local tool | Lost on server restart; no history | Acceptable — local single-operator tool, restart resets queue |
| Single OCR thread (no ProcessPool for web) | Simple progress tracking | Cannot parallelize multiple queued uploads | Acceptable for single-operator use; add queue if multi-file demand emerges |
| JPEG served from memory on each request | No JPEG cache to manage | Re-converts TIFF on every viewer load | Never — cache the JPEG to disk alongside the ALTO XML after first conversion |
| Raw `str.replace()` for XML editing | 10 lines instead of 30 | Corruption on special characters, multi-match | Never — use lxml |
| `flask run` dev server for local deployment | No setup, works immediately | Can't handle concurrent requests reliably | Acceptable for single-operator localhost; use Gunicorn if multi-user |
| Skip XSD validation on save | Faster edit cycle | Edited files can become schema-invalid silently | Never — run `validate_alto_file()` after every save |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pipeline.py + Flask | Call `run_batch()` directly from a route handler | Import and call `process_tiff()` in a `threading.Thread`; track progress in job registry |
| lxml + HTTP response | Return `etree.tostring()` bytes directly with `mimetype='application/xml'` | Correct — but include `xml_declaration=True, encoding='UTF-8'` |
| Pillow + JPEG endpoint | `image.thumbnail()` modifies image in place; changes original object | Work on a copy: `img_copy = img.copy(); img_copy.thumbnail(...)` or use `img.resize()` |
| ALTO namespace + lxml save | `etree.tostring(root)` may inline namespace on child elements | Always use the same serialization as `build_alto21()`: `xml_declaration=True, encoding='UTF-8', pretty_print=True` |
| SSE + Flask dev server | Open SSE connection while OCR runs in the same thread | SSE endpoint reads from job registry (a dict); OCR runs in a separate `threading.Thread` |
| JavaScript EventSource + Flask | CORS headers missing (localhost to localhost can still trigger CORS on some browsers) | Set `Access-Control-Allow-Origin: *` on SSE endpoints, or serve UI and API from same Flask origin |
| werkzeug `secure_filename()` + TIFF stems | `secure_filename()` on `scan 001.tif` returns `scan_001.tif` — stem changes | Use `secure_filename()` for storage, map back to original stem for ALTO XML matching |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| JPEG re-generated on every viewer load | Viewer loads slowly (3–10 seconds per TIFF open) | Cache JPEG alongside ALTO XML at first view; serve from cache on subsequent views | From the first 200 MB TIFF |
| Full ALTO XML parsed on every word-click | Each click triggers a 200–500 ms server round-trip | Parse ALTO once per page view; send all word data as JSON in the initial API response; highlight client-side only | From any page with 500+ words |
| All words rendered as DOM elements | 1000+ `<div>` overlay elements causes layout thrash | Use a `<canvas>` overlay for boxes; only create DOM elements for the currently selected word | Pages with 800+ words |
| TIFF loaded into RAM for JPEG conversion, not discarded | Repeated viewer loads accumulate memory | Use `with Image.open(path) as img:` (context manager ensures close); do not store PIL Image objects in module-level cache | Second viewer load onward |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Serving TIFF files directly without path validation | Path traversal — `GET /tiff?path=../../etc/passwd` | Validate that the resolved path is inside the configured input directory; use `Path.resolve()` and check prefix |
| Using raw `word_id` from the request in an lxml XPath query | XPath injection — crafted ID could select unintended nodes | Validate `word_id` matches `^[a-zA-Z0-9_-]+$` before using in XPath |
| Saving uploaded files without `secure_filename()` | Overwrite any file on disk with a crafted filename | Always `werkzeug.utils.secure_filename()` before `file.save()` |
| No cap on `MAX_CONTENT_LENGTH` | Disk exhaustion from uploading arbitrary-size files | Set `MAX_CONTENT_LENGTH = 300 * 1024 * 1024`; document the 300 MB cap |
| Serving uploaded TIFFs with no content-type | Browser may interpret TIFF as HTML if server omits `Content-Type` | Explicitly set `Content-Type: image/tiff` on TIFF endpoints |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Upload progress not shown separately from OCR progress | Operator sees no feedback during 30-second 200 MB upload; assumes app is frozen | Show upload % via `XMLHttpRequest.upload.onprogress` (separate from OCR SSE stream) |
| OCR failure only visible in server log | Operator thinks OCR is still running when it silently failed | SSE stream must emit an explicit `event: error` frame; UI must display error state |
| No "already processed" indication in file browser | Operator re-queues a file that has a good ALTO XML, triggering unnecessary re-OCR | File browser shows green/grey indicator based on ALTO XML existence; warn before re-queue |
| Word correction saved with no visual confirmation | Operator unsure if edit was saved; may click again and double-save | Show an inline "Saved" confirmation that fades after 2 seconds; disable the Save button while save is in flight |
| JPEG quality too low for proofreading | Operator can't read fine print in compressed JPEG | Use JPEG quality=90 for viewer; quality=75 makes archival text illegible at small sizes |

---

## "Looks Done But Isn't" Checklist

- [ ] **Upload endpoint:** Verify `secure_filename()` is applied and `MAX_CONTENT_LENGTH` is set to 300 MB before testing with real filenames containing spaces or umlauts.
- [ ] **SSE progress:** Verify that the browser EventSource receives events *while* OCR is running, not just after completion. Test with a real 200 MB TIFF, not a fixture.
- [ ] **Bounding box overlay:** Verify coordinate scaling by comparing a word's overlay box against the actual word position at three browser window sizes. Test with a landscape TIFF (wider than tall) separately from portrait.
- [ ] **ALTO save:** Verify saved ALTO file passes `validate_alto_file()` after editing. Test with a word that contains an ampersand (`&`) in OCR text — lxml must escape it to `&amp;`.
- [ ] **JPEG cache:** Verify the JPEG is cached after first generation and not re-converted on every viewer page load. Check with a 200 MB TIFF.
- [ ] **Concurrent edit + re-OCR:** Verify that triggering re-OCR while a word edit save is in flight does not corrupt the ALTO XML. Requires manual test with two browser tabs.
- [ ] **Namespace on save:** After editing any word, run `--validate-only` via the CLI on the saved file to confirm the CCS-GmbH namespace is intact and XSD still passes.
- [ ] **XPath injection:** Verify that a `word_id` like `' or '1'='1` is rejected by the edit endpoint with a 400 error.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SSE blocking (OCR in request thread) | HIGH — requires refactoring the job management model | Extract OCR call into `threading.Thread` with job registry; retrofit SSE endpoint to poll registry |
| Coordinate scaling bug discovered late | MEDIUM — UI-only fix if server sends correct dimensions | Add `original_width`/`original_height` to API response; update JavaScript scale calculation |
| ALTO namespace corruption from bad save | MEDIUM — existing ALTO files may need repair | Re-run `pipeline.py --validate-only` to identify corrupted files; re-run OCR on affected files with `--force` |
| JPEG quality too low (operator can't proofread) | LOW — change quality setting and rebuild cache | Delete cached JPEGs; update quality constant; next viewer load regenerates |
| Concurrent file corruption | HIGH — may require manual XML repair | Add `threading.Lock` per file stem; restore affected ALTO files from the OCR output (re-run `--force`) |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Flask dev server blocks during OCR (#1) | Phase 1: Flask foundation + job management | SSE stream sends events every ~2 seconds during a real 200 MB TIFF OCR run |
| Large file upload buffered into RAM (#2) | Phase 1: Flask foundation | Upload a 200 MB TIFF; confirm `MAX_CONTENT_LENGTH` error is clean, not connection reset |
| TIFF-to-JPEG coordinate mismatch (#3) | Phase 2: TIFF viewer | Compare overlay boxes against actual word positions at three window sizes; test landscape TIFF |
| ALTO namespace lost on save (#4) | Phase 3: Word editing | Run CLI `--validate-only` on every saved file; check namespace declaration is on root element only |
| Concurrent read/write race (#5) | Phase 1 (job registry lock) + Phase 3 (file lock) | Manual test: trigger re-OCR while saving an edit from a second tab |
| ProcessPoolExecutor incompatible with SSE (#6) | Phase 1: Job management design | Confirm OCR thread model (threading.Thread, not ProcessPoolExecutor) before building the UI layer |
| JPEG dimension mismatch (#7) | Phase 2: TIFF viewer | API response must include `original_width`/`original_height`; verify with landscape vs portrait |
| Word-level edit corrupts siblings (#8) | Phase 3: Word editing | Test with: repeated words, `&` in OCR text, multi-column ALTO layout |

---

## Sources

- Flask documentation: `flask.palletsprojects.com/en/stable/patterns/fileuploads/` — `MAX_CONTENT_LENGTH` behavior, Werkzeug temp file handling (HIGH confidence)
- Flask documentation: `flask.palletsprojects.com/en/stable/api/#flask.Flask.run` — `threaded=True` is default since Flask 0.10 (HIGH confidence)
- lxml documentation: serialization behavior with `etree.tostring()`, namespace declarations on child elements vs root (HIGH confidence — confirmed in pipeline.py build_alto21() implementation)
- `pipeline.py` source code: `build_alto21()` function documents the mandatory serialization order; all ALTO-specific pitfalls derive from the existing code's known invariants (HIGH confidence — first-party source)
- Pillow documentation: `Image.thumbnail()` modifies in place, aspect-ratio behavior; `Image.Resampling.LANCZOS` for downscaling (HIGH confidence)
- Python stdlib: `threading.Thread`, `threading.Lock`, `queue.Queue` — thread-safety guarantees (HIGH confidence)
- macOS multiprocessing: `spawn` start method is default on macOS — `ProcessPoolExecutor` created before `if __name__ == '__main__'` guard causes spawn failures (HIGH confidence — documented in Python multiprocessing docs and confirmed in pipeline.py phase 02-01 decision log)
- Server-Sent Events specification: SSE requires a long-lived HTTP response that yields `data:` frames; incompatible with a blocking request handler thread (HIGH confidence — web standard)

---
*Pitfalls research for: Flask web viewer wrapping Python OCR pipeline (v1.4)*
*Researched: 2026-02-27*
