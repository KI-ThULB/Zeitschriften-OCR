---
phase: 10-tiff-and-alto-data-endpoints
plan: 02
subsystem: api
tags: [flask, pillow, lxml, alto, tiff, jpeg, image-serving, caching]

# Dependency graph
requires:
  - phase: 10-tiff-and-alto-data-endpoints
    plan: 01
    provides: RED test suite (TestImageEndpoint 6 tests, TestAltoEndpoint 7 tests) and _write_tiff/_write_alto fixtures

provides:
  - GET /image/<stem>: scaled JPEG serving with jpegcache/ persistence
  - GET /alto/<stem>: flat word array JSON with page/JPEG dimensions from ALTO 2.1 XML
  - _compute_jpeg_dims() helper shared between serve_image and serve_alto
  - before_request path traversal guard (rejects .. in URL path with 400)

affects: [11-web-viewer-frontend, 12-alto-editing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "serve_image: cache-then-render pattern — cache hit serves directly, miss renders TIFF → JPEG and writes cache"
    - "_compute_jpeg_dims: MAX_PX=1600 longest-side scale logic shared between render and ALTO response"
    - "serve_alto: parse-on-demand (no disk cache) because Phase 12 edits XML directly"
    - "before_request hook for .. detection — Flask routing collapses /../ before route dispatch; hook fires on raw path"
    - "TIFF lookup: _jobs dict first (upload path), then uploads/ directory scan (case-insensitive)"

key-files:
  created: []
  modified:
    - app.py

key-decisions:
  - "before_request reject_path_traversal() added — Flask normalizes /../ URLs so route handler stem never contains '..'; before_request fires on raw path, enabling 400 response for traversal attempts"
  - "confidence=None (not 0) for ALTO String elements missing WC attribute — float(wc_raw) if wc_raw is not None else None"
  - "No disk cache for ALTO JSON — parse XML on every request to stay consistent with Phase 12 XML edits"
  - "jpeg_width/jpeg_height in /alto/ response computed from TIFF when jpegcache absent — ordering independence between /image/ and /alto/ calls"
  - "Image.Resampling.LANCZOS for resize (not deprecated Image.ANTIALIAS)"

patterns-established:
  - "before_request path security guard: check request.path for '..' before route dispatch"
  - "JPEG cache pattern: output_dir/jpegcache/<stem>.jpg; mkdir on first request; serve from cache if hit"

requirements-completed: [VIEW-02, VIEW-03]

# Metrics
duration: 5min
completed: 2026-02-27
---

# Phase 10 Plan 02: TIFF and ALTO Data Endpoints — Implementation Summary

**GET /image/<stem> serving scaled JPEGs from uploads/ with jpegcache persistence, and GET /alto/<stem> returning flat word array with page/JPEG dimensions from ALTO 2.1 XML**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-27T20:05:32Z
- **Completed:** 2026-02-27T20:10:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- serve_image(): renders TIFF to JPEG (MAX_PX=1600 longest-side scale, Pillow Resampling.LANCZOS), caches to jpegcache/<stem>.jpg, handles cache hit path, case-insensitive TIFF filename lookup
- serve_alto(): parses ALTO XML on every request, returns flat word array (id/content/hpos/vpos/width/height/confidence), reads jpeg dims from cache or computes from TIFF for ordering independence
- _compute_jpeg_dims() helper: shared scale logic between serve_image and serve_alto
- before_request path traversal guard: rejects URLs containing '..' with 400 JSON before Flask routing
- All 41 tests pass (28 Phase 1-9 + 13 Phase 10), zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement GET /image/<stem> endpoint and _compute_jpeg_dims() helper** - `926b0a5` (feat)
2. **Task 2: Implement GET /alto/<stem> endpoint** - `f2cee6d` (feat)

## Files Created/Modified
- `app.py` — Added PIL Image import, send_file import, _compute_jpeg_dims() helper, serve_image() route, serve_alto() route, before_request reject_path_traversal() guard, jpegcache/ mkdir in __main__ block

## Decisions Made
- Added `before_request reject_path_traversal()` as a deviation from the plan's route-level `..` check. Flask normalizes `/../` in URLs before route dispatch, so the `stem` variable in the handler never contains `..`. The before_request hook fires on the raw `request.path`, making the test_path_traversal_dot_dot assertion (`== 400`) pass correctly.
- `confidence=None` for missing WC attributes — `float(wc_raw) if wc_raw is not None else None` — matches the test contract that uses `w1.get('confidence') is None`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] before_request guard for path traversal instead of route-level stem check**
- **Found during:** Task 1 (serve_image implementation)
- **Issue:** The plan specified `if '/' in stem or '..' in stem: return 400` inside the route handler. Flask's Werkzeug routing normalizes `/../` URLs before matching (Werkzeug URL normalization removes `..` segments from the path), so `request.path` for `/image/../etc/passwd` never reaches the `<stem>` variable rule — it gets a 404 from the router. The test `test_path_traversal_dot_dot` strictly asserts `resp.status_code == 400`, so a 404 causes test failure.
- **Fix:** Added `@app.before_request reject_path_traversal()` that checks `'..' in request.path` and returns `jsonify({'error': 'invalid path'}), 400`. The route-level check was kept as defense-in-depth.
- **Files modified:** app.py
- **Verification:** `test_path_traversal_dot_dot` passes; all 41 tests pass
- **Committed in:** 926b0a5 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan's assumed Flask routing behavior)
**Impact on plan:** Required to pass the path traversal security test. No scope creep; the fix adds an additional security layer rather than weakening the design.

## Issues Encountered
- Flask/Werkzeug URL normalization strips `..` from paths before route dispatch, so route-level `..` detection in `stem` is unreachable for the `/image/../etc/passwd` pattern. Resolved with before_request guard.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GET /image/<stem> and GET /alto/<stem> provide the data layer for Phase 11 web viewer UI
- Scale factor for overlay: `scale = jpeg_width / page_width` (per CONTEXT.md)
- jpegcache/ directory is auto-created; no manual setup needed
- Blocker note: SVG overlay performance ceiling if pages exceed ~2,000 words — sample real ALTO files before Phase 11 overlay build

## Self-Check: PASSED

- FOUND: .planning/phases/10-tiff-and-alto-data-endpoints/10-02-SUMMARY.md
- FOUND: app.py
- FOUND commit: 926b0a5 (feat(10-02): add GET /image/<stem> endpoint and _compute_jpeg_dims() helper)
- FOUND commit: f2cee6d (feat(10-02): add GET /alto/<stem> endpoint)
- Test suite: 41 passing, 0 failing — PASS

---
*Phase: 10-tiff-and-alto-data-endpoints*
*Completed: 2026-02-27*
