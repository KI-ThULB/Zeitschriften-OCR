# Phase 6: Diagnostic Flags - Research

**Researched:** 2026-02-25
**Domain:** Python CLI flag extension — argparse, subprocess capture, time.monotonic, stdout discipline
**Confidence:** HIGH

## Summary

Phase 6 adds two diagnostic CLI flags to the existing single-file `pipeline.py`. The work is purely additive: no changes to OCR logic, output format, or existing function signatures are required. Both flags (`--dry-run` and `--verbose`) are wired through argparse and their behavior is gated by booleans passed into the relevant functions.

The key technical challenges are: (1) capturing Tesseract stdout/stderr inside `process_tiff()`, which currently uses `pytesseract.image_to_alto_xml()` without capturing subprocess output; (2) threading per-stage timing measurements through the existing pipeline stages inside `process_tiff()`; and (3) keeping the parallel worker architecture intact — `process_tiff()` runs inside `ProcessPoolExecutor` workers, so all verbose output must happen inside the worker function and be printed directly (worker stdout is forwarded to the main process by the OS on macOS/Linux).

Dry-run is the simpler of the two: it replicates the skip-check logic from `run_batch()` in a read-only scan before the batch executes, then prints the two-section checklist and exits. No new subprocess interaction is needed. The verbose path requires intercepting Tesseract's raw subprocess output, which `pytesseract` does not expose through its high-level `image_to_alto_xml()` call. The correct approach is to drop down to `pytesseract.run_tesseract()` (the lower-level API) so stdout/stderr streams are available.

**Primary recommendation:** Use `pytesseract.run_tesseract()` for verbose Tesseract output capture; use `time.monotonic()` bracketing for per-stage wall-clock timing; implement dry-run as a standalone pre-flight scan in `main()` before `run_batch()` is called.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase Boundary:**
- `--dry-run`: preview which TIFFs would be processed and which would be skipped, then exit without running OCR
- `--verbose`: print Tesseract stdout/stderr and per-stage wall-clock timing (deskew, crop, OCR, write) for each processed file
- Both flags must combine cleanly with all existing flags. No changes to OCR pipeline logic, output format, or validation behavior.

**Dry-run output format:**
- Display two labeled sections in order:
  1. `Would process (N):` — list of TIFFs that would run OCR
  2. `Would skip (N):` — list of TIFFs that already have output
- Each file shown as filename only (not full path)
- Would-skip entries include a brief reason: e.g., `scan_001.tif (output exists)`
- A summary count line at the end: e.g., `Total: 47 would be processed, 12 already done`
- Output goes to stdout; exit code 0; no files written to output directory
- `--force` affects dry-run skip logic — with `--force`, all TIFFs appear in the would-process list
- `--verbose` is silently ignored when combined with `--dry-run`

**Verbose timing format:**
- Four separate indented lines printed after the filename line for each file:
  ```
  scan_001.tif
    deskew: 0.12s
    crop: 0.05s
    ocr: 2.31s
    write: 0.01s
  ```
- Time unit: seconds with 2 decimal places (e.g., `2.31s`)
- All 4 stages always shown even when a stage was a near-zero passthrough
- Blank line between each file's verbose block for readability
- All verbose output to stdout

**Tesseract output presentation:**
- Tesseract stdout/stderr always printed in `--verbose` mode, even if empty
- Format: labeled header line followed by indented content:
  ```
    tesseract stdout/stderr:
      [tesseract output here, or blank if empty]
  ```
- Tesseract block appears after timing lines for each file
- Blank line between files

**--dry-run + --verbose combination and existing output:**
- `--verbose` silently ignored when `--dry-run` is active
- Existing per-file result lines (e.g., `Processed: scan_001.tif`) stay unchanged
- `--verbose` adds timing block + tesseract block after each file's result line

### Claude's Discretion

