# Phase 2: Batch Orchestration and CLI - Research

**Researched:** 2026-02-24
**Domain:** Python concurrent.futures, argparse CLI, batch error handling, pytesseract startup validation
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BATC-01 | Process all TIFFs in parallel using ProcessPoolExecutor; worker count defaults to `min(os.cpu_count(), 4)`, overridable via CLI | Verified: ProcessPoolExecutor with `submit()` + `as_completed()` provides per-file isolation. `os.cpu_count()` returns 11 on this machine, so `min(11, 4) = 4` is the default. |
| BATC-02 | Skip TIFF if corresponding ALTO XML already exists; bypassed with `--force` | Simple: check `output_dir / 'alto' / (tiff_path.stem + '.xml')` existence before submitting to executor. Collect skip count for progress reporting. |
| BATC-03 | Single TIFF error does not abort the batch | Verified: `submit()` + `as_completed()` + `try/except fut.result()` isolates failures. CRITICAL: requires removing `sys.exit(1)` from `process_tiff()` inner except block — that call propagates exit code 1 to parent and hangs the pool on macOS/spawn. |
| BATC-04 | Write run error log: failed file path, exception type, error message, stack trace | Verified: `traceback.format_exc()` inside `except` after `fut.result()` captures full worker-side `_RemoteTraceback` chain. Write as JSONL (one JSON object per line) to `output_dir/errors_{timestamp}.jsonl`. |
| CLI-01 | Accept `--input DIR` and `--output DIR`; create output directory if absent | Standard argparse + `Path.mkdir(parents=True, exist_ok=True)`. Validate `--input` exists and is a directory at startup. |
| CLI-02 | Accept `--workers N`; default `min(os.cpu_count(), 4)` with memory guidance | argparse `type=int`, default computed at runtime not at parse-time (avoids hardcoding). Document: ~150-250MB per worker (image array + Tesseract LSTM model). |
| CLI-03 | Accept `--force` flag | `argparse add_argument('--force', action='store_true')` |
| CLI-04 | Accept `--lang`, `--padding`, `--psm` | Port from existing single-file CLI; same defaults (deu, 50, 1). |
| CLI-05 | Validate Tesseract installed and language pack available at startup | `pytesseract.get_languages()` raises `TesseractNotFoundError` if Tesseract is absent. Check `lang in pytesseract.get_languages()` for language pack. Must run BEFORE pool creation. |
</phase_requirements>

---

## Summary

Phase 2 transforms `pipeline.py` from a single-TIFF tool into a batch processor. The architectural work is a refactor of the existing `process_tiff()` function (remove its `sys.exit(1)` call, make it return a result dict or raise cleanly) plus adding a `run_batch()` orchestration function that wraps it with `ProcessPoolExecutor`, skip logic, and error collection.

The primary technical risk is a **critical bug in existing code**: `process_tiff()` calls `sys.exit(1)` in its except block (line 274 of pipeline.py). When `process_tiff` runs as a worker inside `ProcessPoolExecutor`, `sys.exit(1)` on macOS/spawn propagates exit code 1 to the parent process and leaves the corresponding future in a permanently `done=True` but unresolvable state, causing pool shutdown issues. This must be fixed before parallelism works correctly. The fix is to `raise` instead of `sys.exit`.

The stack is already locked by STATE.md decisions: `ProcessPoolExecutor`, `argparse`, `tqdm`, `pytesseract.get_languages()` for startup validation. All of these are verified to work correctly for their intended purposes with the specific patterns documented below.

