---
phase: 03-validation-and-reporting
plan: "02"
subsystem: reporting
tags: [json, reporting, alto, validation, argparse, pipeline]

# Dependency graph
requires:
  - phase: 03-validation-and-reporting
    plan: "01"
    provides: "load_xsd(), validate_batch(), validate_alto_file() in pipeline.py; schemas/alto-2-1.xsd bundled"
provides:
  - write_report() — writes output_dir/report_TIMESTAMP.json with summary + files keys (2-space indent)
  - run_batch() returns 4-tuple (processed, skipped, errors, file_records) instead of 3-tuple
  - main() wires validate_batch() + write_report() after OCR completes
  - --validate-only flag for post-OCR-only validation and reporting mode
affects:
  - pipeline.py callers expecting 3-tuple from run_batch() — must unpack 4 values

# Tech tracking
tech-stack:
  added: []
  patterns:
    - write_report() called only when file_records is non-empty — pure skip runs produce no report file
    - XSD loaded once at startup in main(); compiled object passed into validate_batch()
    - validate-only mode builds skeleton file_records from alto/*.xml glob, then calls validate_batch() + write_report()
    - validation_warnings initialised to 0 before if-block so summary line always has the variable defined

key-files:
  created: []
  modified:
    - pipeline.py

key-decisions:
  - "write_report() placed in Validation section before run_batch() — keeps dependency order (run_batch uses it indirectly via main)"
  - "file_records is empty for pure-skip runs — guard `if file_records:` ensures no report written, matching CONTEXT.md decision"
  - "validate_warnings = 0 set before the if-block — ensures the summary print always has the variable even when file_records is empty"
  - "--validate-only skips discover_tiffs() entirely — it globs alto/*.xml directly from output dir"
  - "import time as _time inside main() — avoids name collision with top-level `import time` used by process_tiff()"

patterns-established:
  - "4-tuple return pattern: run_batch() returns (processed, skipped, errors, file_records)"
  - "Post-OCR validation decoupled: validate_batch() runs after run_batch() in main(), not inside worker processes"

requirements-completed: [VALD-03]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 3 Plan 02: Validation Wiring and JSON Reporting Summary

**write_report() added to pipeline.py with 4-tuple run_batch() return, post-OCR validate_batch() pass in main(), and --validate-only mode producing output_dir/report_TIMESTAMP.json**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T07:17:35Z
- **Completed:** 2026-02-25T07:19:36Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Extended run_batch() to return a 4-tuple including per-file records, with success records (word_count read from written ALTO file) and failure records (error_status='failed')
- Added write_report() in the Validation section producing a JSON report with "summary" and "files" keys, pretty-printed with 2-space indent
- Updated main() to: load XSD at startup, unpack 4-tuple from run_batch(), run validate_batch() post-OCR, call write_report() when file_records is non-empty, and print extended status line with validation warnings count
- Implemented --validate-only mode: globs alto/*.xml from output directory, builds skeleton records, validates, writes report, exits cleanly
- Smoke-tested --validate-only against existing output/alto/144528908_0019.xml — validated 1 file with 0 warnings, report written with correct JSON structure

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend run_batch() to return file_records and add write_report()** - `63ef92e` (feat)
2. **Task 2: Wire validation pass, write_report(), and --validate-only into main()** - `4c08a3d` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `pipeline.py` - Extended run_batch() to 4-tuple; added write_report() before run_batch(); updated main() with XSD startup load, --validate-only handler, post-OCR validation pass, report writing, and extended summary line

## Decisions Made

- `write_report()` placed before `run_batch()` in source order to maintain dependency ordering (both are in the Validation section)
- `validation_warnings = 0` initialised before the `if file_records:` guard — ensures the summary print line always has the variable defined even when file_records is empty (pure skip run)
- `--validate-only` mode globs `alto/*.xml` from the output directory directly rather than re-reading `--input` — consistent with the plan's intent of validating existing ALTO output
- `import time as _time` used inside main() to avoid shadowing the top-level `import time` that `process_tiff()` depends on
- Report not written for pure-skip runs (file_records is empty) — matches CONTEXT.md decision documented in STATE.md

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 is now complete: XSD validation (03-01) and JSON reporting (03-02) both done
- All VALD requirements (VALD-01, VALD-02, VALD-03) satisfied
- pipeline.py ready for Phase 4 (if applicable) — the validation and reporting infrastructure is stable and non-breaking for existing callers

## Self-Check: PASSED

- FOUND: pipeline.py (modified, with write_report() and updated main())
- FOUND commit 63ef92e (Task 1: run_batch 4-tuple + write_report)
- FOUND commit 4c08a3d (Task 2: main() wiring)
- VERIFIED: `python -c "from pipeline import run_batch, write_report, validate_batch, load_xsd; print('all imports OK')"` passes
- VERIFIED: `python pipeline.py --help` shows `--validate-only` flag
- VERIFIED: smoke test `python pipeline.py --output ./output --validate-only` produces report with correct JSON structure

---
*Phase: 03-validation-and-reporting*
*Completed: 2026-02-25*
