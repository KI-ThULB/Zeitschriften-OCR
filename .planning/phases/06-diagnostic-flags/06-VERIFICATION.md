---
phase: 06-diagnostic-flags
verified: 2026-02-26T08:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 6: Diagnostic Flags Verification Report

**Phase Goal:** Operators can inspect what the pipeline will do and how it performs without reading source code
**Verified:** 2026-02-26T08:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Running with --dry-run prints a 'Would process (N):' section listing every TIFF that would run OCR, then a 'Would skip (N):' section listing every TIFF already done, then a summary count line, then exits with code 0 | VERIFIED | Lines 933-940: `print(f"Would process ({len(would_process)}):")`, `print(f"Would skip ({len(would_skip)}):")`, `print(f"Total: ...")`, `sys.exit(0)` |
| 2  | No ALTO XML files are written to the output directory when --dry-run is active | VERIFIED | Dry-run block at lines 923-940 calls `sys.exit(0)` before `run_batch()` is ever reached; `write_bytes()` is only inside `process_tiff()` which is never called |
| 3  | With --force combined, all TIFFs appear in 'Would process' and none appear in 'Would skip' | VERIFIED | Line 928: `if not args.force and out_path.exists()` — when `args.force=True` the condition is always False, so every TIFF lands in `would_process` |
| 4  | --dry-run combines cleanly with all existing flags without error | VERIFIED | argparse at lines 828-862 defines all flags independently; dry-run gate fires after all args are parsed and validated |
| 5  | --verbose is silently ignored when combined with --dry-run | VERIFIED | Dry-run block (lines 923-940) contains no reference to `verbose`; `sys.exit(0)` fires before `run_batch()` which is where verbose is first acted upon |
| 6  | Running with --verbose prints four indented timing lines (deskew, crop, ocr, write) after each file's result line, in seconds with 2 decimal places | VERIFIED | Lines 454-457: `f"  deskew: {t_deskew:.2f}s\n"`, `f"  crop: {t_crop:.2f}s\n"`, `f"  ocr: {t_ocr:.2f}s\n"`, `f"  write: {t_write:.2f}s\n"` |
| 7  | Running with --verbose prints a 'tesseract stdout/stderr:' block after the timing lines for each file, with actual Tesseract process output | VERIFIED | Lines 458-459: `f"  tesseract stdout/stderr:\n"` then `f"    {tess_display}"` where `tess_display` comes from `proc.stderr.decode()` captured via `subprocess.run()` |
| 8  | A blank line separates each file's verbose block for readability | VERIFIED | Line 462: `print()` after `print(verbose_block)` |
| 9  | All four timing stages are always printed, even when a stage is a near-zero passthrough | VERIFIED | Timing variables `t_deskew`, `t_crop`, `t_ocr`, `t_write` are always set before the verbose gate (lines 388-435); the `if verbose:` block unconditionally prints all four |
| 10 | --verbose combines cleanly with all existing flags without error | VERIFIED | `verbose` is a simple `bool` threaded as a positional arg through `run_batch()` → `executor.submit()` → `process_tiff()`; no flag interactions |
| 11 | Existing per-file result lines are unchanged — verbose output is purely additive | VERIFIED | Line 448: `print(f"{tiff_path.name} → {out_path} ({elapsed:.1f}s, {word_count} words)...")` unchanged; verbose block at lines 451-462 is appended after, inside `if verbose:` |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pipeline.py` (06-01) | Dry-run pre-flight scan and --dry-run argparse flag; contains `args.dry_run` | VERIFIED | `--dry-run` argparse flag at lines 850-855; pre-flight scan block at lines 923-940; `args.dry_run` gate at line 923 |
| `pipeline.py` (06-02) | Per-stage timing in `process_tiff()` and `--verbose` argparse flag; contains `verbose` | VERIFIED | `--verbose` at lines 856-861; `verbose` param in `process_tiff()` (line 359), `run_batch()` (line 724); timing at lines 388-435; `run_ocr()` `capture_output` at line 229 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main()` argparse block | dry-run pre-flight block in `main()` | `args.dry_run` boolean gate | WIRED | Line 923: `if args.dry_run:` fires after `discover_tiffs()` (line 915) and before `run_batch()` (line 943) |
| dry-run pre-flight | `discover_tiffs()` result | iterate `tiff_files`, replicate `run_batch()` skip-check condition `if not args.force and out_path.exists()` | WIRED | Lines 926-931 iterate `tiff_files` (same list from line 915); line 928 uses exact condition from `run_batch()` line 748 |
| `main()` argparse block | `run_batch()` verbose parameter | `args.verbose` passed through `run_batch()` into `executor.submit()` | WIRED | Line 946: `args.verbose` passed to `run_batch()`; line 773: `verbose` passed as positional arg in `executor.submit()` |
| `run_batch()` `executor.submit()` | `process_tiff()` verbose parameter | positional arg in `submit()` call | WIRED | Lines 764-774: `verbose` is 9th positional arg matching `process_tiff()` signature (line 351-360) |
| `process_tiff()` verbose gate | stdout timing block | `if verbose: print(...)` | WIRED | Line 451: `if verbose:` gates the entire verbose block; all four timing vars used at lines 454-457 |
| `run_ocr()` capture_output path | `subprocess.run()` tesseract invocation | `capture_output=True` → saves PIL image to tempfile, runs tesseract CLI directly | WIRED | Lines 246-268: `capture_output=True` branch saves PNG to `NamedTemporaryFile`, calls `subprocess.run(['tesseract', tmp_path, 'stdout', ...])`, returns `(alto_bytes, tess_text)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| OPER-01 | 06-01-PLAN.md | `--dry-run` flag lists every TIFF that would be processed and every TIFF that would be skipped, then exits without running OCR | SATISFIED | Lines 850-855 (argparse), 923-940 (pre-flight block): correct two-section output format, `sys.exit(0)`, no OCR invoked |
| OPER-02 | 06-02-PLAN.md | `--verbose` flag prints Tesseract stdout/stderr and per-stage wall-clock timing (deskew, crop, OCR, write) for each processed file | SATISFIED | Lines 856-861 (argparse), 388-462 (timing brackets + verbose block): four stages timed with `time.monotonic()`, Tesseract stderr captured via `subprocess.run()` |

**Orphaned requirements check:** REQUIREMENTS.md maps OPER-01 and OPER-02 to Phase 6. Both are claimed in PLAN frontmatter and verified above. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pipeline.py` | 44-45 | `# NEEDS empirical tuning` comments on `ADAPTIVE_BLOCK_SIZE` and `ADAPTIVE_C` | Info | Pre-existing from Phase 5; not introduced in Phase 6; no impact on diagnostic flags |