**Primary recommendation:** Refactor `process_tiff()` to raise exceptions instead of calling `sys.exit()`, wrap batch orchestration in `run_batch()` using `submit()` + `as_completed()` pattern, collect errors into a JSONL log, and call `validate_tesseract()` before the executor starts.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `concurrent.futures.ProcessPoolExecutor` | stdlib (Python 3.11) | Parallel TIFF processing | Locked decision (STATE.md). True process-based parallelism bypasses Python GIL; Tesseract is CPU-bound and spawns subprocesses itself. |
| `argparse` | stdlib | CLI argument parsing | Locked decision. Zero dependencies, already used in pipeline.py. |
| `tqdm` | 4.67.0 | Progress bar | Locked decision. `tqdm(as_completed(futures), total=len(futures))` gives live progress. |
| `pytesseract` | 0.3.13 | Startup validation | Already in requirements.txt. `get_languages()` used for CLI-05 validation. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `traceback` | stdlib | Capture worker-side stack traces | In `except` block after `fut.result()` — format_exc() captures the `_RemoteTraceback` chain |
| `json` | stdlib | Write error log as JSONL | One JSON object per line in error log file |
| `pathlib.Path` | stdlib | File discovery and path manipulation | Already used throughout pipeline.py |
| `os` | stdlib | `os.cpu_count()` for default workers | Runtime CPU count |
| `datetime` | stdlib | Timestamp error log filename | `datetime.now().strftime('%Y%m%d_%H%M%S')` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ProcessPoolExecutor` | `multiprocessing.Pool` | Pool.map() is simpler but harder to isolate per-file errors; ProcessPoolExecutor.submit()+as_completed() is the correct pattern for error isolation |
| `ProcessPoolExecutor` | `ThreadPoolExecutor` | Tesseract is CPU-bound and spawns its own subprocesses; threads wouldn't give true parallelism and would add GIL contention |
| JSONL error log | Plain text log | JSONL is machine-readable for Phase 3 reporting; text log is human-readable but harder to parse |

**Installation:**
```bash
# No new dependencies required — all stdlib or already in requirements.txt
# tqdm is not yet in requirements.txt, add it:
pip install tqdm>=4.67.0
```

---

## Architecture Patterns

### Recommended File Structure
```
pipeline.py                  # Modified in-place (single file per project convention)
  ├── load_tiff()            # Unchanged from Phase 1
  ├── detect_crop_box()      # Unchanged from Phase 1
  ├── run_ocr()              # Unchanged from Phase 1
  ├── build_alto21()         # Unchanged from Phase 1
  ├── count_words()          # Unchanged from Phase 1
  ├── process_tiff()         # MODIFIED: raises exception instead of sys.exit(1)
  ├── validate_tesseract()   # NEW: startup validation (CLI-05)
  ├── run_batch()            # NEW: batch orchestration (BATC-01..04)
  └── main()                 # MODIFIED: accepts --input DIR, batch args, calls run_batch()
output_dir/
  ├── alto/                  # ALTO XML outputs (unchanged path convention)
  │   ├── scan_001.xml
  │   └── scan_002.xml
  └── errors_20260224_143012.jsonl   # NEW: error log (BATC-04)
```

### Pattern 1: Exception Isolation with submit() + as_completed()

**What:** Each file is submitted as a separate Future. Exceptions in workers are caught per-future without affecting siblings.

**When to use:** Always for BATC-03 compliance. Do NOT use `executor.map()` — it raises on first exception.

**Example:**
```python
# Source: verified locally with Python 3.11 subprocess test
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import traceback

def run_batch(tiff_files, output_dir, workers, lang, psm, padding, force):
    errors = []
    skipped = 0
    processed = 0

    # Separate skip logic from submission
    to_process = []
    for tiff_path in tiff_files:
        out_path = output_dir / 'alto' / (tiff_path.stem + '.xml')
        if not force and out_path.exists():
            skipped += 1
        else:
            to_process.append(tiff_path)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_tiff, tiff_path, output_dir, lang, psm, padding, False): tiff_path
            for tiff_path in to_process
        }
        for fut in tqdm(as_completed(futures), total=len(futures), unit='file'):
            tiff_path = futures[fut]
            try:
                fut.result()
                processed += 1
            except Exception as e:
                tb = traceback.format_exc()
                errors.append({
                    'file': str(tiff_path),
                    'exc_type': type(e).__name__,
                    'exc_message': str(e),
                    'traceback': tb,
                })

    return processed, skipped, errors
