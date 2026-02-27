# Project Research Summary

**Project:** Zeitschriften-OCR v1.4 Web Viewer
**Domain:** Local Flask web viewer for batch TIFF OCR pipeline — drag-and-drop upload, live progress streaming, side-by-side TIFF+text viewer, word-level ALTO XML correction
**Researched:** 2026-02-27
**Confidence:** HIGH (stack and architecture verified against first-party codebase and real ALTO output; pitfalls grounded in direct pipeline.py analysis; features cross-referenced with reference tools)

## Executive Summary

v1.4 adds a local Flask web interface to the existing `pipeline.py` CLI. The product is a single-operator localhost tool, not a multi-user server, and every architectural decision must reflect that constraint. The recommended approach is minimal: one new file (`app.py`, ~250 lines), one new dependency (`flask>=3.1.3`), vanilla JS with Jinja2 templates, and Server-Sent Events for live progress — no extensions, no frontend framework, no build step. All OCR logic stays in `pipeline.py`; the web layer calls its functions via direct import, not subprocess. Total new pip dependencies: one package.

The defining architectural challenge is the concurrency model. OCR on archival TIFFs takes 10–60 seconds per file, and the SSE progress stream must deliver events during that window, not after it. The correct pattern is to run OCR in a `threading.Thread` (not in a `ProcessPoolExecutor`, which has no mechanism to yield per-file progress to an SSE stream), write progress dicts to a `queue.Queue`, and have the SSE generator read from that queue with a timeout keepalive. This threading model must be established in Phase 1 before any UI is built on top of it — retrofitting it after the viewer is built is expensive.

The two other non-negotiable correctness constraints are coordinate scaling and ALTO namespace preservation on save. ALTO coordinates live in original full-resolution TIFF pixel space; the browser renders a Pillow-scaled JPEG. Every bounding box overlay must apply a live scale factor computed from the image's current rendered dimensions via `ResizeObserver`, not a one-time calculation at load. On the save path, lxml serialization must use `xml_declaration=True, encoding='UTF-8', pretty_print=True` and the result must pass `validate_alto_file()` before writing to disk — a naive `etree.tostring()` call can scatter namespace declarations onto child elements, silently producing files that fail XSD validation and Goobi ingest.

## Key Findings

### Recommended Stack

The stack delta for v1.4 is deliberately small: add `flask>=3.1.3` to `requirements.txt`. Werkzeug (bundled with Flask), Pillow, and lxml are already present and cover all remaining requirements — JPEG thumbnail generation, ALTO XML parsing, and atomic file writes. No Flask extensions are needed. Flask-SSE requires Redis; Flask-SocketIO adds WebSocket complexity that SSE does not require; Flask-CORS is unnecessary because the app is same-origin. On the frontend, vanilla JS (ES2020+) with Jinja2 server-rendered templates is correct for a four-view app. All required browser APIs are native: `EventSource` for SSE, `fetch` for JSON endpoints, `DataTransfer` for drag-and-drop, and `document.createElementNS` for SVG rect overlays. Alpine.js, HTMX, React, and Vue were evaluated and rejected — the reactive overhead is not justified for this scope.

See `.planning/research/STACK.md` for full decision rationale and rejected alternatives.

**Core technologies:**
- **Flask 3.1.3**: HTTP routing, SSE streaming, file upload, static serving — no extensions needed
- **Werkzeug 3.1.6** (bundled automatically): `secure_filename()` for upload path safety
- **Pillow >=11.1.0** (existing): TIFF-to-JPEG thumbnail generation via `image.resize()` with `LANCZOS`
- **lxml >=5.3.0** (existing): ALTO XML parsing, word extraction, CONTENT attribute update, round-trip serialization
- **Vanilla JS (ES2020+)**: `EventSource`, `fetch`, `DataTransfer`, SVG `createElementNS` — all native browser APIs; no CDN dependency

### Expected Features

The v1.4 scope is fixed by PROJECT.md. All six P1 features are true table stakes — missing any one makes the tool non-functional for the operator workflow. The P2 features add measurable workflow speed without requiring architectural changes. Anti-features (coordinate editing, ALTO structural editing, multi-user, authentication) are firmly out of scope and would add disproportionate complexity.

See `.planning/research/FEATURES.md` for full feature list with complexity ratings, dependency graph, and competitor analysis.