- Exact indentation depth (2 or 4 spaces) for timing and tesseract sub-lines
- How to handle Tesseract output that has only whitespace (treat as empty or print as-is)
- Whether to flush stdout after each file's verbose block in parallel mode

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OPER-01 | `--dry-run` flag lists every TIFF that would be processed and every TIFF that would be skipped (already has ALTO output), then exits without running OCR | Dry-run pre-flight scan in `main()` using existing `discover_tiffs()` + skip-check logic from `run_batch()`; argparse `store_true` flag; `sys.exit(0)` after printing |
| OPER-02 | `--verbose` flag prints Tesseract stdout/stderr and per-stage wall-clock timing (deskew, crop, OCR, write) for each processed file | `pytesseract.run_tesseract()` for subprocess output capture; `time.monotonic()` bracketing at four stage boundaries inside `process_tiff()`; `verbose` bool parameter threaded through call chain |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` (stdlib) | Python 3.x | New `--dry-run` and `--verbose` flags | Already used in `main()`; `add_argument` with `action='store_true'` is the established pattern |
| `time.monotonic()` (stdlib) | Python 3.x | Per-stage wall-clock timing | Already imported and used in `process_tiff()` (`t0 = time.monotonic()`); monotonic avoids NTP jumps |
| `pytesseract` | >=0.3.13 (pinned in requirements.txt) | Tesseract subprocess wrapper | Already a project dependency; has lower-level `run_tesseract()` API that returns stdout/stderr |
| `subprocess` (stdlib) | Python 3.x | Implicit — used inside pytesseract | No direct use needed; pytesseract wraps this |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sys.stdout.flush()` (stdlib) | Python 3.x | Flush output after each verbose block | Needed in verbose parallel mode to prevent interleaved output; Claude's discretion per CONTEXT.md |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pytesseract.run_tesseract()` | `subprocess.run()` wrapping `tesseract` directly | `run_tesseract()` is already the internal mechanism; using it directly keeps things DRY and avoids reimplementing arg quoting |
| `time.monotonic()` | `time.perf_counter()` | Both give wall-clock resolution; `monotonic()` is already the project standard; no reason to change |

**Installation:** No new packages required. All dependencies already in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

No new files. All changes are within `pipeline.py`. The single-file architecture is the established project pattern.

```
pipeline.py   (all changes: process_tiff, run_batch, main)
```

### Pattern 1: Argparse Boolean Flags

**What:** Add `--dry-run` and `--verbose` as `store_true` action flags in `main()`'s argparse block. Pass `args.dry_run` and `args.verbose` as booleans through the call chain.

**When to use:** `store_true` is the standard Python pattern for on/off diagnostic flags. Already used in the codebase for `--force`, `--validate-only`, `--adaptive-threshold`.

**Example:**
```python
# Source: existing argparse block in main() — established project pattern
parser.add_argument('--dry-run', action='store_true',
                    help='List TIFFs that would be processed and skipped, then exit')
parser.add_argument('--verbose', action='store_true',
                    help='Print per-stage timing and Tesseract output for each file')
```

Note: `--dry-run` becomes `args.dry_run` (argparse converts hyphens to underscores).

### Pattern 2: Dry-Run Pre-flight Scan in main()

**What:** After `discover_tiffs()`, before `run_batch()`, check `args.dry_run`. If true, iterate the TIFF list, apply the same skip-check logic as `run_batch()`, print the two-section checklist, and call `sys.exit(0)`.

**When to use:** Implementing dry-run in `main()` keeps `run_batch()` clean and avoids threading a do-nothing flag into the worker pool.

**Example:**
```python
# In main(), after discover_tiffs():
if args.dry_run:
    would_process = []
    would_skip = []
    for tiff_path in tiff_files:
        out_path = args.output / 'alto' / (tiff_path.stem + '.xml')
        if not args.force and out_path.exists():
            would_skip.append(tiff_path.name)
        else:
            would_process.append(tiff_path.name)

    print(f"Would process ({len(would_process)}):")
    for name in would_process:
        print(f"  {name}")
    print(f"Would skip ({len(would_skip)}):")
    for name in would_skip:
        print(f"  {name} (output exists)")
    print(f"Total: {len(would_process)} would be processed, {len(would_skip)} already done")
    sys.exit(0)
```

### Pattern 3: Per-Stage Timing with time.monotonic()

**What:** Bracket each of the four stages (deskew, crop, OCR, write) inside `process_tiff()` with `t_start = time.monotonic()` / `t_end = time.monotonic()`. Accumulate durations. If `verbose=True`, print the four timing lines after the existing result line.