```

### Pattern 2: process_tiff() Refactor (Critical Fix)

**What:** Remove `sys.exit(1)` from the except block of `process_tiff()`. Let exceptions propagate naturally to the pool's future.

**When to use:** Mandatory — current code has `sys.exit(1)` which breaks batch processing.

**Example:**
```python
# Source: verified locally — raising vs sys.exit behavior in ProcessPoolExecutor
def process_tiff(tiff_path, output_dir, lang, psm, padding, no_crop):
    """Process a single TIFF. Raises on failure (do NOT sys.exit in workers)."""
    t0 = time.monotonic()
    # ... existing logic ...
    try:
        # ... existing processing ...
        pass
    except Exception:
        raise   # Let it propagate to the Future — do NOT call sys.exit(1)
    # Remove: except Exception as e: print(...); sys.exit(1)
```

### Pattern 3: Startup Validation (CLI-05)

**What:** Call `pytesseract.get_languages()` before creating the pool. Raises `TesseractNotFoundError` if Tesseract is absent.

**Note:** `get_languages()` is decorated with `@run_once` — it caches its result in the main process. Workers in separate processes will re-run it, but that is acceptable (they need Tesseract anyway).

**Example:**
```python
# Source: verified locally with pytesseract 0.3.13 source inspection
import pytesseract

def validate_tesseract(lang: str) -> None:
    """Validate Tesseract is installed and requested language pack is available.
    Call this before creating ProcessPoolExecutor.
    """
    try:
        available = pytesseract.get_languages()
    except pytesseract.TesseractNotFoundError:
        print(
            "ERROR: Tesseract is not installed or not on PATH.\n"
            "  macOS: brew install tesseract\n"
            "  Linux: apt install tesseract-ocr",
            file=sys.stderr,
        )
        sys.exit(1)

    if lang not in available:
        print(
            f"ERROR: Tesseract language pack '{lang}' is not installed.\n"
            f"  Available packs: {', '.join(sorted(available))}\n"
            f"  macOS: brew install tesseract-lang\n"
            f"  Linux: apt install tesseract-ocr-{lang}",
            file=sys.stderr,
        )
        sys.exit(1)
```

### Pattern 4: JSONL Error Log (BATC-04)

**What:** Write one JSON object per line to an error log file in the output directory.

**When to use:** After the batch completes, if `errors` list is non-empty.

**Example:**
```python
# Source: stdlib json + verified format
import json
from datetime import datetime

def write_error_log(output_dir: Path, errors: list[dict]) -> Path | None:
    if not errors:
        return None
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = output_dir / f'errors_{timestamp}.jsonl'
    with log_path.open('w', encoding='utf-8') as f:
        for entry in errors:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return log_path
```

### Pattern 5: TIFF Discovery

**What:** Find all .tif/.tiff files in input directory, case-insensitive, sorted for deterministic ordering.

**Example:**
```python
# Source: verified locally — pathlib does not natively do case-insensitive globs
def discover_tiffs(input_dir: Path) -> list[Path]:
    return sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in ('.tif', '.tiff')
    )