**Must have (table stakes — v1.4):**
- TIFF-to-JPEG proxy endpoint — browsers cannot display TIFFs; blocks every visual feature
- Coordinate scaling (pixel-to-rendered, dynamic) — correctness gate; wrong scaling makes all overlays wrong
- Word bounding box overlay (SVG rects over `<img>`) — required for visual OCR verification
- Click word in text panel / click box on image — bidirectional cross-reference via ALTO `String/@ID`
- Inline word editing and atomic save to ALTO XML — the core correction workflow
- File browser, drag-and-drop upload, OCR trigger with live SSE progress — entry and navigation flow

**Should have (v1.4.x — add after operator validation):**
- Word confidence coloring (WC attribute already present in ALTO output; low cost to render)
- Keyboard navigation (Tab to next word — substantially speeds systematic correction)
- Resizable split panel (trivial CSS flex + drag divider; operators on wide monitors benefit)
- One-level undo (Ctrl+Z, client-side state only; low cost)

**Defer (v2+):**
- Thumbnail sidebar — HIGH cost, LOW gain at hundreds-of-files scale
- "Jump to next unreviewed word" — requires persistent client state; defer until workflow is validated
- Batch correction across files — full-corpus search; out of scope for single-file viewer

### Architecture Approach

The architecture is a two-file Python project: existing `pipeline.py` unchanged for OCR logic, and new `app.py` for the Flask layer. `app.py` imports directly from `pipeline.py` — no subprocess, no reimplemented OCR. The OCR background worker calls `process_tiff()` sequentially per queued TIFF in a `threading.Thread`, posting progress dicts to a module-level `queue.Queue`. The SSE endpoint (`GET /stream`) reads from that queue with a 30-second timeout and yields keepalive comments to prevent proxy and browser connection drops during long OCR runs. Module-level state (`_ocr_queue`, `_ocr_running`) is appropriate for a single-operator local tool.

The frontend is two HTML pages (not a SPA): `static/index.html` for upload and progress, `static/viewer.html` for the side-by-side TIFF+text viewer and correction. An SVG overlay (`position: absolute` over `<img>`) renders one `<rect>` per ALTO `String` element; the SVG `viewBox` maps ALTO coordinates to rendered-image space. The ALTO JSON API (`GET /alto/<stem>`) returns a flat word array with `page_width`, `page_height`, and per-word `hpos/vpos/width/height/confidence/line_id` — everything the frontend needs in one request.

See `.planning/research/ARCHITECTURE.md` for full build-order phases, concrete endpoint patterns, and anti-patterns to avoid.

**Major components:**
1. **`app.py` (Flask)** — HTTP routing, SSE stream generator, TIFF-to-JPEG thumbnail, ALTO JSON API, word correction endpoint, module-level job state (`_ocr_queue`, `_ocr_running`, `_file_locks`)
2. **`pipeline.py` (existing, no changes)** — `process_tiff()`, `load_tiff()`, `validate_tesseract()`, `load_xsd()`, `validate_alto_file()`, `discover_tiffs()`, `ALTO21_NS`
3. **`static/index.html` + `app.js`** — drag-and-drop upload UI, SSE-driven progress display, file browser
4. **`static/viewer.html` + `viewer.js`** — TIFF image display, SVG bounding box overlay, bidirectional word cross-reference, inline correction

### Critical Pitfalls

See `.planning/research/PITFALLS.md` for full risk analysis with detection signs, recovery costs, and phase-to-pitfall mapping.

1. **OCR blocking the Flask request thread** — calling `process_tiff()` synchronously in a route handler blocks SSE stream delivery for the entire OCR duration; SSE connects but never fires events. Prevention: always run OCR in `threading.Thread(target=worker, daemon=True)`; return 202 from `POST /run` immediately; SSE reads from `queue.Queue`. Must be established in Phase 1.

2. **Coordinate scaling omitted or static** — ALTO coordinates are in original TIFF pixel space; the browser renders a scaled JPEG. Drawing boxes using raw ALTO coordinates on the rendered image produces systematically wrong overlays. Prevention: `GET /alto/<stem>` response must include `page_width` and `page_height`; JavaScript must compute `scaleX = renderedWidth / pageWidth` and recompute on every resize via `ResizeObserver`.