**When to use:** `time.monotonic()` is already imported and used in `process_tiff()` for total elapsed time. Extending it to four-stage granularity is a natural evolution.

**The four stage boundaries in process_tiff() (current code flow):**
1. **deskew**: `deskew_image(img)` call (line ~349)
2. **crop**: `detect_crop_box(img, ...)` + `img.crop(crop_box)` (lines ~367-375)
3. **ocr**: `run_ocr(cropped, ...)` + `build_alto21(alto_bytes, ...)` (lines ~376-379)
4. **write**: `out_path.write_bytes(alto_out)` (line ~383)

**Example:**
```python
# Inside process_tiff(), verbose=False default preserves existing behavior
t_deskew_start = time.monotonic()
img, deskew_angle, deskew_fallback = deskew_image(img)
t_deskew = time.monotonic() - t_deskew_start

t_crop_start = time.monotonic()
# ... adaptive threshold, detect_crop_box, img.crop ...
t_crop = time.monotonic() - t_crop_start

t_ocr_start = time.monotonic()
alto_bytes = run_ocr(cropped, lang=lang, psm=psm, dpi=int(dpi[0]))
alto_out = build_alto21(alto_bytes, crop_box)
t_ocr = time.monotonic() - t_ocr_start

t_write_start = time.monotonic()
out_path.write_bytes(alto_out)
t_write = time.monotonic() - t_write_start

# ... existing result line print ...

if verbose:
    print(f"  deskew: {t_deskew:.2f}s")
    print(f"  crop: {t_crop:.2f}s")
    print(f"  ocr: {t_ocr:.2f}s")
    print(f"  write: {t_write:.2f}s")
    print(f"  tesseract stdout/stderr:")
    print(f"    {tess_output or ''}")
    print()
```

### Pattern 4: Tesseract Output Capture with pytesseract.run_tesseract()

**What:** `pytesseract.image_to_alto_xml()` is a convenience wrapper that does not expose subprocess stdout/stderr. In verbose mode, switch to calling `pytesseract.run_tesseract()` directly to capture the subprocess output.

**When to use:** Only when `verbose=True`. In normal mode, `run_ocr()` continues using `image_to_alto_xml()` unchanged.

**pytesseract.run_tesseract() signature (from pytesseract source):**
```python
run_tesseract(
    input_filename,     # temp file path
    output_filename_base,
    lang=None,
    config='',
    nice=0,
    output_type=Output.STRING,  # controls return format
    timeout=0,
)
```
Returns a `(stdout, stderr)` tuple (or similar). The exact return shape requires verification against the installed version; however the function is a stable internal API that the high-level functions all delegate to.

**Alternative approach — simpler and safer:** Use `subprocess.run()` directly on `tesseract` with `stdout=subprocess.PIPE, stderr=subprocess.PIPE` inside a modified `run_ocr()`. This avoids dependency on pytesseract internals and is fully transparent.

```python
# Verbose-capable run_ocr():
import subprocess, tempfile

def run_ocr(image, lang='deu', psm=1, dpi=300, verbose=False):
    config = f'--psm {psm} --dpi {dpi}'
    result = pytesseract.image_to_alto_xml(image, lang=lang, config=config)
    tess_output = ''
    if verbose:
        # Re-invoke tesseract with captured output (or intercept at subprocess level)
        # Simplest: use pytesseract.get_tesseract_version()/run_tesseract()
        # or wrap with output_type parameter
        pass
    return (result if isinstance(result, bytes) else result.encode('utf-8')), tess_output
```

The cleanest approach is to use `pytesseract.image_to_alto_xml()` normally but also call `pytesseract.run_tesseract_cmd` to check stdout. However, the least risky implementation is to make `run_ocr()` accept a `capture_output` boolean and use `subprocess.run()` directly when that flag is set, since the tesseract command line is already well-understood in the codebase.

### Pattern 5: Threading verbose Through the Call Chain

**What:** `verbose` must travel from `args.verbose` in `main()` → `run_batch()` → `process_tiff()`. Since `process_tiff()` is submitted to `ProcessPoolExecutor.submit()`, it must appear in the function signature.

