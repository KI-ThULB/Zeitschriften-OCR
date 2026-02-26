---
phase: 07-live-progress-display
plan: 01
subsystem: cli
tags: [progress, stderr, tty, eta, tqdm, collections.deque]

# Dependency graph
requires:
  - phase: 06-diagnostic-flags
    provides: run_batch() with verbose flag and submit() + as_completed() loop
provides:
  - ProgressTracker class with in-place stderr progress line and rolling ETA
  - duration_seconds populated with real wall-clock time in file_records
  - tqdm removed from pipeline.py and requirements.txt
affects: [future phases modifying run_batch()]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ProgressTracker class encapsulates all progress state and rendering
    - submit_times dict keyed by future tracks per-file wall-clock duration with parallel workers
    - \r overwrite pattern for in-place terminal progress line
    - TTY guard prevents garbled output in piped/redirected stderr

key-files:
  created: []
  modified:
    - pipeline.py
    - requirements.txt

key-decisions:
  - "tracker.update(duration) placed after try/except (not in finally) — both success and failure completions update the rolling average"
  - "show_progress guard: (not verbose) and sys.stderr.isatty() and len(to_process) > 0 — three independent conditions each with distinct rationale"
  - "submit_times dict built alongside futures dict with explicit for-loop (not dict comprehension) to support parallel submit_time tracking"
  - "ETA calculating... shown until 3 files complete; rolling 10-file window thereafter"

patterns-established:
  - "ProgressTracker.active=False silently no-ops all methods — callers do not need to guard"
  - "duration from submit_times is more accurate than process_tiff() internal timing for multi-worker batches (captures queue wait time)"

requirements-completed: [OPER-03]

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 7 Plan 1: Live Progress Display Summary

**In-place stderr progress bar with rolling ETA using ProgressTracker class, replacing tqdm dependency entirely**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T10:33:56Z
- **Completed:** 2026-02-26T10:35:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- ProgressTracker class delivers `[N/total pct%] ETA: Xm Ys` line that updates in-place on each file completion
- Rolling 10-file ETA average replaces tqdm's progress bar with zero external dependencies
- duration_seconds in file_records now populated with real wall-clock time (was None previously)
- tqdm removed from both pipeline.py and requirements.txt

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ProgressTracker class and integrate into run_batch()** - `c9f7341` (feat)
2. **Task 2: Remove tqdm from requirements.txt** - `7c4df5b` (chore)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `pipeline.py` - Added ProgressTracker class (60 lines), rewrote run_batch() executor block with submit_times dict and tracker calls, removed tqdm import, added deque import
- `requirements.txt` - Removed tqdm>=4.67.0 line; now contains exactly 5 packages

## Decisions Made
- tracker.update(duration) is called unconditionally after the try/except block (not inside finally), ensuring both success and failure completions update the rolling average — matching the original tqdm `finally: pbar.update(1)` semantics without the overhead of a context manager
- show_progress activation guard uses three independent boolean conditions: (1) verbose suppression prevents \r overwrite conflicting with verbose multi-line blocks, (2) isatty() prevents garbled \r characters in piped/redirected output, (3) len(to_process) > 0 prevents ZeroDivisionError in _render() on empty batch
- submit_times is a separate dict alongside futures (not embedded in futures value) to avoid changing the futures dict shape; explicit for-loop replaces dict comprehension to allow parallel dict population

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 7 complete: live progress display ships with zero new dependencies
- progress suppression in --verbose and piped modes is correct by construction
- duration_seconds in JSON reports now reflects actual processing time instead of None
- Ready for Phase 8 if planned

## Self-Check: PASSED

- `pipeline.py` exists and imports without error
- `requirements.txt` exists with exactly 5 packages (tqdm removed)
- `07-01-SUMMARY.md` exists
- Commit `c9f7341` (Task 1: ProgressTracker) confirmed in git log
- Commit `7c4df5b` (Task 2: tqdm removed) confirmed in git log

---
*Phase: 07-live-progress-display*
*Completed: 2026-02-26*
