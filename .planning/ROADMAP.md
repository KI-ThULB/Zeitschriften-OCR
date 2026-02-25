# Roadmap: Zeitschriften-OCR

## Milestones

- ✅ **v1.0 Single-File Pipeline** — Phase 1 (shipped 2026-02-24)
- 📋 **v1.1 Batch Processor** — Phases 2–3 (planned)

## Phases

<details>
<summary>✅ v1.0 Single-File Pipeline — SHIPPED 2026-02-24</summary>

- [x] Phase 1: Single-File Pipeline (2/2 plans) — completed 2026-02-24

See archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 📋 v1.1 Batch Processor (Planned)

- [x] **Phase 2: Batch Orchestration and CLI** - Process a full folder in parallel with skip logic, error isolation, and full CLI (completed 2026-02-24)
- [ ] **Phase 3: Validation and Reporting** - Validate all output and produce per-run summary reports

#### Phase 2: Batch Orchestration and CLI
**Goal**: The tool processes a full folder of TIFFs in parallel, skips already-processed files on rerun, isolates per-file errors, and exposes a complete CLI surface
**Depends on**: Phase 1
**Requirements**: BATC-01, BATC-02, BATC-03, BATC-04, CLI-01, CLI-02, CLI-03, CLI-04, CLI-05
**Success Criteria** (what must be TRUE):
  1. Running `python pipeline.py --input DIR --output DIR` processes all TIFFs in the input folder and writes ALTO XML to the output folder
  2. Rerunning the same command skips TIFFs that already have ALTO XML output; passing `--force` reprocesses them
  3. A TIFF that raises an error during processing does not abort the batch — remaining files continue and complete
  4. A run error log is written recording each failed file's path, exception type, error message, and stack trace
  5. At startup, the tool validates that Tesseract is installed and the requested language pack is available, exiting with a clear error message if either is missing
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Fix critical bugs (sys.exit in worker, schemaLocation) + add validate_tesseract, discover_tiffs, write_error_log helpers
- [ ] 02-02-PLAN.md — Add run_batch() orchestrator + rewrite main() for full batch CLI

#### Phase 3: Validation and Reporting
**Goal**: Every ALTO output file is validated against the ALTO 2.1 XSD schema and a per-run JSON summary report is written, giving the operator confidence in the batch before Goobi ingest
**Depends on**: Phase 2
**Requirements**: VALD-01, VALD-02, VALD-03
**Success Criteria** (what must be TRUE):
  1. Each ALTO output file is validated against the ALTO 2.1 XSD schema; violations are logged per file without aborting the batch
  2. Each ALTO file is checked for word bounding boxes that exceed the page dimensions; violations are logged per file without aborting
  3. After a batch run, a JSON summary report exists containing for each file: input path, output path, processing duration (seconds), word count, and error status
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Bundle namespace-adapted ALTO 2.1 XSD + add load_xsd(), validate_alto_file(), _check_coordinates(), validate_batch() to pipeline.py
- [ ] 03-02-PLAN.md — Extend run_batch() to collect per-file records, add write_report(), wire validation pass and --validate-only into main()

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Single-File Pipeline | v1.0 | 2/2 | Complete | 2026-02-24 |
| 2. Batch Orchestration and CLI | 2/2 | Complete   | 2026-02-24 | - |
| 3. Validation and Reporting | 1/2 | In Progress|  | - |