```

### Pattern 6: main() CLI Wiring

**What:** Complete argparse setup for batch mode.

**Example:**
```python
# Source: argparse stdlib + project conventions
def main() -> None:
    parser = argparse.ArgumentParser(
        description='Batch OCR: TIFF folder → ALTO 2.1 XML'
    )
    parser.add_argument('--input', required=True, type=Path,
                        help='Input folder containing TIFF files')
    parser.add_argument('--output', required=True, type=Path,
                        help='Output folder for ALTO XML files')
    parser.add_argument('--workers', type=int, default=None,
                        help='Parallel workers (default: min(cpu_count, 4); ~150-250MB RAM per worker)')
    parser.add_argument('--force', action='store_true',
                        help='Reprocess TIFFs that already have ALTO XML output')
    parser.add_argument('--lang', default='deu',
                        help='Tesseract language code (default: deu)')
    parser.add_argument('--padding', type=int, default=50,
                        help='Crop border padding in pixels (default: 50)')
    parser.add_argument('--psm', type=int, default=1,
                        help='Tesseract page segmentation mode (default: 1)')
    args = parser.parse_args()

    # Resolve default workers at runtime
    n_workers = args.workers if args.workers is not None else min(os.cpu_count() or 1, 4)

    # Startup validation
    validate_tesseract(args.lang)

    # Input validation
    if not args.input.is_dir():
        print(f"ERROR: --input must be a directory: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Discover TIFFs
    tiff_files = discover_tiffs(args.input)
    if not tiff_files:
        print(f"No TIFF files found in {args.input}", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(tiff_files)} TIFF(s) in {args.input}")

    # Run batch
    processed, skipped, errors = run_batch(
        tiff_files, args.output, n_workers, args.lang, args.psm, args.padding, args.force
    )

    # Write error log
    log_path = write_error_log(args.output, errors)

    # Summary
    print(f"Done: {processed} processed, {skipped} skipped, {len(errors)} failed")
    if log_path:
        print(f"Error log: {log_path}")

    sys.exit(1 if errors else 0)
```

### Anti-Patterns to Avoid

- **`sys.exit()` in worker functions:** Calling `sys.exit()` inside `process_tiff()` when it runs as a ProcessPoolExecutor worker leaves the corresponding future in a `done=True` but permanently unresolvable state on macOS/spawn, propagates exit code 1 to the parent process, and prevents clean pool shutdown. Always `raise` instead.
- **`executor.map()` for error isolation:** `map()` raises immediately on the first exception encountered during iteration, aborting remaining results. Use `submit()` + `as_completed()` instead.
- **Evaluating `os.cpu_count()` at module import / argparse `default=`:** `default=min(os.cpu_count(), 4)` in `add_argument()` evaluates at import time. Use `default=None` and resolve in `main()` after `parse_args()`.
- **`if __name__ == '__main__'` guard missing:** On macOS, the default multiprocessing start method is `spawn`. Workers import `__main__` to pickle the worker function. Without the guard, `main()` runs recursively in every worker, causing infinite process spawning and immediate crash.
- **Submitting work before startup validation:** Create the pool AFTER `validate_tesseract()` — validation failure should be a clean `sys.exit(1)` with no dangling worker processes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress reporting | Manual counter + print() | `tqdm(as_completed(futures), total=len(futures))` | Handles terminal width, rate, ETA, thread-safe updates automatically |
| Language validation | subprocess Tesseract call | `pytesseract.get_languages()` | Already in requirements.txt; handles encoding, error cases, macOS/Linux differences |
| Exception propagation from workers | Custom pipe/queue | `future.result()` in try/except | ProcessPoolExecutor serializes exceptions across process boundary automatically |
| Worker-side traceback | Reconstruct manually | `traceback.format_exc()` in main process after `fut.result()` raises | Captures `_RemoteTraceback` chain with worker-side stack included |

**Key insight:** `concurrent.futures` is specifically designed for this use case — parallel work with per-task error isolation. The `submit()` + `as_completed()` pattern is the canonical approach for batches where individual failures must not abort the run.

---

## Common Pitfalls

### Pitfall 1: sys.exit() in Worker Kills Parent Process

**What goes wrong:** `process_tiff()` currently calls `sys.exit(1)` inside its except block (line 274). When this function runs as a ProcessPoolExecutor worker on macOS (spawn start method), `sys.exit(1)` exits the worker process. The worker's abrupt exit propagates exit code 1 to the main process on macOS, and the future for that file is left in `done=True` but permanently unresolvable state. Pool shutdown may hang.

**Why it happens:** On macOS, `multiprocessing` defaults to `spawn` (not `fork`). A worker calling `sys.exit()` is functionally identical to the process being killed. The `ProcessPoolExecutor` cannot distinguish this from a crash, so it never delivers a result or exception for that future.

**How to avoid:** Remove the `sys.exit(1)` call from `process_tiff()`. Let the exception propagate up — `concurrent.futures` will serialize it and deliver it to `future.result()` in the main process.

**Warning signs:** Batch appears to complete but some files are silently missing from output; no ERROR entry in the error log for those files; main process exits with code 1 even when no exceptions were caught.

### Pitfall 2: Missing `if __name__ == '__main__'` Guard

**What goes wrong:** On macOS/spawn, worker processes import the `__main__` module. If `main()` is called unconditionally at module level (or via the existing `if __name__ == '__main__': main()` block being triggered by the import), each worker spawns more workers recursively.

**Why it happens:** `spawn` start method pickles the worker function and re-imports the module in a fresh interpreter. The module's top-level code runs again. The existing `if __name__ == '__main__': main()` guard DOES protect against this — it must remain in place.

**How to avoid:** The existing `if __name__ == '__main__': main()` guard at the bottom of `pipeline.py` is correct and must not be removed or moved inside a function.

**Warning signs:** Process count explodes immediately on batch start; `RecursionError` or `OSError: [Errno 35]` from too many processes.

### Pitfall 3: tqdm + as_completed Output Corruption

**What goes wrong:** If `process_tiff()` prints directly to stdout using `print()`, the progress bar and the print statements will interleave and corrupt each other in the terminal.

**Why it happens:** `tqdm` writes to stderr by default and uses ANSI escape codes to manage the progress bar line. Direct `print()` calls from worker processes write to stdout but the interleaving still disrupts the display.

**How to avoid:** In batch mode, `process_tiff()` should NOT print its result line to stdout — the orchestrator (`run_batch()`) handles progress display via tqdm. Remove or guard the `print(f"{tiff_path.name} → ...")` line for batch runs. Either: (a) pass a `verbose` flag and only print when not in batch mode, or (b) use `tqdm.write()` for per-file result lines.

**Warning signs:** Scrambled terminal output; progress bar jumping around; tqdm percentage not advancing smoothly.

### Pitfall 4: Error Log Timestamp Collision

**What goes wrong:** Two quick reruns produce the same timestamp, and the second run overwrites the first error log.

**Why it happens:** `datetime.now().strftime('%Y%m%d_%H%M%S')` has 1-second resolution.

**How to avoid:** Either append instead of overwrite (`'a'` mode), or accept the 1-second granularity as sufficient (reruns within the same second are extremely unlikely in practice). For this project, write-and-overwrite is acceptable.

### Pitfall 5: Worker Count When os.cpu_count() Returns None

**What goes wrong:** `os.cpu_count()` can return `None` on some container/virtual environments.

**Why it happens:** The OS doesn't expose CPU count (e.g., certain Docker configurations).

**How to avoid:** Use `min(os.cpu_count() or 1, 4)` — the `or 1` provides a safe fallback.

---

## Code Examples

### Full run_batch() Implementation Pattern

```python
# Source: verified locally with Python 3.11 ProcessPoolExecutor subprocess tests
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import traceback, json
from datetime import datetime

def run_batch(
    tiff_files: list[Path],
    output_dir: Path,
    workers: int,
    lang: str,
    psm: int,
    padding: int,
    force: bool,
) -> tuple[int, int, list[dict]]:
    """Run OCR on all tiff_files in parallel.

    Returns:
        (processed_count, skipped_count, error_list)
        error_list entries have keys: file, exc_type, exc_message, traceback
    """
    errors = []
    skipped = 0
    processed = 0

    to_process = []
    for tiff_path in tiff_files:
        out_path = output_dir / 'alto' / (tiff_path.stem + '.xml')
        if not force and out_path.exists():
            skipped += 1
        else:
            to_process.append(tiff_path)

    if skipped:
        print(f"Skipping {skipped} already-processed file(s). Use --force to reprocess.")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_tiff, tiff_path, output_dir, lang, psm, padding, False): tiff_path
            for tiff_path in to_process
        }
        with tqdm(total=len(futures), unit='file', desc='OCR') as pbar:
            for fut in as_completed(futures):
                tiff_path = futures[fut]
                try:
                    fut.result()
                    processed += 1
                except Exception as e:
                    errors.append({
                        'file': str(tiff_path),
                        'exc_type': type(e).__name__,
                        'exc_message': str(e),
                        'traceback': traceback.format_exc(),
                    })
                finally:
                    pbar.update(1)

    return processed, skipped, errors
