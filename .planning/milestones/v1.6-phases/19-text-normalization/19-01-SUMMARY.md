---
phase: 19-text-normalization
plan: 01
subsystem: api
tags: [flask, alto-xml, lxml, text-normalization, column-sort, hyphen-rejoin]

# Dependency graph
requires:
  - phase: 10-viewer
    provides: serve_alto() endpoint returning flat words array
provides:
  - GET /alto/<stem> now returns 'blocks' array (TextBlock geometry + word_ids) and 'line_end' boolean per word
  - lxml proxy recycling fix: all_strings materialized once; elem_to_idx and last_in_line use positional indices
affects:
  - 19-02 (column sort and hyphen rejoin client algorithms consume blocks/line_end)
  - 19-03 (any further text normalization depending on line boundary info)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Materialise lxml iterators once: all_strings = list(root.iter(...)) avoids proxy recycling across multiple iter() calls"
    - "Content+HPOS+VPOS triple used as block-membership key when lxml proxy ids differ across iter() calls"
    - "Additive JSON fields: new fields blocks and line_end added without removing existing keys"

key-files:
  created: []
  modified:
    - app.py
    - tests/test_app.py

key-decisions:
  - "Used (CONTENT, HPOS, VPOS) tuple as fallback block-membership key instead of id() to handle lxml proxy recycling across separate iter() calls"
  - "Kept implementation additive: no existing response keys removed, no existing tests modified"

patterns-established:
  - "lxml pattern: always materialise root.iter() into a list before building id()-based lookups to avoid proxy recycling"

requirements-completed: [TEXT-01, TEXT-02]

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 19 Plan 01: Text Normalization Metadata Summary

**GET /alto/\<stem\> extended with TextBlock geometry blocks array and per-word line_end boolean, enabling column sort and hyphen rejoin algorithms in Plan 02**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T16:45:55Z
- **Completed:** 2026-03-02T16:49:05Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Extended serve_alto() to return a blocks array: each TextBlock's id/hpos/vpos/width/height and list of word_ids (e.g. ['w0', 'w1'])
- Added line_end boolean to every word in the words array (True only for the last String in its TextLine)
- Fixed lxml proxy recycling: materialised all String elements once into all_strings list; all subsequent id-based lookups use indices from that stable list
- Added 3 new TestAltoEndpoint tests; full suite grew from 133 to 136 tests with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend serve_alto() to return blocks array and line_end flags** - `805863e` (feat)
2. **Task 2: Add tests for blocks array and line_end flag in TestAltoEndpoint** - `59024f8` (test)

**Plan metadata:** (docs commit — see final_commit)

## Files Created/Modified
- `app.py` - serve_alto() extended with all_strings materialisation, last_in_line set, elem_to_idx map, blocks_out array, and line_end per word
- `tests/test_app.py` - Three new TestAltoEndpoint test methods: test_alto_blocks_array, test_alto_line_end_flag, test_alto_blocks_empty_when_no_textblocks

## Decisions Made
- Used `(CONTENT, HPOS, VPOS)` tuple as block-membership key for matching TextBlock String children against the global all_strings list. lxml creates new proxy objects on each `iter()` call, making `id()` unstable across calls. The tuple key is correct for real ALTO files (words at unique coordinates); duplicate triples would be pathological.
- Kept the additive pattern: blocks and line_end are new fields, no existing response keys removed or renamed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed lxml proxy recycling causing empty blocks word_ids**
- **Found during:** Task 2 (writing tests revealed block.word_ids == [] when expected ['w0', 'w1'])
- **Issue:** The plan specified using `id(elem)` across multiple `root.iter()` calls. lxml creates fresh Python proxy objects on each `iter()` call, so `id()` values differ between the words loop and the blocks loop, causing elem_to_idx lookups to find no matches.
- **Fix:** Materialised all String elements into `all_strings = list(root.iter(...))` once; built `elem_to_idx` from that stable list; used `(CONTENT, HPOS, VPOS)` tuple key for block-membership matching across separate iter() calls.
- **Files modified:** app.py
- **Verification:** All 10 TestAltoEndpoint tests pass; spot-check shows blocks[0].word_ids == ['w0', 'w1']
- **Committed in:** 805863e (Task 1 commit, fix applied during implementation)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential correctness fix. The plan's id()-based strategy works in simple Python but not with lxml's proxy model. No scope creep.

## Issues Encountered
- lxml proxy recycling: Python `id()` is the memory address of the proxy wrapper, not the underlying XML node. Separate `iter()` calls on the same tree may return proxies at different addresses. Solved by materialising the iterator once.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- blocks array and line_end flag available in GET /alto/<stem> response
- Plan 02 can implement column sort using TextBlock HPOS/WIDTH from blocks
- Plan 02 can implement hyphen rejoin using line_end flag to detect line boundaries
- No blockers

---
*Phase: 19-text-normalization*
*Completed: 2026-03-02*
