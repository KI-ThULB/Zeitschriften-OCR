# Phase 3: Validation and Reporting - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Post-batch quality layer: validate each ALTO 2.1 XML output against the XSD schema, check word bounding box coordinates, and produce a per-run JSON summary report. This runs after OCR completes and gives the operator confidence before Goobi ingest. No changes to OCR logic, no new output formats beyond JSON.

</domain>

<decisions>
## Implementation Decisions

### Schema sourcing
- XSD bundled in the repo at `schemas/alto-2-1.xsd` — no network required at runtime
- Validate that the XSD is loadable at startup (before any TIFF is processed); fail fast with a clear error if the file is missing or corrupt
- If the XSD file is missing at runtime (e.g. deleted after startup check), skip validation, emit a warning, and continue — do not abort the batch

### Validation output
- Record first lxml validation error per file only (not all cascading errors)
- All violations (XSD and coordinate) go into the JSON summary report only — no separate violations log file
- Coordinate check: flag any element where `HPOS + WIDTH > page_width` OR `VPOS + HEIGHT > page_height` (strict — any bleed outside declared page bounds)
- Files with validation violations get status `ocr_ok, validation_warnings` — not failed, not silently ok. Operator decides whether to proceed with Goobi ingest.

### Report format and location
- Written to `output_dir/report_TIMESTAMP.json` — timestamped, alongside the JSONL error log, never overwritten
- Per-file record fields: `input_path`, `output_path`, `duration_seconds`, `word_count`, `error_status`, `schema_valid` (bool), `coord_violations` (list of violation description strings)
- Run-level summary at top of report: `total_files`, `processed`, `skipped`, `failed_ocr`, `validation_warnings`, `total_duration_seconds`
- Pretty-printed with 2-space indentation
- Report written only if at least one file was processed or validated (pure skip runs produce no report)

### Validation timing
- Separate post-processing pass after `run_batch()` completes — clean separation, OCR parallelism unaffected, validation pass can run independently
- `--validate-only` flag: skip OCR, validate existing output files and produce a report. Enables re-validation without re-running OCR.
- Final status line format: `Done: N processed, M skipped, P failed, Q validation warnings` — extends the existing Phase 2 format

### Claude's Discretion
- The lxml validator call pattern and error extraction from `etree.XMLSchema.error_log`
- Page dimension extraction from the ALTO `<Page>` element attributes
- How to handle ALTO files that are missing `<Page>` dimensions (probably skip coordinate check with a note)
- Exact structure of `coord_violations` entries (likely `"HPOS+WIDTH=X > page_width=Y at String CONTENT"`)

</decisions>

<specifics>
## Specific Ideas

- The `schemas/alto-2-1.xsd` should be committed directly to the repo — no download script needed
- The report is the operator's single source of truth before Goobi ingest: OCR errors + validation warnings all in one place
- `--validate-only` is a power-user flag for re-validation after schema updates or manual ALTO edits

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-validation-and-reporting*
*Context gathered: 2026-02-24*