3. **ALTO namespace mangled on lxml round-trip** — naive `etree.tostring(root)` scatters `xmlns=` onto child elements; omitting `xml_declaration=True` drops the declaration Goobi requires. Prevention: serialize with `xml_declaration=True, encoding='UTF-8', pretty_print=True`; run `validate_alto_file()` before every disk write; return error to browser if validation fails — never silently overwrite.

4. **ProcessPoolExecutor used from a Flask thread** — `run_batch()` uses `ProcessPoolExecutor` internally; it cannot yield per-file progress to an SSE stream and causes `OSError: Bad file descriptor` on macOS when spawned from a Flask request thread. Prevention: call `process_tiff()` directly in a `threading.Thread`. The CLI's `run_batch()` path is preserved unchanged; web and CLI paths must be separate.

5. **Concurrent ALTO XML read/write corruption** — re-triggering OCR on a file while a word correction save is in flight can corrupt the ALTO file. Prevention: use `threading.Lock` per file stem (`defaultdict(threading.Lock)` keyed on stem); the edit endpoint holds the lock through the full read-modify-write-validate cycle.

## Implications for Roadmap

The build-order dependencies are explicit from both the architecture and pitfalls research: the threading/SSE concurrency model must be established before any UI, the JPEG endpoint must exist before the viewer can be built, and the ALTO save correctness (lxml serialization + validation gating) must be established before any word edit interaction. The roadmap should follow this sequence without collapsing phases.

### Phase 1: Flask Foundation and Job Management

**Rationale:** The concurrency model (threading.Thread + queue.Queue for SSE) is the highest-risk failure mode in the project. If it is wrong, everything built on top must be refactored. Establish it first with no UI; verify with curl and server logs against a real 200 MB TIFF before writing any HTML.
**Delivers:** Bootable `app.py` with `/files` listing, upload staging, background OCR thread, SSE progress stream — verified end-to-end before any viewer UI exists.
**Addresses:** File browser, drag-and-drop upload, OCR trigger, live progress (all P1 features in the upload/orchestration layer)
**Avoids:** Pitfall 1 (blocking thread), Pitfall 4 (ProcessPoolExecutor on macOS), Pitfall 5 (concurrent file corruption — job registry lock must be here)
**Stack:** Flask 3.1.3, `threading.Thread`, `queue.Queue`, `werkzeug.utils.secure_filename`, `MAX_CONTENT_LENGTH=300MB`, `defaultdict(threading.Lock)`

### Phase 2: TIFF-to-JPEG Serving and Coordinate API

**Rationale:** The JPEG endpoint and coordinate API are correctness blockers for the viewer. Both must exist and be verified against real 200 MB TIFFs — including landscape TIFFs — before any overlay or correction UI is built. A coordinate scaling bug discovered after the viewer is built is expensive to retrofit because it invalidates all overlay positioning logic.
**Delivers:** `GET /image/<stem>` serving scaled JPEG; `GET /alto/<stem>` returning flat word array with `page_width`, `page_height`, per-word bbox and confidence. Verified that scale factors are correct at three browser window widths, for both portrait and landscape TIFFs.
**Addresses:** TIFF proxy endpoint, coordinate scaling (P1 correctness gates)
**Avoids:** Pitfall 3 (coordinate mismatch), Pitfall 7 (JPEG dimension mismatch — use `image.resize()` with explicit computed dimensions, not `thumbnail()`)
**Stack:** Pillow `image.resize()` with `LANCZOS`, lxml `parse_alto_words()`, JSON response including `page_width`/`page_height`/`jpeg_width`/`jpeg_height`

### Phase 3: Side-by-Side Viewer UI

**Rationale:** Depends on Phase 2 (JPEG endpoint + ALTO JSON must be correct before viewer is built). The SVG overlay on the JPEG image, text panel, and bidirectional word-click cross-reference form one coherent UI unit — implement and test together.
**Delivers:** `static/viewer.html` + `viewer.js` — TIFF image in left panel (60% width), word text in right panel (40%), SVG `<rect>` bounding boxes at 20–30% opacity, click-in-text highlights box, click-on-box highlights text.
**Addresses:** Side-by-side layout, word bounding box overlay, click-to-highlight cross-reference (P1 features)
**Avoids:** Coordinate errors on resize (ResizeObserver for dynamic scale recompute); SVG viewBox for automatic coordinate-space mapping without JS math

### Phase 4: Word Correction Endpoint and Edit Interaction

