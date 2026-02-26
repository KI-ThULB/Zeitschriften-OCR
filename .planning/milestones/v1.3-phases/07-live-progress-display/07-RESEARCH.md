# Phase 7: Live Progress Display - Research

**Researched:** 2026-02-26
**Domain:** Python terminal progress display, carriage-return in-place line update, ETA calculation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Progress line format:** `[done/total percentage%] ETA: Xm Ys` — e.g., `[47/200 23%] ETA: 1m 30s`
- **Before enough data:** `[3/200 1%] ETA: calculating...` (switches to ETA after 3 files)
- **ETA format:** `Xm Ys` when over 1 minute (e.g., `1m 30s`), `Xs` when under (e.g., `42s`)
- **No current filename shown** — counts/percentage/ETA only
- **Output stream: stderr** — keeps progress separate from per-file result lines on stdout; pipes cleanly
- **ETA algorithm:** Rolling average of last N completed files — adapts to speed changes mid-batch
- **Show `ETA: calculating...`** until 3 files have completed
- **Update on every file completion** (not rate-limited — OCR speeds 1–5s/file won't cause flicker)
- **`--verbose` active:** suppress progress line entirely — verbose multi-line blocks per file conflict with `\r` in-place overwriting
- **Non-TTY stderr** (`sys.stderr.isatty()` returns False): suppress progress — `\r` in log files looks like garbage
- **`--dry-run`:** no suppression needed — `sys.exit(0)` fires before `run_batch()` is reached
- **`--workers > 1`:** progress still updates per completion — `as_completed()` loop already fires per file; parallelism is transparent to display
- **0 files to process (all skipped):** no progress line — skip straight to Done
- **Terminal cleanup:** Clear by overwriting with spaces (same width) then `\r`, then print Done summary on fresh line
- **Single-file batches:** show progress line normally
- **Non-TTY failure mid-batch:** no cleanup needed (progress was never printed)

### Claude's Discretion

- Rolling window size N for the rolling average
- Whether to use `\r` or ANSI escape codes for in-place update
- Exact padding/width strategy for the progress line to prevent leftover characters

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OPER-03 | During batch processing, a live progress line shows files completed, total count, percentage, and estimated time remaining (updated as each file completes) | Custom `\r`-based stderr progress in `run_batch()` as_completed loop; rolling-average ETA; TTY guard with `sys.stderr.isatty()`; tqdm removal |
</phase_requirements>

---

## Summary

Phase 7 adds a single in-place progress line to `run_batch()` in `pipeline.py`. The implementation is pure stdlib Python: write to `sys.stderr` using `\r` (carriage return) to overwrite the same terminal line on each file completion. A rolling average of per-file durations provides the ETA estimate.

The most important discovery for planning: **the current `pipeline.py` already imports and uses `tqdm`** (lines 18, 778–815). The tqdm progress bar in `run_batch()` must be replaced or removed as part of this phase. Tqdm writes to stderr by default and its bar would conflict with the custom `\r` line. The locked decisions do not mention tqdm at all — they describe a hand-rolled format. The planner must include removal of the `tqdm` import and the `with tqdm(...)` / `pbar.update(1)` block from `run_batch()`.

No new dependencies are required. `collections.deque` (stdlib) is the right data structure for the rolling window. The `time` module (already imported) provides timestamps. All suppression logic relies on `sys.stderr.isatty()` which is stdlib.

**Primary recommendation:** Replace the existing tqdm wrapper in `run_batch()` with a custom `ProgressTracker` helper class that writes `\r`-based lines to stderr. Remove tqdm from `requirements.txt` and imports if it is used nowhere else after the replacement. All logic stays in `pipeline.py` (single-file project convention).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sys` (stdlib) | Python 3.x | `sys.stderr`, `sys.stderr.isatty()`, `sys.stderr.write()`, `sys.stderr.flush()` | No dependency; direct terminal detection and write access |
| `time` (stdlib) | Python 3.x | `time.monotonic()` for per-file duration measurement | Already imported in pipeline.py |
| `collections.deque` (stdlib) | Python 3.x | Fixed-size rolling window for per-file durations | O(1) append/evict; `maxlen` parameter exactly fits rolling-window semantics |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tqdm` (currently in requirements.txt) | 4.67.0 | Current progress display — **to be removed from run_batch()** | Remove from this phase; check if used elsewhere before deleting import/requirement |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `\r` overwrite | ANSI escape `\033[2K\r` (erase line then CR) | More robust against variable-length lines; avoids needing space-padding; but adds ANSI dependency and less universally supported on all terminals. `\r` + space-padding is simpler and sufficient for this fixed-format line. |
| `collections.deque(maxlen=N)` | Plain list with slice | deque with maxlen is O(1) append/evict; list slice is O(N); deque is the standard for bounded rolling windows |
| Hand-rolled progress | Keep tqdm, configure it to match format | tqdm's format string is flexible but the locked decision format (`[47/200 23%] ETA: 1m 30s`) is non-standard for tqdm and would require a custom bar_format string that is harder to maintain; cleaner to remove tqdm entirely from this code path |

**Installation:** No new packages required. `tqdm` may be removed from `requirements.txt` if unused after this phase.

---

## Architecture Patterns

### Pattern 1: ProgressTracker Class in pipeline.py

**What:** A small helper class encapsulating all progress state and rendering logic. Lives at module level in `pipeline.py` before `run_batch()`. Not a separate file — project uses a single-file architecture (see CLAUDE.md).

**When to use:** Whenever progress state (count, durations deque, last-line-width) needs to be threaded through the `as_completed()` loop without polluting `run_batch()`'s argument list.

**Example:**
```python
import sys
import time
from collections import deque

class ProgressTracker:
    """In-place progress line on stderr for batch OCR.

    Suppressed when:
      - active is False (verbose mode or non-TTY stderr)
      - to_process count is 0 (all skipped — caller doesn't create tracker)

    Usage:
        tracker = ProgressTracker(total=len(to_process), active=active)
        tracker.update(duration_seconds)  # call after each file completes
        tracker.clear()                   # call before Done summary line
    """

    _WINDOW = 10  # rolling window size (discretion item)

    def __init__(self, total: int, active: bool) -> None:
        self.total = total
        self.active = active
        self.done = 0
        self._times: deque[float] = deque(maxlen=self._WINDOW)
        self._last_width = 0

    def update(self, duration: float) -> None:
        if not self.active:
            return
        self.done += 1
        self._times.append(duration)
        self._render()

    def _eta_str(self) -> str:
        if len(self._times) < 3:
            return "calculating..."
        remaining = self.total - self.done
        avg = sum(self._times) / len(self._times)
        secs = int(avg * remaining)
        if secs >= 60:
            return f"{secs // 60}m {secs % 60}s"
        return f"{secs}s"

    def _render(self) -> None:
        pct = int(self.done / self.total * 100)
        line = f"[{self.done}/{self.total} {pct}%] ETA: {self._eta_str()}"
        # Pad to previous width to erase leftover characters
        padded = line.ljust(self._last_width)
        self._last_width = len(line)
        sys.stderr.write(f"\r{padded}")
        sys.stderr.flush()

    def clear(self) -> None:
        if not self.active:
            return
        # Overwrite line with spaces then return to start
        sys.stderr.write(f"\r{' ' * self._last_width}\r")
        sys.stderr.flush()
```

**Key note on `duration` parameter:** `process_tiff()` currently prints timing internally but does not return it. `run_batch()` tracks wall-clock time per future in the `as_completed()` loop using `time.monotonic()` calls wrapping `executor.submit()` / `fut.result()`. The simplest approach is to record `time.monotonic()` just before each `fut.result()` call returns (or to time from submit to result). This gives an accurate per-file wall-clock that feeds the rolling window. Alternatively, the `file_records` dict currently records `duration_seconds: None` — this could be populated here as well, addressing a known TODO in the code.

### Pattern 2: Integration in run_batch() as_completed Loop

**What:** Create tracker before the loop, call `tracker.update(duration)` after each successful or failed future, call `tracker.clear()` after the loop ends.

**When to use:** Always — this is the only loop that sees all file completions.

**Example:**
```python
# Determine if progress should be active
show_progress = (not verbose) and sys.stderr.isatty() and len(to_process) > 0
tracker = ProgressTracker(total=len(to_process), active=show_progress)

t_batch_start = time.monotonic()
with ProcessPoolExecutor(max_workers=workers) as executor:
    futures = { executor.submit(...): tiff_path for tiff_path in to_process }
    for fut in as_completed(futures):
        tiff_path = futures[fut]
        t_file_start = time.monotonic()
        try:
            fut.result()
            t_file_elapsed = time.monotonic() - t_file_start
            processed += 1
            # ... existing file_records append ...
        except Exception as e:
            t_file_elapsed = time.monotonic() - t_file_start
            # ... existing error handling ...
        tracker.update(t_file_elapsed)

tracker.clear()
```

**Note:** The tqdm `with tqdm(total=len(futures), ...) as pbar:` block and `pbar.update(1)` call must be removed. The `as_completed(futures)` iterator is iterated directly.

### Pattern 3: Activation Guard

**What:** A single boolean computed before tracker creation: `active = (not verbose) and sys.stderr.isatty()`. This collapses all suppression rules into one condition, evaluated once.

**Why:** Avoids repeated TTY checks inside the hot path; makes suppression logic obvious and testable in isolation.

**Suppression rules map:**
| Condition | isatty() | verbose | active result |
|-----------|----------|---------|---------------|
| Normal terminal run | True | False | True |
| `--verbose` flag | True | True | False |
| Piped stderr (non-TTY) | False | any | False |
| `--dry-run` | N/A — never reaches run_batch() | N/A | N/A |
| 0 files to process | N/A — early return before tracker | N/A | N/A |

### Anti-Patterns to Avoid

- **Not removing tqdm:** Leaving the tqdm import and `with tqdm(...) as pbar` block alongside the new tracker. The two write to stderr simultaneously and produce garbled output.
- **Using `print(..., end='\r', file=sys.stderr)`:** Works but does not flush — use `sys.stderr.write()` + `sys.stderr.flush()` for reliability in all buffering modes.
- **Not padding to previous width:** If the line gets shorter (e.g., ETA `1m 30s` → `42s`), leftover characters from the previous render remain visible. Always `ljust(self._last_width)` before writing.
- **Timing future.result() only on success:** Errors also consume wall time and should update the rolling window so ETA stays accurate across mixed batches.
- **Creating the tracker when to_process is empty:** The `if not to_process: return ...` guard in run_batch() already exits early — but be explicit that the tracker is created only after confirming to_process is non-empty.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rolling window of last N items | Custom list + manual eviction | `collections.deque(maxlen=N)` | deque with maxlen auto-evicts oldest item on append — O(1), zero boilerplate |
| TTY detection | Custom platform checks | `sys.stderr.isatty()` | stdlib, reliable, the standard Unix pattern |
| Line-length padding | Custom string truncation | `str.ljust(width)` | stdlib; handles all cases |

**Key insight:** This phase requires no external libraries. The entire implementation is ~40 lines of stdlib Python inserted into the existing `run_batch()` function and a small helper class above it.

---

## Common Pitfalls

### Pitfall 1: tqdm Conflict
**What goes wrong:** The existing tqdm progress bar in `run_batch()` writes to stderr. If the new custom progress line also writes `\r` to stderr, they interleave and produce garbage output in the terminal.
**Why it happens:** tqdm maintains its own cursor position management internally.
**How to avoid:** Remove the `with tqdm(...) as pbar:` wrapper and the `pbar.update(1)` call. Remove `from tqdm import tqdm` from imports. Check whether tqdm is used anywhere else in the file before removing from `requirements.txt` — as of the current code, tqdm is imported at line 18 and used only in `run_batch()`.
**Warning signs:** `\r` characters visible in output, progress line appears on multiple lines.

### Pitfall 2: Leftover Characters After Line Shortens
**What goes wrong:** After the ETA transitions from `1m 30s` to `42s`, the rendered line is shorter. The previous characters are not erased, so stale text remains visible at the end of the line.
**Why it happens:** `\r` moves the cursor to the start of the line but does not erase the line. Writing a shorter string leaves the old characters in place.
**How to avoid:** Track `_last_width` (the character length of the most recently written line). Before writing the new line, pad it with `ljust(_last_width)`. Update `_last_width` to the new (unpadded) line length.
**Warning signs:** Visual artifacts at end of progress line, especially around the ETA minute-to-seconds transition.

### Pitfall 3: Flush Not Called
**What goes wrong:** The progress line updates do not appear in the terminal until the buffer is full or the process exits.
**Why it happens:** Python's stderr can be line-buffered or block-buffered. `\r` does not end a line, so line-buffered stderr will not flush on `\r` alone.
**How to avoid:** Always call `sys.stderr.flush()` immediately after every `sys.stderr.write()` call inside `_render()` and `clear()`.
**Warning signs:** Progress appears in bursts or only at the end.

### Pitfall 4: Duration Measurement Includes Queue Wait, Not OCR Time
**What goes wrong:** If `time.monotonic()` is called just before `fut.result()` returns (rather than wrapping the entire submit-to-result cycle), the measured duration only reflects the queue-to-result delay seen from the main process, not actual OCR duration when multiple workers run concurrently.
**Why it happens:** With `workers > 1`, `as_completed()` yields futures as they complete — the time from when `fut.result()` is called to when it returns is effectively zero (the future is already done). The wall clock between submit and result is the true per-file duration.
**How to avoid:** Record `time.monotonic()` at submit time by storing start times in a dict keyed by future:
```python
submit_times: dict = {}
for tiff_path in to_process:
    fut = executor.submit(process_tiff, ...)
    futures[fut] = tiff_path
    submit_times[fut] = time.monotonic()

for fut in as_completed(futures):
    duration = time.monotonic() - submit_times[fut]
    tracker.update(duration)
```
This gives the correct per-file elapsed time regardless of worker count.
**Warning signs:** ETA is wildly inaccurate with `--workers > 1` (e.g., always shows near-zero durations).

### Pitfall 5: Progress Line Visible in Final Output
**What goes wrong:** The progress line is not cleared before the "Done:" summary line prints, leaving a leftover `[200/200 100%] ETA: 0s` line above the Done output.
**Why it happens:** `tracker.clear()` is not called before the `Done:` print in `main()`. Clear must happen before the print.
**How to avoid:** Call `tracker.clear()` immediately after the `as_completed` loop exits (before `run_batch()` returns), not in `main()`. The `run_batch()` function owns the progress lifecycle: create, update, clear. `main()` does not need to know about the tracker.
**Warning signs:** Stale progress line appears in terminal output above the Done summary.

### Pitfall 6: Single-File Batches Show No Progress
**What goes wrong:** For a batch of 1 file, the progress line shows `[0/1 0%] ETA: calculating...` then immediately clears, giving no visible feedback.
**Why it happens:** Initial render at 0 done is never called — the first render happens after the first (and only) file completes, which immediately triggers `clear()`.
**How to avoid:** Print an initial `[0/total 0%] ETA: calculating...` line before the `as_completed` loop starts (when `active` is True). This matches the user decision that "single-file batches show progress line normally."
**Warning signs:** No progress line visible at all for 1-file batches.

---

## Code Examples

Verified patterns from stdlib documentation and standard Python practices:

### isatty() TTY Check
```python
# Source: Python stdlib docs - io module
# sys.stderr.isatty() returns True only when stderr is connected to a terminal
active = sys.stderr.isatty() and not verbose
```

### deque Rolling Window
```python
# Source: Python stdlib docs - collections.deque
from collections import deque
window: deque[float] = deque(maxlen=10)
window.append(3.2)   # auto-evicts oldest when full
avg = sum(window) / len(window)  # simple mean of up to 10 values
```

### \r In-Place Line Update
```python
# Source: Standard Unix terminal pattern — verified against Python docs
# write \r + content — moves cursor to start of current line, overwrites
sys.stderr.write(f"\r{line.ljust(last_width)}")
sys.stderr.flush()   # REQUIRED — stderr may be buffered
```

### Clear Line
```python
# Overwrite with spaces, then return to start of line
sys.stderr.write(f"\r{' ' * last_width}\r")
sys.stderr.flush()
```

### ETA Format
```python
def _format_eta(seconds: int) -> str:
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"
```

### Submit-Time Tracking for Correct Duration with Multiple Workers
```python
submit_times: dict = {}
futures: dict = {}
for tiff_path in to_process:
    fut = executor.submit(process_tiff, tiff_path, ...)
    futures[fut] = tiff_path
    submit_times[fut] = time.monotonic()

for fut in as_completed(futures):
    duration = time.monotonic() - submit_times[fut]
    tiff_path = futures[fut]
    try:
        fut.result()
        # ... success handling
    except Exception as e:
        # ... error handling
    tracker.update(duration)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tqdm-based progress in run_batch() | Custom \r progress line on stderr | Phase 7 | tqdm removed from run_batch(); no new dependencies |
| tqdm to stderr (default) | Custom stderr write with isatty() guard | Phase 7 | Progress suppressed cleanly when piped |

**Deprecated/outdated after this phase:**
- `from tqdm import tqdm` import (line 18 of pipeline.py): remove entirely if tqdm is confirmed unused elsewhere after this phase.
- `with tqdm(total=len(futures), unit='file', desc='OCR') as pbar:` block in run_batch(): replace with `ProgressTracker`.
- `pbar.update(1)` call in the finally block (line 815): remove with tqdm block.
- `tqdm>=4.67.0` in requirements.txt: remove if tqdm has no other callers.

---

## Open Questions

1. **Rolling window size N**
   - What we know: User left this to Claude's discretion. OCR speed is 1–5s/file. Typical batches are dozens to hundreds of files.
   - What's unclear: Whether N=10 gives enough smoothing without being too slow to adapt to speed changes.
   - Recommendation: N=10 is the right default. Provides good smoothing (averages ~10–50 seconds of data at typical speeds) while adapting if operator changes workload mid-batch. Encode as a class constant `_WINDOW = 10` so it is easy to tune.

2. **`\r` vs ANSI `\033[2K\r`**
   - What we know: User left this to Claude's discretion. `\r` is simpler; ANSI erase-line is more robust against variable-length lines.
   - What's unclear: Whether any operator terminals commonly used (macOS Terminal, iTerm2, Linux terminals) would not support ANSI.
   - Recommendation: Use `\r` with `ljust(last_width)` space padding. Simpler, zero risk of ANSI incompatibility, and the line format is fixed-width enough that space padding is reliable. ANSI codes are unnecessary complexity for this use case.

3. **Should `file_records` duration_seconds be populated here?**
   - What we know: Currently `duration_seconds: None` in file_records (a known TODO in the code comment at line 794). The submit-time tracking required for the ETA rolling window produces accurate per-file durations.
   - Recommendation: Yes — populate `duration_seconds` in file_records as a side benefit. The tracking dict is being created anyway; storing the float costs nothing and removes the None placeholder. This is a quality improvement, not scope creep.

---

## Sources

### Primary (HIGH confidence)

- Python stdlib docs — `collections.deque` with `maxlen`: bounded ring-buffer semantics confirmed
- Python stdlib docs — `sys.stderr.isatty()`: returns True only for interactive terminals; standard Unix TTY detection
- Python stdlib docs — `sys.stderr.write()` / `sys.stderr.flush()`: direct byte/string write with explicit flush
- pipeline.py (project codebase, read directly) — confirmed tqdm usage at lines 18, 778–815

### Secondary (MEDIUM confidence)

- [tqdm/tqdm GitHub](https://github.com/tqdm/tqdm) — confirms tqdm writes to stderr by default; confirms `disable=` parameter exists; confirms conflict risk with custom \r writes
- [Redowan Delowar — tqdm with concurrent.futures](https://rednafi.com/python/tqdm-progressbar-with-concurrent-futures/) — practical pattern showing tqdm wrapping as_completed; reinforces that removal is straightforward

### Tertiary (LOW confidence)

- General web search results on `\r`-based progress bars — consistent with stdlib docs; no surprises found

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are Python stdlib; no external libraries required
- Architecture: HIGH — derived directly from reading pipeline.py and matching to locked CONTEXT.md decisions
- Pitfalls: HIGH (tqdm conflict, leftover chars, flush) — confirmed by code inspection; MEDIUM (duration measurement) — confirmed by concurrent.futures semantics

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stable stdlib; tqdm API stable)
