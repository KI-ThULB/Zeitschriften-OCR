# Phase 7: Live Progress Display - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a single in-place progress line to the batch pipeline that updates each time a file completes, showing files-done/total/percentage and an estimated time remaining. The line clears cleanly before the final Done summary line prints. No changes to per-file result lines, ALTO output, validation, or error handling.

</domain>

<decisions>
## Implementation Decisions

### Progress line format
- Format: `[done/total percentage%] ETA: Xm Ys` — e.g., `[47/200 23%] ETA: 1m 30s`
- Before enough data: `[3/200 1%] ETA: calculating...` (switches after 3 files)
- ETA format: `Xm Ys` when over 1 minute (e.g., `1m 30s`), `Xs` when under (e.g., `42s`)
- No current filename shown — counts/percentage/ETA only
- Output stream: **stderr** (keeps progress separate from per-file result lines on stdout; pipes cleanly)

### ETA calculation
- Rolling average of last N completed files — adapts to speed changes mid-batch
- Show `ETA: calculating...` until 3 files have completed
- Update on every file completion (not rate-limited — OCR speeds 1–5s/file won't cause flicker)

### Suppression rules
- **`--verbose` active**: suppress progress line entirely — verbose multi-line blocks per file conflict with `\r` in-place overwriting
- **Non-TTY stderr** (`sys.stderr.isatty()` returns False): suppress progress — `\r` in log files looks like garbage; standard Unix practice
- **`--dry-run`**: no suppression needed — `sys.exit(0)` fires before `run_batch()` is reached
- **`--workers > 1`**: progress still updates per completion — `as_completed()` loop already fires per file; parallelism is transparent to display
- **0 files to process** (all skipped): no progress line — skip straight to Done

### Terminal cleanup
- Clear by overwriting with spaces (same width) then `\r`, then print Done summary on fresh line
- Single-file batches: show progress line normally (`[0/1 0%] ETA: calculating...` → `[1/1 100%]` → Done)
- Non-TTY failure mid-batch: no cleanup needed (progress was never printed)

### Claude's Discretion
- Rolling window size N for the rolling average
- Whether to use `\r` or ANSI escape codes for in-place update
- Exact padding/width strategy for the progress line to prevent leftover characters

</decisions>

<specifics>
## Specific Ideas

- Progress line updates should feel live — every file completion should visibly advance the counter
- The `ETA: calculating...` placeholder is preferable to a possibly-wrong early estimate
- Stderr for progress is deliberate — operators piping stdout to a file should still see progress in their terminal

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-live-progress-display*
*Context gathered: 2026-02-26*