**Rationale:** Depends on Phase 3 (viewer must work before inline editing is added as an interaction layer). The save path must be established with full lxml round-trip correctness and XSD validation gating before operators use it on real files.
**Delivers:** `POST /alto/<stem>` write-back; inline `<input>` edit in viewer.js; Tab/Enter/Escape keyboard handling; atomic `.xml.tmp` → `.xml` rename; post-save `validate_alto_file()` check with error return on failure.
**Addresses:** Inline word editing, save to ALTO XML (P1 features)
**Avoids:** Pitfall 3 (namespace corruption on lxml save), Pitfall 5 (file lock already in place from Phase 1), Pitfall 8 (sibling element corruption via XPath injection — validate `word_id` against `^[a-zA-Z0-9_-]+$`)
**Stack:** lxml `find(f'.//{{{NS}}}String[@ID="{word_id}"]')`, `etree.tostring(xml_declaration=True, encoding='UTF-8', pretty_print=True)`, `validate_alto_file()` as write gate

### Phase 5: Upload UI, SSE Progress Display, and End-to-End Integration

**Rationale:** The upload UI and SSE client can be built in parallel with Phases 3–4 (the backend thread model from Phase 1 is already complete). Bringing it together as the final integration step ensures all pieces are individually verified before end-to-end operator testing.
**Delivers:** `static/index.html` + `app.js` — drag-and-drop upload zone, file queue display, upload progress via `XMLHttpRequest.upload.onprogress`, SSE-driven progress bar, "already processed" indicator in file browser, error state display. Full workflow: upload TIFF → trigger OCR → watch live progress → browse to viewer → correct words.
**Addresses:** All P1 features integrated; complete operator workflow validated
**Stack:** `EventSource('/stream')`, `FormData` + `fetch`, `XMLHttpRequest.upload.onprogress` for pre-OCR upload progress (separate from SSE)

### Phase 6: P2 Enhancements

**Rationale:** Add only after Phase 5 is validated with an operator on real files. These are low-cost additions that require no architectural changes and can ship as independent v1.4.x patches.
**Delivers:** Word confidence coloring (parse `@WC`, CSS gradient), keyboard navigation (Tab/Shift-Tab advances word, Enter saves, Escape reverts), resizable split panel (CSS flex + drag divider), one-level undo (Ctrl+Z, client-side state).
**Addresses:** P2 differentiator features
**Note:** Each P2 feature is independent; they do not need to ship together.

### Phase Ordering Rationale

- Phase 1 must come first: the SSE concurrency model underlies every progress-related feature; getting it wrong invalidates all subsequent work.
- Phase 2 must come before Phase 3: the viewer cannot be built or tested without correct JPEG serving and ALTO coordinate data.
- Phase 3 must come before Phase 4: inline editing requires a working viewer as its host context.
- Phase 5 integrates last: the upload+progress frontend shares only the Phase 1 backend; completing it last ensures all backend pieces are individually verified before end-to-end testing.
- Phase 6 is fully decoupled: it adds features without touching the core data flow and can be done in any order after Phase 5.

### Research Flags

Phases with standard patterns (no additional research phase needed):
- **Phase 1 (Flask threading + SSE):** Pattern is fully documented in ARCHITECTURE.md with concrete, working code examples. Flask `stream_with_context` + `threading.Thread` + `queue.Queue` is a well-established pattern.
- **Phase 2 (Pillow JPEG + lxml ALTO parsing):** Both libraries are already in use in the project; patterns are verified against real ALTO output files in this codebase.
- **Phase 5 (Upload UI + SSE client):** All required APIs are native browser; MDN-documented patterns apply directly.