**Current `process_tiff()` signature:**
```python
def process_tiff(
    tiff_path: Path,
    output_dir: Path,
    lang: str,
    psm: int,
    padding: int,
    no_crop: bool,
    adaptive_threshold: bool,
) -> None:
```

**Required change:** Add `verbose: bool = False` as final parameter. Update the `executor.submit()` call in `run_batch()` to pass it. Update `run_batch()` signature to accept and forward `verbose`.

**The `no_crop` parameter** is currently hardcoded to `False` in the `executor.submit()` call (line 698). This is an existing pattern to note — `verbose` should be passed explicitly, not hardcoded.

### Anti-Patterns to Avoid

- **Putting dry-run logic inside run_batch()**: Makes `run_batch()` carry a do-nothing mode. Keep dry-run as a pure pre-flight in `main()`.
- **Using time.time() instead of time.monotonic()**: `time.time()` can jump backward on NTP adjustment. Project already uses `time.monotonic()`; don't mix.
- **Capturing Tesseract output by parsing stderr from pytesseract exceptions**: Tesseract does not raise on warnings; this would miss normal output.
- **Modifying the existing per-file result line format**: CONTEXT.md states existing lines stay unchanged. Verbose output is additive.
- **Printing verbose output from main() instead of the worker**: Output ordering is nondeterministic in parallel mode regardless, but the worker's stdout goes to the terminal; adding a second print site in `main()` would duplicate timing for a different purpose.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess output capture | Custom pipe plumbing | `subprocess.run(..., capture_output=True)` or `pytesseract.run_tesseract()` | OS-level buffering edge cases; pytesseract already handles temp-file lifecycle |
| Wall-clock timing | Custom clock class | `time.monotonic()` brackets | Already in stdlib, already in use in the file; no new dependency needed |
| Argparse flag wiring | Manual `sys.argv` parsing | `argparse.add_argument('--dry-run', action='store_true')` | Argparse handles `--help`, type coercion, and hyphen-to-underscore conversion |

**Key insight:** Every primitive needed for this phase is already available in the project (stdlib `time`, `argparse`, `subprocess`) or in the installed dependency (`pytesseract`). No new packages are needed.

---

## Common Pitfalls

### Pitfall 1: ProcessPoolExecutor and Verbose Output Interleaving

**What goes wrong:** In parallel mode (`--workers > 1`), multiple workers print verbose blocks simultaneously. Lines from different files can be interleaved on stdout, making the output unreadable.

**Why it happens:** Each worker process writes to its own stdout, which the OS forwards to the terminal without synchronization. With 4 workers processing files concurrently, all four could print timing lines at the same moment.

**How to avoid:** The user did not request serialized verbose output. The CONTEXT.md leaves stdout flushing as Claude's discretion. The pragmatic approach is to: (a) construct the entire verbose block as a single string and call one `print()` per file (minimizes interleaving since `print()` is atomic within a single call), and (b) note in implementation that `--verbose --workers 1` gives fully clean sequential output for debugging.

**Warning signs:** Timing lines from different files appearing mid-block in test output.

### Pitfall 2: hyphen vs underscore in argparse

**What goes wrong:** `parser.add_argument('--dry-run', ...)` creates `args.dry_run` (underscore), not `args.dry-run`. Accessing `args.dry-run` raises `AttributeError`.

**Why it happens:** argparse converts hyphens to underscores in the `dest`. Already handled correctly elsewhere in the codebase (`--validate-only` → `args.validate_only`).

**How to avoid:** Always use `args.dry_run` (not `args.dry-run`) when reading the flag value.

**Warning signs:** `AttributeError: Namespace object has no attribute 'dry-run'`.

### Pitfall 3: pytesseract.image_to_alto_xml() Does Not Expose Subprocess Output

**What goes wrong:** Attempting to intercept Tesseract stdout/stderr by monkey-patching or reading `pytesseract`'s internal state after calling `image_to_alto_xml()`. The output is not stored anywhere accessible.

**Why it happens:** `image_to_alto_xml()` is a convenience function that discards subprocess streams after the call completes.

**How to avoid:** For verbose mode, either (a) save the image to a temp file and call `tesseract` via `subprocess.run()` directly, or (b) use the lower-level `pytesseract.run_tesseract()` before calling `image_to_alto_xml()`. Option (a) is simpler and more reliable; option (b) risks invoking Tesseract twice (once for output, once for ALTO XML).