```

### Startup Validation Pattern (CLI-05)

```python
# Source: pytesseract 0.3.13 source inspection + local verification
def validate_tesseract(lang: str) -> None:
    try:
        available = pytesseract.get_languages()
    except pytesseract.TesseractNotFoundError:
        print(
            "ERROR: Tesseract OCR is not installed or not on PATH.\n"
            "  macOS:  brew install tesseract\n"
            "  Ubuntu: apt install tesseract-ocr",
            file=sys.stderr,
        )
        sys.exit(1)
    if lang not in available:
        print(
            f"ERROR: Tesseract language pack '{lang}' is not installed.\n"
            f"  Available: {', '.join(sorted(available))}\n"
            f"  macOS:  brew install tesseract-lang\n"
            f"  Ubuntu: apt install tesseract-ocr-{lang}",
            file=sys.stderr,
        )
        sys.exit(1)
```

---

## Known Bug to Fix (From Phase 1)

CLAUDE.md documents a bug in `build_alto21()` Step 5 where `xsi:schemaLocation` removal silently no-ops. The fix is:

```python
# Add after Step 1 (etree.fromstring), before Step 3 (etree.tostring):
root.attrib.pop('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', None)
```

This is NOT in scope for Phase 2 (it's a Phase 1 bug) but the Phase 2 plan should NOT break existing behavior by touching `build_alto21()`. The fix should be documented as a Phase 2 task only if it's explicitly included in the plan.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `multiprocessing.Pool.map()` | `ProcessPoolExecutor.submit()` + `as_completed()` | Python 3.2+ | Per-task exception isolation; cleaner future API |
| `tqdm(iterator)` for sequential loops | `tqdm(as_completed(futures), total=N)` | tqdm 4.x | Works with concurrent futures; total= required since as_completed length is unknown |
| Manual `os.walk()` for file discovery | `Path.iterdir()` with suffix filter | Python 3.4+ | Cleaner API; suffix.lower() handles mixed-case extensions |

**Deprecated/outdated:**
- `executor.map()` for batch jobs with error isolation: raises on first failure, cannot collect all errors without complex wrapper code — use `submit()` + `as_completed()` instead.

---

## Open Questions

1. **Should process_tiff() print its result line in batch mode?**
   - What we know: In single-file mode, `print(f"{name} → {out_path} ({elapsed}s, {n} words)")` is part of the spec (CLAUDE.md). In batch mode, tqdm provides progress.
   - What's unclear: Whether the requirement is for per-file lines to still appear (verbose) or be suppressed (progress bar only).
   - Recommendation: Suppress `print()` in batch mode; add a comment explaining why. The batch orchestrator can optionally use `tqdm.write()` for per-file summaries. Requirements don't mandate verbose per-file output for batch.

2. **Error log location: output_dir root vs subdirectory?**
   - What we know: BATC-04 says "writes a run error log" without specifying location. Output ALTO XML goes to `output_dir/alto/`. No location specified.
   - What's unclear: Whether the error log should be in `output_dir/` root or a subdirectory.
   - Recommendation: Write to `output_dir/errors_{timestamp}.jsonl` (root level) — easy to find, not mixed in with ALTO XML.

3. **What if --input contains zero TIFFs?**
   - What we know: `discover_tiffs()` returns empty list.
   - What's unclear: Should this be a warning (exit 0) or error (exit 1)?
   - Recommendation: `print()` a warning and `sys.exit(0)` — not an error condition.

---

## Sources

### Primary (HIGH confidence)
- Python 3.11 stdlib docs (local `help()`) — `ProcessPoolExecutor`, `as_completed`, `Future.result()`, `traceback.format_exc()`
- pytesseract 0.3.13 (local source inspection) — `get_languages()`, `TesseractNotFoundError`, `@run_once` decorator behavior
- Local subprocess execution tests — verified: `raise` vs `sys.exit()` in workers, `as_completed` exception isolation, tqdm 4.67.0 signature

### Secondary (MEDIUM confidence)
- Python 3.11 stdlib `argparse` module — standard behavior confirmed via local testing
- Local test confirming macOS spawn start method and its implications for `if __name__ == '__main__'` guard

### Tertiary (LOW confidence)
- Memory estimate per worker (~150-250MB) is based on typical TIFF dimensions and Tesseract LSTM model size from training data — not measured on actual Zeitschriften files

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified locally at specific versions
- Architecture: HIGH — exception isolation and startup validation patterns verified with subprocess tests
- Pitfalls: HIGH — sys.exit() worker behavior confirmed experimentally; other pitfalls verified logically from source inspection

**Research date:** 2026-02-24
**Valid until:** 2026-09-24 (stable stdlib APIs; 6-month estimate)
