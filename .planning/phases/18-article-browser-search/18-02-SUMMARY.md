---
phase: 18-article-browser-search
plan: 02
subsystem: ui
tags: [flask, html, javascript, fts5, sqlite, search, viewer]

# Dependency graph
requires:
  - phase: 18-01
    provides: GET /articles/<stem> endpoint returning regions with bounding_box, GET /search JSON API (now /api/search), search.py FTS5 module
provides:
  - Article browser panel in viewer right-panel below OCR words
  - Green dashed highlight rect on article region click
  - URL hash deep-link: /viewer/<stem>#<region_id> highlights region on load
  - Search bar on upload dashboard navigating to /search?q=...
  - Standalone search results page at /search fetching from /api/search
  - /api/search JSON API (renamed from /search to avoid route conflict)
affects: [19-polish, future-phases-using-viewer-or-search]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Poll-based async coordination: DOMContentLoaded polls currentArticles array after loadFile() returns to handle hash deep-link"
    - "Route split for content negotiation: /search serves HTML, /api/search serves JSON"
    - "Article highlight rect isolated from segment overlay — clearSegmentRegions() never touches #article-highlight-rect"

key-files:
  created:
    - templates/search.html
  modified:
    - templates/viewer.html
    - templates/upload.html
    - app.py
    - tests/test_search.py

key-decisions:
  - "Renamed GET /search JSON route to GET /api/search to avoid conflict with new HTML search page at GET /search — cleanest approach, avoids content negotiation complexity"
  - "Article highlight rect (#article-highlight-rect) is a sibling to #highlight-rect in the SVG overlay and styled via CSS (not inline style) for easy override"
  - "loadArticles() called after loadSegments() in loadFile() try block — both are fire-and-forget async; 404 is silently ignored (unsegmented files show no article section)"
  - "Hash deep-link polling: 50ms interval up to 5s (100 attempts) — avoids race between async loadArticles() completion and highlightRegionById() needing currentArticles"
  - "article-highlight-rect display fix: CSS rule sets display:none; rect.style.display='' removes inline override but CSS wins; must use rect.style.display='block' to show"
  - "initial_stem passed explicitly as None from viewer_index() — avoids Jinja2 is-defined ambiguity in production mode"
  - "search.html fetches /api/search (not /search) so the same-origin search page does not recurse"

patterns-established:
  - "Search API split: HTML page at /search, JSON API at /api/search — use this pattern for any future search-like UI/API pairs"
  - "Article list cleared on every file load via renderArticleList([]) at start of loadArticles()"

requirements-completed: [STRUCT-05, STRUCT-06]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 18 Plan 02: Article Browser and Search UI Summary

**Article browser panel in viewer (card list + green dashed region highlight), search bar on upload dashboard, and standalone search results page at /search backed by /api/search FTS5 JSON endpoint**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T07:54:11Z
- **Completed:** 2026-03-02T07:58:28Z
- **Tasks:** 2 (+ 1 human-verify checkpoint, not yet approved)
- **Files modified:** 5

## Accomplishments
- Viewer right-panel shows "Articles (N)" heading with card-per-region list (type label + title) for any segmented file; empty for unsegmented files
- Clicking an article card draws a green dashed highlight rect on the TIFF image; clicking again toggles off; clicking different card moves rect
- URL hash deep-link: visiting /viewer/<stem>#<region_id> loads the file and highlights the named region after async data arrives
- Upload dashboard has a search bar ("Search articles…") that navigates to /search?q=... on Enter or button click
- Standalone search results page at /search fetches /api/search?q= and renders ranked results as clickable links to /viewer/<stem>#<region_id>
- Renamed API route from /search to /api/search to eliminate route conflict; updated all 3 test calls accordingly

## Task Commits

Each task was committed atomically:

1. **Task 1: Add article list panel to viewer.html** - `0251de7` (feat)
2. **Task 2: Add search bar to upload.html and create search.html** - `0b26f51` (feat)

**Plan metadata:** (pending — docs commit after checkpoint approval)

## Files Created/Modified
- `templates/viewer.html` - Article browser CSS, #article-highlight-rect in SVG, loadArticles/renderArticleList/selectArticle/highlightRegion/clearArticleHighlight/highlightRegionById functions, loadFile wiring, hash deep-link polling
- `templates/upload.html` - Search bar HTML + doSearch() JS function
- `templates/search.html` - New standalone search results page fetching /api/search
- `app.py` - Renamed @app.get('/search') to @app.get('/api/search'); added @app.get('/search') serving search.html
- `tests/test_search.py` - Updated 3 test endpoint paths from /search to /api/search

## Decisions Made
- Renamed GET /search JSON API to GET /api/search: cleanest resolution of route conflict; no content negotiation complexity; update to 3 test calls was trivial
- Poll-based deep-link coordination: loadFile() is async and loadArticles() is an additional async call inside it; a simple 50ms poll on currentArticles.length safely handles the timing without requiring Promise chaining through existing code

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] search.html fetch URL corrected from /search to /api/search**
- **Found during:** Task 2 (creating search.html)
- **Issue:** The plan template for search.html used `fetch('/search?q=...')` which would call the HTML page route (infinite redirect loop). The plan's recommended approach (Step 2d) correctly specifies /api/search for the JSON API.
- **Fix:** Created search.html fetching `/api/search?q=` as specified in the plan's Step 2d recommended approach
- **Files modified:** templates/search.html
- **Verification:** Route verification confirms /api/search returns JSON; /search serves HTML
- **Committed in:** 0b26f51 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — corrected fetch URL in search.html template)
**Impact on plan:** Necessary for correctness. Without this fix the search page would loop on itself.

## Issues Encountered (during human verification)

1. **article-highlight-rect invisible despite correct coordinates** — `highlightRegion()` used `rect.style.display = ''` (empty string). For `#highlight-rect` (which has an inline `style="display:none"`) this works: removing the inline override reveals the element. But `#article-highlight-rect` has `display:none` in a CSS rule, not inline, so `''` just removes any inline override and the CSS rule wins → element stays hidden. Fix: `rect.style.display = 'block'`.

2. **`initialStem` JS variable undefined in template** — `viewer_index()` didn't pass `initial_stem` to `render_template`, causing the Jinja2 `is defined` check to be unreliable in production mode. Fix: pass `initial_stem=None` explicitly. Also simplified template to `{{ initial_stem|tojson }}` (no `is defined` check needed).

3. **Deep-link poll timeout too short** — extended from 40 to 100 attempts (2s → 5s) for slower systems; poll now only calls `highlightRegionById` when articles are actually loaded (not on timeout with empty list).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Article browser UI complete; ready for human verification
- Search pipeline end-to-end: upload → segment → index → search → viewer deep-link
- Segment button still wired to showSegmentRegions() which is independent of article browser
- After human approval: ready for phase 19 (polish/final touches) or project completion

---
*Phase: 18-article-browser-search*
*Completed: 2026-03-02*

## Self-Check: PASSED

- FOUND: templates/viewer.html
- FOUND: templates/upload.html
- FOUND: templates/search.html
- FOUND: app.py
- FOUND: tests/test_search.py
- FOUND: commit 0251de7 (Task 1)
- FOUND: commit 0b26f51 (Task 2)
- FOUND: commit 3bc574b (docs)