The cleanest design: refactor `run_ocr()` to accept `capture_output: bool = False`. When `True`, use `subprocess.run()` with `capture_output=True` and return `(alto_bytes, stdout_text)`. When `False`, use `pytesseract.image_to_alto_xml()` as today and return `(alto_bytes, '')`.

**Warning signs:** Tesseract block always empty even when Tesseract prints warnings.

### Pitfall 4: no_crop is Hardcoded to False in executor.submit()

**What goes wrong:** The `executor.submit()` call in `run_batch()` passes `False` for `no_crop` (line 698 in current pipeline.py). This is an existing bug/simplification — `--no-crop` flag does not actually exist in the codebase yet; the parameter is unused from the CLI side. Adding `verbose` as a new parameter must be done correctly; it cannot just be appended to the positional args list without checking the order.

**How to avoid:** When adding `verbose` to `process_tiff()`, use keyword arguments in `executor.submit()` to make the call explicit and avoid positional order errors.

```python
executor.submit(
    process_tiff,
    tiff_path,
    output_dir,
    lang,
    psm,
    padding,
    False,          # no_crop — hardcoded (no --no-crop flag exists yet)
    adaptive_threshold,
    verbose,        # NEW — Phase 6
)
```

### Pitfall 5: Adaptive Threshold Stage is Conditional — Timing Still Required

**What goes wrong:** The `adaptive_threshold` step only runs when `--adaptive-threshold` is set. If the timing brackets are placed naively, the `t_crop` measurement might accidentally include adaptive threshold time when it's enabled.

**How to avoid:** Stage boundaries per CONTEXT.md are: deskew, crop, OCR, write. Adaptive threshold happens between deskew and crop in the current code. The simplest correct approach: include adaptive threshold time in the `crop` stage measurement (it is a preprocessing step before crop detection). This is consistent with "all 4 stages always shown" (CONTEXT.md) — the crop stage absorbs adaptive threshold when active.

### Pitfall 6: Dry-Run Must Respect --force

**What goes wrong:** Implementing dry-run's skip-check without checking `args.force`. With `--force`, nothing should appear in the "would skip" list — all TIFFs appear in "would process".

**Why it happens:** `run_batch()` gates its skip-check on `if not force and out_path.exists()`. Dry-run must replicate the same logic, not invent a simpler version.

**How to avoid:** Copy the exact condition from `run_batch()`: `if not args.force and out_path.exists()`.

---

## Code Examples

Verified patterns from the existing codebase and stdlib:

### Argparse store_true (existing project pattern)
```python
# Source: pipeline.py main() — existing --force, --validate-only, --adaptive-threshold flags
parser.add_argument('--dry-run', action='store_true',
                    help='List TIFFs that would be processed and skipped, then exit')
parser.add_argument('--verbose', action='store_true',
                    help='Print per-stage timing and Tesseract output for each file')
```

### time.monotonic() stage brackets (extending existing pattern)
```python
# Source: pipeline.py process_tiff() — t0 = time.monotonic() already used
t_deskew_start = time.monotonic()
img, deskew_angle, deskew_fallback = deskew_image(img)
t_deskew = time.monotonic() - t_deskew_start
```

### subprocess.run for Tesseract capture (verbose mode only)
```python
# Source: Python docs subprocess.run — stdlib pattern
import subprocess
proc = subprocess.run(
    ['tesseract', str(tmp_path), 'stdout', '--psm', str(psm), '--dpi', str(dpi),
     '-l', lang, 'alto'],
    capture_output=True, text=True
)
tess_output = (proc.stdout + proc.stderr).strip()
```

### Dry-run pre-flight structure
```python
# In main(), after tiff_files = discover_tiffs(args.input):
if args.dry_run:
    would_process, would_skip = [], []
    for tiff_path in tiff_files:
        out_path = args.output / 'alto' / (tiff_path.stem + '.xml')
        if not args.force and out_path.exists():
            would_skip.append(tiff_path.name)
        else:
            would_process.append(tiff_path.name)
    print(f"Would process ({len(would_process)}):")
    for name in would_process:
        print(f"  {name}")
    print(f"Would skip ({len(would_skip)}):")
    for name in would_skip:
        print(f"  {name} (output exists)")
    print(f"Total: {len(would_process)} would be processed, {len(would_skip)} already done")
    sys.exit(0)
```

