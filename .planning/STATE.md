# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.
**Current focus:** v1.5 Web Viewer Complete — defining requirements and roadmap

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements for v1.5
Last activity: 2026-02-28 — Milestone v1.5 started (Word Correction + Upload UI)

Progress: [█████░░░░░] 33% (v1.4 Phase 11 complete — 2/2 plans done)

## Performance Metrics

**Velocity:**
- Total plans completed: 13
- Average duration: 2.4 min
- Total execution time: 31 min

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

**Recent Trend:**
- Last 5 plans: 06-01 (2 min), 06-02 (4 min), 07-01 (2 min), 08-01 (5 min), 08-02 (6 min)
- Trend: stable

| 9. Flask Foundation and Job State | 2/2 | 3 min | 1.5 min |
| 10. TIFF and ALTO Data Endpoints | 2/2 | 7 min | 3.5 min |
| 11. Side-by-Side Viewer UI | 2/2 | ~62 min | ~31 min |

*Updated after each plan completion*
| Phase 10 P02 | 5 | 2 tasks | 1 files |
| Phase 11 P01 | 2 | 1 task | 3 files |
| Phase 11 P02 | ~60 | 2 tasks | 2 files |

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

### Pending Todos

None.

### Blockers/Concerns

- SVG overlay performance ceiling: if any production page exceeds ~2,000 words, Canvas fallback path should be planned from Phase 11 start — sample real ALTO files for word count before building overlay
- lxml namespace round-trip: spike-test etree.tostring(xml_declaration=True, encoding='UTF-8', pretty_print=True) against a real project ALTO file as first task of Phase 12

## Session Continuity

Last session: 2026-02-28
Stopped at: Completed 11-02-PLAN.md — complete side-by-side viewer UI, SVG overlay, ResizeObserver, INPUT_DIR fix (47 passing, 0 failing)
Resume file: None
