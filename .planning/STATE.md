# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.5 Web Viewer Complete — Phase 17 (VLM Settings UI) in progress

## Current Position

Phase: 17 — VLM Settings UI (in progress)
Plan: 17-02 next — frontend settings panel in upload.html
Status: 17-01 complete — OpenAICompatibleProvider, GET/POST /settings, GET /settings/models, segment_page() reads settings.json
Last activity: 2026-03-01 — 17-01 executed (settings backend, 116 tests pass)

Progress: [█████████░░░░░░░░] 16/18 phases complete (Phase 17 planning)

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: 3.6 min
- Total execution time: 51 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Single-File Pipeline | 2/2 | 4 min | 2 min |
| 2. Batch Orchestration and CLI | 2/2 | 4 min | 2 min |
| 3. Validation and Reporting | 2/2 | 6 min | 3 min |
| 4. Deskew | 1/1 | 6 min | 6 min |
| 5. Adaptive Thresholding | 1/1 | 2 min | 2 min |
| 6. Diagnostic Flags | 2/2 | 6 min | 3 min |
| 7. Live Progress Display | 1/1 | 2 min | 2 min |
| 8. Config File Support | 2/2 | 11 min | 5.5 min |
| 9. Flask Foundation and Job State | 2/2 | 3 min | 1.5 min |
| 10. TIFF and ALTO Data Endpoints | 2/2 | 7 min | 3.5 min |
| 11. Side-by-Side Viewer UI | 2/2 | ~62 min | ~31 min |
| 12. Word Correction | 2/2 | ~7 min | ~3.5 min |
| 13. Upload UI and Live Progress | 2/2 | ~10 min | ~5 min |
| 14. Viewer Zoom and Pan | 1/1 | ~25 min | ~25 min |
| 15. VLM Article Segmentation | 2/2 | ~23 min | ~11.5 min |
| 16. METS/MODS Output | 1/2 | 27 min | 27 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.4 research]: OCR must run in threading.Thread (not ProcessPoolExecutor) — ProcessPoolExecutor cannot yield per-file progress to SSE stream and causes OSError on macOS spawn from Flask thread
- [v1.4 research]: SSE via queue.Queue with 30s timeout keepalive — prevents proxy/browser connection drops during long OCR runs
- [v1.4 research]: Use image.resize() (not thumbnail()) — explicit computed dimensions needed; record jpeg_width/jpeg_height in ALTO API response
- [v1.4 research]: defaultdict(threading.Lock) keyed on stem — prevents concurrent ALTO read/write corruption on re-trigger
- [v1.4 research]: lxml serialize with xml_declaration=True, encoding=UTF-8, pretty_print=True + validate_alto_file() gate before every write
- [v1.4 research]: secure_filename() stem normalization must be consistent across upload, ALTO path, JPEG path, and viewer routing
- [Phase 09-flask-foundation-and-job-state]: Use importlib.import_module('app') inside fixture body — defers ImportError to test time, not conftest load time
- [Phase 09-flask-foundation-and-job-state]: monkeypatch.setattr(app_module.pipeline, 'process_tiff', mock) pattern for OCR worker isolation in tests
- [Phase 09-02]: threading.Thread (not ProcessPoolExecutor) for _ocr_worker — enables per-file SSE streaming, avoids macOS spawn issues
- [Phase 09-02]: _run_active.clear() in finally block — PROC-04 contract: active flag clears even if all files fail
- [Phase 10-01]: test_path_traversal_slash uses lenient assertion (400 or 404) — Flask route matching returns 404 before endpoint logic runs; both confirm no 200 JPEG is returned for slash-containing stems
- [Phase 10-01]: confidence=None (not 0) for ALTO words missing WC attribute — explicitly asserted with is None to prevent silent coercion bugs in implementation
- [Phase 10-02]: before_request path traversal guard added — Flask/Werkzeug normalizes /../ URLs before route dispatch; route-level stem check unreachable; before_request fires on raw request.path
- [Phase 10-02]: No disk cache for ALTO JSON — parse XML on every request to stay consistent with Phase 12 XML edits
- [Phase 11-01]: GET /files returns empty stems list when alto/ directory does not exist (graceful no-dir handling)
- [Phase 11-01]: templates/viewer.html is a stub in plan 01; full implementation delivered in plan 02
- [Phase 11-02]: Generation counter (loadGen++) in loadFile() prevents stale async fetch results on rapid file switching
- [Phase 11-02]: img.clientWidth (not naturalWidth) used for SVG scale factors — clientWidth reflects CSS display size matching ALTO coordinate space
- [Phase 11-02]: --input CLI flag + INPUT_DIR fallback added to serve_image() — enables viewer JPEG display for CLI-processed TIFFs not in uploads/
- [Phase 12-01]: pipeline.SCHEMA_PATH promoted to module-level Path constant — was local variable in main(), needed as module attribute for app.py access
- [Phase 12-01]: XSD-valid test fixture requires Page ID+PHYSICAL_IMG_NR and element dimension attributes — minimal ALTO fixture fails XSD gate correctly
- [Phase 12-01]: Atomic write via tempfile.mkstemp+os.replace in same directory — prevents partial-write corruption on ALTO XML edits
- [Phase 12-02]: editingSpan module-level variable enforces single-edit-at-a-time — one null check in onclick covers all cases
- [Phase 12-02]: setTimeout(0) in blur handler defers cancel to let onclick fire first on word-to-word transitions
- [Phase 12-02]: void span.offsetWidth reflow trick required to restart CSS animation on re-edit of same word
- [Phase 12-02]: loadFile() guard (if editingSpan) cancelEdit() handles file-switch-while-editing cleanly
- [Phase 13-01]: GET / renamed from viewer() to index() — semantically correct for upload dashboard entry point
- [Phase 13-01]: GET /viewer/<stem> path traversal guard uses same if '/' in stem or '..' in stem pattern as /image/<stem> and /alto/<stem>
- [Phase 13-01]: TestViewerRoute tests left red (TemplateNotFound: upload.html) until Plan 02 creates the template — expected, not a regression
- [Phase 13-02]: File objects stored in queue Map entries so FormData can be built at startRun() time — required because browser File objects cannot be reconstructed from filenames
- [Phase 13-02]: stem = tiff_path.stem.lower() in _ocr_worker — SSE d.stem must match JS stem() which lowercases; original case caused silent file_done row update failures
- [Phase 13-02]: Parse POST /upload JSON response in startRun() to identify already_processed files — totalInRun must exclude already-done files or status counter denominator is wrong
- [Phase 14-01]: ZOOM_STEP increased 1.1 → 1.3 after user verification — 1.1 per-tick feel was too subtle for newspaper inspection workflow
- [Phase 14-01]: translate before scale in applyTransform() — panX/panY remain pre-scale screen pixels for natural 1:1 drag feel
- [Phase 14-01]: overflow: hidden on #image-panel required — overflow: auto creates scrollbars that conflict with transform-based pan
- [Phase 14-01]: Shared-container transform (single div wrapping img + svg) eliminates all per-word coordinate recalculation for zoom/pan
- [Phase 15-01]: Lazy SDK imports inside segment() methods — vlm.py loads without anthropic/openai installed; error surfaces only at call time if SDK absent
- [Phase 15-01]: _parse_regions uses re.search(r'\{[\s\S]*\}') for JSON extraction — handles VLM preamble/postamble text without requiring clean output
- [Phase 15-01]: Any Exception from provider.segment() returns 502 (not 500) — distinguishes upstream API errors from internal server errors
- [Phase 15-02]: currentStem and jpeg_width/jpeg_height added as module-level JS vars — segment functions need them without threading through call chains
- [Phase 15-02]: loadSegments() called after renderWords() inside ALTO success block — ensures jpeg_width/jpeg_height are set before showSegmentRegions() is called
- [Phase 15-02]: segmentPage() re-enables button in finally block — prevents button getting permanently stuck disabled on network error
- [Phase 15-02]: clearSegmentRegions() called at start of loadFile() — prevents stale regions from previous file persisting during fetch for new file
- [Phase 16-mets-mods-output]: Bounding box overlap uses intersection logic (HPOS < hpos_max AND HPOS+WIDTH > hpos_min), not containment — allows partial-overlap strings to be included in regions
- [Phase 16-mets-mods-output]: GET /mets returns 204 (not 404) when no ALTO files — semantically correct: resource exists but has no content yet
- [Phase 16-mets-mods-output]: mets.py ALTO21_NS = 'http://schema.ccs-gmbh.com/ALTO' matches pipeline.py constant — correct namespace for all project ALTO files after namespace rewrite in build_alto21()
- [Phase 17-01]: sys.modules patching in tests for lazy openai import inside route handlers and segment() — monkeypatch.setattr doesn't intercept imports that haven't happened yet
- [Phase 17-01]: settings.json provider resolution: _make_provider_from_settings returns None when backend not in _VALID_BACKENDS or model empty — avoids partial-config provider creation
- [Phase 17-01]: provider_name/model for result dict set in else branch when provider came from settings.json — prevents NameError on settings-based segmentation calls

### Pending Todos

None.

### Blockers/Concerns

- SVG overlay performance ceiling: if any production page exceeds ~2,000 words, Canvas fallback path should be planned from Phase 11 start — sample real ALTO files for word count before building overlay
- lxml namespace round-trip: spike-test etree.tostring(xml_declaration=True, encoding='UTF-8', pretty_print=True) against a real project ALTO file as first task of Phase 12
- Phase 15 VLM provider selection: need to evaluate Claude Vision, GPT-4o, and Gemini Vision API response format differences for structured region output before committing to the provider abstraction interface
- Phase 16-02: Second METS plan — confirm scope before executing

## Session Continuity

Last session: 2026-03-01
Stopped at: Completed 17-01-PLAN.md — settings backend, OpenAICompatibleProvider, 116 tests pass
Resume at: Execute Phase 17-02 — VLM Settings UI frontend panel in upload.html