### Verbose block output (atomic print to minimize interleaving)
```python
# Construct as single string, one print() call per file
if verbose:
    lines = [
        f"  deskew: {t_deskew:.2f}s",
        f"  crop: {t_crop:.2f}s",
        f"  ocr: {t_ocr:.2f}s",
        f"  write: {t_write:.2f}s",
        f"  tesseract stdout/stderr:",
        f"    {tess_output if tess_output.strip() else ''}",
        "",
    ]
    print("\n".join(lines))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No diagnostic flags | `--dry-run` + `--verbose` | Phase 6 | Operators can inspect pipeline behavior without running OCR |
| Total-elapsed timing only | Per-stage timing (deskew/crop/ocr/write) | Phase 6 | Identifies bottleneck stage per file |
| No subprocess output visibility | Tesseract stdout/stderr printed in verbose mode | Phase 6 | Surfaces Tesseract warnings (language pack issues, OSD fallback, etc.) |

**Deprecated/outdated:**
- Nothing deprecated. This is a pure additive change.

---

## Open Questions

1. **How to capture Tesseract output without invoking it twice**
   - What we know: `pytesseract.image_to_alto_xml()` does not expose subprocess streams. Tesseract can be called via `subprocess.run()` with `capture_output=True`, but this requires managing a temp image file.
   - What's unclear: Whether `pytesseract.run_tesseract()` (internal API) provides a cleaner path without temp file management, and whether its return type changed across pytesseract versions.
   - Recommendation: In the plan, implement verbose Tesseract capture using `subprocess.run()` directly (write temp file, run tesseract, read alto output, capture stdout/stderr). This is explicit, version-stable, and avoids pytesseract internal API churn. `pytesseract` already writes a temp PNG internally anyway; the plan can use `tempfile.NamedTemporaryFile` for the verbose path.

2. **Stdout interleaving in verbose + parallel mode**
   - What we know: Worker stdout is forwarded to the terminal; no synchronization exists.
   - What's unclear: Whether users will encounter this in practice (most runs are sequential for debugging, or parallel for throughput but not typically with `--verbose`).
   - Recommendation: Document in CLI help that `--verbose --workers 1` gives clean sequential output. Build verbose block as single `print()` call to minimize (not eliminate) interleaving. No synchronization primitives needed.

3. **Whether to skip validate_tesseract() for dry-run**
   - What we know: Currently `validate_tesseract()` runs before OCR in `main()`. For `--dry-run`, no Tesseract invocation occurs.
   - What's unclear: Whether operators expect `--dry-run` to also validate Tesseract is installed, or whether they want pure filesystem inspection even without Tesseract.
   - Recommendation: Keep `validate_tesseract()` call before the dry-run gate. Dry-run should still fail fast if Tesseract is missing — it validates that the full run _would_ succeed, not just that files exist.

---

## Sources

### Primary (HIGH confidence)
- Python stdlib `argparse` docs — `action='store_true'` pattern, hyphen-to-underscore conversion
- Python stdlib `time.monotonic()` docs — wall-clock timing, monotonic guarantee
- `pipeline.py` source (direct read) — existing patterns for argparse, timing, `executor.submit()` call signatures, `no_crop` hardcoding
- `requirements.txt` (direct read) — confirmed no new packages needed
- `CLAUDE.md` (project instructions, injected via system-reminder) — architecture constraints, single-file pattern, `raise` requirement for workers

### Secondary (MEDIUM confidence)
- pytesseract PyPI page / source — `run_tesseract()` internal API exists; return type needs verification against installed 0.3.13 version
- Python `subprocess.run()` docs — `capture_output=True` is stable since Python 3.7

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; stdlib only
- Architecture: HIGH — patterns directly derived from reading existing pipeline.py code
- Pitfalls: HIGH — derived from direct code analysis (hardcoded `no_crop`, argparse hyphen conversion, pytesseract output capture limitation) and confirmed stdlib behavior

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable domain — stdlib + existing codebase; no fast-moving dependencies)
