---
phase: 18-article-browser-search
plan: 01
subsystem: api
tags: [sqlite, fts5, search, flask, tdd]

# Dependency graph
requires:
  - phase: 15-vlm-article-segmentation
    provides: segment JSON files at output/segments/<stem>.json with regions
provides:
  - SQLite FTS5 search module (search.py) with init_db(), index_stem(), query()
  - GET /articles/<stem> endpoint returning region list from segment JSON
  - GET /search?q= endpoint returning ranked FTS5 matches
  - Auto-index hook in POST /segment/<stem> keeping search.db current
affects: [18-02, frontend-search-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQLite FTS5 virtual table for full-text search without external dependencies"
    - "Delete-then-insert for idempotent FTS5 upsert (REPLACE not reliable with FTS5)"
    - "stem UNINDEXED in FTS5 schema — key column stored but not tokenized"
    - "TDD RED-GREEN: failing tests committed first, then implementation"

key-files:
  created:
    - search.py
    - tests/test_search.py
  modified:
    - app.py

key-decisions:
  - "Used DELETE+INSERT (not INSERT OR REPLACE) for FTS5 idempotency — FTS5 REPLACE semantics differ from regular tables"
  - "stem UNINDEXED in FTS5 schema — stem is a key, not content to search"
  - "GET /articles/<stem> reads segment JSON directly, no DB read — simpler, always current"
  - "GET /search route (not /api/search) per plan — /search page reserved for 18-02 SSR/JS page, JSON returned by same route"
  - "Auto-index in segment_page() calls search.init_db() before index_stem() — ensures DB exists even on first segmentation"

patterns-established:
  - "search.py module isolation: DB path computed from output_dir parameter, no global state"
  - "FTS5 graceful degradation: query() returns [] on missing DB or OperationalError"

requirements-completed: [STRUCT-05, STRUCT-06]

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 18 Plan 01: Article Browser Search Backend Summary

**SQLite FTS5 search module (search.py) with init_db/index_stem/query, GET /articles/<stem> and GET /search?q= Flask endpoints, auto-index hook in POST /segment/<stem> — 17 new tests, 133 total passing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T07:34:48Z
- **Completed:** 2026-03-02T07:38:08Z
- **Tasks:** 3
- **Files modified:** 3 (search.py created, tests/test_search.py created, app.py modified)

## Accomplishments

- Created `search.py` with `init_db()` (FTS5 table creation), `index_stem()` (delete+insert upsert), `query()` (BM25-ranked FTS5 search)
- Added `GET /articles/<stem>` returning region list from segment JSON (400 traversal guard, 404 if not segmented)
- Added `GET /search?q=` returning ranked FTS5 matches as `{"results": [...]}` (empty for blank query or missing DB)
- Wired `search.init_db()` + `search.index_stem()` auto-call after `segment_page()` writes segment JSON — index stays current without manual rebuild
- TDD executed cleanly: 15 RED tests committed, then all 17 GREEN after implementation; 116 prior tests still pass (133 total)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write TDD tests (RED)** - `b4394cf` (test)
2. **Task 2: Implement search.py and app.py endpoints (GREEN)** - `d450018` (feat)
3. **Task 3: Full test suite GREEN** - no additional commit (verified 133 passed)

## Files Created/Modified

- `/Users/zu54tav/Zeitschriften-OCR/search.py` — SQLite FTS5 module: `init_db()`, `index_stem()`, `query()`
- `/Users/zu54tav/Zeitschriften-OCR/tests/test_search.py` — 17 TDD tests covering all three functions and all new endpoints
- `/Users/zu54tav/Zeitschriften-OCR/app.py` — added `import search`, two new routes, auto-index hook in `segment_page()`

## Decisions Made

- Used `DELETE FROM articles WHERE stem = ?` followed by `executemany INSERT` for idempotent upsert — FTS5 does not support `INSERT OR REPLACE` reliably due to shadow table mechanics
- `stem UNINDEXED` in the FTS5 schema — stem is a lookup key, tokenizing it would produce false positives on word-part queries
- `GET /articles/<stem>` reads the segment JSON file directly rather than querying the FTS5 DB — simpler, always consistent with the authoritative JSON, no DB state dependency
- `search.init_db()` is called before `search.index_stem()` in the auto-index hook so the DB is guaranteed to exist even on the very first segmentation call

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. SQLite FTS5 is built into Python's standard library sqlite3 module.

## Next Phase Readiness

- `GET /articles/<stem>` and `GET /search?q=` are live and tested — Plan 18-02 (frontend) can call them immediately
- Search DB is auto-populated whenever `POST /segment/<stem>` is called — no manual rebuild step needed
- No blockers for 18-02

## Self-Check

- `[ -f search.py ]` FOUND
- `[ -f tests/test_search.py ]` FOUND
- `git log` shows b4394cf and d450018 for 18-01

## Self-Check: PASSED

---
*Phase: 18-article-browser-search*
*Completed: 2026-03-02*