Phases that benefit from a targeted spike before full implementation:
- **Phase 3 (SVG overlay with ResizeObserver):** Straightforward pattern, but should be tested early against real ALTO files from this project specifically. Multi-column layouts with 800+ words per page are the edge case to validate. If any page exceeds ~2,000 words, evaluate Canvas as a fallback for rendering performance.
- **Phase 4 (ALTO save + lxml namespace round-trip):** Spike-test `etree.tostring(xml_declaration=True, encoding='UTF-8', pretty_print=True)` against a real ALTO file from this project before building the full endpoint. The namespace preservation behavior of lxml under round-trip edit needs one confirmed working example before the endpoint is built around it.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Flask version verified via pip (Feb 2026); Werkzeug, Pillow, lxml versions confirmed against existing requirements.txt; Pillow JPEG conversion tested locally (0.163s for 4000×5500 TIFF); lxml ALTO round-trip tested locally |
| Features | MEDIUM | P1 features from PROJECT.md are HIGH confidence; reference tool analysis (KBNL, eScriptorium, Transkribus, PRImA ALTOVIEWER) is training-data MEDIUM — UX patterns are well-established even if not freshly web-verified |
| Architecture | HIGH | Conclusions drawn from direct inspection of pipeline.py (1,146 lines) and real ALTO XML output file; Flask 3.1.x streaming patterns verified against official documentation |
| Pitfalls | HIGH | All critical pitfalls derive from first-party sources (pipeline.py, lxml serialization behavior, Python multiprocessing macOS constraints, Flask documentation); no speculative risks |

**Overall confidence:** HIGH

### Gaps to Address

- **`thumbnail()` vs `resize()` discrepancy:** STACK.md recommends Pillow `thumbnail()` while PITFALLS.md recommends `resize()` for predictable output dimensions. Resolution: use `image.resize()` with explicit computed dimensions in Phase 2; record both `jpeg_width` and `jpeg_height` in the ALTO API response to avoid any ambiguity in the JavaScript scale calculation.

- **SVG overlay performance ceiling:** FEATURES.md flags Canvas as preferred above ~5,000 words/page. Sample real ALTO files from this project for word count before committing to SVG-only in Phase 3. If any production page exceeds ~2,000 words, plan a Canvas fallback path from the start.

- **`secure_filename()` stem normalization:** `secure_filename("Scan 001.tif")` returns `"Scan_001.tif"` — the stem changes. Phase 1 must establish a canonical stem normalization rule applied consistently at upload time, ALTO path resolution, JPEG path resolution, and viewer routing. Inconsistency between these four paths is a latent bug that only surfaces on filenames with spaces or umlauts.

- **lxml namespace round-trip — one confirmed example needed:** Research documents the risk and the correct serialization call. A five-minute spike test against a real ALTO file from this project should be the first task of Phase 4 to confirm the exact invocation before the endpoint is built.

## Sources

### Primary (HIGH confidence)
- `pipeline.py` (1,146 lines, direct inspection) — function signatures, ProcessPoolExecutor pattern, ALTO namespace constants, `build_alto21()` serialization invariants, macOS spawn constraint
- `output/alto/Ve_Volk_165945877_1957_Band_1-0001.xml` (real ALTO output, direct inspection) — confirmed pixel coordinates, `MeasurementUnit=pixel`, page dimensions 5146×7548, String element structure with ID/HPOS/VPOS/WIDTH/HEIGHT/WC/CONTENT
- `pip index versions flask` / `pip index versions werkzeug` — confirmed Flask 3.1.3 and Werkzeug 3.1.6 as current stable (Feb 2026)
- Flask 3.1.x official documentation — `stream_with_context`, `Response`, `send_file`, `threaded=True`, `MAX_CONTENT_LENGTH`
- Python stdlib — `threading.Thread`, `threading.Lock`, `queue.Queue`, `collections.defaultdict` (thread-safety guarantees)
- Pillow documentation — `Image.thumbnail()` in-place behavior, `Image.Resampling.LANCZOS`, TIFF lazy decode behavior
- lxml documentation — `etree.tostring()` namespace declaration behavior, `xml_declaration=True` parameter
- MDN Server-Sent Events specification — wire format, `EventSource` browser API, keepalive comment syntax
- Python multiprocessing docs — macOS `spawn` start method; `ProcessPoolExecutor` pre-fork constraints

### Secondary (MEDIUM confidence)
- KBNL alto-editor (training data) — word-level editing patterns, SVG overlay, String ID cross-reference
- eScriptorium (training data) — synchronized panel UX patterns, inline editing, image-text coupling
- Transkribus (training data) — word confidence visualization, keyboard navigation patterns
- PRImA ALTOVIEWER (training data) — two-panel read-only viewer; confirms 60/40 image/text split as established convention

### Tertiary (LOW confidence)
- Pillow JPEG conversion performance on 4000×5500 TIFFs: 0.163s (single local test, not benchmarked systematically — verify on operator hardware before committing to in-memory serving strategy)

---
*Research completed: 2026-02-27*
*Ready for roadmap: yes*