No Phase 6 anti-patterns detected. No TODOs, placeholders, empty implementations, or stub handlers introduced in this phase.

---

### Human Verification Required

#### 1. Dry-run output format with real TIFFs

**Test:** Run `python pipeline.py --input ./scans/ --output /tmp/testout --dry-run` with at least one real TIFF in `./scans/`.
**Expected:** Two-section output (`Would process (N):` / `Would skip (M):`), file names indented 2 spaces, `Total: N would be processed, M already done`, exit code 0, no files created in `/tmp/testout/alto/`.
**Why human:** Cannot verify exact stdout format and exit code against real file system state programmatically in this context.

#### 2. Verbose timing output with real OCR

**Test:** Run `python pipeline.py --input ./scans/ --output ./output --verbose --workers 1` with at least one real TIFF.
**Expected:** After each file's result line, four indented timing lines appear (`deskew: Xs`, `crop: Xs`, `ocr: Xs`, `write: Xs`), followed by `tesseract stdout/stderr:` block, then a blank line separator.
**Why human:** Requires actual Tesseract execution to verify the captured stderr output appears and that timing values are non-zero and plausible.

#### 3. --dry-run --verbose combination produces no verbose output

**Test:** Run `python pipeline.py --input ./scans/ --output /tmp/testout --dry-run --verbose`.
**Expected:** Only the standard two-section dry-run output; no timing lines, no `tesseract stdout/stderr:` section.
**Why human:** Requires real invocation to confirm the absence of verbose content at runtime.

---

### Gaps Summary

No gaps. All 11 observable truths verified against the codebase. Both OPER-01 and OPER-02 are fully implemented and wired. The phase goal — operators can inspect what the pipeline will do and how it performs without reading source code — is achieved through:

1. `--dry-run`: pre-flight scan correctly mirrors `run_batch()` skip-check logic, exits without writing files, integrates cleanly with `--force`.
2. `--verbose`: four-stage timing brackets in `process_tiff()`, Tesseract stderr capture via `subprocess.run()` in `run_ocr()`, verbose bool threaded correctly from `main()` through `run_batch()` into `executor.submit()` into `process_tiff()`.

The only items requiring human validation are runtime behavior checks that cannot be verified by static code analysis.

---

_Verified: 2026-02-26T08:00:00Z_
_Verifier: Claude (gsd-verifier)_
