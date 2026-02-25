# Phase 6: Diagnostic Flags - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add two new CLI flags to the existing batch pipeline:
- `--dry-run`: preview which TIFFs would be processed and which would be skipped, then exit without running OCR
- `--verbose`: print Tesseract stdout/stderr and per-stage wall-clock timing (deskew, crop, OCR, write) for each processed file

Both flags must combine cleanly with all existing flags (`--force`, `--lang`, `--workers`, `--padding`, `--psm`, `--adaptive-threshold`). No changes to OCR pipeline logic, output format, or validation behavior.

</domain>

<decisions>
## Implementation Decisions

### Dry-run output format
- Display two labeled sections in order:
  1. `Would process (N):` — list of TIFFs that would run OCR
  2. `Would skip (N):` — list of TIFFs that already have output
- Each file shown as filename only (not full path)
- Would-skip entries include a brief reason: e.g., `scan_001.tif (output exists)`
- A summary count line at the end: e.g., `Total: 47 would be processed, 12 already done`
- Output goes to stdout; exit code 0; no files written to output directory
- `--force` affects dry-run skip logic — with `--force`, all TIFFs appear in the would-process list (mirrors actual `--force` behavior)
- `--verbose` is silently ignored when combined with `--dry-run` (no OCR runs = nothing for verbose to report)

### Verbose timing format
- Four separate indented lines printed after the filename line for each file:
  ```
  scan_001.tif
    deskew: 0.12s
    crop: 0.05s
    ocr: 2.31s
    write: 0.01s
  ```
- Time unit: seconds with 2 decimal places (e.g., `2.31s`)
- All 4 stages always shown even when a stage was a near-zero passthrough (consistent output structure)
- Blank line between each file's verbose block for readability
- All verbose output to stdout

### Tesseract output presentation
- Tesseract stdout/stderr always printed in `--verbose` mode, even if empty
- Format: labeled header line followed by indented content:
  ```
    tesseract stdout/stderr:
      [tesseract output here, or blank if empty]
  ```
- Tesseract block appears after timing lines for each file
- Blank line between files

### --dry-run + --verbose combination and existing output
- `--verbose` silently ignored when `--dry-run` is active
- Existing per-file result lines (e.g., `Processed: scan_001.tif`) stay unchanged — verbose adds new lines before/after, does not modify or replace existing output
- `--verbose` adds timing block + tesseract block after each file's result line

### Claude's Discretion
- Exact indentation depth (2 or 4 spaces) for timing and tesseract sub-lines
- How to handle Tesseract output that has only whitespace (treat as empty or print as-is)
- Whether to flush stdout after each file's verbose block in parallel mode

</decisions>

<specifics>
## Specific Ideas

- Dry-run output should feel like a checklist operators can review before committing to a long run
- Verbose timing is for diagnosing which stage is the bottleneck (deskew vs OCR)
- Empty Tesseract output block is informative (confirms Tesseract ran cleanly with no warnings)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-diagnostic-flags*
*Context gathered: 2026-02-25*
